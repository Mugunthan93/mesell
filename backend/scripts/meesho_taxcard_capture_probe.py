"""Meesho ADD-CATALOG RIGHT-SIDE TAX-DETAIL-CARD capture probe — ROUND 8.

FOUNDER round-2 of option-2 (read-the-preview, NO go-live)
----------------------------------------------------------
Round 7 reached the "Add Product Details" step but NEVER reached the price
INPUT cells (they are per-size table columns gated behind the FULL ~30-field
mandatory form). Because it never entered prices, it never triggered the
RIGHT-SIDE TAX DETAIL CARD the founder confirms updates when prices change.

THIS run must:
  1. Log in (proven auth-WebKit + Akamai-bypass idiom).
  2. Reach Add-SINGLE-Catalog by REAL sidebar nav; select ONE category
     (default target "Hair Bands" or "Hair Spa" — report id/name).
  3. Upload the placeholder image; Continue → "Add Product Details".
  4. ⭐ FILL ALL BLOCKING MANDATORY FIELDS with dummy-but-valid values so the
     Meesho Price / MRP / Wrong-Defective / Inventory input cells RENDER:
       - Size  (pick first option, e.g. "Free Size"/"S"/"L")
       - every mandatory attribute dropdown (~12; pick the FIRST valid option)
       - the 9-field Manufacturer/Packer/Importer compliance block
         (name/address/pincode — dummy valid: pincode 560001)
       - product_weight_in_gms, any pincode fields
       - product name / style code text
  5. ⭐ ENTER PRICES: Meesho Price 150 / MRP 400 / Wrong-Defective 140 /
     Inventory 5. Then RE-ENTER a SECOND Meesho Price (300) to watch the
     right-side card RECALCULATE (proves price-reactivity + reveals formula).
  6. ⭐⭐ CAPTURE THE RIGHT-SIDE TAX DETAIL CARD: every line + label + value
     (GST/TCS/TDS/commission/shipping/settlement-payout/margin), AND the XHR
     that computes it on price change (endpoint + request payload + full
     response body). Screenshot the card at BOTH price points.
  7. Click "Discard Catalog". Confirm getCatalogUploadPerformance
     total_upload_count stays 0. Report end-state.

ABSOLUTE HARD LINE (unchanged): NEVER Publish / Submit / Submit-for-QC /
List / Go-Live / any final action that creates a sellable listing or submits
for review. A strict deny-list blocks those verbs. End on Discard Catalog.

Output (all gitignored)
-----------------------
  * logs/scraper/taxcard_capture_<ts>.log
  * logs/scraper/taxcard_capture_xhrs_<ts>.json   (raw price/compute/config XHR bodies)
  * logs/scraper/taxcard_p1_150.png / taxcard_p2_300.png   (card at both prices)
  * logs/scraper/taxcard_dom_p1.txt / taxcard_dom_p2.txt
  * stdout JSON summary.
Nothing committed. Nothing under backend/app/data written. No creds logged.
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
PLACEHOLDER_IMG = Path("/tmp/meesell_placeholder_1200.jpg")

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
NEUTRAL_URL = LOGIN_URL
LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000

SESSION_STOP_CODES = {401, 403, 429}
TOLERATED_BLOCK_CODES = {463}

# Dummy-but-valid compliance values.
DUMMY = {
    "name": "Test Supplier Co",
    "address": "12 Test Street, Test Area, Bengaluru",
    "pincode": "560001",
    "weight": "100",
    "style": "TST-001",
    "product_name": "Test Placeholder Product",
    "generic": "Test Product",
    "hsn": "",          # leave HSN to its own picker if present
}

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the code)\b", re.I)

# The computing XHR for the right-side card. Round-7 found the create flow's
# fetchProductDetailsV3 has no commission, BUT a SEPARATE price-compute XHR
# may fire when prices are entered (the card the founder sees). Capture EVERY
# price-namespace XHR during the price phase, broadly.
PRICE_COMPUTE_XHR_RE = re.compile(
    r"price|pricing|commission|referral[-_]?fee|monetization|payout|transfer|"
    r"break[-_]?up|breakup|fee|charge|tax|gst|tcs|tds|deduction|net[-_]?amount|"
    r"earning|settle|margin|estimate|calculate|recommend|wdrp|"
    r"productprice|pricerecommend|fetchprice|getprice|profitability|"
    r"effective[-_]?price|landing[-_]?price|selling[-_]?price", re.I)
CONFIG_XHR_RE = re.compile(
    r"prefetch-supply-data|supplier/config|fetch-registration-status|"
    r"fetch-home|fetch-supplier-products|getCatalogUploadPerformance|fetch-sscat-image", re.I)
IMAGE_XHR_RE = re.compile(r"uploadSingleCatalogImages|image|upload|media|signed[-_]?url", re.I)

# JSON keys that, if present in a captured XHR, signal the tax/fee breakdown.
TAX_KEY_RE = re.compile(
    r"commission|referral|monetization|payout|transfer|net[-_]?amount|payable|"
    r"earning|gst|tcs|tds|tax|fee|charge|deduction|settle|margin|"
    r"shipping|logistic|effective|landing|breakup|break[-_]?up", re.I)
PRICE_KEY_RE = re.compile(
    r"price|mrp|cost|amount|selling|listing|meesho[-_]?price|transfer|wdrp|inventory", re.I)

# DOM text patterns for the right-side card lines.
DOM_TAXLINE_RE = re.compile(
    r"(commission|referral fee|gst|tcs|tds|tax collected|tax deducted|"
    r"shipping|logistic|you(?:'ll| will)? (?:get|receive|earn)|"
    r"net (?:amount|payout|earning|settlement)|transfer price|payout|"
    r"settlement|deduction|wrong\s*/?\s*defective|wdrp|margin|profit|"
    r"effective price|landing price|total deduction|amount you receive)"
    r"[^0-9₹%\n]{0,45}(₹\s?-?\d[\d,]*\.?\d*|-?\d{1,3}(?:\.\d+)?\s?%)",
    re.I)


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"taxcard_capture_{ts}.log"
    logger = logging.getLogger("meesho-taxcard")
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
    logger.info("Tax-card capture probe logfile: %s", log_path)
    return logger, ts


log = logging.getLogger("meesho-taxcard")


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

    async def _first(cands):
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
    "account": {"supplier_id": None, "identifier": None, "store_name": None,
                "registration_status": None, "agreement_accepted": None,
                "default_monetization_percent": None},
    "add_catalog": {"reached_via": None, "url": None, "sidebar_label": None},
    "category_selected": {"id": None, "name": None, "path": None},
    "image_upload": {"attempted": False, "accepted": None, "rejection_text": None,
                     "required_images_count": None, "upload_xhrs": []},
    "form_fill": {"size": None, "dropdowns_filled": [], "compliance_filled": [],
                  "text_filled": [], "weight": None, "pincodes": [], "notes": []},
    "price_cells_rendered": None,
    "price_points": [],          # [{point, meesho_price, mrp, wdrp, inventory, card_lines, screenshot, dom_excerpt}]
    "tax_card": {"found": None, "lines_p1": [], "lines_p2": [], "reactive": None,
                 "container_html": None, "notes": []},
    "computing_xhr": [],         # THE PRIZE: [{url, method, request_post_data, status, tax_keys, price_keys, phase, price_point}]
    "config_xhrs": [],
    "upload_count_check": {"total_upload_count": None, "single_upload_count": None, "raw": None},
    "blocked_endpoints": [],
    "discarded": None,
    "end_state": None,
    "hard_stop": None,
}

raw_xhr_bodies: dict[str, Any] = {}
_mode = {"phase": "login", "price_point": None}


def _walk_extract(obj: Any, out: dict[str, Any], depth: int = 0) -> None:
    if depth > 9:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                kl = k.lower()
                if TAX_KEY_RE.search(k) and isinstance(v, (int, float, str)):
                    out.setdefault("tax", {}).setdefault(k, v)
                if PRICE_KEY_RE.search(k) and isinstance(v, (int, float, str)):
                    out.setdefault("price", {}).setdefault(k, v)
                if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                    findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or v
                if kl in ("store_name", "shop_name", "supplier_name", "business_name") and isinstance(v, str) and v not in ("-", ""):
                    findings["account"]["store_name"] = findings["account"]["store_name"] or v
                if kl == "default_monetization_percent" and isinstance(v, (int, float, str)):
                    findings["account"]["default_monetization_percent"] = v
                if kl == "registration_status" and isinstance(v, str):
                    findings["account"]["registration_status"] = v
                if kl in ("agreement_accepted", "is_agreement_accepted") and isinstance(v, (bool, str)):
                    findings["account"]["agreement_accepted"] = v
                if kl == "required_images_count" and isinstance(v, (int, str)):
                    findings["image_upload"]["required_images_count"] = v
                if kl in ("total_upload_count", "single_upload_count") and isinstance(v, (int, str)):
                    findings["upload_count_check"][kl] = v
                if kl == "supplier_identifier_to_id_mapping" and isinstance(v, dict):
                    for ident, sid in v.items():
                        findings["account"]["identifier"] = findings["account"]["identifier"] or ident
                        findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or sid
            _walk_extract(v, out, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:150]:
            _walk_extract(item, out, depth + 1)


async def on_response(resp: Response) -> None:
    url = resp.url
    status = resp.status
    if status in SESSION_STOP_CODES:
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

    mined: dict[str, Any] = {}
    _walk_extract(body, mined)

    is_price = bool(PRICE_COMPUTE_XHR_RE.search(url))
    is_config = bool(CONFIG_XHR_RE.search(url))
    is_image = bool(IMAGE_XHR_RE.search(url))

    # Persist raw bodies for price/config/image XHRs on FIRST arrival (so a later
    # 403 can't lose the prize). During price phase, persist EVERY JSON XHR.
    persist = is_price or is_config or is_image or _mode["phase"] == "price"
    if persist:
        key = f"[{_mode.get('price_point') or _mode['phase']}] {_safe_url(url)}"
        if key not in raw_xhr_bodies:
            txt = json.dumps(body, default=str)
            raw_xhr_bodies[key] = body if len(txt) <= 300_000 else {
                "_truncated_len": len(txt),
                "_top_keys": sorted(body.keys())[:80] if isinstance(body, dict) else "[list]",
            }

    req = resp.request
    try:
        post_data = req.post_data
    except Exception:  # noqa: BLE001
        post_data = None

    record = {
        "url": _safe_url(url),
        "status": status,
        "method": req.method,
        "phase": _mode["phase"],
        "price_point": _mode.get("price_point"),
        "request_post_data": (post_data[:4000] if isinstance(post_data, str) else None),
        "top_keys": sorted(list(body.keys()))[:60] if isinstance(body, dict) else "[list]",
        "tax_keys": sorted((mined.get("tax") or {}).keys()),
        "price_keys": sorted((mined.get("price") or {}).keys()),
        "tax_sample": dict(list((mined.get("tax") or {}).items())[:30]),
        "price_sample": dict(list((mined.get("price") or {}).items())[:30]),
    }

    # Capture as a computing-XHR candidate when: price-namespace OR during the
    # price phase with any tax/price keys.
    if (is_price and not is_config) or (_mode["phase"] == "price" and not is_config and
                                        (record["tax_keys"] or record["price_keys"])):
        findings["computing_xhr"].append(record)
        log.info("COMPUTE XHR [%s/%s] %s %s tax=%s price=%s",
                 _mode["phase"], _mode.get("price_point"), req.method, _safe_url(url),
                 record["tax_keys"], record["price_keys"])
    elif is_config:
        findings["config_xhrs"].append({"url": record["url"], "status": status,
                                        "tax_keys": record["tax_keys"]})
    elif is_image:
        findings["image_upload"]["upload_xhrs"].append(
            {"url": record["url"], "status": status, "method": req.method})


def detect_identifier_from_url(url: str) -> None:
    m = re.search(r"/(?:growth|payments|fulfillment|cataloging|root)/([a-z0-9]{3,12})/", url)
    if m and m.group(1) not in ("new", "root"):
        findings["account"]["identifier"] = findings["account"]["identifier"] or m.group(1)


# ---------------------------------------------------------------------------
# Sidebar nav + category select (round-7 proven)
# ---------------------------------------------------------------------------

async def goto_single_select_category(page: Page) -> bool:
    ident = findings["account"]["identifier"] or "oinpw"
    catalog_menu = [
        page.get_by_role("link", name=re.compile(r"^\s*(catalog|cataloging|products?|my products)\s*$", re.I)),
        page.get_by_role("button", name=re.compile(r"^\s*(catalog|cataloging|products?)\s*$", re.I)),
        page.locator("a,button,span,div").filter(has_text=re.compile(r"^\s*(Catalogs?|Products?)\s*$", re.I)),
    ]
    for cand in catalog_menu:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 3)):
            try:
                el = cand.nth(i)
                if await el.is_visible():
                    await el.click(timeout=4000)
                    await asyncio.sleep(2.5)
                    break
            except Exception:  # noqa: BLE001
                continue
    add_cands = [
        page.get_by_role("link", name=re.compile(r"add (a )?single (product|catalog)", re.I)),
        page.get_by_role("button", name=re.compile(r"add (a )?single (product|catalog)", re.I)),
        page.get_by_text(re.compile(r"single (product|catalog)|add one product", re.I)),
    ]
    for cand in add_cands:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 6)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                label_txt = (await el.inner_text(timeout=1500)).strip()[:60]
                if re.search(r"bulk", label_txt, re.I):
                    continue
                await el.click(timeout=4000)
                await asyncio.sleep(4.0)
                findings["add_catalog"]["reached_via"] = "sidebar_click"
                findings["add_catalog"]["sidebar_label"] = label_txt
                findings["add_catalog"]["url"] = _safe_url(page.url)
                if "select-category" in page.url or re.search(r"catalog", page.url, re.I):
                    return True
            except Exception:  # noqa: BLE001
                continue
    url = f"https://supplier.meesho.com/panel/v3/new/cataloging/{ident}/catalogs/single/select-category"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
        await asyncio.sleep(4.0)
        findings["add_catalog"]["reached_via"] = "direct_route_fallback"
        findings["add_catalog"]["url"] = _safe_url(page.url)
        return "select-category" in page.url
    except Exception as exc:  # noqa: BLE001
        log.warning("direct route fallback failed: %s", exc)
        return False


async def select_one_category(page: Page, search: str = "hair") -> bool:
    cat_input = [
        page.get_by_placeholder(re.compile(r"search.*(category|product)", re.I)),
        page.get_by_role("textbox", name=re.compile(r"category|search", re.I)),
        page.locator("input[type='text']").first,
    ]
    for cand in cat_input:
        try:
            if await cand.count() and await cand.first.is_visible():
                await cand.first.click(timeout=3000)
                await cand.first.fill(search, timeout=3000)
                await asyncio.sleep(2.5)
                break
        except Exception:  # noqa: BLE001
            continue
    options = [
        page.get_by_role("option"),
        page.locator("[role='option'], li, .ant-select-item, .category-item, [class*='option']"),
    ]
    # Prefer a "Hair Bands" leaf (simpler attribute set than Hair Spa).
    preferred = re.compile(r"hair bands?", re.I)
    fallback_el = None
    for cand in options:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 14)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                name = (await el.inner_text(timeout=1500)).strip()
                if not name or len(name) > 90:
                    continue
                if preferred.search(name):
                    await el.click(timeout=3000)
                    await asyncio.sleep(3.5)
                    findings["category_selected"]["name"] = name[:90]
                    log.info("Selected PREFERRED category: %s", name[:90])
                    return True
                if fallback_el is None:
                    fallback_el = (cand, i, name)
            except Exception:  # noqa: BLE001
                continue
    if fallback_el is not None:
        cand, i, name = fallback_el
        try:
            await cand.nth(i).click(timeout=3000)
            await asyncio.sleep(3.5)
            findings["category_selected"]["name"] = name[:90]
            log.info("Selected fallback category: %s", name[:90])
            return True
        except Exception:  # noqa: BLE001
            pass
    findings["form_fill"]["notes"].append("No category option clickable")
    return False


# ---------------------------------------------------------------------------
# Image upload (round-7 proven)
# ---------------------------------------------------------------------------

SAFE_NEXT_RE = re.compile(r"^\s*(next|continue|proceed|save (and )?(continue|next)|done|add product details)\s*$", re.I)
GO_LIVE_DENY_RE = re.compile(
    r"submit|publish|go ?live|list product|submit for qc|send for review|"
    r"send for qc|launch|create catalog|create listing", re.I)


async def upload_placeholder_image(page: Page) -> bool:
    _mode["phase"] = "image"
    findings["image_upload"]["attempted"] = True
    if not PLACEHOLDER_IMG.exists():
        findings["image_upload"]["rejection_text"] = f"placeholder missing at {PLACEHOLDER_IMG}"
        return False
    try:
        btn = page.get_by_role("button", name=re.compile(r"add product images|upload image|add image", re.I))
        if await btn.count() and await btn.first.is_visible():
            await btn.first.click(timeout=4000)
            await asyncio.sleep(2.0)
    except Exception:  # noqa: BLE001
        pass
    file_inputs = page.locator("input[type='file']")
    try:
        n = await file_inputs.count()
    except Exception:  # noqa: BLE001
        n = 0
    if n == 0:
        findings["image_upload"]["rejection_text"] = "no file input found"
        return False
    set_ok = False
    for i in range(min(n, 4)):
        try:
            await file_inputs.nth(i).set_input_files(str(PLACEHOLDER_IMG), timeout=8000)
            set_ok = True
            log.info("set_input_files OK on file input #%d", i)
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("set_input_files #%d failed: %s", i, exc)
    if not set_ok:
        findings["image_upload"]["rejection_text"] = "set_input_files failed on all inputs"
        return False
    accepted = False
    for poll in range(8):
        await asyncio.sleep(4.0)
        if findings["image_upload"]["upload_xhrs"]:
            accepted = True
            break
        try:
            fwd = page.get_by_role("button", name=SAFE_NEXT_RE)
            if await fwd.count() and await fwd.first.is_visible():
                accepted = True
                break
        except Exception:  # noqa: BLE001
            pass
    findings["image_upload"]["accepted"] = accepted
    log.info("Image accepted=%s upload_xhrs=%d", accepted, len(findings["image_upload"]["upload_xhrs"]))
    return accepted


async def click_continue(page: Page) -> bool:
    for cand in (page.get_by_role("button", name=SAFE_NEXT_RE),
                 page.locator("button").filter(has_text=SAFE_NEXT_RE)):
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 5)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                label = (await el.inner_text(timeout=1500)).strip()
                if GO_LIVE_DENY_RE.search(label) or not SAFE_NEXT_RE.search(label):
                    continue
                log.info("Clicking SAFE advance '%s'", label[:40])
                await el.click(timeout=4000)
                await asyncio.sleep(4.5)
                return True
            except Exception:  # noqa: BLE001
                continue
    return False


# ---------------------------------------------------------------------------
# ⭐ FULL mandatory-form fill — the new round-8 capability
# ---------------------------------------------------------------------------

async def fill_all_text_inputs(page: Page) -> None:
    """Fill labelled text inputs (name, style, compliance name/address) and
    number inputs (weight, pincode) with dummy-valid values."""
    try:
        specs = await page.evaluate(
            """() => Array.from(document.querySelectorAll('input,textarea'))
                .map((e,i) => ({i, t:(e.type||e.tagName||'').toLowerCase(),
                    n:(e.name||'').toLowerCase(), p:(e.placeholder||'').toLowerCase(),
                    aria:(e.getAttribute('aria-label')||'').toLowerCase(),
                    vis:!!e.offsetParent, val:(e.value||'')}))
                .filter(f => f.vis)""")
    except Exception as exc:  # noqa: BLE001
        log.warning("field enumerate failed: %s", exc)
        return
    all_inputs = page.locator("input,textarea")
    for f in specs:
        hint = f"{f['n']} {f['p']} {f['aria']}"
        if f.get("val"):
            continue
        try:
            loc = all_inputs.nth(f["i"])
            if re.search(r"pincode|pin code|pin-code|postal", hint):
                await loc.fill(DUMMY["pincode"], timeout=2500)
                findings["form_fill"]["pincodes"].append(hint.strip()[:40])
            elif re.search(r"weight|gms|gram", hint):
                await loc.fill(DUMMY["weight"], timeout=2500)
                findings["form_fill"]["weight"] = DUMMY["weight"]
            elif re.search(r"length|width|height|dimension|depth|diameter", hint):
                await loc.fill("10", timeout=2500)
                findings["form_fill"]["text_filled"].append("dim:" + hint.strip()[:25])
            elif re.search(r"address", hint):
                await loc.fill(DUMMY["address"], timeout=2500)
                findings["form_fill"]["compliance_filled"].append("address:" + hint.strip()[:30])
            elif re.search(r"name", hint) and re.search(r"manufactur|packer|importer|seller|legal|brand", hint):
                await loc.fill(DUMMY["name"], timeout=2500)
                findings["form_fill"]["compliance_filled"].append("name:" + hint.strip()[:30])
            elif re.search(r"product name|title", hint):
                await loc.fill(DUMMY["product_name"], timeout=2500)
                findings["form_fill"]["text_filled"].append("product_name")
            elif re.search(r"style|sku code|sku id", hint):
                await loc.fill(DUMMY["style"], timeout=2500)
                findings["form_fill"]["text_filled"].append("style")
            elif f["t"] in ("text", "textarea") and re.search(r"name|enter", hint):
                # generic mandatory text — give a safe value
                await loc.fill(DUMMY["name"], timeout=2500)
                findings["form_fill"]["text_filled"].append("generic:" + hint.strip()[:25])
            else:
                continue
            await asyncio.sleep(0.4)
        except Exception:  # noqa: BLE001
            continue
    log.info("Text/number fill: compliance=%s text=%s weight=%s pincodes=%d",
             findings["form_fill"]["compliance_filled"], findings["form_fill"]["text_filled"],
             findings["form_fill"]["weight"], len(findings["form_fill"]["pincodes"]))


async def _pick_first_option(page: Page) -> str | None:
    """After a dropdown is opened, click the first concrete option in the
    portal listbox. Returns the option text, or None."""
    opt = page.locator(
        "[role='option'], .ant-select-item-option, li[class*='option'], "
        "[class*='MenuItem'], [class*='dropdown'] li, [class*='menu'] li, "
        "ul li, [class*='Option']")
    try:
        no = await opt.count()
    except Exception:  # noqa: BLE001
        no = 0
    for j in range(min(no, 25)):
        o = opt.nth(j)
        try:
            if not await o.is_visible():
                continue
            name = (await o.inner_text(timeout=1200)).strip()
            if name and 0 < len(name) < 60 and not re.search(r"^\s*(select|choose|all)\b", name, re.I):
                await o.click(timeout=2500)
                await asyncio.sleep(1.0)
                return name[:40]
        except Exception:  # noqa: BLE001
            continue
    return None


# Meesho's mandatory attribute dropdowns are <input type=text placeholder="Select">
# with a name= matching the attribute. They open a portal listbox on click.
DROPDOWN_NAMES = [
    "size", "color", "colour", "material", "pattern", "occasion", "ideal_for",
    "generic_name", "multipack", "type", "product_dimension_unit",
    "country_of_origin", "brand", "net_quantity", "fabric", "sleeve_length",
    "neck", "fit_shape", "hair_type", "concern", "flavour", "form", "skin_type",
]


async def fill_all_dropdowns(page: Page, max_rounds: int = 24) -> None:
    """Fill every mandatory attribute dropdown. Meesho renders them as
    <input type='text' name='<attr>' placeholder='Select'> that opens a portal
    listbox on click — NOT native <select>, NOT role=combobox. Target by the
    'Select' placeholder + empty value; click → pick first option."""
    # Native <select> (rare here, but cheap to cover).
    selects = page.locator("select")
    try:
        ns = await selects.count()
    except Exception:  # noqa: BLE001
        ns = 0
    for i in range(min(ns, max_rounds)):
        try:
            sel = selects.nth(i)
            if not await sel.is_visible():
                continue
            opts = await sel.locator("option").all_text_contents()
            for ot in opts:
                ot = (ot or "").strip()
                if ot and not re.search(r"^select|^choose|^-+$", ot, re.I):
                    await sel.select_option(label=ot, timeout=2500)
                    findings["form_fill"]["dropdowns_filled"].append("native:" + ot[:25])
                    await asyncio.sleep(0.5)
                    break
        except Exception:  # noqa: BLE001
            continue

    # Custom "Select"-placeholder text inputs. Re-enumerate each round because
    # the DOM mutates (and selecting one may reveal conditional dropdowns).
    for _round in range(max_rounds):
        try:
            specs = await page.evaluate(
                """() => Array.from(document.querySelectorAll('input[type=text]'))
                    .map((e,i) => ({i, n:(e.name||'').toLowerCase(),
                        p:(e.placeholder||''), val:(e.value||''), vis:!!e.offsetParent,
                        ro:e.readOnly}))
                    .filter(f => f.vis && f.val==='' &&
                        (/^select$/i.test((f.p||'').trim()) || f.ro))""")
        except Exception:  # noqa: BLE001
            specs = []
        # Only those that look like attribute dropdowns (named, empty, placeholder Select).
        targets = [s for s in specs if s["n"] and (re.fullmatch(r"select", (s["p"] or "").strip(), re.I) or s["ro"])]
        if not targets:
            break
        all_text = page.locator("input[type=text]")
        progressed = False
        for s in targets:
            try:
                el = all_text.nth(s["i"])
                # re-check still empty (a prior pick may have filled a sibling)
                if (await el.input_value() or "").strip():
                    continue
                await el.scroll_into_view_if_needed(timeout=2500)
                await el.click(timeout=2500)
                await asyncio.sleep(1.3)
                picked = await _pick_first_option(page)
                if picked is None:
                    # maybe it's a search-combobox needing a keystroke
                    try:
                        await el.type("a", delay=40)
                        await asyncio.sleep(1.2)
                        picked = await _pick_first_option(page)
                    except Exception:  # noqa: BLE001
                        pass
                if picked is None:
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:  # noqa: BLE001
                        pass
                    continue
                findings["form_fill"]["dropdowns_filled"].append(f"{s['n']}={picked}")
                if s["n"] == "size":
                    findings["form_fill"]["size"] = picked
                progressed = True
                await asyncio.sleep(0.8)
                break  # re-enumerate from scratch
            except Exception:  # noqa: BLE001
                continue
        if not progressed:
            break
    log.info("Dropdowns filled (%d): %s", len(findings["form_fill"]["dropdowns_filled"]),
             findings["form_fill"]["dropdowns_filled"])


async def price_cells_present(page: Page) -> bool:
    """Detect the Meesho Price / MRP price input cells (per-size table)."""
    try:
        hit = await page.evaluate(
            """() => {
                const ins = Array.from(document.querySelectorAll('input'));
                return ins.some(e => {
                    if (!e.offsetParent) return false;
                    const h = ((e.name||'')+' '+(e.placeholder||'')+' '+
                               (e.getAttribute('aria-label')||'')).toLowerCase();
                    return /meesho price|product_mrp|\\bmrp\\b|only_wrong_return|wrong.*defective|meesho_price/.test(h);
                });
            }""")
        if hit:
            return True
    except Exception:  # noqa: BLE001
        pass
    try:
        txt = await page.locator("body").inner_text(timeout=2500)
        return bool(re.search(r"meesho price|wrong/?\s*defective", txt, re.I))
    except Exception:  # noqa: BLE001
        return False


# ---------------------------------------------------------------------------
# ⭐⭐ Right-side tax-card capture
# ---------------------------------------------------------------------------

async def capture_tax_card(page: Page, point_label: str) -> dict[str, Any]:
    """Read the right-side tax/fee/settlement card. Strategy: dump full DOM text,
    regex the tax lines; also try to isolate the card container's outerHTML for
    the structured line list."""
    out: dict[str, Any] = {"lines": [], "excerpt": None, "container_text": None}
    try:
        txt = await page.locator("body").inner_text(timeout=4000)
    except Exception:  # noqa: BLE001
        return out
    if OTP_HINT_RE.search(txt):
        raise HardStop(f"OTP_REQUIRED — detected at {point_label}")
    for m in DOM_TAXLINE_RE.finditer(txt):
        line = re.sub(r"\s+", " ", m.group(0)).strip()[:140]
        if line not in out["lines"]:
            out["lines"].append(line)
    # Try to find the card container (a panel mentioning the breakdown terms).
    try:
        container_text = await page.evaluate(
            r"""() => {
                const terms = /commission|you.?ll receive|net amount|payout|settlement|gst|tcs|tds|total deduction|price breakup|breakup|amount you receive|effective price/i;
                const moneyRe = /₹\s?-?\d/;
                let best = null, bestScore = 0;
                for (const el of Array.from(document.querySelectorAll('div,section,aside'))) {
                    const t = el.innerText || '';
                    if (t.length < 20 || t.length > 1600) continue;
                    if (!terms.test(t)) continue;
                    const money = (t.match(/₹\s?-?\d[\d,]*/g)||[]).length;
                    const hits = (t.match(terms)||[]).length;
                    const score = hits*2 + money;
                    // prefer the SMALLEST container with high score (the card itself)
                    if (score > bestScore || (score===bestScore && best && t.length < best.length)) {
                        best = t; bestScore = score;
                    }
                }
                return best;
            }"""
        )
        if container_text:
            out["container_text"] = re.sub(r"[ \t]+", " ", container_text).strip()[:1600]
    except Exception as exc:  # noqa: BLE001
        log.warning("container extract failed: %s", exc)
    m = re.search(r".{0,80}(commission|payout|you.?ll receive|net amount|settlement|gst|tcs|breakup).{0,400}", txt, re.I)
    if m:
        out["excerpt"] = re.sub(r"\s+", " ", m.group(0)).strip()[:600]
    return out


async def _fill_labeled_number(page: Page, label_re: re.Pattern, value: str) -> bool:
    for builder in (
        lambda: page.get_by_placeholder(label_re),
        lambda: page.get_by_role("spinbutton", name=label_re),
        lambda: page.get_by_role("textbox", name=label_re),
    ):
        try:
            loc = builder()
            if await loc.count() and await loc.first.is_visible():
                await loc.first.click(timeout=2500)
                await loc.first.fill(value, timeout=2500)
                await loc.first.press("Tab")
                return True
        except Exception:  # noqa: BLE001
            continue
    # Label-proximity fallback.
    try:
        lbl = page.get_by_text(label_re, exact=False)
        cnt = await lbl.count()
        for i in range(min(cnt, 4)):
            el = lbl.nth(i)
            if not await el.is_visible():
                continue
            for xp in ("xpath=following::input[1]",
                       "xpath=ancestor::*[self::div or self::label][1]//input[1]",
                       "xpath=ancestor::*[self::div][2]//input[1]"):
                try:
                    inp = el.locator(xp)
                    if await inp.count() and await inp.first.is_visible():
                        await inp.first.click(timeout=2000)
                        await inp.first.fill(value, timeout=2000)
                        await inp.first.press("Tab")
                        return True
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass
    return False


async def enter_prices(page: Page, meesho: str, mrp: str, wdrp: str, inventory: str) -> dict[str, bool]:
    res = {}
    res["meesho_price"] = await _fill_labeled_number(page, re.compile(r"meesho price", re.I), meesho)
    await asyncio.sleep(1.0)
    res["mrp"] = await _fill_labeled_number(page, re.compile(r"^\s*mrp|maximum retail", re.I), mrp)
    await asyncio.sleep(1.0)
    res["wdrp"] = await _fill_labeled_number(page, re.compile(r"wrong.*defective", re.I), wdrp)
    await asyncio.sleep(1.0)
    res["inventory"] = await _fill_labeled_number(page, re.compile(r"inventory|stock|quantity", re.I), inventory)
    await asyncio.sleep(4.5)   # let the card compute
    return res


# ---------------------------------------------------------------------------
# Discard + upload-count safety check
# ---------------------------------------------------------------------------

DISCARD_RE = re.compile(r"discard catalog|discard( product| draft)?|delete( draft| catalog)?", re.I)
CONFIRM_DISCARD_RE = re.compile(r"^\s*(yes|discard|confirm|delete|ok|yes,? discard)\s*$", re.I)


async def discard_catalog(page: Page) -> bool:
    _mode["phase"] = "discard"
    for cand in (page.get_by_role("button", name=re.compile(r"discard catalog", re.I)),
                 page.get_by_role("button", name=DISCARD_RE),
                 page.get_by_role("link", name=DISCARD_RE),
                 page.locator("a,button").filter(has_text=re.compile(r"discard", re.I))):
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 4)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                label = (await el.inner_text(timeout=1500)).strip()
                if GO_LIVE_DENY_RE.search(label):
                    continue
                log.info("Clicking discard '%s'", label[:40])
                await el.click(timeout=4000)
                await asyncio.sleep(2.5)
                try:
                    confirm = page.get_by_role("button", name=CONFIRM_DISCARD_RE)
                    if await confirm.count() and await confirm.first.is_visible():
                        clabel = (await confirm.first.inner_text(timeout=1500)).strip()
                        if not GO_LIVE_DENY_RE.search(clabel):
                            await confirm.first.click(timeout=4000)
                            await asyncio.sleep(3.0)
                except Exception:  # noqa: BLE001
                    pass
                findings["discarded"] = True
                return True
            except Exception:  # noqa: BLE001
                continue
    findings["discarded"] = False
    findings["tax_card"]["notes"].append("Discard control not found — abandoning by nav-away")
    return False


async def verify_upload_count(page: Page) -> None:
    """Hit getCatalogUploadPerformance to confirm total_upload_count stays 0."""
    ident = findings["account"]["identifier"] or "oinpw"
    for url in (
        f"https://supplier.meesho.com/api/cataloging/getCatalogUploadPerformance",
        f"https://supplier.meesho.com/api/cataloging/bulkCatalogUpload/getCatalogUploadPerformance",
    ):
        try:
            res = await page.context.request.get(url, timeout=12000)
            if res.status == 200:
                body = await res.json()
                findings["upload_count_check"]["raw"] = body
                _walk_extract(body, {})
                log.info("getCatalogUploadPerformance -> %s", json.dumps(body, default=str)[:300])
                return
        except Exception as exc:  # noqa: BLE001
            log.warning("upload-count check failed for %s: %s", url, exc)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run() -> dict[str, Any]:
    user, pwd = load_creds()
    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True)
        ctx = await browser.new_context(
            locale="en-IN", timezone_id="Asia/Kolkata",
            viewport={"width": 1600, "height": 1000},
        )
        ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
        ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)
        ctx.on("response", lambda r: asyncio.create_task(on_response(r)))
        try:
            page = await ctx.new_page()
            _mode["phase"] = "login"
            await perform_login(page, user, pwd)
            await asyncio.sleep(5.0)
            detect_identifier_from_url(page.url)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            log.info("Account: %s", findings["account"])

            _mode["phase"] = "nav"
            if not await goto_single_select_category(page):
                findings["tax_card"]["notes"].append("Could not reach single/select-category")
                raise HardStop("Add-Catalog single flow not reached")
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])

            _mode["phase"] = "category"
            await asyncio.sleep(2.0)
            await select_one_category(page)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])

            img_ok = await upload_placeholder_image(page)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            if not img_ok:
                findings["tax_card"]["notes"].append(
                    "Image gate not satisfied: " + str(findings["image_upload"]["rejection_text"]))
                raise HardStop("Image gate not passed")

            _mode["phase"] = "advance"
            await click_continue(page)
            await asyncio.sleep(3.0)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])

            # ⭐ FULL FORM FILL until the price cells render.
            _mode["phase"] = "form_fill"
            for attempt in range(4):
                await fill_all_dropdowns(page)
                await fill_all_text_inputs(page)
                # Re-pick the Size combobox specifically if still empty.
                await asyncio.sleep(2.0)
                if await price_cells_present(page):
                    findings["price_cells_rendered"] = True
                    log.info("Price cells RENDERED after fill attempt %d", attempt)
                    break
                # Some flows need a 'Save'/'Next' within the details step to surface
                # the price table — click a SAFE advance and retry.
                await click_continue(page)
                await asyncio.sleep(2.5)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
            if findings["price_cells_rendered"] is None:
                findings["price_cells_rendered"] = await price_cells_present(page)

            # Diagnostic dump of the form state.
            try:
                dump = await page.evaluate(
                    """() => Array.from(document.querySelectorAll('input,select,textarea'))
                        .map(e => ({t:(e.type||e.tagName), n:e.name||'', p:e.placeholder||'',
                                    aria:e.getAttribute('aria-label')||'',
                                    vis:!!e.offsetParent, val:(e.value||'').slice(0,18)}))
                        .filter(f=>f.vis).slice(0,90)""")
                findings["form_fill"]["notes"].append({"fields_before_price": dump})
            except Exception:  # noqa: BLE001
                pass

            if not findings["price_cells_rendered"]:
                findings["tax_card"]["notes"].append(
                    "Price input cells did NOT render even after full-form fill — "
                    "some mandatory field likely still blank. See fields_before_price dump.")
                log.warning("Price cells did not render after full fill")

            # ⭐ PRICE POINT 1: 150 / 400 / 140 / 5
            _mode["phase"] = "price"
            _mode["price_point"] = "p1_150"
            r1 = await enter_prices(page, "150", "400", "140", "5")
            await asyncio.sleep(4.0)
            card1 = await capture_tax_card(page, "p1_150")
            try:
                await page.screenshot(path=str(LOG_DIR / "taxcard_p1_150.png"), full_page=True)
                (LOG_DIR / "taxcard_dom_p1.txt").write_text(await page.locator("body").inner_text(timeout=4000))
            except Exception:  # noqa: BLE001
                pass
            findings["price_points"].append({"point": "p1", "fills": r1,
                                             "meesho_price": 150, "mrp": 400, "wdrp": 140, "inventory": 5,
                                             "card_lines": card1["lines"],
                                             "card_container": card1["container_text"],
                                             "dom_excerpt": card1["excerpt"]})
            findings["tax_card"]["lines_p1"] = card1["lines"]
            findings["tax_card"]["container_html"] = card1["container_text"]
            log.info("P1 card lines: %s", card1["lines"])
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])

            # ⭐ PRICE POINT 2: change Meesho Price to 300 → watch recalc.
            _mode["price_point"] = "p2_300"
            await _fill_labeled_number(page, re.compile(r"meesho price", re.I), "300")
            await asyncio.sleep(5.5)
            card2 = await capture_tax_card(page, "p2_300")
            try:
                await page.screenshot(path=str(LOG_DIR / "taxcard_p2_300.png"), full_page=True)
                (LOG_DIR / "taxcard_dom_p2.txt").write_text(await page.locator("body").inner_text(timeout=4000))
            except Exception:  # noqa: BLE001
                pass
            findings["price_points"].append({"point": "p2", "meesho_price": 300,
                                             "card_lines": card2["lines"],
                                             "card_container": card2["container_text"],
                                             "dom_excerpt": card2["excerpt"]})
            findings["tax_card"]["lines_p2"] = card2["lines"]
            log.info("P2 card lines: %s", card2["lines"])

            findings["tax_card"]["found"] = bool(
                card1["lines"] or card2["lines"] or card1["container_text"]
                or any(x["tax_keys"] for x in findings["computing_xhr"]))
            findings["tax_card"]["reactive"] = bool(
                card1["lines"] and card2["lines"] and card1["lines"] != card2["lines"])

            # MANDATORY discard + upload-count safety check.
            await verify_upload_count(page)
            await discard_catalog(page)
            await verify_upload_count(page)

            try:
                _mode["phase"] = "abandon"
                await page.goto(NEUTRAL_URL, wait_until="domcontentloaded", timeout=15_000)
            except Exception:  # noqa: BLE001
                pass

            findings["end_state"] = (
                "DISCARDED (Discard Catalog clicked + abandoned)" if findings["discarded"]
                else "NOT-EXPLICITLY-DISCARDED — abandoned by nav-away; no go-live action taken")

        except HardStop as exc:
            findings["hard_stop"] = str(exc)
            findings["end_state"] = (findings.get("end_state") or
                                     "HARD-STOP before completion — no go-live action taken")
            log.error("HARD STOP: %s", exc)
            try:
                await verify_upload_count(page)
                await discard_catalog(page)
            except Exception:  # noqa: BLE001
                pass
        finally:
            await asyncio.sleep(2.0)
            try:
                await ctx.close()
            except Exception:  # noqa: BLE001
                pass
            try:
                await browser.close()
            except Exception:  # noqa: BLE001
                pass
    return {"findings": findings, "raw_xhr_bodies": raw_xhr_bodies}


def main() -> int:
    _logger, ts = configure_logging()
    log.info("==== Meesho RIGHT-SIDE TAX-CARD capture probe (round 8) @ %s ====",
             datetime.now().isoformat())
    if not PLACEHOLDER_IMG.exists():
        log.error("Placeholder image not found at %s", PLACEHOLDER_IMG)
        return 2
    result = asyncio.run(run())
    f = result["findings"]
    raw_path = LOG_DIR / f"taxcard_capture_xhrs_{ts}.json"
    try:
        raw_path.write_text(json.dumps(result["raw_xhr_bodies"], indent=2, default=str))
        log.info("Raw XHR bodies -> %s", raw_path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not persist raw bodies: %s", exc)

    print("\n========= TAX-CARD CAPTURE PROBE SUMMARY =========")
    print(json.dumps(f, indent=2, default=str))
    print("\n--- raw XHR body keys captured ---")
    for url, body in list(result["raw_xhr_bodies"].items())[:40]:
        keys = sorted(body.keys())[:50] if isinstance(body, dict) else "[list]"
        print(f"  {url}  keys={keys}")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
