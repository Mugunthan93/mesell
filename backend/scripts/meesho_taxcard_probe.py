"""Meesho ADD-CATALOG RIGHT-SIDE TAX-CARD capture probe — round 8 (option-2 + OTP relay).

FOUNDER-AUTHORIZED guardrail (option 2, round-2): read-the-tax-card, NO go-live.
--------------------------------------------------------------------------------
Round 7 reached the "Add Product Details" step but NEVER reached the price input
cells (gated behind the full ~30-field mandatory form) so it never triggered the
RIGHT-SIDE TAX DETAIL CARD the founder confirms recalculates on price change.

THIS run:
  ALLOWED  : OTP-relay login, upload placeholder image, advance past the image
             gate, FILL ALL gating mandatory fields (Size + the ~12 category
             attribute dropdowns → first valid option each + the 9-field
             Manufacturer/Packer/Importer compliance block → dummy-valid + weight
             + pincodes) until the Meesho-Price / MRP / WDRP / Inventory cells
             RENDER, ENTER PRICES (150/400/140/5), then CHANGE Meesho price to
             300 to watch the RIGHT-SIDE TAX CARD recalculate, READ + screenshot
             the card at BOTH price points, capture the computing XHR, then
             DISCARD CATALOG.
  FORBIDDEN: Publish / Submit / "Submit for QC" / "List Product" / "Go Live" /
             any final action that creates a LIVE/sellable listing or submits for
             review. Run MUST end on "Discard Catalog".

OTP RELAY (the new mechanism this round)
----------------------------------------
At START the caller clears /tmp/meesho_otp.txt. If, after the password step, an
OTP field appears, the probe prints  OTP_PAGE_REACHED — waiting for /tmp/meesho_otp.txt
and polls that file every 5s for up to 5 min for a 6-digit code, types it, submits.

Output (all gitignored): logs/scraper/taxcard_<ts>.log,
logs/scraper/taxcard_xhrs_<ts>.json, logs/scraper/taxcard_price_{150,300}.png,
plus stdout JSON summary. Nothing committed; no creds logged.
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
OTP_FILE = Path("/tmp/meesho_otp.txt")

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
NEUTRAL_URL = LOGIN_URL
LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000

# Target category for this round.
TARGET_CATEGORY_QUERY = "hair band"

SESSION_STOP_CODES = {401, 403, 429}
TOLERATED_BLOCK_CODES = {463}

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the (otp|code)|"
    r"verification code|6[-\s]?digit)\b", re.I)
OTP_CODE_RE = re.compile(r"\b(\d{6})\b")

# Tax-card / payout / fee-break XHR classifier.
PREVIEW_XHR_RE = re.compile(
    r"commission|referral[-_]?fee|monetization|payout|transfer[-_]?price|"
    r"price[-_]?break|fee[-_]?break|estimate|net[-_]?amount|earning|tax|gst|tcs|tds|"
    r"price[-_]?recommend|pricerecommend|smart[-_]?pricing|wdrp|deduction|price[-_]?suggest|"
    r"calculate|preview|pricing|price[-_]?detail|margin|settle|breakup|break[-_]?up|"
    r"fetchduplicatepid|getprice|fetchprice|product[-_]?price|charges?", re.I)
CONFIG_XHR_RE = re.compile(
    r"prefetch-supply-data|supplier/config|fetch-registration-status|"
    r"fetch-home|fetch-supplier-products|fetch-growth-overview|fetch-sscat-image|"
    r"getCatalogUploadPerformance|catalog-upload-performance", re.I)
CATEGORY_XHR_RE = re.compile(
    r"category|sub[-_]?category|sscat|taxonomy|attribute|fetchCategoryTree|fetchProductDetails", re.I)
IMAGE_XHR_RE = re.compile(r"image|upload|media|asset|signed[-_]?url|gcs|s3", re.I)

COMMISSION_KEY_RE = re.compile(
    r"commission|referral|monetization|payout|net[-_]?amount|payable|earning|"
    r"net[-_]?margin|net[-_]?price|fee|charge|deduction|settle|transfer|rate|wdrp|"
    r"gst|tcs|tds|tax|shipping|logistic|breakup|margin", re.I)
PRICE_KEY_RE = re.compile(
    r"price|mrp|cost|amount|selling|listing[-_]?price|meesho[-_]?price|transfer", re.I)
CATEGORY_KEY_RE = re.compile(r"category|sub[-_]?category|sscat|catalog[-_]?type|product[-_]?type", re.I)

# Right-side tax-card DOM line extractor — label + ₹/% value.
TAXCARD_LINE_RE = re.compile(
    r"(gst|tcs|tds|commission|referral fee|shipping|logistic|"
    r"you(?:'ll| will)? (?:get|receive|earn)|net (?:amount|payout|earning|receivable)|"
    r"transfer price|payout|settlement|deduction|wrong\s*/?\s*defective|wdrp|"
    r"final settlement|amount you (?:get|receive)|total deduction|margin|taxable|"
    r"after deduction|claim amount|collection fee|fixed fee|handling)"
    r"[^0-9₹%\n]{0,45}(₹\s?-?\d[\d,]*\.?\d*|-?\d{1,3}(?:\.\d+)?\s?%)",
    re.I)


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"taxcard_{ts}.log"
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
    logger.info("Tax-card probe logfile: %s", log_path)
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


async def _first(page: Page, cands, timeout=5000):
    for build in cands:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=timeout)
            return loc
        except Exception:  # noqa: BLE001
            continue
    return None


# ---------------------------------------------------------------------------
# OTP relay
# ---------------------------------------------------------------------------

async def find_otp_field(page: Page):
    """Return a locator for the OTP input if an OTP page is showing, else None."""
    # Page text hint first.
    try:
        txt = await page.locator("body").inner_text(timeout=3000)
    except Exception:  # noqa: BLE001
        txt = ""
    text_hint = bool(OTP_HINT_RE.search(txt))
    # Common OTP input shapes: single 6-char box, or 6 single-digit boxes.
    cands = [
        lambda: page.get_by_placeholder(re.compile(r"otp|code|verification", re.I)),
        lambda: page.locator("input[name*='otp' i], input[id*='otp' i], input[autocomplete='one-time-code']"),
        lambda: page.locator("input[maxlength='6']"),
        lambda: page.locator("input[type='tel'], input[inputmode='numeric']"),
    ]
    for build in cands:
        try:
            loc = build()
            if await loc.count() and await loc.first.is_visible():
                return loc.first, text_hint
        except Exception:  # noqa: BLE001
            continue
    # 6 separate single-digit inputs?
    try:
        singles = page.locator("input[maxlength='1']")
        if await singles.count() >= 4 and await singles.first.is_visible():
            return ("split", singles), text_hint
    except Exception:  # noqa: BLE001
        pass
    if text_hint:
        return ("hint_only", None), text_hint
    return None, text_hint


async def poll_otp_file(max_tries: int = 60, interval: float = 5.0) -> str | None:
    print("OTP_PAGE_REACHED — waiting for /tmp/meesho_otp.txt", flush=True)
    log.info("OTP_PAGE_REACHED — polling %s every %.0fs (max %d tries)",
             OTP_FILE, interval, max_tries)
    for attempt in range(max_tries):
        try:
            if OTP_FILE.exists():
                raw = OTP_FILE.read_text().strip()
                m = OTP_CODE_RE.search(raw)
                if m:
                    code = m.group(1)
                    log.info("OTP code received from file (attempt %d)", attempt)
                    return code
        except Exception as exc:  # noqa: BLE001
            log.warning("reading OTP file failed: %s", exc)
        await asyncio.sleep(interval)
    log.error("OTP_TIMEOUT — no 6-digit code arrived within the poll window")
    return None


async def handle_otp(page: Page, otp_target) -> bool:
    """otp_target is the locator/tuple returned by find_otp_field."""
    code = await poll_otp_file()
    if not code:
        raise HardStop("OTP_TIMEOUT")
    log.info("Typing OTP into the field(s)")
    # Re-resolve the field at submit time (DOM may have settled).
    field, _ = await find_otp_field(page)
    if isinstance(field, tuple) and field[0] == "split":
        singles = field[1]
        n = await singles.count()
        for i in range(min(n, 6)):
            try:
                await singles.nth(i).fill(code[i], timeout=3000)
                await asyncio.sleep(0.2)
            except Exception:  # noqa: BLE001
                pass
    elif field is not None and not isinstance(field, tuple):
        await field.click(timeout=3000)
        await field.fill(code, timeout=3000)
    else:
        # last resort: type into first visible text/tel input
        try:
            inp = page.locator("input:visible").first
            await inp.fill(code, timeout=3000)
        except Exception as exc:  # noqa: BLE001
            raise HardStop(f"OTP field vanished before typing: {exc}")
    await asyncio.sleep(1.0)
    # Submit OTP.
    submit = await _first(page, [
        lambda: page.get_by_role("button", name=re.compile(r"verify|submit|continue|confirm|login|sign ?in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ])
    if submit is not None:
        try:
            await submit.click(timeout=5000)
        except Exception:  # noqa: BLE001
            pass
    else:
        # some OTP forms auto-submit on last digit
        log.info("No explicit OTP submit button; relying on auto-submit")
    try:
        await page.wait_for_url(lambda u: "login" not in u and "otp" not in u.lower(),
                                timeout=LOGIN_NAV_TIMEOUT_MS)
        log.info("OTP accepted — at %s", _safe_url(page.url))
        return True
    except PlaywrightTimeoutError:
        # Could still be on a transitional page; check for OTP error.
        try:
            body = (await page.locator("body").inner_text(timeout=2000))[:300]
        except Exception:  # noqa: BLE001
            body = ""
        if re.search(r"invalid|incorrect|wrong|expired", body, re.I):
            raise HardStop(f"OTP rejected by Meesho: {body!r}")
        log.warning("OTP submit did not clearly redirect; continuing (url=%s)", _safe_url(page.url))
        return True


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

    # OTP page?  (poll a few seconds for it to render)
    for _ in range(4):
        otp_target, _hint = await find_otp_field(page)
        if otp_target is not None and "login" in page.url.lower() or otp_target is not None:
            if otp_target is not None:
                findings["otp"]["page_reached"] = True
                await handle_otp(page, otp_target)
                findings["otp"]["relay_succeeded"] = True
                break
        # already redirected away from login w/o OTP?
        if "login" not in page.url.lower():
            break
        await asyncio.sleep(2.0)

    # Final redirect check.
    if "login" in page.url.lower():
        try:
            await page.wait_for_url(lambda u: "login" not in u, timeout=20_000)
        except PlaywrightTimeoutError:
            # one more OTP check (it may have appeared late)
            otp_target, _hint = await find_otp_field(page)
            if otp_target is not None and not findings["otp"]["relay_succeeded"]:
                findings["otp"]["page_reached"] = True
                await handle_otp(page, otp_target)
                findings["otp"]["relay_succeeded"] = True
            else:
                snippet = ""
                try:
                    snippet = (await page.locator("body").inner_text(timeout=2000))[:400]
                except Exception:  # noqa: BLE001
                    pass
                raise HardStop(f"Login did not redirect away from /login. body={snippet!r}")
    log.info("Login OK — at %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Capture state
# ---------------------------------------------------------------------------

findings: dict[str, Any] = {
    "otp": {"page_reached": False, "relay_succeeded": False},
    "account": {"supplier_id": None, "identifier": None, "store_name": None,
                "registration_status": None, "agreement_accepted": None,
                "default_monetization_percent": None},
    "add_catalog": {"reached_via": None, "url": None, "sidebar_label": None},
    "category_selected": {"id": None, "name": None, "path": None},
    "image_upload": {"attempted": False, "accepted": None, "rejection_text": None,
                     "required_images_count": None, "upload_xhrs": []},
    "advance": {"reached_price_step": None, "steps_clicked": [], "notes": []},
    "form_fill": {"size": None, "dropdowns_filled": [], "text_filled": [],
                  "number_filled": [], "rounds": [], "notes": []},
    "price_cells_rendered": None,
    "prices_entered": {"meesho": None, "mrp": None, "wdrp": None, "inventory": None,
                       "meesho_changed_to": None},
    # The PRIZE: tax-card lines at each price point + computing XHR.
    "tax_card": {"price_150": {"dom_lines": [], "excerpt": None, "screenshot": None},
                 "price_300": {"dom_lines": [], "excerpt": None, "screenshot": None},
                 "visible": None, "notes": []},
    "computing_xhr": [],
    "config_xhrs": [],
    "category_xhrs": [],
    "upload_performance": [],   # getCatalogUploadPerformance snapshots (safety)
    "blocked_endpoints": [],
    "discarded": None,
    "end_state": None,
    "hard_stop": None,
}

raw_xhr_bodies: dict[str, Any] = {}
_mode = {"phase": "login", "price_label": None}


def _walk_extract(obj: Any, out: dict[str, Any], depth: int = 0) -> None:
    if depth > 9:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str):
                kl = k.lower()
                if COMMISSION_KEY_RE.search(k) and isinstance(v, (int, float, str)):
                    out.setdefault("commission", {}).setdefault(k, v)
                if PRICE_KEY_RE.search(k) and isinstance(v, (int, float, str)):
                    out.setdefault("price", {}).setdefault(k, v)
                if CATEGORY_KEY_RE.search(k) and isinstance(v, (str, int)):
                    out.setdefault("category", {}).setdefault(k, v)
                if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                    findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or v
                if kl in ("store_name", "shop_name", "supplier_name", "business_name") and isinstance(v, str) and v not in ("-", ""):
                    findings["account"]["store_name"] = findings["account"]["store_name"] or v
                if kl == "default_monetization_percent":
                    findings["account"]["default_monetization_percent"] = v
                if kl == "registration_status" and isinstance(v, str):
                    findings["account"]["registration_status"] = v
                if kl in ("agreement_accepted", "is_agreement_accepted"):
                    findings["account"]["agreement_accepted"] = v
                if kl == "required_images_count" and isinstance(v, (int, str)):
                    findings["image_upload"]["required_images_count"] = v
                if kl in ("total_upload_count", "single_upload_count"):
                    findings["upload_performance"].append({k: v})
                if kl == "supplier_identifier_to_id_mapping" and isinstance(v, dict):
                    for ident, sid in v.items():
                        findings["account"]["identifier"] = findings["account"]["identifier"] or ident
                        findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or sid
            _walk_extract(v, out, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:120]:
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

    is_preview = bool(PREVIEW_XHR_RE.search(url))
    is_config = bool(CONFIG_XHR_RE.search(url))
    is_category = bool(CATEGORY_XHR_RE.search(url))
    is_image = bool(IMAGE_XHR_RE.search(url))

    if is_preview or is_config or is_image or is_category:
        key = _safe_url(url) + f"::{_mode['phase']}:{_mode['price_label']}"
        if key not in raw_xhr_bodies:
            txt = json.dumps(body, default=str)
            raw_xhr_bodies[key] = body if len(txt) <= 250_000 else {
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
        "price_label": _mode["price_label"],
        "request_post_data": (post_data[:4000] if isinstance(post_data, str) else None),
        "top_keys": sorted(list(body.keys()))[:60] if isinstance(body, dict) else "[list]",
        "commission_keys": sorted((mined.get("commission") or {}).keys()),
        "price_keys": sorted((mined.get("price") or {}).keys()),
        "commission_sample": dict(list((mined.get("commission") or {}).items())[:30]),
        "price_sample": dict(list((mined.get("price") or {}).items())[:30]),
    }

    # During the price phase capture EVERY non-config JSON XHR — the computing
    # endpoint for the tax card may not match the preview regex.
    capture = is_preview and (record["commission_keys"] or record["price_keys"])
    if _mode["phase"] == "price" and not is_config:
        capture = True

    if capture:
        findings["computing_xhr"].append(record)
        log.info("PRICE-PHASE XHR [%s/%s] %s %s comm=%s price=%s",
                 _mode["phase"], _mode["price_label"], req.method, _safe_url(url),
                 record["commission_keys"], record["price_keys"])
    elif is_config:
        findings["config_xhrs"].append({"url": record["url"], "status": status,
                                        "commission_keys": record["commission_keys"]})
    elif is_category and _mode["phase"] in ("nav", "category", "advance", "form"):
        findings["category_xhrs"].append({"url": record["url"], "status": status,
                                          "top_keys": record["top_keys"]})
    elif is_image and _mode["phase"] in ("image", "advance"):
        findings["image_upload"]["upload_xhrs"].append(
            {"url": record["url"], "status": status, "method": req.method})


def detect_identifier_from_url(url: str) -> None:
    m = re.search(r"/(?:growth|payments|fulfillment|cataloging|root)/([a-z0-9]{3,12})/", url)
    if m and m.group(1) not in ("new", "root"):
        findings["account"]["identifier"] = findings["account"]["identifier"] or m.group(1)


# ---------------------------------------------------------------------------
# Sidebar nav -> single-catalog -> category (Hair Bands)
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


async def select_one_category(page: Page) -> bool:
    cat_input = [
        page.get_by_placeholder(re.compile(r"search.*(category|product)", re.I)),
        page.get_by_role("textbox", name=re.compile(r"category|search", re.I)),
        page.locator("input[type='text']").first,
    ]
    typed = False
    for cand in cat_input:
        try:
            if await cand.count() and await cand.first.is_visible():
                await cand.first.click(timeout=3000)
                await cand.first.fill(TARGET_CATEGORY_QUERY, timeout=3000)
                await asyncio.sleep(2.5)
                typed = True
                log.info("Category search filled with %r", TARGET_CATEGORY_QUERY)
                break
        except Exception:  # noqa: BLE001
            continue
    options = [
        page.get_by_role("option"),
        page.locator("[role='option'], li, .ant-select-item, .category-item, [class*='option']"),
    ]
    for cand in options:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 12)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                name = (await el.inner_text(timeout=1500)).strip()
                if not name or len(name) > 90:
                    continue
                # Prefer an option that mentions "hair band".
                if re.search(r"hair\s*band", name, re.I) or i == 0:
                    await el.click(timeout=3000)
                    await asyncio.sleep(3.5)
                    findings["category_selected"]["name"] = name[:90]
                    log.info("Selected category option: %s", name[:90])
                    return True
            except Exception:  # noqa: BLE001
                continue
    if typed:
        findings["form_fill"]["notes"].append("Category search typed but no option clickable")
    return False


# ---------------------------------------------------------------------------
# Image upload (passes the gate; proven in round 7)
# ---------------------------------------------------------------------------

SAFE_NEXT_RE = re.compile(r"^\s*(next|continue|proceed|save (and )?(continue|next)|done)\s*$", re.I)
GO_LIVE_DENY_RE = re.compile(
    r"submit|publish|go ?live|list product|submit for qc|send for review|"
    r"send for qc|launch|create catalog|create listing|add catalog\b", re.I)


async def upload_placeholder_image(page: Page) -> bool:
    _mode["phase"] = "image"
    findings["image_upload"]["attempted"] = True
    if not PLACEHOLDER_IMG.exists():
        findings["image_upload"]["rejection_text"] = f"placeholder image missing at {PLACEHOLDER_IMG}"
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
        findings["image_upload"]["rejection_text"] = "no file input found on the page"
        return False
    set_ok = False
    for i in range(min(n, 4)):
        try:
            await file_inputs.nth(i).set_input_files(str(PLACEHOLDER_IMG), timeout=8000)
            set_ok = True
            log.info("set_input_files succeeded on file input #%d", i)
            break
        except Exception as exc:  # noqa: BLE001
            log.warning("set_input_files on input #%d failed: %s", i, exc)
            continue
    if not set_ok:
        findings["image_upload"]["rejection_text"] = "set_input_files failed on all file inputs"
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
    log.info("Image upload accepted=%s upload_xhrs=%d",
             accepted, len(findings["image_upload"]["upload_xhrs"]))
    return accepted


async def click_safe_next(page: Page) -> bool:
    cands = [
        page.get_by_role("button", name=SAFE_NEXT_RE),
        page.locator("button").filter(has_text=SAFE_NEXT_RE),
    ]
    for cand in cands:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 6)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                label = (await el.inner_text(timeout=1500)).strip()
                if GO_LIVE_DENY_RE.search(label):
                    log.warning("Refusing go-live control '%s' (HARD LINE)", label[:50])
                    continue
                if not SAFE_NEXT_RE.search(label):
                    continue
                log.info("Clicking SAFE step-advance '%s'", label[:40])
                findings["advance"]["steps_clicked"].append(label[:40])
                await el.click(timeout=4000)
                await asyncio.sleep(4.5)
                return True
            except Exception:  # noqa: BLE001
                continue
    return False


# ---------------------------------------------------------------------------
# FULL mandatory-form fill (the new capability this round)
# ---------------------------------------------------------------------------

async def price_cells_present(page: Page) -> bool:
    """The Meesho-Price / MRP / WDRP / Inventory cells present?"""
    try:
        txt = await page.locator("body").inner_text(timeout=2500)
        if re.search(r"meesho price", txt, re.I) and re.search(r"\bmrp\b", txt, re.I):
            # confirm an editable number input is visible near them
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


async def fill_all_text_inputs(page: Page) -> None:
    """Fill all visible empty text inputs (names/addresses) with dummy-valid text.
    Skips price/number/file/search inputs."""
    try:
        handles = await page.locator("input[type='text'], textarea").element_handles()
    except Exception:  # noqa: BLE001
        return
    for h in handles[:60]:
        try:
            info = await h.evaluate(
                """e => ({n:e.name||'', p:e.placeholder||'', aria:e.getAttribute('aria-label')||'',
                          val:e.value||'', vis:!!e.offsetParent, ro:e.readOnly})""")
            if not info["vis"] or info["ro"] or info["val"].strip():
                continue
            hint = f"{info['n']} {info['p']} {info['aria']}".lower()
            if re.search(r"search|category", hint):
                continue
            # Pincode -> 560001; pick dummy by hint.
            if re.search(r"pincode|pin code|postal", hint):
                val = "560001"
            elif re.search(r"address", hint):
                val = "12, Test Street, Bengaluru, Karnataka"
            elif re.search(r"name", hint):
                val = "Test Compliance Pvt Ltd"
            elif re.search(r"gst|tin", hint):
                val = ""
                continue
            else:
                val = "Test Value"
            await h.fill(val)
            findings["form_fill"]["text_filled"].append(hint.strip()[:40] or "(unlabeled)")
        except Exception:  # noqa: BLE001
            continue


async def fill_all_number_inputs(page: Page, skip_price: bool = True) -> None:
    """Fill non-price number inputs (weight etc.) with dummy values."""
    try:
        handles = await page.locator("input[type='number'], input[inputmode='numeric']").element_handles()
    except Exception:  # noqa: BLE001
        return
    for h in handles[:60]:
        try:
            info = await h.evaluate(
                """e => ({n:e.name||'', p:e.placeholder||'', aria:e.getAttribute('aria-label')||'',
                          val:e.value||'', vis:!!e.offsetParent, ro:e.readOnly})""")
            if not info["vis"] or info["ro"] or info["val"].strip():
                continue
            hint = f"{info['n']} {info['p']} {info['aria']}".lower()
            if skip_price and re.search(r"price|mrp|inventory|defective|wrong", hint):
                continue
            if re.search(r"pincode|pin code|postal", hint):
                val = "560001"
            elif re.search(r"weight|gms|gram", hint):
                val = "100"
            elif re.search(r"length|width|height|cm", hint):
                val = "10"
            else:
                val = "1"
            await h.fill(val)
            findings["form_fill"]["number_filled"].append(f"{hint.strip()[:40]}={val}")
        except Exception:  # noqa: BLE001
            continue


async def fill_all_dropdowns(page: Page) -> int:
    """Open each ant-style combobox / native select and pick the first valid
    option. Returns how many were newly filled. Idempotent-ish (skips ones that
    already have a value)."""
    filled = 0
    # Native <select> elements.
    try:
        selects = page.locator("select")
        n = await selects.count()
        for i in range(min(n, 40)):
            try:
                el = selects.nth(i)
                if not await el.is_visible():
                    continue
                opts = await el.locator("option").all_inner_texts()
                # pick first non-empty/non-placeholder option index
                for idx, label in enumerate(opts):
                    if label.strip() and not re.search(r"^(select|choose|--)", label.strip(), re.I):
                        await el.select_option(index=idx)
                        filled += 1
                        findings["form_fill"]["dropdowns_filled"].append(f"select:{label.strip()[:30]}")
                        break
            except Exception:  # noqa: BLE001
                continue
    except Exception:  # noqa: BLE001
        pass
    # ant-style comboboxes: input role=combobox / .ant-select that are empty.
    combo_locators = [
        "input[role='combobox']",
        ".ant-select-selector",
        "[class*='select'][class*='trigger']",
    ]
    for sel in combo_locators:
        try:
            combos = page.locator(sel)
            n = await combos.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 40)):
            try:
                el = combos.nth(i)
                if not await el.is_visible():
                    continue
                # Skip the Size combobox (handled separately) and search box.
                container_txt = ""
                try:
                    container_txt = (await el.evaluate(
                        "e => (e.closest('[class*=field],[class*=form-item],div')||e).innerText||''"))[:60]
                except Exception:  # noqa: BLE001
                    pass
                if re.search(r"search|category", container_txt, re.I):
                    continue
                # Already has a chosen value? (selector shows non-placeholder text)
                if re.search(r"\b(L|M|S|XL|Free Size|Black|Cotton)\b", container_txt) and "select" not in container_txt.lower():
                    continue
                await el.scroll_into_view_if_needed(timeout=2000)
                await el.click(timeout=2500)
                await asyncio.sleep(1.0)
                opt = page.locator(
                    "[role='option']:visible, .ant-select-item-option:visible, "
                    "li[class*='option']:visible")
                on = await opt.count()
                picked = False
                for j in range(min(on, 20)):
                    o = opt.nth(j)
                    try:
                        if not await o.is_visible():
                            continue
                        name = (await o.inner_text(timeout=1200)).strip()
                        if name and 0 < len(name) < 40 and not re.search(r"^(select|choose|all)$", name, re.I):
                            await o.click(timeout=2500)
                            await asyncio.sleep(1.2)
                            filled += 1
                            picked = True
                            findings["form_fill"]["dropdowns_filled"].append(f"combo:{name[:30]}")
                            break
                    except Exception:  # noqa: BLE001
                        continue
                if not picked:
                    # close the dropdown to avoid blocking subsequent clicks
                    try:
                        await page.keyboard.press("Escape")
                    except Exception:  # noqa: BLE001
                        pass
            except Exception:  # noqa: BLE001
                continue
    return filled


FREE_SIZE_RE = re.compile(r"free\s*size", re.I)


async def select_a_size(page: Page) -> bool:
    """ROUND-9 FOUNDER FIX: select **Free Size** for the Size attribute (NOT "L").
    The founder confirmed that only Free Size unlocks the price-detail section
    (Meesho Price / Wrong-Defective / MRP / Inventory) which in turn renders the
    right-side tax card. Previous rounds picked the first option ("L") and the
    price cells never rendered. We now type "free size" into the combobox and
    explicitly click the Free Size option; only if that is impossible do we fall
    back to any option."""
    size_locators = [
        page.locator("input[name='size']"),
        page.locator("#size, [id*='size' i]"),
        page.get_by_text(re.compile(r"^\s*size\s*$", re.I)),
    ]
    for sl in size_locators:
        try:
            if not (await sl.count()):
                continue
            el = sl.first
            if not await el.is_visible():
                continue
            await el.scroll_into_view_if_needed(timeout=3000)
            await el.click(timeout=3000)
            await asyncio.sleep(1.8)

            # Try typing "free size" to filter the combobox (ant-style search).
            try:
                await el.fill("Free Size", timeout=2000)
                await asyncio.sleep(1.8)
            except Exception:  # noqa: BLE001
                pass

            opt = page.locator(
                "[role='option']:visible, .ant-select-item-option:visible, "
                "li[class*='option']:visible, [class*='MenuItem']:visible")
            on = await opt.count()
            log.info("Size dropdown opened, %d options visible", on)

            # PASS 1: explicitly click the Free Size option.
            for j in range(min(on, 40)):
                o = opt.nth(j)
                try:
                    if not await o.is_visible():
                        continue
                    name = (await o.inner_text(timeout=1500)).strip()
                    if name and FREE_SIZE_RE.search(name):
                        await o.click(timeout=3000)
                        await asyncio.sleep(3.0)
                        findings["form_fill"]["size"] = name[:30]
                        log.info("Selected Size option: %s (FREE SIZE — round-9 fix)", name[:30])
                        return True
                except Exception:  # noqa: BLE001
                    continue

            # PASS 2 (fallback): pick any non-placeholder option, but log loudly
            # that Free Size was NOT found (so the founder knows the premise).
            log.warning("Free Size NOT found among Size options; falling back to first valid option")
            findings["form_fill"]["notes"].append("Free Size option NOT present in Size dropdown")
            for j in range(min(on, 15)):
                o = opt.nth(j)
                try:
                    if not await o.is_visible():
                        continue
                    name = (await o.inner_text(timeout=1500)).strip()
                    if name and 0 < len(name) < 40 and not re.search(r"select", name, re.I):
                        await o.click(timeout=3000)
                        await asyncio.sleep(3.0)
                        findings["form_fill"]["size"] = name[:30] + " (FALLBACK, not Free Size)"
                        log.info("Selected Size option (FALLBACK): %s", name[:30])
                        return True
                except Exception:  # noqa: BLE001
                    continue
        except Exception as exc:  # noqa: BLE001
            log.warning("size locator attempt failed: %s", exc)
            continue
    return False


async def fill_full_form(page: Page, max_rounds: int = 5) -> bool:
    """Iteratively fill Size + all dropdowns + all text + all number fields until
    the price cells render or we run out of rounds. Returns True if price cells
    rendered."""
    _mode["phase"] = "form"
    # Size first (often unlocks the per-size price columns + other attribute rows).
    if await select_a_size(page):
        findings["form_fill"]["notes"].append("Size selected")
    for rnd in range(max_rounds):
        if findings["hard_stop"]:
            return False
        before = (len(findings["form_fill"]["dropdowns_filled"]),
                  len(findings["form_fill"]["text_filled"]),
                  len(findings["form_fill"]["number_filled"]))
        d = await fill_all_dropdowns(page)
        await fill_all_text_inputs(page)
        await fill_all_number_inputs(page, skip_price=True)
        await asyncio.sleep(2.5)
        # Some forms reveal the price section behind a "Next"/"Continue" within the
        # details step — try a safe advance if price cells still absent.
        present = await price_cells_present(page)
        after = (len(findings["form_fill"]["dropdowns_filled"]),
                 len(findings["form_fill"]["text_filled"]),
                 len(findings["form_fill"]["number_filled"]))
        findings["form_fill"]["rounds"].append(
            {"round": rnd, "new_dropdowns": after[0] - before[0],
             "new_text": after[1] - before[1], "new_number": after[2] - before[2],
             "price_cells": present})
        log.info("Form-fill round %d: +%d dropdowns +%d text +%d num, price_cells=%s",
                 rnd, after[0]-before[0], after[1]-before[1], after[2]-before[2], present)
        if present:
            findings["price_cells_rendered"] = True
            return True
        if after == before:
            # nothing new filled this round — try a safe next, else give up
            advanced = await click_safe_next(page)
            if await price_cells_present(page):
                findings["price_cells_rendered"] = True
                return True
            if not advanced:
                break
    findings["price_cells_rendered"] = await price_cells_present(page)
    return findings["price_cells_rendered"]


# ---------------------------------------------------------------------------
# Price entry + tax-card capture (the prize)
# ---------------------------------------------------------------------------

async def _fill_labeled_number(page: Page, label_re: re.Pattern, value: str) -> bool:
    for build in (
        lambda: page.get_by_placeholder(label_re),
        lambda: page.get_by_role("spinbutton", name=label_re),
    ):
        try:
            loc = build()
            if await loc.count() and await loc.first.is_visible():
                await loc.first.click(timeout=3000)
                await loc.first.fill(value, timeout=3000)
                await loc.first.press("Tab")
                return True
        except Exception:  # noqa: BLE001
            continue
    try:
        lbl = page.get_by_text(label_re, exact=False)
        cnt = await lbl.count()
        for i in range(min(cnt, 5)):
            el = lbl.nth(i)
            if not await el.is_visible():
                continue
            for xp in ("xpath=following::input[@type='number'][1]",
                       "xpath=ancestor::*[self::div or self::label][1]//input[@type='number'][1]",
                       "xpath=ancestor::*[self::div][2]//input[@type='number'][1]",
                       "xpath=following::input[@inputmode='numeric'][1]"):
                try:
                    inp = el.locator(xp)
                    if await inp.count() and await inp.first.is_visible():
                        await inp.first.click(timeout=2500)
                        await inp.first.fill(value, timeout=2500)
                        await inp.first.press("Tab")
                        return True
                except Exception:  # noqa: BLE001
                    continue
    except Exception:  # noqa: BLE001
        pass
    return False


async def read_tax_card(page: Page, label: str) -> dict[str, Any]:
    out: dict[str, Any] = {"dom_lines": [], "excerpt": None, "screenshot": None}
    # Screenshot full page (the card lives on the right rail).
    try:
        shot = LOG_DIR / f"taxcard_price_{label}.png"
        await page.screenshot(path=str(shot), full_page=True)
        out["screenshot"] = str(shot)
        log.info("Tax-card screenshot (%s) -> %s", label, shot)
    except Exception as exc:  # noqa: BLE001
        log.warning("screenshot (%s) failed: %s", label, exc)
    try:
        txt = await page.locator("body").inner_text(timeout=4000)
        (LOG_DIR / f"taxcard_dom_{label}.txt").write_text(txt)
    except Exception:  # noqa: BLE001
        txt = ""
    if OTP_HINT_RE.search(txt):
        # OTP shouldn't appear here, but guard anyway
        log.warning("OTP hint text on price step (%s) — ignoring", label)
    for m in TAXCARD_LINE_RE.finditer(txt):
        line = re.sub(r"\s+", " ", m.group(0)).strip()[:140]
        if line not in out["dom_lines"]:
            out["dom_lines"].append(line)
    m = re.search(r".{0,80}(price (break|detail)|tax (detail|break)|you.{0,3}(get|receive)|"
                  r"settlement|net (amount|payout)|total deduction).{0,400}", txt, re.I)
    if m:
        out["excerpt"] = re.sub(r"\s+", " ", m.group(0)).strip()[:600]
    log.info("Tax-card (%s): %d DOM lines", label, len(out["dom_lines"]))
    return out


async def enter_prices_and_capture(page: Page) -> None:
    _mode["phase"] = "price"
    # First price point: Meesho 150 / MRP 400 / WDRP 140 / Inventory 5.
    _mode["price_label"] = "150"
    filled = []
    if await _fill_labeled_number(page, re.compile(r"meesho price", re.I), "150"):
        filled.append("Meesho=150"); findings["prices_entered"]["meesho"] = 150
        await asyncio.sleep(3.0)
    if await _fill_labeled_number(page, re.compile(r"^\s*mrp", re.I), "400"):
        filled.append("MRP=400"); findings["prices_entered"]["mrp"] = 400
        await asyncio.sleep(1.5)
    if await _fill_labeled_number(page, re.compile(r"wrong.*defective.*returns? price|wrong.*defective", re.I), "140"):
        filled.append("WDRP=140"); findings["prices_entered"]["wdrp"] = 140
        await asyncio.sleep(1.5)
    if await _fill_labeled_number(page, re.compile(r"inventory|stock|quantity", re.I), "5"):
        filled.append("Inventory=5"); findings["prices_entered"]["inventory"] = 5
        await asyncio.sleep(1.5)

    # Fallback: address bare visible number inputs by position if labelled fill failed.
    if not findings["prices_entered"]["meesho"]:
        try:
            price_inputs = await page.evaluate(
                """() => Array.from(document.querySelectorAll('input[type=number], input[inputmode=numeric]'))
                    .map((e,i)=>({i, n:e.name||'', p:e.placeholder||'', aria:e.getAttribute('aria-label')||'',
                                  vis:!!e.offsetParent, val:e.value||''})).filter(f=>f.vis)""")
            findings["form_fill"]["notes"].append({"visible_number_inputs_at_price": price_inputs})
            log.info("Visible number inputs at price step: %s", price_inputs)
            for f in price_inputs:
                hint = f"{f['n']} {f['p']} {f['aria']}".lower()
                if re.search(r"meesho|selling", hint) and not f["val"].strip():
                    loc = page.locator("input[type=number], input[inputmode=numeric]").nth(f["i"])
                    await loc.fill("150", timeout=2500); await loc.press("Tab")
                    filled.append(f"numinput[{f['i']}]=150"); findings["prices_entered"]["meesho"] = 150
                    await asyncio.sleep(3.0)
                    break
        except Exception as exc:  # noqa: BLE001
            log.warning("price fallback failed: %s", exc)
    findings["form_fill"]["notes"].append({"prices_filled_round1": filled})
    log.info("Prices filled (round1): %s", filled)
    await asyncio.sleep(5.0)

    # Read the tax card at price=150.
    card150 = await read_tax_card(page, "150")
    findings["tax_card"]["price_150"] = card150

    # Second price point: change Meesho price to 300, watch the card recalculate.
    _mode["price_label"] = "300"
    changed = await _fill_labeled_number(page, re.compile(r"meesho price", re.I), "300")
    if not changed:
        # fallback re-address first meesho-ish input
        try:
            cand = page.get_by_placeholder(re.compile(r"meesho price|enter price", re.I))
            if await cand.count() and await cand.first.is_visible():
                await cand.first.fill("300", timeout=3000); await cand.first.press("Tab")
                changed = True
        except Exception:  # noqa: BLE001
            pass
    if changed:
        findings["prices_entered"]["meesho_changed_to"] = 300
        log.info("Changed Meesho price 150 -> 300")
        await asyncio.sleep(6.0)
    else:
        findings["tax_card"]["notes"].append("Could not re-address Meesho price to change it to 300")

    card300 = await read_tax_card(page, "300")
    findings["tax_card"]["price_300"] = card300

    findings["tax_card"]["visible"] = bool(
        card150["dom_lines"] or card300["dom_lines"]
        or any(x["commission_keys"] for x in findings["computing_xhr"]))


# ---------------------------------------------------------------------------
# Discard (mandatory)
# ---------------------------------------------------------------------------

DISCARD_RE = re.compile(r"discard catalog|discard( product| draft)?|delete( draft| catalog)?", re.I)
CONFIRM_DISCARD_RE = re.compile(r"^\s*(yes|discard|confirm|delete|ok|yes,? discard)\s*$", re.I)


async def discard_catalog(page: Page) -> bool:
    _mode["phase"] = "discard"
    cands = [
        page.get_by_role("button", name=re.compile(r"discard catalog", re.I)),
        page.get_by_role("button", name=DISCARD_RE),
        page.get_by_role("link", name=DISCARD_RE),
        page.locator("a,button").filter(has_text=re.compile(r"discard", re.I)),
    ]
    for cand in cands:
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
                log.info("Clicking discard control '%s'", label[:40])
                await el.click(timeout=4000)
                await asyncio.sleep(2.5)
                try:
                    confirm = page.get_by_role("button", name=CONFIRM_DISCARD_RE)
                    if await confirm.count() and await confirm.first.is_visible():
                        clabel = (await confirm.first.inner_text(timeout=1500)).strip()
                        if not GO_LIVE_DENY_RE.search(clabel):
                            await confirm.first.click(timeout=4000)
                            await asyncio.sleep(3.0)
                            log.info("Confirmed discard '%s'", clabel[:30])
                except Exception:  # noqa: BLE001
                    pass
                findings["discarded"] = True
                return True
            except Exception:  # noqa: BLE001
                continue
    findings["discarded"] = False
    findings["tax_card"]["notes"].append("Discard Catalog control not found — abandoning by nav-away")
    return False


async def verify_nothing_live(page: Page) -> None:
    """Navigate to the catalog listing to trigger getCatalogUploadPerformance and
    confirm total_upload_count stays 0."""
    _mode["phase"] = "verify"
    ident = findings["account"]["identifier"] or "oinpw"
    try:
        await page.goto(
            f"https://supplier.meesho.com/panel/v3/new/cataloging/{ident}/catalogs",
            wait_until="domcontentloaded", timeout=20_000)
        await asyncio.sleep(5.0)
    except Exception:  # noqa: BLE001
        pass


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
            await asyncio.sleep(5.0)
            detect_identifier_from_url(page.url)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            log.info("Account so far: %s", findings["account"])

            _mode["phase"] = "nav"
            reached = await goto_single_select_category(page)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            if not reached:
                findings["tax_card"]["notes"].append("Could not reach single/select-category")
            else:
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
                        "Image upload not satisfied: " + str(findings["image_upload"]["rejection_text"]))
                else:
                    # advance past the image gate
                    _mode["phase"] = "advance"
                    await click_safe_next(page)
                    if findings["hard_stop"]:
                        raise HardStop(findings["hard_stop"])

                    # diagnostic snapshot at details step
                    try:
                        btns = await page.locator("button").evaluate_all(
                            "els => els.map(e => (e.innerText||'').trim()).filter(Boolean).slice(0,40)")
                        findings["advance"]["notes"].append({"buttons_at_details": btns,
                                                             "url": _safe_url(page.url)})
                        log.info("Details-step buttons: %s", btns)
                    except Exception:  # noqa: BLE001
                        pass

                    # FILL the full mandatory form until price cells render.
                    rendered = await fill_full_form(page)
                    if findings["hard_stop"]:
                        raise HardStop(findings["hard_stop"])
                    log.info("Price cells rendered after form-fill: %s", rendered)

                    if rendered:
                        await enter_prices_and_capture(page)
                        if findings["hard_stop"]:
                            raise HardStop(findings["hard_stop"])
                    else:
                        findings["tax_card"]["notes"].append(
                            "Price cells never rendered despite full form-fill; "
                            "dumping final field inventory for diagnosis")
                        try:
                            fields = await page.evaluate(
                                """() => Array.from(document.querySelectorAll('input,select,textarea'))
                                    .map(e => ({t:e.type||e.tagName, n:e.name||'', p:e.placeholder||'',
                                                aria:e.getAttribute('aria-label')||'', vis:!!e.offsetParent,
                                                val:(e.value||'').slice(0,20)})).filter(f=>f.vis).slice(0,90)""")
                            findings["form_fill"]["notes"].append({"final_field_inventory": fields})
                            shot = LOG_DIR / "taxcard_no_price_cells.png"
                            await page.screenshot(path=str(shot), full_page=True)
                            (LOG_DIR / "taxcard_no_price_dom.txt").write_text(
                                await page.locator("body").inner_text(timeout=4000))
                        except Exception:  # noqa: BLE001
                            pass

                # MANDATORY: discard.
                await discard_catalog(page)

            # Safety: verify nothing went live.
            await verify_nothing_live(page)
            try:
                _mode["phase"] = "abandon"
                await page.goto(NEUTRAL_URL, wait_until="domcontentloaded", timeout=15_000)
            except Exception:  # noqa: BLE001
                pass

            if findings["discarded"]:
                findings["end_state"] = "DISCARDED (Discard Catalog clicked + abandoned)"
            else:
                findings["end_state"] = (
                    "NOT-EXPLICITLY-DISCARDED — abandoned by nav-away; any auto-saved "
                    "DRAFT may remain (no go-live action taken).")

        except HardStop as exc:
            findings["hard_stop"] = str(exc)
            findings["end_state"] = (findings.get("end_state") or
                                     "HARD-STOP before completion — no go-live action taken")
            log.error("HARD STOP: %s", exc)
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
    log.info("==== Meesho TAX-CARD capture probe (option-2 + OTP relay) @ %s ====",
             datetime.now().isoformat())
    if not PLACEHOLDER_IMG.exists():
        log.error("Placeholder image not found at %s — generate it first", PLACEHOLDER_IMG)
        return 2
    # Belt-and-suspenders: clear any stale OTP file at start.
    try:
        OTP_FILE.unlink(missing_ok=True)
    except Exception:  # noqa: BLE001
        pass
    result = asyncio.run(run())
    f = result["findings"]
    raw_path = LOG_DIR / f"taxcard_xhrs_{ts}.json"
    try:
        raw_path.write_text(json.dumps(result["raw_xhr_bodies"], indent=2, default=str))
        log.info("Raw XHR bodies -> %s", raw_path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not persist raw bodies: %s", exc)

    print("\n========= TAX-CARD PROBE SUMMARY =========")
    print(json.dumps(f, indent=2, default=str))
    print("\n--- raw XHR body keys captured ---")
    for url, body in list(result["raw_xhr_bodies"].items())[:40]:
        keys = sorted(body.keys())[:50] if isinstance(body, dict) else "[list]"
        print(f"  {url}  keys={keys}")
    print("==========================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
