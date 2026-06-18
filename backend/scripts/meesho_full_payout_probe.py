"""Meesho FULL per-product payout probe — STRICTLY READ-ONLY (round 4).

Goal
----
ROUND 4. Prior runs proved the breakthrough source — the catalog LISTING fires
``GET /api/growth/activation/fetch-supplier-products`` which returns, PER PRODUCT,
the real economics (current_price / current_transfer_price = seller payout / wdrp
band / minimum recommendation) WITHOUT the e-signature wall. But every prior run
captured only ONE product before Akamai 403'd, and the full body was never
PERSISTED (only truncated to stdout).

This probe fixes both problems:

  GOAL 1 (priority) — capture the FULL fetch-supplier-products body for ALL ~15
  products and PERSIST THE RAW JSON TO DISK THE MOMENT IT ARRIVES (inside the
  response handler), so a later 403 cannot lose it. Then tabulate per-product
  effective deduction = (current_price - current_transfer_price)/current_price.

  GOAL 2 — re-diagnose the REAL blocker now that the founder confirms the
  e-signature IS done. Enumerate EVERY agreement/KYC/onboarding/registration
  status field across prefetch-supply-data + fetch-registration-status (not just
  is_agreement_accepted, which our prior diagnosis leaned on and may be the wrong
  or stale signal). Then GENTLY retry the commission rate-card + settlement and,
  if they still fail, capture the exact HTTP status / error body / missing-XHR.

PACING (prior runs tripped Akamai 403/463)
------------------------------------------
  * Navigate to the FEWEST pages possible. ONE listing nav for Goal 1.
  * Persist fetch-supplier-products on FIRST arrival, immediately, to disk.
  * The SPA auto-fires prefetch-supply-data on every nav; a 403 on THAT specific
    repeat does NOT discard already-captured product data — we record it and keep
    the data we have rather than nuking the run.
  * Long dwells, spaced navs. Hard-stop on OTP. 401/403/429 -> stop new navs but
    flush what we captured. 463 tolerated (recorded).
  * READ-ONLY: navigation + response interception only. ZERO clicks on any
    Save/Update/Submit/Publish/Confirm control. Never logs credentials.

Output
------
  * logs/scraper/full_payout_<ts>.log              (gitignored)
  * logs/scraper/fetch_supplier_products_<ts>.json (gitignored) RAW full body
  * logs/scraper/status_snapshots_<ts>.json        (gitignored) agreement/KYC snaps
  * stdout: per-product payout table + agreement/status enumeration + rate-card/
    settlement retry diagnosis.
Nothing committed. Nothing under backend/app/data written.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from playwright.async_api import (
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

PROJECT_ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS_FILE = PROJECT_ROOT / ".meesho_creds.env"
LOG_DIR = PROJECT_ROOT / "logs" / "scraper"
TS = datetime.now().strftime("%Y-%m-%d_%H-%M")

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000

SESSION_STOP_CODES = {401, 403, 429}
TOLERATED_BLOCK_CODES = {463}

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the code)\b", re.I)

# The product-economics endpoint (proven, not guessed — intercepted in round 3).
SUPPLIER_PRODUCTS_RE = re.compile(r"fetch-supplier-products|smart-pricing-products", re.I)
# Account/agreement/KYC status snapshots.
STATUS_SNAP_RE = re.compile(
    r"prefetch-supply-data|fetch-registration-status|supplier/config|fetch-home|"
    r"fetch-growth-overview|onboarding|kyc|agreement|signature",
    re.I,
)
# Commission rate-card / settlement candidates (gentle retry, Goal 2).
RATECARD_RE = re.compile(r"referral[-_]?fee|commission|rate[-_]?card|monetization", re.I)
SETTLEMENT_RE = re.compile(
    r"settlement|payment|payout|transaction|order[-_]?payment|ledger|nodal", re.I)

# Status-field key hunting (Goal 2): every candidate that could reflect e-sig done.
STATUS_KEY_RE = re.compile(
    r"agreement|signature|sign[-_]?status|e[-_]?sign|kyc|onboard|registration|"
    r"verified|verification|consent|accepted|activation|gst|bank|approved|"
    r"is_active|account[-_]?status|supplier[-_]?status|seller[-_]?status",
    re.I,
)

LOG_DIR.mkdir(parents=True, exist_ok=True)
RAW_PRODUCTS_PATH = LOG_DIR / f"fetch_supplier_products_{TS}.json"
STATUS_PATH = LOG_DIR / f"status_snapshots_{TS}.json"


def configure_logging() -> logging.Logger:
    log_path = LOG_DIR / f"full_payout_{TS}.log"
    logger = logging.getLogger("meesho-full-payout")
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
    logger.info("Full-payout probe logfile: %s", log_path)
    return logger


log = logging.getLogger("meesho-full-payout")


class HardStop(RuntimeError):
    pass


def load_creds() -> tuple[str, str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Credentials file missing: {CREDS_FILE}")
    load_dotenv(CREDS_FILE)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    return user, pwd


def _safe_url(url: str) -> str:
    return url.split("?", 1)[0]


async def perform_login(page: Page, username: str, password: str) -> None:
    log.info("Navigating to login")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await asyncio.sleep(2.0)

    body_text = ""
    try:
        body_text = await page.locator("body").inner_text(timeout=3000)
    except Exception:  # noqa: BLE001
        pass
    if OTP_HINT_RE.search(body_text):
        raise HardStop("OTP_REQUIRED — login page is asking for an OTP")

    async def _first(cands: list) -> Any:
        for build in cands:
            try:
                loc = build()
                await loc.wait_for(state="visible", timeout=5000)
                return loc
            except Exception:  # noqa: BLE001
                continue
        return None

    user_field = await _first([
        lambda: page.get_by_placeholder(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_role("textbox", name=re.compile(r"email|mobile", re.I)),
        lambda: page.locator("input[type='text']").first,
    ])
    if user_field is None:
        raise HardStop("Could not locate username field on login page")
    await user_field.fill(username)
    await asyncio.sleep(1.0)

    pwd_field = await _first([
        lambda: page.get_by_placeholder(re.compile(r"password", re.I)),
        lambda: page.locator("input[type='password']").first,
    ])
    if pwd_field is None:
        raise HardStop("Could not locate password field — account may be OTP-only (OTP_REQUIRED)")
    await pwd_field.fill(password)
    await asyncio.sleep(1.0)

    submit = await _first([
        lambda: page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ])
    if submit is None:
        raise HardStop("Could not locate login submit button")
    await submit.click()

    try:
        await page.wait_for_url(lambda u: "login" not in u, timeout=LOGIN_NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        snippet = ""
        try:
            snippet = (await page.locator("body").inner_text(timeout=2000))[:400]
        except Exception:  # noqa: BLE001
            pass
        if OTP_HINT_RE.search(snippet):
            raise HardStop("OTP_REQUIRED — login did not redirect; OTP prompt detected")
        raise HardStop(f"Login did not redirect away from /login. URL={_safe_url(page.url)!r}")
    log.info("Login OK — at %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Capture state
# ---------------------------------------------------------------------------

findings: dict[str, Any] = {
    "supplier_id": None,
    "identifier": None,
    "supplier_products_captured": False,
    "supplier_products_raw_path": str(RAW_PRODUCTS_PATH),
    "status_fields": {},          # Goal 2: every agreement/KYC/onboarding status field found
    "status_snapshot_urls": [],
    "ratecard_attempts": [],      # Goal 2: rate-card retry diagnosis
    "settlement_attempts": [],    # Goal 2: settlement retry diagnosis
    "blocked_endpoints": [],
    "soft_403_seen": False,       # a 403 happened but we keep captured data
    "hard_stop": None,
}

# Raw bodies persisted to disk as soon as they arrive.
_raw_products: list[dict[str, Any]] = []
_status_snaps: dict[str, Any] = {}


def _flush_products() -> None:
    try:
        RAW_PRODUCTS_PATH.write_text(json.dumps(_raw_products, indent=2, default=str))
    except Exception as exc:  # noqa: BLE001
        log.warning("could not flush products raw: %s", exc)


def _flush_status() -> None:
    try:
        STATUS_PATH.write_text(json.dumps(_status_snaps, indent=2, default=str))
    except Exception as exc:  # noqa: BLE001
        log.warning("could not flush status raw: %s", exc)


def _harvest_status_fields(obj: Any, depth: int = 0) -> None:
    """Goal 2: collect EVERY key matching status/agreement/kyc + its scalar value."""
    if depth > 10:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and STATUS_KEY_RE.search(k) and isinstance(v, (str, int, float, bool)):
                # keep first-seen value per key; record both if they differ
                if k not in findings["status_fields"]:
                    findings["status_fields"][k] = v
                elif findings["status_fields"][k] != v:
                    findings["status_fields"][f"{k}#alt"] = v
            kl = k.lower() if isinstance(k, str) else ""
            if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                findings["supplier_id"] = findings["supplier_id"] or v
            _harvest_status_fields(v, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:100]:
            _harvest_status_fields(item, depth + 1)


async def on_response(resp: Response) -> None:
    url = resp.url
    status = resp.status

    if status in TOLERATED_BLOCK_CODES:
        findings["blocked_endpoints"].append(f"{status} {_safe_url(url)}")
        log.warning("tolerated block %d on %s (continuing)", status, _safe_url(url))
        return

    if status in SESSION_STOP_CODES:
        # Record the 403, but DON'T discard data already captured. The SPA's
        # prefetch-supply-data repeat 403 is the usual culprit; keep going only
        # if we haven't yet captured the priority product body.
        findings["soft_403_seen"] = True
        findings["blocked_endpoints"].append(f"{status} {_safe_url(url)}")
        log.error("HTTP %d on %s", status, _safe_url(url))
        # Categorize for Goal 2 diagnosis.
        if RATECARD_RE.search(url):
            findings["ratecard_attempts"].append({"url": _safe_url(url), "status": status, "error": "blocked"})
        if SETTLEMENT_RE.search(url):
            findings["settlement_attempts"].append({"url": _safe_url(url), "status": status, "error": "blocked"})
        # Only declare a hard stop if we already have the priority data.
        if findings["supplier_products_captured"]:
            findings["hard_stop"] = f"HTTP {status} on {_safe_url(url)} (after products captured)"
        return

    ct = (resp.headers or {}).get("content-type", "")
    if "json" not in ct:
        return

    # ---- GOAL 1: the priority product-economics body ----
    if SUPPLIER_PRODUCTS_RE.search(url):
        try:
            body = await resp.json()
            _raw_products.append({"url": _safe_url(url), "status": status, "body": body})
            _flush_products()  # PERSIST IMMEDIATELY — a later 403 can't lose it
            findings["supplier_products_captured"] = True
            n = len(body) if isinstance(body, list) else (
                len(body.get("products", body.get("data", []))) if isinstance(body, dict) else "?")
            log.info("CAPTURED %s (status %d) — persisted to disk; product_count~=%s",
                     _safe_url(url), status, n)
        except Exception as exc:  # noqa: BLE001
            log.warning("could not parse products body: %s", exc)
        return

    # ---- GOAL 2: status / agreement / KYC snapshots ----
    if STATUS_SNAP_RE.search(url):
        try:
            snap = await resp.json()
            _status_snaps[_safe_url(url)] = snap
            findings["status_snapshot_urls"].append(_safe_url(url))
            _harvest_status_fields(snap)
            _flush_status()
        except Exception:  # noqa: BLE001
            pass
        return

    # ---- GOAL 2: rate-card success (if e-sig now lets it through) ----
    if RATECARD_RE.search(url):
        try:
            body = await resp.json()
            findings["ratecard_attempts"].append({
                "url": _safe_url(url), "status": status,
                "top_keys": sorted(body.keys())[:30] if isinstance(body, dict) else "[list]",
            })
            log.info("RATECARD XHR ok %d %s", status, _safe_url(url))
        except Exception:  # noqa: BLE001
            pass
        return

    # ---- GOAL 2: settlement success ----
    if SETTLEMENT_RE.search(url):
        try:
            body = await resp.json()
            findings["settlement_attempts"].append({
                "url": _safe_url(url), "status": status,
                "top_keys": sorted(body.keys())[:30] if isinstance(body, dict) else "[list]",
            })
            log.info("SETTLEMENT XHR ok %d %s", status, _safe_url(url))
        except Exception:  # noqa: BLE001
            pass
        return


def detect_identifier_from_url(url: str) -> None:
    m = re.search(r"/(?:growth|payments|fulfillment|cataloging)/([a-z0-9]{3,12})/", url)
    if m:
        findings["identifier"] = findings["identifier"] or m.group(1)


async def dom_otp_check(page: Page, label: str) -> None:
    try:
        txt = await page.locator("body").inner_text(timeout=4000)
    except Exception:  # noqa: BLE001
        return
    if OTP_HINT_RE.search(txt):
        raise HardStop(f"OTP_REQUIRED — detected on {label}")


async def run() -> dict[str, Any]:
    user, pwd = load_creds()
    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-IN", timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 900},
        )
        ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
        ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)
        ctx.on("response", lambda r: asyncio.create_task(on_response(r)))
        try:
            page = await ctx.new_page()
            await perform_login(page, user, pwd)
            await asyncio.sleep(5.0)  # let login-time snapshots arrive
            detect_identifier_from_url(page.url)
            ident = findings["identifier"] or "kdwec"
            log.info("Using identifier=%s", ident)

            # ---- GOAL 1: ONE listing nav that fires fetch-supplier-products ----
            # Round-3 log proved the growth/activation XHRs (incl fetch-supplier-products)
            # fire on the growth home + catalogs views. Use the growth HOME page: it is
            # the dashboard that loads fetch-supplier-products + fetch-growth-overview.
            home_nav = f"https://supplier.meesho.com/panel/v3/new/growth/{ident}/home"
            log.info("--- GOAL 1 listing/home nav: %s", _safe_url(home_nav))
            try:
                await page.goto(home_nav, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                await asyncio.sleep(10.0)  # generous dwell for ALL product XHRs to land
                await dom_otp_check(page, "home")
            except HardStop:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("home nav failed (non-fatal): %s", exc)

            # If products not yet captured, try ONE more page (smart-pricing tab),
            # but only if no 403 has been seen yet (respect pacing).
            if not findings["supplier_products_captured"] and not findings["soft_403_seen"]:
                sp_nav = f"https://supplier.meesho.com/panel/v3/new/growth/{ident}/smart-pricing"
                log.info("--- GOAL 1 fallback smart-pricing nav: %s", _safe_url(sp_nav))
                try:
                    await page.goto(sp_nav, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                    await asyncio.sleep(10.0)
                    await dom_otp_check(page, "smart-pricing")
                except HardStop:
                    raise
                except Exception as exc:  # noqa: BLE001
                    log.warning("smart-pricing nav failed (non-fatal): %s", exc)

            # ---- GOAL 2: gentle rate-card / settlement retry ----
            # Only attempt if we already have the priority data AND no hard 403 yet,
            # so we never sacrifice Goal 1 for Goal 2.
            if findings["supplier_products_captured"] and not findings["hard_stop"]:
                # The referral-fee / payments panels — visit ONE each, paced.
                goal2_navs = [
                    ("ratecard", f"https://supplier.meesho.com/panel/v3/new/growth/{ident}/referral-fee"),
                    ("payments", f"https://supplier.meesho.com/panel/v3/new/payments/{ident}/payments"),
                ]
                for label, nav in goal2_navs:
                    if findings["hard_stop"]:
                        log.info("skipping remaining Goal-2 navs (403 seen after products captured)")
                        break
                    log.info("--- GOAL 2 retry nav '%s': %s", label, _safe_url(nav))
                    try:
                        await page.goto(nav, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                        await asyncio.sleep(8.0)
                        await dom_otp_check(page, label)
                        # Capture whether the panel actually mounted commission/settlement
                        try:
                            txt = await page.locator("body").inner_text(timeout=4000)
                            esig = bool(re.search(
                                r"add signature|e-?signature|sign(?:ature)? is missing|"
                                r"accept.{0,20}agreement|complete.{0,20}agreement", txt, re.I))
                            empty = bool(re.search(
                                r"no (?:data|payments|transactions|settlement)|nothing here|"
                                r"you (?:have )?no", txt, re.I))
                            findings.setdefault("goal2_dom", {})[label] = {
                                "esig_wall_text": esig, "empty_state_text": empty,
                                "text_len": len(txt),
                            }
                            log.info("GOAL2 '%s' dom: esig_wall=%s empty=%s", label, esig, empty)
                        except Exception:  # noqa: BLE001
                            pass
                    except HardStop:
                        raise
                    except Exception as exc:  # noqa: BLE001
                        log.warning("goal2 nav '%s' failed (non-fatal): %s", label, exc)
                    await asyncio.sleep(5.0)  # pace

        except HardStop as exc:
            findings["hard_stop"] = str(exc)
            log.error("HARD STOP: %s", exc)
        finally:
            _flush_products()
            _flush_status()
            await asyncio.sleep(2.0)
            try:
                await ctx.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                pass
    return findings


# ---------------------------------------------------------------------------
# Post-processing: per-product payout table (Goal 1)
# ---------------------------------------------------------------------------

def _coerce_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(str(v).replace("₹", "").replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _extract_products(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten fetch-supplier-products bodies into a per-product list."""
    products: list[dict[str, Any]] = []
    for entry in raw:
        if "fetch-supplier-products" not in entry["url"]:
            continue
        body = entry["body"]
        items: list[Any] = []
        if isinstance(body, list):
            items = body
        elif isinstance(body, dict):
            for key in ("products", "data", "result", "items", "supplier_products"):
                val = body.get(key)
                if isinstance(val, list):
                    items = val
                    break
            if not items:
                # maybe nested one level
                for v in body.values():
                    if isinstance(v, dict):
                        for key in ("products", "data", "items"):
                            if isinstance(v.get(key), list):
                                items = v[key]
                                break
        for it in items:
            if not isinstance(it, dict):
                continue
            cp = _coerce_float(it.get("current_price"))
            tp = _coerce_float(it.get("current_transfer_price"))
            ded = None
            if cp and tp is not None and cp > 0:
                ded = round((cp - tp) / cp * 100, 1)
            products.append({
                "product_id": it.get("product_id") or it.get("id") or it.get("catalog_id"),
                "sku": it.get("sku") or it.get("sku_id") or it.get("variation"),
                "category_id": it.get("category_id") or it.get("sub_category_id"),
                "category_name": it.get("category_name") or it.get("category")
                or it.get("sub_category_name") or it.get("product_type"),
                "name": it.get("name") or it.get("product_name") or it.get("title"),
                "current_price": cp,
                "current_transfer_price": tp,
                "current_wdrp_price": _coerce_float(it.get("current_wdrp_price")),
                "current_wdrp_transfer_price": _coerce_float(it.get("current_wdrp_transfer_price")),
                "minimum_recommendation_price": _coerce_float(it.get("minimum_recommendation_price")),
                "effective_deduction_pct": ded,
            })
    return products


