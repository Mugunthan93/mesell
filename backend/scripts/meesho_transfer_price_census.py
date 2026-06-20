"""Full census — getTransferPrice for ALL ~3,772 leaf categories.

One call per category at price=100. Incremental + resumable:
  - Output: logs/scraper/transfer_price_census.jsonl  (append, one JSON object per line)
  - On restart: reads the JSONL, skips sscat_ids already present
  - Sanity gate: sscat_id=10949 @ price=100 must return transfer_price=85.06

Contract (founder-decoded, round-14 verified):
  POST https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getTransferPrice
  Body:   {"sscat_id":<leaf_id>, "gst_percentage":null, "price":100,
           "supplier_id":4359160, "duplicate_pid":null, "gst_type":"ENROLMENT"}
  Headers: identifier=oinpw, client-type=d-web, client-package-version=1.0.1,
           supplier-id=4359160, content-type=application/json;charset=UTF-8

Safety: compute-API ONLY. No listing, no image, no Submit, no go-live.
Pace: ~1 call per 2.5s. Hard stop on 401/403/429/463.
No OTP this run (password-only per founder ruling).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from playwright.async_api import (
    APIResponse,
    BrowserContext,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

# ---------------------------------------------------------------------------
# Paths / constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS_FILE = PROJECT_ROOT / ".meesho_creds.env"
LOG_DIR = PROJECT_ROOT / "logs" / "scraper"
CATEGORY_TREE_FILE = PROJECT_ROOT / "backend" / "app" / "data" / "meesho_category_tree.json"

# Incremental output (JSONL — one JSON object per line)
CENSUS_JSONL = LOG_DIR / "transfer_price_census.jsonl"
# Final summary JSON written on completion
CENSUS_SUMMARY_JSON = LOG_DIR / "transfer_price_census_summary.json"
# Storage state from round-14 — try to reuse warm session
STORAGE_STATE_FILE = LOG_DIR / "meesho_storage_state.json"

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
API_BASE = "https://supplier.meesho.com/api"
TRANSFER_PRICE_URL = f"{API_BASE}/cataloging/singleCatalogUpload/getTransferPrice"

LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000
API_TIMEOUT_MS = 30_000
INTER_CALL_SLEEP = 2.5  # seconds between API calls — keeps us at 1 req/2.5s

# Hard-stop HTTP codes (scoped to supplier.meesho.com/api on the TARGET endpoint only)
# 463 = Meesho "Token missing" — only fatal on getTransferPrice itself, not on
# background registration/config XHRs that fire during login page load before auth.
SESSION_STOP_CODES = {401, 429}  # codes that stop on ANY API URL
TRANSFER_PRICE_STOP_CODES = {401, 403, 429, 463}  # codes that stop ONLY on getTransferPrice

# Background XHR paths that are allowed to return 403/463 without triggering a hard stop
# (these fire before auth is established during SPA initialisation)
IGNORE_STOP_URL_PATTERNS = [
    "fetch-registration-status",
    "supplier/config",
    "prefetch-supply-data",
    "fetch-unread-count",
    "fetch-total-count",
    "live-optin-event",
    "fetch-stepper-journey",
    "fetch-web-popup",
]

# Sanity gate
CONTROL_SSCAT_ID = 10949
CONTROL_PRICE = 100
CONTROL_EXPECTED_TRANSFER_PRICE = 85.06
SANITY_TOLERANCE = 0.10

# Census price point
CENSUS_PRICE = 100

# Supplier identity
SUPPLIER_ID = 4359160
IDENTIFIER = "oinpw"

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------
_hard_stop: list[str] = []
_account: dict[str, Any] = {}

log = logging.getLogger("meesho-census")

OTP_CODE_RE = re.compile(r"\b(\d{6})\b")


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
def configure_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"transfer_price_census_{ts}.log"
    logger = logging.getLogger("meesho-census")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    fh = logging.FileHandler(log_path)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    logger.propagate = False
    logger.info("Log: %s", log_path)
    logger.info("Census JSONL: %s", CENSUS_JSONL)


# ---------------------------------------------------------------------------
# Credentials
# ---------------------------------------------------------------------------
def load_creds() -> tuple[str, str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Creds missing: {CREDS_FILE}")
    load_dotenv(CREDS_FILE, override=True)
    u = os.environ.get("MEESHO_USERNAME", "").strip()
    p = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not u or not p:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    return u, p


# ---------------------------------------------------------------------------
# Category tree: extract all 3,772 leaf sscat_ids
# ---------------------------------------------------------------------------
def load_leaf_categories() -> list[dict[str, Any]]:
    """Load the category tree and return list of {sscat_id, leaf_name, path_str}."""
    with open(CATEGORY_TREE_FILE) as f:
        tree = json.load(f)
    categories = tree.get("categories", [])
    leaves = []
    for cat in categories:
        leaf_id_raw = cat.get("leaf_id")
        if not leaf_id_raw:
            continue
        try:
            sscat_id = int(leaf_id_raw)
        except (ValueError, TypeError):
            log.warning("Skipping non-integer leaf_id: %s", leaf_id_raw)
            continue
        leaf_name = cat.get("leaf_name", "")
        path = cat.get("path", [])
        path_str = " > ".join(path) if isinstance(path, list) else str(path)
        leaves.append({
            "sscat_id": sscat_id,
            "leaf_name": leaf_name,
            "path_str": path_str,
        })
    # Sort by sscat_id for deterministic ordering
    leaves.sort(key=lambda x: x["sscat_id"])
    log.info("Loaded %d leaf categories from tree", len(leaves))
    return leaves


# ---------------------------------------------------------------------------
# Resume: read existing JSONL to find already-done sscat_ids
# ---------------------------------------------------------------------------
def load_already_done() -> set[int]:
    """Return set of sscat_ids already in the census JSONL (completed results)."""
    done: set[int] = set()
    if not CENSUS_JSONL.exists():
        return done
    with open(CENSUS_JSONL) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                sid = obj.get("sscat_id")
                # Only count as done if it has a real result (not just error)
                if sid is not None and obj.get("transfer_price") is not None:
                    done.add(int(sid))
                elif sid is not None and obj.get("error"):
                    # Also count errors as done (don't retry)
                    done.add(int(sid))
            except Exception:
                pass
    log.info("Resume: %d sscat_ids already in JSONL", len(done))
    return done


# ---------------------------------------------------------------------------
# Incremental append: write one result line to JSONL
# ---------------------------------------------------------------------------
def append_result(result: dict[str, Any]) -> None:
    with open(CENSUS_JSONL, "a") as f:
        f.write(json.dumps(result, default=str) + "\n")


# ---------------------------------------------------------------------------
# Response listener (account data + hard-stop detection)
# ---------------------------------------------------------------------------
async def on_response(resp: Response) -> None:
    url = resp.url
    status = resp.status

    # Only trigger hard stop on session-critical codes for real API paths
    # Ignore known infrastructure URLs that return 463/403 before auth is fully established
    if "supplier.meesho.com/api" in url:
        is_ignored_path = any(pat in url for pat in IGNORE_STOP_URL_PATTERNS)
        if not is_ignored_path and status in SESSION_STOP_CODES:
            _hard_stop.append(f"HTTP {status} on {url.split('?')[0]}")
            log.error("HARD-STOP triggered: HTTP %d on %s", status, url.split("?")[0])
            return
        if is_ignored_path and status in (403, 463):
            log.debug("Tolerated HTTP %d on background path %s", status, url.split("?")[0])

    ct = (resp.headers or {}).get("content-type", "")
    if "json" not in ct:
        return
    try:
        body = await resp.json()
    except Exception:
        return

    if ("prefetch-supply-data" in url or "registration-status" in url
            or "supplier/config" in url):
        _walk_account(body)


def _walk_account(body: Any) -> None:
    stack = [body]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                kl = k.lower()
                if kl in ("supplier_id", "supplierid") and not _account.get("supplier_id"):
                    _account["supplier_id"] = v
                if (kl in ("identifier", "supplier_identifier") and isinstance(v, str)
                        and v and len(v) < 24 and not _account.get("identifier")):
                    _account["identifier"] = v
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)


# ---------------------------------------------------------------------------
# Login (password only — NO OTP per founder ruling)
# ---------------------------------------------------------------------------
async def _first(page: Page, cands: list, timeout: int = 5000):
    for build in cands:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


async def detect_otp_page(page: Page) -> bool:
    """Return True if we're on an OTP page."""
    try:
        txt = await page.locator("body").inner_text(timeout=3000)
        if re.search(r"\b(otp|one.time.password|verify your (mobile|number)|"
                     r"enter the (otp|code)|verification code|6.digit)\b", txt, re.I):
            return True
        inputs = page.locator("input[maxlength='6'], input[autocomplete='one-time-code'],"
                              " input[name*='otp' i], input[id*='otp' i]")
        if await inputs.count() > 0:
            return True
    except Exception:
        pass
    return False


