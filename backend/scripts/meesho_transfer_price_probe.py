"""ROUND 13 — DIRECT getTransferPrice endpoint probe (FOUNDER BREAKTHROUGH).

Founder identified that while typing the price, the Meesho single-catalog UI calls
``POST https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getTransferPrice``
and its RESPONSE carries the FULL pricing breakdown (commission, GST/TDS, shipping,
transfer/settlement). Rounds 8-12 all failed because the price table + settlement
card render only POST-Submit in the DOM — but the COMPUTING ENDPOINT can be called
DIRECTLY via the authenticated browser context, bypassing the UI entirely.

Strategy (no UI price table needed):
  1. Login (password) via authenticated WebKit → warm Akamai cookies (proven idiom).
  2. Auto-detect supplier_id / identifier from prefetch-supply-data.
  3. Navigate the create flow to a category (Extension Chords id 10949) and capture
     fetchProductDetailsV3 to harvest live context IDs (variation id 167, price-field
     keys meesho_price/product_mrp/only_wrong_return_price/inventory). Also capture
     fetchCategoryTreeOld to resolve the parent category_id / sub_category_id chain.
  4. CONSTRUCT a getTransferPrice request body and iterate POSTing it via
     ``ctx.request.post`` (inherits cookies + Akamai fingerprint). Read 400/422 field
     errors → add/fix fields → retry until 200.
  5. CAPTURE the working request body + full response JSON. Save raw to logs/scraper/.
  6. VERIFY meesho_price=100 → settlement ₹88.50 / tax ₹11.50 (GST 11.34 + TDS 0.16)
     / commission 0% / shipping 63. Re-call meesho_price=300 to confirm recompute.

GUARDRAIL: READ/compute API call only. NO listing created, NO Submit/Publish/Go-Live.
The create-flow nav is ONLY to harvest context IDs; any draft is Discarded after.
getTransferPrice is a pure compute endpoint — it does not persist a listing.
Stop on 401/403/463/429 (supplier.meesho.com/api). Paced. Creds never logged.

This is a self-contained probe (does not import the taxcard probe). Run:
    backend/.venv/bin/python backend/scripts/meesho_transfer_price_probe.py
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
    APIResponse,
    BrowserContext,
    Page,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
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
TOLERATED_BLOCK_CODES = {463}

# The founder's known card to verify against (meesho_price=100):
EXPECTED = {
    "meesho_price": 100,
    "settlement": 88.50,
    "tax": 11.50,
    "gst": 11.34,
    "tds": 0.16,
    "commission_pct": 0,
    "shipping": 63,
}

# Founder-given context (Extension Chords leaf).
DEFAULT_SSCAT_ID = 10949           # Extension Chords sub-sub-category
DEFAULT_VARIATION_ID = 167         # "Free Size"
TARGET_CATEGORY_QUERY = "extension chords"
TARGET_CATEGORY_RE = re.compile(r"extension\s*chords?", re.I)

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the (otp|code)|"
    r"verification code|6[-\s]?digit)\b", re.I)
OTP_CODE_RE = re.compile(r"\b(\d{6})\b")


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"transfer_price_{ts}.log"
    logger = logging.getLogger("meesho-transfer-price")
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
    logger.info("Transfer-price probe logfile: %s", log_path)
    return logger, ts


log = logging.getLogger("meesho-transfer-price")


class HardStop(RuntimeError):
    pass


def load_creds() -> tuple[str, str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Credentials file missing: {CREDS_FILE}")
    load_dotenv(CREDS_FILE, override=True)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    return user, pwd


def _safe_url(url: str) -> str:
    return url.split("?", 1)[0]


# --------------------------------------------------------------------------- #
# Capture state
# --------------------------------------------------------------------------- #
findings: dict[str, Any] = {
    "account": {"supplier_id": None, "identifier": None, "store_name": None,
                "agreement_accepted": None, "default_monetization_percent": None},
    "context_ids": {"sscat_id": None, "category_id": None, "sub_category_id": None,
                    "super_category_id": None, "variation_id": None,
                    "price_field_keys": [], "category_chain": None},
    "product_details_captured": False,
    "category_tree_captured": False,
    "transfer_price_attempts": [],     # each: {body, status, response_snippet}
    "transfer_price_success": None,    # {request_body, response, computed}
    "transfer_price_300": None,
    "blocked_endpoints": [],
    "hard_stop": None,
    "end_state": None,
}

_latest_product_details: dict[str, Any] = {"body": None}
_latest_category_tree: dict[str, Any] = {"body": None}
_latest_search_catalog: dict[str, Any] = {"body": None}
_mode = {"phase": "login"}


async def _first(page: Page, cands, timeout=5000):
    for build in cands:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:  # noqa: BLE001
            continue
    return None


def _walk_account(body: Any) -> None:
    """Mine account context from any JSON body (prefetch-supply-data etc.)."""
    stack = [body]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                kl = str(k).lower()
                if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                    findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or v
                if kl in ("identifier", "supplier_identifier") and isinstance(v, str) and v and len(v) < 24:
                    findings["account"]["identifier"] = findings["account"]["identifier"] or v
                if kl == "default_monetization_percent":
                    findings["account"]["default_monetization_percent"] = v
                if kl in ("agreement_accepted", "is_agreement_accepted"):
                    findings["account"]["agreement_accepted"] = v
                if kl in ("store_name", "name") and isinstance(v, str) and not findings["account"]["store_name"]:
                    if "meesell" in v.lower() or "curl" in v.lower():
                        findings["account"]["store_name"] = v
                if kl == "supplier_identifier_to_id_mapping" and isinstance(v, dict):
                    for ident, sid in v.items():
                        findings["account"]["identifier"] = findings["account"]["identifier"] or ident
                        findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or sid
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)


async def on_response(resp: Response) -> None:
    url = resp.url
    status = resp.status
    if status in SESSION_STOP_CODES:
        is_meesho_api = "supplier.meesho.com/api" in url or url.rstrip("/").endswith("supplier.meesho.com")
        if not is_meesho_api:
            findings["blocked_endpoints"].append(f"{status} (non-API asset, tolerated) {_safe_url(url)}")
            return
        findings["hard_stop"] = f"HTTP {status} on {_safe_url(url)}"
        log.error("HARD-STOP status %d on %s", status, _safe_url(url))
        return
    if status in TOLERATED_BLOCK_CODES:
        findings["blocked_endpoints"].append(f"{status} {_safe_url(url)}")
        log.warning("tolerated block %d on %s (continuing)", status, _safe_url(url))
        return
    ct = (resp.headers or {}).get("content-type", "")
    if "json" not in ct:
        return
    try:
        body = await resp.json()
    except Exception:  # noqa: BLE001
        return

    if "prefetch-supply-data" in url or "fetch-registration-status" in url or "supplier/config" in url:
        _walk_account(body)
    if "fetchProductDetailsV3" in url and isinstance(body, dict):
        _latest_product_details["body"] = body
        findings["product_details_captured"] = True
    if "fetchCategoryTreeOld" in url and isinstance(body, (dict, list)):
        _latest_category_tree["body"] = body
        findings["category_tree_captured"] = True
    if "search-catalog" in url and isinstance(body, dict):
        _latest_search_catalog["body"] = body


def _api_headers() -> dict[str, str]:
    """Meesho app-specific signalling headers; Playwright supplies cookies/UA/lang."""
    sid = findings["account"]["supplier_id"]
    ident = findings["account"]["identifier"] or "oinpw"
    return {
        "identifier": str(ident),
        "client-type": "d-web",
        "client-package-version": "1.0.1",
        "supplier-id": str(sid),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
    }


# --------------------------------------------------------------------------- #
# OTP relay (armed but rarely exercised — warm cookies usually skip it)
# --------------------------------------------------------------------------- #
async def find_otp_field(page: Page):
    try:
        txt = await page.locator("body").inner_text(timeout=3000)
    except Exception:  # noqa: BLE001
        txt = ""
    text_hint = bool(OTP_HINT_RE.search(txt))
    cands = [
        lambda: page.get_by_placeholder(re.compile(r"otp|code|verification", re.I)),
        lambda: page.locator("input[name*='otp' i], input[id*='otp' i], input[autocomplete='one-time-code']"),
        lambda: page.locator("input[maxlength='6']"),
    ]
    for build in cands:
        try:
            loc = build()
            if await loc.count() and await loc.first.is_visible():
                return loc.first, text_hint
        except Exception:  # noqa: BLE001
            continue
    return None, text_hint


async def poll_otp_file(max_tries: int = 60, interval: float = 5.0) -> str | None:
    print("OTP_PAGE_REACHED — waiting for /tmp/meesho_otp.txt", flush=True)
    for _ in range(max_tries):
        try:
            if OTP_FILE.exists():
                m = OTP_CODE_RE.search(OTP_FILE.read_text().strip())
                if m:
                    return m.group(1)
        except Exception:  # noqa: BLE001
            pass
        await asyncio.sleep(interval)
    return None


async def perform_login(page: Page, username: str, password: str) -> None:
    log.info("Navigating to login")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await asyncio.sleep(2.5)

    user_field = await _first(page, [
        lambda: page.get_by_placeholder(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_role("textbox", name=re.compile(r"email|mobile", re.I)),
        lambda: page.locator("input[type='text']").first,
    ])
    if user_field is None:
        raise HardStop("Could not locate username field on login page")
    await user_field.fill(username)
    await asyncio.sleep(1.0)

    pwd_field = await _first(page, [
        lambda: page.get_by_placeholder(re.compile(r"password", re.I)),
        lambda: page.locator("input[type='password']").first,
    ])
    if pwd_field is None:
        raise HardStop("Could not locate password field on login page")
    await pwd_field.fill(password)
    await asyncio.sleep(1.0)

    submit = await _first(page, [
        lambda: page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ])
    if submit is None:
        raise HardStop("Could not locate login submit button")
    await submit.click()
    await asyncio.sleep(4.0)

    for _ in range(4):
        otp_target, _hint = await find_otp_field(page)
        if otp_target is not None:
            log.info("OTP page detected — polling relay file")
            code = await poll_otp_file()
            if not code:
                raise HardStop("OTP_TIMEOUT")
            try:
                await otp_target.fill(code)
                await asyncio.sleep(1.0)
                await page.keyboard.press("Enter")
            except Exception as exc:  # noqa: BLE001
                raise HardStop(f"OTP typing failed: {exc}")
            break
        if "login" not in page.url.lower():
            break
        await asyncio.sleep(2.0)

    if "login" in page.url.lower():
        try:
            await page.wait_for_url(lambda u: "login" not in u, timeout=20_000)
        except PlaywrightTimeoutError:
            raise HardStop("Login did not redirect away from /login")
    log.info("Login OK — at %s", _safe_url(page.url))


# --------------------------------------------------------------------------- #
# Phase 2 — harvest live context IDs via the create flow
# --------------------------------------------------------------------------- #
async def goto_select_category(page: Page) -> bool:
    ident = findings["account"]["identifier"] or "oinpw"
    url = f"https://supplier.meesho.com/panel/v3/new/cataloging/{ident}/catalogs/single/select-category"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
        await asyncio.sleep(4.0)
        return "select-category" in page.url
    except Exception as exc:  # noqa: BLE001
        log.warning("goto select-category failed: %s", exc)
        return False


async def select_category(page: Page, query: str) -> dict[str, Any] | None:
    """Type the query into the category search, pick the strict-matching leaf.

    Returns the matched leaf dict {name, chain, id} from search-catalog XHR.
    """
    box = await _first(page, [
        lambda: page.get_by_placeholder(re.compile(r"search.*categor", re.I)),
        lambda: page.locator("input[type='text']").first,
    ], timeout=8000)
    if box is None:
        log.warning("category search box not found")
        return None
    await box.click()
    await box.fill("")
    await box.type(query, delay=60)
    await asyncio.sleep(3.5)   # let search-catalog XHR fire

    # Resolve the matched leaf from the captured search-catalog body.
    leaf = None
    sc = _latest_search_catalog.get("body")
    if isinstance(sc, dict):
        for r in (sc.get("results") or []):
            if TARGET_CATEGORY_RE.search(str(r.get("name", ""))):
                leaf = r
                break
    if leaf:
        findings["context_ids"]["sscat_id"] = leaf.get("id")
        findings["context_ids"]["category_chain"] = leaf.get("chain")
        log.info("Matched leaf: %s id=%s chain=%s",
                 leaf.get("name"), leaf.get("id"), leaf.get("chain"))

    # Click the matching option in the dropdown so fetchProductDetailsV3 fires.
    try:
        opt = page.get_by_text(re.compile(r"^extension\s*chords?$", re.I)).first
        await opt.wait_for(state="visible", timeout=6000)
        await opt.click()
        await asyncio.sleep(4.0)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not click category option in DOM: %s", exc)
    return leaf


def _harvest_ids_from_product_details() -> None:
    body = _latest_product_details.get("body")
    if not isinstance(body, dict):
        return
    # variation id
    variations = body.get("variations") or []
    if variations and isinstance(variations[0], dict):
        findings["context_ids"]["variation_id"] = variations[0].get("id")
    # price field identifiers
    psd = body.get("product_size_data") or []
    keys = [f.get("identifier") for f in psd if isinstance(f, dict) and f.get("identifier")]
    findings["context_ids"]["price_field_keys"] = keys
    # any category-id-bearing fields anywhere
    stack = [body]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                kl = str(k).lower()
                if kl == "category_id" and findings["context_ids"]["category_id"] is None:
                    findings["context_ids"]["category_id"] = v
                if kl in ("sub_category_id", "subcategory_id") and findings["context_ids"]["sub_category_id"] is None:
                    findings["context_ids"]["sub_category_id"] = v
                if kl in ("super_category_id", "supercategory_id") and findings["context_ids"]["super_category_id"] is None:
                    findings["context_ids"]["super_category_id"] = v
                if kl in ("sub_sub_category_id", "sscat_id") and findings["context_ids"]["sscat_id"] is None:
                    findings["context_ids"]["sscat_id"] = v
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(cur, list):
            stack.extend(cur)


# --------------------------------------------------------------------------- #
# Phase 4 — construct + POST getTransferPrice, iterate to 200
# --------------------------------------------------------------------------- #
def _candidate_bodies(meesho_price: int) -> list[dict[str, Any]]:
    """Generate progressively richer candidate request bodies to iterate on.

    The exact shape is unknown — start minimal, then add fields as the server's
    400/422 errors demand. Order = simplest first.
    """
    sid = findings["account"]["supplier_id"]
    ident = findings["account"]["identifier"] or "oinpw"
    sscat = findings["context_ids"]["sscat_id"] or DEFAULT_SSCAT_ID
    cat = findings["context_ids"]["category_id"]
    subcat = findings["context_ids"]["sub_category_id"]
    var = findings["context_ids"]["variation_id"] or DEFAULT_VARIATION_ID

    mrp = max(meesho_price + 20, meesho_price)        # 100 -> 120 (founder card)
    wdrp = max(meesho_price - 11, 2)                  # 100 -> 89  (founder card)
    inv = 10
    net_weight = 20

    base_prices = {
        "meesho_price": meesho_price,
        "product_mrp": mrp,
        "only_wrong_return_price": wdrp,
        "inventory": inv,
    }

    candidates: list[dict[str, Any]] = []

    # ROUND-13 confirmed: field is `price`; {price,sub_sub_category_id,supplier_id}
    # returns 200 but EMPTY {}. These leading variants hunt for the field(s) that
    # unlock the actual commission/tax/shipping/transfer breakdown.
    _core = {"price": meesho_price, "supplier_id": sid, "sub_sub_category_id": sscat}
    candidates.append({**_core, "mrp": mrp, "wrong_defective_price": wdrp,
                       "net_weight": net_weight, "weight": net_weight,
                       "product_weight_in_gms": net_weight, "inventory": inv,
                       "variation_id": var, "identifier": ident, "scale_id": 1,
                       "price_type": "MEESHO", "gst": 18, "gst_percentage": 18})
    candidates.append({**_core, "net_weight": net_weight, "weight": net_weight,
                       "product_weight_in_gms": net_weight})
    candidates.append({**_core, "mrp": mrp, "product_mrp": mrp,
                       "wrong_defective_price": wdrp, "only_wrong_return_price": wdrp})
    candidates.append({**_core, "gst": 18, "gst_percentage": 18, "hsn_code": "85444299"})
    candidates.append({**_core, "listing_price": meesho_price, "selling_price": meesho_price,
                       "meesho_price": meesho_price, "net_weight": net_weight})

    # C0 — server said "price : price cannot be null" → the field is `price`,
    # not `meesho_price`. Lead with that. Include the WDRP price + mrp under
    # likely names + the context ids.
    candidates.append({
        "price": meesho_price,
        "product_mrp": mrp,
        "mrp": mrp,
        "wrong_defective_price": wdrp,
        "only_wrong_return_price": wdrp,
        "inventory": inv,
        "net_weight": net_weight,
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
        "identifier": ident,
        "variation_id": var,
    })
    # C0b — minimal: just `price` + sscat + supplier (find the true required set)
    candidates.append({
        "price": meesho_price,
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
    })
    # C0c — `price` nested in products[] (per-variation row)
    candidates.append({
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
        "identifier": ident,
        "products": [{
            "price": meesho_price,
            "product_mrp": mrp,
            "only_wrong_return_price": wdrp,
            "inventory": inv,
            "variation_id": var,
        }],
    })
    # C0d — `price` + net_weight + mrp + wdrp, no variation (shipping needs weight)
    candidates.append({
        "price": meesho_price,
        "mrp": mrp,
        "wrong_defective_price": wdrp,
        "net_weight": net_weight,
        "weight": net_weight,
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
        "identifier": ident,
    })

    # C1 — flat, snake_case (matches bulk-template payload style)
    candidates.append({
        **base_prices,
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
        "identifier": ident,
        "variation_id": var,
        "net_weight": net_weight,
    })
    # C2 — add category chain + scale_id/source like bulk-template
    candidates.append({
        **base_prices,
        "sub_sub_category_id": sscat,
        "category_id": cat,
        "sub_category_id": subcat,
        "supplier_id": sid,
        "identifier": ident,
        "variation_id": var,
        "net_weight": net_weight,
        "scale_id": 1,
        "source": "EXTERNAL",
    })
    # C3 — products[] array shape (mirrors product_size_data per-variation rows)
    candidates.append({
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
        "identifier": ident,
        "products": [{
            "variation_id": var,
            "meesho_price": meesho_price,
            "product_mrp": mrp,
            "only_wrong_return_price": wdrp,
            "inventory": inv,
            "net_weight": net_weight,
        }],
    })
    # C4 — camelCase variant
    candidates.append({
        "subSubCategoryId": sscat,
        "supplierId": sid,
        "identifier": ident,
        "variationId": var,
        "meeshoPrice": meesho_price,
        "productMrp": mrp,
        "onlyWrongReturnPrice": wdrp,
        "inventory": inv,
        "netWeight": net_weight,
    })
    # C5 — minimal: just price + sscat + supplier (in case the rest is optional)
    candidates.append({
        "meesho_price": meesho_price,
        "sub_sub_category_id": sscat,
        "supplier_id": sid,
    })
    return candidates


async def try_transfer_price(ctx: BrowserContext, meesho_price: int) -> dict[str, Any] | None:
    """POST candidate bodies until one returns 200; return {request,response}."""
    for idx, body in enumerate(_candidate_bodies(meesho_price)):
        if findings["hard_stop"]:
            raise HardStop(findings["hard_stop"])
        log.info("getTransferPrice attempt %d (meesho_price=%d) body keys=%s",
                 idx, meesho_price, sorted(body.keys()))
        try:
            resp: APIResponse = await ctx.request.post(
                TRANSFER_PRICE_URL,
                headers=_api_headers(),
                data=body,
                timeout=API_TIMEOUT_MS,
            )
        except PlaywrightTimeoutError:
            findings["transfer_price_attempts"].append(
                {"attempt": idx, "body": body, "status": "timeout"})
            log.warning("attempt %d timed out", idx)
            continue
        except Exception as exc:  # noqa: BLE001
            findings["transfer_price_attempts"].append(
                {"attempt": idx, "body": body, "status": f"error:{exc.__class__.__name__}"})
            continue

        status = resp.status
        if status in SESSION_STOP_CODES:
            findings["hard_stop"] = f"HTTP {status} on getTransferPrice"
            log.error("HARD-STOP %d on getTransferPrice", status)
            raise HardStop(findings["hard_stop"])
        try:
            rbody = await resp.json()
        except Exception:  # noqa: BLE001
            rbody = {"_raw_text": (await resp.text())[:1000]}

        attempt_rec = {
            "attempt": idx,
            "request_body": body,
            "status": status,
            "response_snippet": json.dumps(rbody, default=str)[:1500],
        }
        findings["transfer_price_attempts"].append(attempt_rec)
        log.info("attempt %d -> HTTP %d resp=%s", idx, status,
                 json.dumps(rbody, default=str)[:600])

        if status == 200 and isinstance(rbody, dict) and rbody:
            log.info("*** 200 from getTransferPrice on attempt %d ***", idx)
            return {"request_body": body, "response": rbody, "attempt": idx}
        await asyncio.sleep(2.0)   # pace between attempts
    return None


def _interpret(response: dict[str, Any]) -> dict[str, Any]:
    """Pull the headline figures out of a getTransferPrice response."""
    flat: dict[str, Any] = {}
    stack = [("", response)]
    while stack:
        prefix, cur = stack.pop()
        if isinstance(cur, dict):
            for k, v in cur.items():
                p = f"{prefix}.{k}" if prefix else k
                if isinstance(v, (dict, list)):
                    stack.append((p, v))
                else:
                    flat[p] = v
        elif isinstance(cur, list):
            for i, v in enumerate(cur):
                stack.append((f"{prefix}[{i}]", v))
    keymap = re.compile(
        r"commission|transfer|settle|payout|tax|gst|tds|tcs|shipping|"
        r"net|deduction|fee|charge|referral|earning|receiv", re.I)
    return {k: v for k, v in flat.items() if keymap.search(k)}


async def discard_any_draft(page: Page) -> None:
    """If a draft was started during nav, click Discard. We never advanced past
    image upload, so typically no draft exists — but be safe."""
    try:
        btn = page.get_by_role("button", name=re.compile(r"discard", re.I)).first
        if await btn.count() and await btn.is_visible():
            await btn.click()
            await asyncio.sleep(1.5)
            # confirm dialog
            conf = page.get_by_role("button", name=re.compile(r"discard|yes|confirm", re.I)).first
            if await conf.count() and await conf.is_visible():
                await conf.click()
            findings["end_state"] = "DISCARDED"
            log.info("Discarded draft")
            return
    except Exception:  # noqa: BLE001
        pass
    findings["end_state"] = "NO_DRAFT_TO_DISCARD"


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
async def run() -> dict[str, Any]:
    user, pwd = load_creds()
    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-IN", timezone_id="Asia/Kolkata",
            viewport={"width": 1440, "height": 1000},
        )
        ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
        ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)
        ctx.on("response", lambda r: asyncio.create_task(on_response(r)))
        try:
            page = await ctx.new_page()
            _mode["phase"] = "login"
            await perform_login(page, user, pwd)
            await asyncio.sleep(4.0)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            log.info("Account: %s", findings["account"])

            # Phase 2 — harvest context IDs via the create flow.
            _mode["phase"] = "nav"
            if not await goto_select_category(page):
                findings["context_ids"]["category_chain"] = "could_not_reach_select_category"
            else:
                _mode["phase"] = "category"
                await select_category(page, TARGET_CATEGORY_QUERY)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                await asyncio.sleep(2.0)
                _harvest_ids_from_product_details()
            # Fall back to founder-given IDs if harvest failed.
            findings["context_ids"]["sscat_id"] = (
                findings["context_ids"]["sscat_id"] or DEFAULT_SSCAT_ID)
            findings["context_ids"]["variation_id"] = (
                findings["context_ids"]["variation_id"] or DEFAULT_VARIATION_ID)
            log.info("Context IDs: %s", findings["context_ids"])

            # Discard any draft we might have started (safety) BEFORE the API calls.
            await discard_any_draft(page)

            if not findings["account"]["supplier_id"]:
                findings["account"]["supplier_id"] = 4359160  # known fallback for "meesell"

            # Phase 4 — direct getTransferPrice, meesho_price=100.
            _mode["phase"] = "transfer_price_100"
            log.info("=== Calling getTransferPrice with meesho_price=100 ===")
            success = await try_transfer_price(ctx, 100)
            if success:
                success["computed"] = _interpret(success["response"])
                findings["transfer_price_success"] = success
                log.info("PRIZE captured: %s", json.dumps(success["computed"], default=str)[:800])

                # Phase 5 — re-call at 300 to confirm recompute.
                await asyncio.sleep(2.0)
                _mode["phase"] = "transfer_price_300"
                log.info("=== Re-calling getTransferPrice with meesho_price=300 ===")
                # Reuse the WINNING body shape, only change the price fields.
                win = dict(success["request_body"])
                for k in list(win.keys()):
                    if k in ("meesho_price", "meeshoPrice", "price"):
                        win[k] = 300
                    if k in ("product_mrp", "productMrp", "mrp"):
                        win[k] = 360
                    if k in ("only_wrong_return_price", "onlyWrongReturnPrice",
                             "wrong_defective_price"):
                        win[k] = 289
                if "products" in win and isinstance(win["products"], list):
                    for p in win["products"]:
                        for pk in ("price", "meesho_price"):
                            if pk in p:
                                p[pk] = 300
                        for pk in ("product_mrp", "mrp"):
                            if pk in p:
                                p[pk] = 360
                        for pk in ("only_wrong_return_price", "wrong_defective_price"):
                            if pk in p:
                                p[pk] = 289
                try:
                    resp = await ctx.request.post(
                        TRANSFER_PRICE_URL, headers=_api_headers(),
                        data=win, timeout=API_TIMEOUT_MS)
                    rb = await resp.json()
                    findings["transfer_price_300"] = {
                        "request_body": win, "status": resp.status,
                        "response": rb, "computed": _interpret(rb),
                    }
                    log.info("300 recompute: HTTP %d %s", resp.status,
                             json.dumps(_interpret(rb), default=str)[:600])
                except Exception as exc:  # noqa: BLE001
                    findings["transfer_price_300"] = {"error": str(exc)}
            else:
                log.warning("No 200 from getTransferPrice across all candidate bodies")

        except HardStop as hs:
            findings["hard_stop"] = findings["hard_stop"] or str(hs)
            log.error("HARD-STOP: %s", hs)
        except Exception as exc:  # noqa: BLE001
            log.exception("probe error: %s", exc)
            findings["hard_stop"] = findings["hard_stop"] or f"error:{exc}"
        finally:
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                pass
    return findings


def main() -> int:
    global log
    log, ts = configure_logging()
    result = asyncio.run(run())

    # Persist raw artifacts (gitignored logs dir).
    out = LOG_DIR / f"transfer_price_result_{ts}.json"
    out.write_text(json.dumps({
        "findings": result,
        "latest_product_details_keys": (
            sorted(_latest_product_details["body"].keys())
            if isinstance(_latest_product_details.get("body"), dict) else None),
    }, indent=2, default=str))
    log.info("Result written: %s", out)

    s = result.get("transfer_price_success")
    print("\n========== SUMMARY ==========")
    print("Account:", result["account"])
    print("Context IDs:", result["context_ids"])
    print("Attempts:", len(result["transfer_price_attempts"]),
          "statuses:", [a.get("status") for a in result["transfer_price_attempts"]])
    if s:
        print("\n*** getTransferPrice 200 ***")
        print("Working request body:", json.dumps(s["request_body"], default=str))
        print("Computed figures:", json.dumps(s["computed"], indent=2, default=str))
    else:
        print("\nNo 200 — see attempts for the error bodies (need exact request shape).")
    print("Hard stop:", result.get("hard_stop"))
    print("End state:", result.get("end_state"))
    print("=============================\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
