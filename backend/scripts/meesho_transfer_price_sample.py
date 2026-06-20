"""ROUND 14 — Stratified getTransferPrice category sample.

Founder-decoded contract (verified):
  POST https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getTransferPrice
  Body:   {"sscat_id":<leaf_id>,"gst_percentage":null,"price":<price>,
           "supplier_id":4359160,"duplicate_pid":null,"gst_type":"ENROLMENT"}
  Headers: identifier=oinpw, client-type=d-web, client-package-version=1.0.1,
           supplier-id=4359160, content-type=application/json;charset=UTF-8

Control verified by founder: sscat_id=10949 (Extension Chords) @ price=100
  -> {commission_fees:0, commission_percentage:0, gst_price:14.76, tcs:0,
      tds:0.18, shipping_charges:82, transfer_price:85.06, total_price:182}

Formula (all rows must satisfy):
  gst_price       = 0.18 * shipping_charges   (18% GST on shipping)
  total_price     = price + shipping_charges
  tds             = 0.001 * total_price        (0.1% TDS on total)
  transfer_price  = price - commission_fees - gst_price - tds - tcs

Plan:
  1. Login via password (WebKit Akamai bypass). OTP relay armed (poll /tmp/meesho_otp.txt).
  2. SANITY GATE: call getTransferPrice sscat_id=10949 @ price=100 -> must match control.
  3. For each of ~12 stratified leaf categories: search the search-catalog XHR to get
     the sscat_id, then call getTransferPrice @ price=100 AND price=500.
  4. Record per (category, price): all fields + formula-check.
  5. Save raw JSON to logs/scraper/ + print clean table.

Safety: compute-API ONLY. No listing, no image, no Submit, no go-live.
Pace: ~1 call per 2-3s. Stop on 401/403/429 scoped to supplier.meesho.com/api.
"""

from __future__ import annotations

import asyncio
import json
import logging
import math
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
OTP_FILE = Path("/tmp/meesho_otp.txt")

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
API_BASE = "https://supplier.meesho.com/api"
TRANSFER_PRICE_URL = f"{API_BASE}/cataloging/singleCatalogUpload/getTransferPrice"
SEARCH_CATALOG_URL = f"{API_BASE}/cataloging/catalog-upload/search-catalog"

LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000
API_TIMEOUT_MS = 30_000

SESSION_STOP_CODES = {401, 403, 429}

# Known control
CONTROL_SSCAT_ID = 10949
CONTROL_CATEGORY_NAME = "Extension Chords"
CONTROL_PRICE = 100
CONTROL_EXPECTED_TRANSFER_PRICE = 85.06

# Founder-verified supplier details
SUPPLIER_ID = 4359160
IDENTIFIER = "oinpw"