async def perform_login(page: Page, username: str, password: str) -> None:
    log.info("Navigating to login URL")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await asyncio.sleep(2.5)

    user_field = await _first(page, [
        lambda: page.get_by_placeholder(re.compile(r"email.*mobile|mobile.*email", re.I)),
        lambda: page.get_by_role("textbox", name=re.compile(r"email|mobile|phone", re.I)),
        lambda: page.locator("input[type='text']").first,
    ])
    if user_field is None:
        raise RuntimeError("Cannot locate username field on login page")
    await user_field.fill(username)
    await asyncio.sleep(1.0)

    pwd_field = await _first(page, [
        lambda: page.get_by_placeholder(re.compile(r"password", re.I)),
        lambda: page.locator("input[type='password']").first,
    ])
    if pwd_field is None:
        raise RuntimeError("Cannot locate password field on login page")
    await pwd_field.fill(password)
    await asyncio.sleep(1.0)

    submit_btn = await _first(page, [
        lambda: page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ])
    if submit_btn is None:
        raise RuntimeError("Cannot locate login submit button")
    await submit_btn.click()
    await asyncio.sleep(4.0)

    # OTP detection — STOP immediately if OTP page (per founder ruling)
    for _ in range(3):
        if await detect_otp_page(page):
            raise RuntimeError(
                "OTP_REQUIRED — halted per no-OTP ruling. "
                f"Got as far as: login submitted, now on OTP page at {page.url}"
            )
        if "login" not in page.url.lower():
            break
        await asyncio.sleep(2.0)

    if "login" in page.url.lower():
        try:
            await page.wait_for_url(lambda u: "login" not in u, timeout=20_000)
        except PlaywrightTimeoutError:
            raise RuntimeError("Login did not redirect — check creds or possible OTP block")

    log.info("Login OK — now at: %s", page.url.split("?")[0])