def main() -> int:
    configure_logging()
    log.info("==== Meesho FULL per-product payout READ-ONLY probe @ %s ====", datetime.now().isoformat())
    f = asyncio.run(run())

    products = _extract_products(_raw_products)

    print("\n========= GOAL 1: PER-PRODUCT PAYOUT TABLE =========")
    print(f"raw fetch-supplier-products bodies captured: "
          f"{sum(1 for e in _raw_products if 'fetch-supplier-products' in e['url'])}")
    print(f"raw JSON persisted to: {RAW_PRODUCTS_PATH}")
    print(f"products parsed: {len(products)}")
    if products:
        hdr = f"{'product_id':<14}{'category':<24}{'price':>8}{'payout':>9}{'ded%':>7}{'wdrp_p':>8}{'wdrp_pay':>9}{'min_rec':>9}"
        print(hdr)
        print("-" * len(hdr))
        for p in products:
            print(f"{str(p['product_id'] or '?'):<14}"
                  f"{str(p['category_name'] or p['category_id'] or '?')[:23]:<24}"
                  f"{str(p['current_price'] or ''):>8}"
                  f"{str(p['current_transfer_price'] or ''):>9}"
                  f"{str(p['effective_deduction_pct'] or ''):>7}"
                  f"{str(p['current_wdrp_price'] or ''):>8}"
                  f"{str(p['current_wdrp_transfer_price'] or ''):>9}"
                  f"{str(p['minimum_recommendation_price'] or ''):>9}")

    print("\n========= GOAL 2: STATUS / AGREEMENT / KYC FIELDS =========")
    print(json.dumps(f.get("status_fields", {}), indent=2, default=str))
    print(f"\nstatus snapshot urls: {f.get('status_snapshot_urls')}")
    print(f"status snapshots persisted to: {STATUS_PATH}")

    print("\n========= GOAL 2: RATE-CARD / SETTLEMENT RETRY =========")
    print("ratecard_attempts:", json.dumps(f.get("ratecard_attempts", []), indent=2, default=str))
    print("settlement_attempts:", json.dumps(f.get("settlement_attempts", []), indent=2, default=str))
    print("goal2_dom:", json.dumps(f.get("goal2_dom", {}), indent=2, default=str))

    print("\n========= RUN META =========")
    meta = {k: f[k] for k in ("supplier_id", "identifier", "supplier_products_captured",
                              "soft_403_seen", "blocked_endpoints", "hard_stop")}
    print(json.dumps(meta, indent=2, default=str))
    print("===================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