# ---------------------------------------------------------------------------
# Stratified leaf categories: 12 families, diverse verticals.
# sscat_ids resolved from the local meesho_category_tree.json (3,772 leaves).
# Extension Chords (10949) is the control included in this list.
# ---------------------------------------------------------------------------
SAMPLE_CATEGORIES: list[dict[str, Any]] = [
    # --- Control (founder-verified) ---
    {
        "sscat_id": 10949,
        "category_name": "Extension Chords",
        "category_chain": "Appliances > Small appliances > Home Appliances > Extension Chords",
        "family_label": "Electronics/Appliances",
        "is_control": True,
    },
    # --- Consumer Electronics ---
    {
        "sscat_id": 13445,
        "category_name": "Stick PCs",
        "category_chain": "Consumer Electronics > Computers & Accessories > Desktops > Stick PCs",
        "family_label": "Consumer Electronics",
        "is_control": False,
    },
    # --- Appliances ---
    {
        "sscat_id": 10405,
        "category_name": "Hair Stylers",
        "category_chain": "Appliances > Small appliances > Personal Grooming > Hair Stylers",
        "family_label": "Appliances",
        "is_control": False,
    },
    # --- Apparel (Women) ---
    {
        "sscat_id": 10003,
        "category_name": "Sarees",
        "category_chain": "Women Fashion > Ethnic Wear > Sarees, Blouses & Petticoats > Sarees",
        "family_label": "Apparel/Sarees",
        "is_control": False,
    },
    {
        "sscat_id": 10213,
        "category_name": "Skirts",
        "category_chain": "Women Fashion > Ethnic Wear > Ethnic Skirts > Skirts",
        "family_label": "Apparel/Skirts",
        "is_control": False,
    },
    # --- Apparel (Men) ---
    {
        "sscat_id": 10262,
        "category_name": "Trousers",
        "category_chain": "Men Fashion > Mens Clothing > Men Bottom Wear > Trousers",
        "family_label": "Apparel/Trousers",
        "is_control": False,
    },
    # --- Home & Kitchen ---
    {
        "sscat_id": 12983,
        "category_name": "Salt & Pepper Shakers",
        "category_chain": "Home & Kitchen > Kitchen & Dining > Kitchen Storage > Salt & Pepper Shakers",
        "family_label": "Home & Kitchen",
        "is_control": False,
    },
    # --- Beauty / Personal Care ---
    {
        "sscat_id": 10516,
        "category_name": "BB & CC Cream",
        "category_chain": "Beauty & Personal Care > Makeup > Face > BB & CC Cream",
        "family_label": "Beauty/Makeup",
        "is_control": False,
    },
    {
        "sscat_id": 10116,
        "category_name": "Facewash & Scrubs",
        "category_chain": "Personal Care & Wellness > Skin Care > Facewash & Scrubs",
        "family_label": "Personal Care",
        "is_control": False,
    },
    # --- Jewellery / Accessories ---
    {
        "sscat_id": 10109,
        "category_name": "Earrings & Studs",
        "category_chain": "Women Fashion > Accessories > Jewellery > Earrings & Studs",
        "family_label": "Jewellery/Accessories",
        "is_control": False,
    },
    # --- Bags / Travel ---
    {
        "sscat_id": 12412,
        "category_name": "Pouches",
        "category_chain": "Bags, Luggage & Travel Accessories > Travel Bags > Pouches",
        "family_label": "Bags/Pouches",
        "is_control": False,
    },
    # --- Sports / Fitness ---
    {
        "sscat_id": 14745,
        "category_name": "Tennis Balls",
        "category_chain": "Sports & Fitness > Outdoor Sports > Tennis > Tennis Balls",
        "family_label": "Sports/Tennis",
        "is_control": False,
    },
    # --- Health / Wellness ---
    {
        "sscat_id": 11283,
        "category_name": "Orthopedic Knee Support",
        "category_chain": "Health & Wellness > Orthopedic support > Orthopedic Knee Support",
        "family_label": "Health/Medical",
        "is_control": False,
    },
]

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
_account: dict[str, Any] = {"supplier_id": None, "identifier": None}
_hard_stop: list[str] = []
_search_results: dict[str, Any] = {}   # keyword -> raw search-catalog response

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|"
    r"enter the (otp|code)|verification code|6[-\s]?digit)\b", re.I)
OTP_CODE_RE = re.compile(r"\b(\d{6})\b")

log = logging.getLogger("meesho-sample")


def configure_logging() -> str:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"transfer_price_sample_{ts}.log"
    logger = logging.getLogger("meesho-sample")
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
    logger.info("Log file: %s", log_path)
    return ts