# ---------------------------------------------------------------------------
# Headers for getTransferPrice
# ---------------------------------------------------------------------------
def _transfer_price_headers() -> dict[str, str]:
    return {
        "identifier": IDENTIFIER,
        "client-type": "d-web",
        "client-package-version": "1.0.1",
        "supplier-id": str(SUPPLIER_ID),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
    }


# ---------------------------------------------------------------------------
# Single getTransferPrice call
# ---------------------------------------------------------------------------
async def call_transfer_price(
    ctx: BrowserContext, sscat_id: int, price: int
) -> dict[str, Any] | None:
    body = {
        "sscat_id": sscat_id,
        "gst_percentage": None,
        "price": price,
        "supplier_id": SUPPLIER_ID,
        "duplicate_pid": None,
        "gst_type": "ENROLMENT",
    }
    try:
        resp: APIResponse = await ctx.request.post(
            TRANSFER_PRICE_URL,
            headers=_transfer_price_headers(),
            data=body,
            timeout=API_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        log.warning("getTransferPrice sscat=%d TIMEOUT", sscat_id)
        return None
    except Exception as exc:
        log.warning("getTransferPrice sscat=%d error: %s", sscat_id, exc)
        return None

    status = resp.status

    # 463 = Meesho "Token missing" — only fatal when directly calling getTransferPrice
    if status in TRANSFER_PRICE_STOP_CODES:
        _hard_stop.append(f"HTTP {status} on getTransferPrice sscat={sscat_id}")
        log.error("HARD-STOP: HTTP %d on getTransferPrice sscat=%d", status, sscat_id)
        return None

    try:
        rbody = await resp.json()
    except Exception:
        text = await resp.text()
        log.warning("sscat=%d non-JSON (HTTP %d): %s", sscat_id, status, text[:300])
        return None

    if not isinstance(rbody, dict) or not rbody:
        log.warning("sscat=%d empty/non-dict response: %s", sscat_id, str(rbody)[:200])
        return None

    return rbody


# ---------------------------------------------------------------------------
# Formula verification
# ---------------------------------------------------------------------------
def verify_formula(price: int, row: dict[str, Any]) -> dict[str, Any]:
    shipping = float(row.get("shipping_charges", 0) or 0)
    commission_fees = float(row.get("commission_fees", 0) or 0)
    gst_price = float(row.get("gst_price", 0) or 0)
    tds = float(row.get("tds", 0) or 0)
    tcs = float(row.get("tcs", 0) or 0)
    transfer_price = float(row.get("transfer_price", 0) or 0)
    total_price = float(row.get("total_price", 0) or 0)

    computed_total = price + shipping
    computed_gst = round(0.18 * shipping, 2)
    computed_tds = round(0.001 * computed_total, 2)
    computed_transfer = round(price - commission_fees - computed_gst - computed_tds - tcs, 2)

    tol = 0.05
    formula_ok = (
        abs(computed_total - total_price) < tol
        and abs(computed_gst - gst_price) < tol
        and abs(computed_tds - tds) < tol
        and abs(computed_transfer - transfer_price) < tol
    )
    return {
        "formula_ok": formula_ok,
        "delta_total": round(computed_total - total_price, 4),
        "delta_gst": round(computed_gst - gst_price, 4),
        "delta_tds": round(computed_tds - tds, 4),
        "delta_transfer": round(computed_transfer - transfer_price, 4),
    }


# ---------------------------------------------------------------------------
# Main run
# ---------------------------------------------------------------------------
async def run() -> None:
    configure_logging()
    user, pwd = load_creds()

    log.info("=== MeeSell Full Census: getTransferPrice for all ~3,772 leaf categories ===")
    log.info("Account: %s*** / supplier_id=%d / identifier=%s",
             user[:4], SUPPLIER_ID, IDENTIFIER)
    log.info("Contract: price=%d (single point), pace=%.1fs per call", CENSUS_PRICE, INTER_CALL_SLEEP)

    # Load all leaf categories
    all_leaves = load_leaf_categories()
    log.info("Total leaves in tree: %d", len(all_leaves))

    # Resume: find already-done
    already_done = load_already_done()
    remaining = [leaf for leaf in all_leaves if leaf["sscat_id"] not in already_done]
    log.info("Already done: %d  |  Remaining: %d  |  Total: %d",
             len(already_done), len(remaining), len(all_leaves))

    if not remaining:
        log.info("All categories already done — nothing to run. Generating summary.")
        generate_summary(all_leaves)
        return

    # Estimate time
    est_mins = len(remaining) * INTER_CALL_SLEEP / 60
    log.info("Estimated time for remaining %d: %.0f minutes (%.1f hours)",
             len(remaining), est_mins, est_mins / 60)

    done_this_run = 0
    errors_this_run = 0
    hard_stop_at: str | None = None

    async with async_playwright() as pw:
        # Try to reuse warm session (storage_state from prior run)
        warm_session_used = False
        storage_state: Any = None
        if STORAGE_STATE_FILE.exists():
            try:
                storage_state = json.loads(STORAGE_STATE_FILE.read_text())
                log.info("Warm storage_state loaded from %s — will try session reuse", STORAGE_STATE_FILE)
            except Exception as e:
                log.warning("Could not load storage_state: %s — will do fresh login", e)
                storage_state = None

        browser = await pw.webkit.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 1000},
            storage_state=storage_state,
        )
        ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
        ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)
        ctx.on("response", lambda r: asyncio.create_task(on_response(r)))

        try:
            page = await ctx.new_page()

            # ------------------------------------------------------------------
            # Login (or session verification)
            # ------------------------------------------------------------------
            await perform_login(page, user, pwd)
            await asyncio.sleep(3.0)

            if _hard_stop:
                hard_stop_at = f"at login: {_hard_stop}"
                log.error("Hard stop at login: %s", _hard_stop)
                return

            log.info("Account state after login XHRs: %s", _account)

            # ------------------------------------------------------------------
            # Save storage state for future warm reuse
            # ------------------------------------------------------------------
            try:
                state = await ctx.storage_state()
                STORAGE_STATE_FILE.write_text(json.dumps(state))
                log.info("Storage state saved to %s for future warm reuse", STORAGE_STATE_FILE)
            except Exception as e:
                log.warning("Could not save storage state: %s", e)

            # ------------------------------------------------------------------
            # SANITY GATE
            # ------------------------------------------------------------------
            log.info("=== SANITY GATE: sscat=%d @ price=%d ===", CONTROL_SSCAT_ID, CONTROL_PRICE)
            sanity_resp = await call_transfer_price(ctx, CONTROL_SSCAT_ID, CONTROL_PRICE)
            await asyncio.sleep(INTER_CALL_SLEEP)

            if _hard_stop:
                hard_stop_at = f"at sanity gate: {_hard_stop}"
                log.error("Hard stop at sanity gate: %s", _hard_stop)
                return

            if sanity_resp is None:
                log.error("SANITY GATE FAILED: null response for control sscat=%d. STOPPING.",
                          CONTROL_SSCAT_ID)
                return

            actual_tp = float(sanity_resp.get("transfer_price", 0) or 0)
            delta = abs(actual_tp - CONTROL_EXPECTED_TRANSFER_PRICE)
            if delta > SANITY_TOLERANCE:
                log.error("SANITY GATE FAILED: transfer_price=%.4f expected=%.2f delta=%.4f. "
                          "STOPPING — contract may have changed.",
                          actual_tp, CONTROL_EXPECTED_TRANSFER_PRICE, delta)
                log.error("Full response: %s", json.dumps(sanity_resp, default=str))
                return

            log.info("SANITY GATE PASSED: transfer_price=%.4f (expected %.2f, delta=%.4f)",
                     actual_tp, CONTROL_EXPECTED_TRANSFER_PRICE, delta)

            # Record control in JSONL if not already there
            if CONTROL_SSCAT_ID not in already_done:
                ctrl_row = {
                    "sscat_id": CONTROL_SSCAT_ID,
                    "leaf_name": "Extension Chords",
                    "path_str": "Appliances > Small appliances > Home Appliances > Extension Chords",
                    "price": CONTROL_PRICE,
                    "sanity_control": True,
                    **{k: sanity_resp.get(k) for k in [
                        "commission_percentage", "commission_fees", "shipping_charges",
                        "gst_price", "tds", "tcs", "transfer_price", "total_price",
                    ]},
                    "formula_check": verify_formula(CONTROL_PRICE, sanity_resp),
                }
                append_result(ctrl_row)
                already_done.add(CONTROL_SSCAT_ID)
                done_this_run += 1
                log.info("Control row recorded.")

            # ------------------------------------------------------------------
            # Main census loop
            # ------------------------------------------------------------------
            total_leaves = len(all_leaves)
            for i, leaf in enumerate(remaining):
                if _hard_stop:
                    hard_stop_at = f"sscat={leaf['sscat_id']} ({leaf['leaf_name']}): {_hard_stop}"
                    log.error("Hard stop mid-census at sscat=%d: %s", leaf["sscat_id"], _hard_stop)
                    break

                sscat_id = leaf["sscat_id"]

                # Already done check (may have been added this run via control)
                if sscat_id in already_done:
                    continue

                resp = await call_transfer_price(ctx, sscat_id, CENSUS_PRICE)
                await asyncio.sleep(INTER_CALL_SLEEP)

                total_done_so_far = len(already_done) + done_this_run
                progress_pct = total_done_so_far / total_leaves * 100

                if _hard_stop:
                    hard_stop_at = f"sscat={sscat_id} ({leaf['leaf_name']}): {_hard_stop}"
                    log.error("Hard stop: %s", hard_stop_at)
                    if resp:
                        row = _build_row(leaf, resp)
                        append_result(row)
                        done_this_run += 1
                    break

                if resp is None:
                    err_row = {
                        "sscat_id": sscat_id,
                        "leaf_name": leaf["leaf_name"],
                        "path_str": leaf["path_str"],
                        "price": CENSUS_PRICE,
                        "error": "null_response",
                    }
                    append_result(err_row)
                    errors_this_run += 1
                    already_done.add(sscat_id)
                    log.warning("sscat=%d error=null_response (errors=%d so far)",
                                sscat_id, errors_this_run)
                else:
                    row = _build_row(leaf, resp)
                    append_result(row)
                    done_this_run += 1
                    already_done.add(sscat_id)

                    if done_this_run % 50 == 0:
                        log.info(
                            "Progress: %d done this run | %d total done | %.1f%% of %d | "
                            "errors=%d | last: sscat=%d %s",
                            done_this_run, len(already_done), progress_pct,
                            total_leaves, errors_this_run, sscat_id, leaf["leaf_name"],
                        )

        except RuntimeError as exc:
            log.error("Runtime error: %s", exc)
            if "OTP_REQUIRED" in str(exc):
                print(f"\nOTP_REQUIRED — halted per no-OTP ruling. Details: {exc}", flush=True)
                return
            raise
        except Exception as exc:
            log.exception("Unexpected error: %s", exc)
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Run summary
    # ------------------------------------------------------------------
    total_done = len(load_already_done())  # re-read to get accurate count
    log.info("=== RUN COMPLETE ===")
    log.info("Done this run: %d (errors: %d)", done_this_run, errors_this_run)
    log.info("Total in JSONL: %d / %d", total_done, len(all_leaves))
    log.info("Hard stops: %s", _hard_stop or "none")

    if total_done >= len(all_leaves) - 1:  # allow 1 slack for duplicates
        log.info("Census COMPLETE — all categories covered. Generating summary.")
        generate_summary(all_leaves)
    else:
        remaining_count = len(all_leaves) - total_done
        log.info("Census INCOMPLETE — %d categories remaining. Resume by re-running this script.",
                 remaining_count)
        print_partial_report(total_done, len(all_leaves), hard_stop_at)