def load_creds() -> tuple[str, str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Creds missing: {CREDS_FILE}")
    load_dotenv(CREDS_FILE, override=True)
    u = os.environ.get("MEESHO_USERNAME", "").strip()
    p = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not u or not p:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing")
    return u, p


def _safe_url(url: str) -> str:
    return url.split("?", 1)[0]


# ---------------------------------------------------------------------------
# Response listener (minimal — account fields + search-catalog capture)
# ---------------------------------------------------------------------------
async def on_response(resp: Response) -> None:
    url = resp.url
    status = resp.status

    if status in SESSION_STOP_CODES and "supplier.meesho.com/api" in url:
        _hard_stop.append(f"HTTP {status} on {_safe_url(url)}")
        log.error("HARD-STOP: HTTP %d on %s", status, _safe_url(url))
        return

    ct = (resp.headers or {}).get("content-type", "")
    if "json" not in ct:
        return
    try:
        body = await resp.json()
    except Exception:
        return

    # Mine account fields
    if "prefetch-supply-data" in url or "registration-status" in url or "supplier/config" in url:
        _walk_account(body)

    # Capture search-catalog responses
    if "search-catalog" in url and isinstance(body, dict):
        results = body.get("results") or body.get("data") or []
        log.info("search-catalog fired: %d results", len(results) if isinstance(results, list) else 0)
        # Store keyed by the last search term we fired (we manage the key from the search call)
        _search_results["__latest__"] = body


def _walk_account(body: Any) -> None:
    stack = [body]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                kl = k.lower()
                if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)) and not _account["supplier_id"]:
                    _account["supplier_id"] = v
                if kl in ("identifier", "supplier_identifier") and isinstance(v, str) and v and len(v) < 24 and not _account["identifier"]:
                    _account["identifier"] = v
                if kl == "supplier_identifier_to_id_mapping" and isinstance(v, dict):
                    for ident, sid in v.items():
                        _account["identifier"] = _account["identifier"] or ident
                        _account["supplier_id"] = _account["supplier_id"] or sid
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
async def _first(page: Page, cands, timeout=5000):
    for build in cands:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:
            continue
    return None


async def find_otp_field(page: Page):
    try:
        txt = await page.locator("body").inner_text(timeout=3000)
    except Exception:
        txt = ""
    cands = [
        lambda: page.get_by_placeholder(re.compile(r"otp|code|verification", re.I)),
        lambda: page.locator("input[name*='otp' i], input[id*='otp' i], input[autocomplete='one-time-code']"),
        lambda: page.locator("input[maxlength='6']"),
    ]
    for build in cands:
        try:
            loc = build()
            if await loc.count() and await loc.first.is_visible():
                return loc.first
        except Exception:
            continue
    return None


async def poll_otp_file(max_tries: int = 60, interval: float = 5.0) -> str | None:
    print("OTP_PAGE_REACHED — waiting for /tmp/meesho_otp.txt", flush=True)
    for _ in range(max_tries):
        try:
            if OTP_FILE.exists():
                m = OTP_CODE_RE.search(OTP_FILE.read_text().strip())
                if m:
                    return m.group(1)
        except Exception:
            pass
        await asyncio.sleep(interval)
    return None


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

    # OTP relay
    for _ in range(4):
        otp_field = await find_otp_field(page)
        if otp_field is not None:
            log.info("OTP page detected — polling OTP relay file")
            code = await poll_otp_file()
            if not code:
                raise RuntimeError("OTP_TIMEOUT: no code in /tmp/meesho_otp.txt within 5 min")
            try:
                await otp_field.fill(code)
                await asyncio.sleep(1.0)
                await page.keyboard.press("Enter")
            except Exception as exc:
                raise RuntimeError(f"OTP typing failed: {exc}")
            break
        if "login" not in page.url.lower():
            break
        await asyncio.sleep(2.0)

    if "login" in page.url.lower():
        try:
            await page.wait_for_url(lambda u: "login" not in u, timeout=20_000)
        except PlaywrightTimeoutError:
            raise RuntimeError("Login did not redirect away from /login — check creds or OTP")

    log.info("Login OK — at %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Search-catalog: resolve sscat_id from keyword
# ---------------------------------------------------------------------------
async def resolve_sscat_id(ctx: BrowserContext, keyword: str, name_re: str) -> tuple[int | None, str | None, str | None]:
    """Call search-catalog XHR directly via ctx.request, parse results for the matching leaf.

    Returns (sscat_id, leaf_name, category_chain) or (None, None, None) on failure.
    """
    pattern = re.compile(name_re, re.I)

    # First try: use the Meesho search-catalog API directly
    try:
        resp: APIResponse = await ctx.request.get(
            SEARCH_CATALOG_URL,
            params={"q": keyword, "limit": 20},
            headers={
                "identifier": IDENTIFIER,
                "client-type": "d-web",
                "client-package-version": "1.0.1",
                "supplier-id": str(SUPPLIER_ID),
                "accept": "application/json, text/plain, */*",
                "referer": "https://supplier.meesho.com/",
            },
            timeout=API_TIMEOUT_MS,
        )
        status = resp.status
        log.info("search-catalog '%s' -> HTTP %d", keyword, status)
        if status in SESSION_STOP_CODES:
            _hard_stop.append(f"HTTP {status} on search-catalog '{keyword}'")
            return None, None, None
        body = await resp.json()
    except PlaywrightTimeoutError:
        log.warning("search-catalog '%s' timed out", keyword)
        return None, None, None
    except Exception as exc:
        log.warning("search-catalog '%s' error: %s", keyword, exc)
        return None, None, None

    # Parse results
    results = body.get("results") or body.get("data") or body.get("categories") or []
    if not isinstance(results, list):
        # Some responses wrap in a different key — flatten
        for v in body.values():
            if isinstance(v, list) and v:
                results = v
                break

    log.info("search-catalog '%s': %d results in body", keyword, len(results))
    for item in results:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or item.get("category_name", "") or "")
        item_id = item.get("id") or item.get("sscat_id") or item.get("sub_sub_category_id")
        chain = item.get("chain") or item.get("category_chain") or item.get("path")
        if pattern.search(name) and item_id:
            log.info("Matched leaf '%s' id=%s chain=%s for keyword '%s'", name, item_id, chain, keyword)
            return int(item_id), name, str(chain) if chain else None

    # If strict match failed, fall back to first result with an id
    for item in results:
        if not isinstance(item, dict):
            continue
        item_id = item.get("id") or item.get("sscat_id") or item.get("sub_sub_category_id")
        name = str(item.get("name", "") or "")
        chain = item.get("chain") or item.get("path")
        if item_id:
            log.warning("Strict match failed for '%s'; using first result: '%s' id=%s",
                        keyword, name, item_id)
            return int(item_id), name, str(chain) if chain else None

    log.warning("search-catalog '%s': no usable result in %d items", keyword, len(results))
    return None, None, None