def _build_row(leaf: dict[str, Any], resp: dict[str, Any]) -> dict[str, Any]:
    return {
        "sscat_id": leaf["sscat_id"],
        "leaf_name": leaf["leaf_name"],
        "path_str": leaf["path_str"],
        "price": CENSUS_PRICE,
        **{k: resp.get(k) for k in [
            "commission_percentage", "commission_fees", "shipping_charges",
            "gst_price", "tds", "tcs", "transfer_price", "total_price",
        ]},
        "formula_check": verify_formula(CENSUS_PRICE, resp),
    }


# ---------------------------------------------------------------------------
# Summary generation (run when census is complete)
# ---------------------------------------------------------------------------
def generate_summary(all_leaves: list[dict[str, Any]]) -> None:
    log.info("Generating summary from %s ...", CENSUS_JSONL)
    rows = []
    with open(CENSUS_JSONL) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except Exception:
                pass

    data_rows = [r for r in rows if r.get("transfer_price") is not None]
    error_rows = [r for r in rows if r.get("error")]

    # Commission analysis
    non_zero_commission = [
        r for r in data_rows
        if float(r.get("commission_percentage", 0) or 0) != 0.0
    ]

    # Shipping distribution
    ship_vals = [float(r.get("shipping_charges", 0) or 0) for r in data_rows]
    ship_sorted = sorted(ship_vals)
    ship_min = min(ship_vals) if ship_vals else None
    ship_max = max(ship_vals) if ship_vals else None
    ship_unique = sorted(set(ship_sorted))

    # Histogram (buckets of 10)
    histogram: dict[str, int] = {}
    for v in ship_vals:
        bucket = f"{int(v // 10) * 10}-{int(v // 10) * 10 + 9}"
        histogram[bucket] = histogram.get(bucket, 0) + 1

    # Formula check
    formula_ok_count = sum(1 for r in data_rows if (r.get("formula_check") or {}).get("formula_ok"))
    formula_fail_rows = [r for r in data_rows if not (r.get("formula_check") or {}).get("formula_ok")]

    # Lookup table: sscat_id -> {commission_pct, shipping}
    lookup = {}
    for r in data_rows:
        sid = r.get("sscat_id")
        if sid:
            lookup[str(sid)] = {
                "leaf_name": r.get("leaf_name", ""),
                "path_str": r.get("path_str", ""),
                "commission_percentage": r.get("commission_percentage"),
                "shipping_charges": r.get("shipping_charges"),
                "transfer_price_at_100": r.get("transfer_price"),
                "formula_ok": (r.get("formula_check") or {}).get("formula_ok"),
            }

    summary = {
        "generated_at": datetime.now().isoformat(),
        "total_leaves": len(all_leaves),
        "rows_with_data": len(data_rows),
        "error_rows": len(error_rows),
        "census_price": CENSUS_PRICE,
        "commission_analysis": {
            "non_zero_count": len(non_zero_commission),
            "non_zero_rows": non_zero_commission,
            "conclusion": (
                "ALL commission_percentage = 0 across all categories"
                if not non_zero_commission
                else f"{len(non_zero_commission)} categories have non-zero commission"
            ),
        },
        "shipping_distribution": {
            "min": ship_min,
            "max": ship_max,
            "unique_values": ship_unique,
            "histogram_by_10": dict(sorted(histogram.items())),
            "count": len(ship_vals),
        },
        "formula_check": {
            "passed": formula_ok_count,
            "failed": len(formula_fail_rows),
            "total": len(data_rows),
            "all_ok": len(formula_fail_rows) == 0,
            "fail_rows": [
                {
                    "sscat_id": r["sscat_id"],
                    "leaf_name": r.get("leaf_name"),
                    "formula_check": r.get("formula_check"),
                }
                for r in formula_fail_rows
            ],
        },
        "lookup": lookup,
    }

    CENSUS_SUMMARY_JSON.write_text(json.dumps(summary, indent=2, default=str))
    log.info("Summary written: %s", CENSUS_SUMMARY_JSON)

    # Print to stdout
    _print_summary(summary)