# ---------------------------------------------------------------------------
# The DECODED getTransferPrice call
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


async def call_transfer_price(ctx: BrowserContext, sscat_id: int, price: int) -> dict[str, Any] | None:
    """POST the DECODED getTransferPrice body and return the parsed response dict, or None."""
    body = {
        "sscat_id": sscat_id,
        "gst_percentage": None,
        "price": price,
        "supplier_id": SUPPLIER_ID,
        "duplicate_pid": None,
        "gst_type": "ENROLMENT",
    }
    log.info("getTransferPrice sscat=%d price=%d body=%s", sscat_id, price, json.dumps(body))
    try:
        resp: APIResponse = await ctx.request.post(
            TRANSFER_PRICE_URL,
            headers=_transfer_price_headers(),
            data=body,
            timeout=API_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        log.warning("getTransferPrice sscat=%d price=%d TIMEOUT", sscat_id, price)
        return None
    except Exception as exc:
        log.warning("getTransferPrice sscat=%d price=%d error: %s", sscat_id, price, exc)
        return None

    status = resp.status
    log.info("getTransferPrice sscat=%d price=%d -> HTTP %d", sscat_id, price, status)

    if status in SESSION_STOP_CODES:
        _hard_stop.append(f"HTTP {status} on getTransferPrice sscat={sscat_id} price={price}")
        log.error("HARD-STOP: HTTP %d on getTransferPrice sscat=%d price=%d", status, sscat_id, price)
        return None

    try:
        rbody = await resp.json()
    except Exception:
        text = await resp.text()
        log.warning("getTransferPrice sscat=%d price=%d non-JSON response: %s", sscat_id, price, text[:500])
        return None

    log.info("getTransferPrice sscat=%d price=%d response=%s", sscat_id, price,
             json.dumps(rbody, default=str)[:600])
    return rbody if isinstance(rbody, dict) and rbody else None


# ---------------------------------------------------------------------------
# Formula verification
# ---------------------------------------------------------------------------
def verify_formula(row: dict[str, Any]) -> dict[str, Any]:
    """Verify the founder-given formula on a single row. Returns formula_ok + computed fields."""
    price = row.get("price", 0)
    shipping = row.get("shipping_charges", 0)
    commission_fees = row.get("commission_fees", 0)
    commission_pct = row.get("commission_percentage", 0)
    gst_price = row.get("gst_price", 0)
    tds = row.get("tds", 0)
    tcs = row.get("tcs", 0)
    transfer_price = row.get("transfer_price", 0)
    total_price = row.get("total_price", 0)

    computed_total = price + shipping
    computed_gst = round(0.18 * shipping, 2)
    computed_tds = round(0.001 * computed_total, 2)
    computed_transfer = round(price - commission_fees - computed_gst - computed_tds - tcs, 2)

    # Allow ±0.05 tolerance for rounding
    tol = 0.05
    total_ok = abs(computed_total - total_price) < tol
    gst_ok = abs(computed_gst - gst_price) < tol
    tds_ok = abs(computed_tds - tds) < tol
    transfer_ok = abs(computed_transfer - transfer_price) < tol

    formula_ok = total_ok and gst_ok and tds_ok and transfer_ok

    return {
        "formula_ok": formula_ok,
        "computed_total_price": computed_total,
        "computed_gst_price": computed_gst,
        "computed_tds": computed_tds,
        "computed_transfer_price": computed_transfer,
        "delta_total": round(computed_total - total_price, 4),
        "delta_gst": round(computed_gst - gst_price, 4),
        "delta_tds": round(computed_tds - tds, 4),
        "delta_transfer": round(computed_transfer - transfer_price, 4),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def run() -> None:
    ts = configure_logging()
    user, pwd = load_creds()

    log.info("=== MeeSell Round-14 stratified getTransferPrice sample ===")
    log.info("Account: %s / supplier_id=%s / identifier=%s", user[:4] + "****", SUPPLIER_ID, IDENTIFIER)

    results_raw: list[dict[str, Any]] = []       # full per-(category,price) dicts
    categories_captured = 0

    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 1000},
        )
        ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
        ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)
        ctx.on("response", lambda r: asyncio.create_task(on_response(r)))

        try:
            page = await ctx.new_page()

            # ----------------------------------------------------------------
            # Step 1 — Login
            # ----------------------------------------------------------------
            await perform_login(page, user, pwd)
            await asyncio.sleep(3.0)

            if _hard_stop:
                log.error("Hard stop after login: %s", _hard_stop)
                return

            # Give the home page XHRs time to fire (account data)
            await asyncio.sleep(3.0)
            log.info("Account state: %s", _account)

            # ----------------------------------------------------------------
            # Step 2 — SANITY GATE: control call sscat=10949 @ price=100
            # ----------------------------------------------------------------
            log.info("=== SANITY GATE: sscat=%d price=%d ===", CONTROL_SSCAT_ID, CONTROL_PRICE)
            sanity_resp = await call_transfer_price(ctx, CONTROL_SSCAT_ID, CONTROL_PRICE)
            await asyncio.sleep(2.5)

            if _hard_stop:
                log.error("Hard stop at sanity gate: %s", _hard_stop)
                return

            sanity_pass = False
            if sanity_resp is None:
                log.error("SANITY GATE FAILED: no response from getTransferPrice for control sscat=%d price=%d",
                          CONTROL_SSCAT_ID, CONTROL_PRICE)
                log.error("STOPPING — the call is wrong. Report: null response on control.")
                return
            else:
                actual_transfer = sanity_resp.get("transfer_price")
                actual_shipping = sanity_resp.get("shipping_charges")
                log.info("Sanity control response: transfer_price=%s shipping=%s full=%s",
                         actual_transfer, actual_shipping,
                         json.dumps(sanity_resp, default=str)[:400])
                if actual_transfer is None:
                    log.error("SANITY GATE FAILED: transfer_price key missing in response. Keys=%s",
                              list(sanity_resp.keys()))
                    log.error("STOPPING — the decoded contract may still be wrong.")
                    return
                tol = 0.10
                if abs(float(actual_transfer) - CONTROL_EXPECTED_TRANSFER_PRICE) <= tol:
                    log.info("SANITY GATE PASSED: transfer_price=%s (expected %.2f, delta=%.4f)",
                             actual_transfer, CONTROL_EXPECTED_TRANSFER_PRICE,
                             float(actual_transfer) - CONTROL_EXPECTED_TRANSFER_PRICE)
                    sanity_pass = True
                else:
                    log.error("SANITY GATE FAILED: transfer_price=%s expected %.2f (delta=%.4f)",
                              actual_transfer, CONTROL_EXPECTED_TRANSFER_PRICE,
                              float(actual_transfer) - CONTROL_EXPECTED_TRANSFER_PRICE)
                    log.error("STOPPING — control does not match. Full response: %s",
                              json.dumps(sanity_resp, default=str))
                    return

            # Record control row
            ctrl_row = {
                "sscat_id": CONTROL_SSCAT_ID,
                "category_name": CONTROL_CATEGORY_NAME,
                "category_chain": "Home/Extension Chords",
                "family_label": "Electronics",
                "price": CONTROL_PRICE,
                **{k: sanity_resp.get(k) for k in [
                    "commission_percentage", "commission_fees", "shipping_charges",
                    "gst_price", "tds", "tcs", "transfer_price", "total_price",
                ]},
                "formula_check": verify_formula({"price": CONTROL_PRICE, **sanity_resp}),
                "sanity_control": True,
            }
            results_raw.append(ctrl_row)
            categories_captured += 1

            # Also call control at price=500
            log.info("Control sscat=%d @ price=500", CONTROL_SSCAT_ID)
            ctrl_500 = await call_transfer_price(ctx, CONTROL_SSCAT_ID, 500)
            await asyncio.sleep(2.5)
            if ctrl_500:
                ctrl_row_500 = {
                    "sscat_id": CONTROL_SSCAT_ID,
                    "category_name": CONTROL_CATEGORY_NAME,
                    "category_chain": "Home/Extension Chords",
                    "family_label": "Electronics",
                    "price": 500,
                    **{k: ctrl_500.get(k) for k in [
                        "commission_percentage", "commission_fees", "shipping_charges",
                        "gst_price", "tds", "tcs", "transfer_price", "total_price",
                    ]},
                    "formula_check": verify_formula({"price": 500, **ctrl_500}),
                    "sanity_control": True,
                }
                results_raw.append(ctrl_row_500)

            if _hard_stop:
                log.error("Hard stop after control calls: %s", _hard_stop)
                return

            # ----------------------------------------------------------------
            # Step 3 — Stratified categories: call at price=100 and price=500
            # (sscat_ids resolved from local meesho_category_tree.json)
            # Skip Extension Chords (already called as control above)
            # ----------------------------------------------------------------
            for target in SAMPLE_CATEGORIES:
                if _hard_stop:
                    log.error("Hard stop mid-sample at category '%s': %s",
                              target["category_name"], _hard_stop)
                    break

                sscat_id = target["sscat_id"]
                leaf_name = target["category_name"]
                chain = target["category_chain"]
                family_label = target["family_label"]
                is_control = target.get("is_control", False)

                # Skip the control — already captured above
                if is_control:
                    log.info("Skipping control sscat=%d (already captured above)", sscat_id)
                    continue

                log.info("--- Category: %s sscat=%d ---", family_label, sscat_id)

                if _hard_stop:
                    break

                # Call @ price=100
                resp_100 = await call_transfer_price(ctx, sscat_id, 100)
                await asyncio.sleep(2.5)

                if resp_100:
                    row_100 = {
                        "sscat_id": sscat_id,
                        "category_name": leaf_name,
                        "category_chain": chain,
                        "family_label": family_label,
                        "price": 100,
                        **{k: resp_100.get(k) for k in [
                            "commission_percentage", "commission_fees", "shipping_charges",
                            "gst_price", "tds", "tcs", "transfer_price", "total_price",
                        ]},
                        "formula_check": verify_formula({"price": 100, **resp_100}),
                        "sanity_control": False,
                    }
                    results_raw.append(row_100)
                else:
                    results_raw.append({
                        "sscat_id": sscat_id,
                        "category_name": leaf_name,
                        "family_label": family_label,
                        "price": 100,
                        "error": "null_response",
                    })

                if _hard_stop:
                    break

                # Call @ price=500
                resp_500 = await call_transfer_price(ctx, sscat_id, 500)
                await asyncio.sleep(2.5)

                if resp_500:
                    row_500 = {
                        "sscat_id": sscat_id,
                        "category_name": leaf_name,
                        "category_chain": chain,
                        "family_label": family_label,
                        "price": 500,
                        **{k: resp_500.get(k) for k in [
                            "commission_percentage", "commission_fees", "shipping_charges",
                            "gst_price", "tds", "tcs", "transfer_price", "total_price",
                        ]},
                        "formula_check": verify_formula({"price": 500, **resp_500}),
                        "sanity_control": False,
                    }
                    results_raw.append(row_500)
                else:
                    results_raw.append({
                        "sscat_id": sscat_id,
                        "category_name": leaf_name,
                        "family_label": family_label,
                        "price": 500,
                        "error": "null_response",
                    })

                categories_captured += 1
                log.info("Category '%s' (sscat=%d) done — total categories=%d",
                         leaf_name, sscat_id, categories_captured)

            # ----------------------------------------------------------------
            # Step 4 — Save raw results
            # ----------------------------------------------------------------
            raw_path = LOG_DIR / f"transfer_price_sample_{ts}.json"
            raw_path.write_text(json.dumps({
                "run_ts": ts,
                "supplier_id": SUPPLIER_ID,
                "identifier": IDENTIFIER,
                "sanity_pass": sanity_pass,
                "categories_captured": categories_captured,
                "hard_stops": _hard_stop,
                "results": results_raw,
            }, indent=2, default=str))
            log.info("Raw results saved: %s", raw_path)

        except Exception as exc:
            log.exception("Probe error: %s", exc)
        finally:
            try:
                await browser.close()
            except Exception:
                pass

    # ----------------------------------------------------------------
    # Step 5 — Analysis + clean table
    # ----------------------------------------------------------------
    print_report(results_raw, ts)


def print_report(results: list[dict[str, Any]], ts: str) -> None:
    print("\n" + "=" * 90)
    print("MeeSell Round-14: getTransferPrice Stratified Sample")
    print(f"Run: {ts}")
    print("=" * 90)

    # Filter to rows with actual data
    data_rows = [r for r in results if r.get("transfer_price") is not None]
    error_rows = [r for r in results if "error" in r]

    print(f"\nRows with data: {len(data_rows)}  |  Errors/skipped: {len(error_rows)}")

    if data_rows:
        # Table header
        hdr = (f"{'Category':<30} {'Family':<22} {'sscat_id':>8} {'Price':>6} "
               f"{'Commission%':>12} {'CommFees':>9} {'Shipping':>9} "
               f"{'GST':>7} {'TDS':>5} {'TCS':>5} {'Total':>7} {'Transfer':>10} "
               f"{'Formula':>8}")
        print("\n" + hdr)
        print("-" * len(hdr))

        for r in data_rows:
            fc = r.get("formula_check", {})
            formula_ok = "OK" if fc.get("formula_ok") else "FAIL"
            cat_name = str(r.get("category_name", "?"))[:29]
            family = str(r.get("family_label", "?"))[:21]
            print(
                f"{cat_name:<30} {family:<22} {r.get('sscat_id', '?'):>8} "
                f"{r.get('price', '?'):>6} {r.get('commission_percentage', '?'):>12} "
                f"{r.get('commission_fees', '?'):>9} {r.get('shipping_charges', '?'):>9} "
                f"{r.get('gst_price', '?'):>7} {r.get('tds', '?'):>5} "
                f"{r.get('tcs', '?'):>5} {r.get('total_price', '?'):>7} "
                f"{r.get('transfer_price', '?'):>10} {formula_ok:>8}"
            )

    # Analysis
    print("\n" + "=" * 90)
    print("ANALYSIS")
    print("=" * 90)

    if data_rows:
        # Commission percentage findings
        non_zero_commission = [r for r in data_rows if float(r.get("commission_percentage", 0) or 0) != 0.0]
        print(f"\n1. Commission percentage non-zero rows: {len(non_zero_commission)}")
        if non_zero_commission:
            print("   NON-ZERO commission rows:")
            for r in non_zero_commission:
                print(f"     sscat={r['sscat_id']} cat={r.get('category_name')} "
                      f"price={r['price']} commission%={r['commission_percentage']} "
                      f"fees={r['commission_fees']}")
        else:
            print("   commission_percentage = 0 on ALL rows (no non-zero found)")

        # Shipping variation
        print("\n2. Shipping charges by category (price=100 vs price=500):")
        by_sscat: dict[int, list[dict]] = {}
        for r in data_rows:
            sid = r.get("sscat_id")
            if sid:
                by_sscat.setdefault(int(sid), []).append(r)

        for sscat_id, rows in sorted(by_sscat.items()):
            r100 = next((r for r in rows if r.get("price") == 100), None)
            r500 = next((r for r in rows if r.get("price") == 500), None)
            s100 = r100.get("shipping_charges") if r100 else "N/A"
            s500 = r500.get("shipping_charges") if r500 else "N/A"
            name = (r100 or r500 or {}).get("category_name", "?")
            price_var = "SAME" if s100 == s500 else f"DIFFERS ({s100}@100 vs {s500}@500)"
            print(f"   sscat={sscat_id} {name[:35]:<36}: shipping@100={s100}, @500={s500} [{price_var}]")

        # Unique shipping values
        ship_vals = sorted({float(r.get("shipping_charges", 0) or 0) for r in data_rows})
        print(f"\n   Unique shipping values across all rows: {ship_vals}")

        # Formula check summary
        formula_fails = [r for r in data_rows if not (r.get("formula_check") or {}).get("formula_ok")]
        print(f"\n3. Formula check: {len(data_rows) - len(formula_fails)}/{len(data_rows)} rows PASS")
        if formula_fails:
            print("   FAILING rows:")
            for r in formula_fails:
                fc = r.get("formula_check", {})
                print(f"     sscat={r['sscat_id']} price={r['price']} "
                      f"delta_transfer={fc.get('delta_transfer')} "
                      f"delta_gst={fc.get('delta_gst')} delta_tds={fc.get('delta_tds')}")

        # Lookup table
        print("\n4. LOOKUP TABLE: sscat_id -> (category_name, commission%, shipping@100, shipping@500)")
        print(f"   {'sscat_id':>8} {'commission%':>12} {'shipping@100':>12} {'shipping@500':>12} "
              f"{'category_name':<35} {'chain'}")
        print("   " + "-" * 100)
        for sscat_id, rows in sorted(by_sscat.items()):
            r100 = next((r for r in rows if r.get("price") == 100), None)
            r500 = next((r for r in rows if r.get("price") == 500), None)
            ref = r100 or r500
            if ref:
                comm_pct = ref.get("commission_percentage", 0)
                s100 = r100.get("shipping_charges") if r100 else "N/A"
                s500 = r500.get("shipping_charges") if r500 else "N/A"
                name = ref.get("category_name", "?")[:34]
                chain = ref.get("category_chain", "?") or "?"
                print(f"   {sscat_id:>8} {str(comm_pct):>12} {str(s100):>12} {str(s500):>12} "
                      f"{name:<35} {chain}")

    if error_rows:
        print("\n5. Errors / skipped categories:")
        for r in error_rows:
            print(f"   family={r.get('family_label')} keyword={r.get('keyword', '?')} "
                  f"sscat={r.get('sscat_id')} error={r.get('error')}")

    if _hard_stop:
        print(f"\nHARD STOPS encountered: {_hard_stop}")

    print("\n" + "=" * 90)
    print("SAFETY ATTESTATION")
    print(f"  - Compute-API calls only (getTransferPrice + search-catalog GET)")
    print(f"  - No listing, no image upload, no Submit, no go-live")
    print(f"  - No creds logged or committed (creds file: {CREDS_FILE})")
    print(f"  - Logs gitignored: {LOG_DIR}")
    print(f"  - Hard stops: {_hard_stop or 'none'}")
    print("=" * 90 + "\n")


def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