def _print_summary(s: dict[str, Any]) -> None:
    print("\n" + "=" * 90)
    print("MeeSell Full Census — getTransferPrice Summary")
    print(f"Generated: {s['generated_at']}")
    print("=" * 90)
    print(f"\nCoverage: {s['rows_with_data']} of {s['total_leaves']} categories "
          f"({s['error_rows']} errors/skipped)")
    print(f"\n--- COMMISSION ANALYSIS ---")
    ca = s["commission_analysis"]
    print(f"Non-zero commission rows: {ca['non_zero_count']}")
    print(f"Conclusion: {ca['conclusion']}")
    if ca["non_zero_rows"]:
        for r in ca["non_zero_rows"]:
            print(f"  sscat={r['sscat_id']} {r.get('leaf_name')} "
                  f"commission%={r.get('commission_percentage')} fees={r.get('commission_fees')}")
    print(f"\n--- SHIPPING DISTRIBUTION ---")
    sd = s["shipping_distribution"]
    print(f"Min: {sd['min']}  Max: {sd['max']}  Unique values: {len(sd['unique_values'])}")
    print(f"Unique shipping values: {sd['unique_values']}")
    print(f"Histogram (by ₹10 bucket):")
    for bucket, count in sd["histogram_by_10"].items():
        bar = "#" * min(count // 10, 60)
        print(f"  ₹{bucket:<8}: {count:>5}  {bar}")
    fc = s["formula_check"]
    print(f"\n--- FORMULA CHECK ---")
    print(f"Passed: {fc['passed']} / {fc['total']}  |  Failed: {fc['failed']}")
    if fc["fail_rows"]:
        print("Failing rows:")
        for r in fc["fail_rows"]:
            print(f"  sscat={r['sscat_id']} {r.get('leaf_name')} check={r.get('formula_check')}")
    print(f"\n--- LOOKUP TABLE ---")
    print(f"Full lookup written to: {CENSUS_SUMMARY_JSON}")
    print(f"  Format: sscat_id -> {{leaf_name, commission_percentage, shipping_charges, "
          f"transfer_price_at_100, formula_ok}}")
    print("=" * 90 + "\n")


def print_partial_report(done: int, total: int, hard_stop_at: str | None) -> None:
    print("\n" + "=" * 90)
    print(f"Census PARTIAL — {done} / {total} done ({done/total*100:.1f}%)")
    if hard_stop_at:
        print(f"Stopped at: {hard_stop_at}")
    print(f"\nResume instructions:")
    print(f"  Just re-run: /Users/mugunthansrinivasan/Project/mesell/backend/.venv/bin/python "
          f"/Users/mugunthansrinivasan/Project/mesell/backend/scripts/meesho_transfer_price_census.py")
    print(f"  Existing results: {CENSUS_JSONL}")
    print(f"  The script will skip already-completed sscat_ids automatically.")
    print("=" * 90 + "\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
