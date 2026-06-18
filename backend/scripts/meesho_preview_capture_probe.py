"""Meesho ADD-CATALOG create-flow commission/payout PREVIEW CAPTURE probe — round 7.

FOUNDER-REVISED guardrail (option 2: read-the-preview, NO go-live)
-----------------------------------------------------------------
Round 6 proved the live commission/payout preview is IMAGE-GATED: the price
section only renders AFTER the mandatory product-image upload. The founder has
now AUTHORIZED (for this run only) getting PAST that gate to READ the preview:

  ALLOWED  : upload a PLACEHOLDER image, advance the wizard past the image gate
             to the PRICE/details step, enter a test price (+ minimal required
             fields) to TRIGGER the commission/payout preview, then READ the
             preview DOM + capture the computing XHR. When done, DISCARD CATALOG.
  FORBIDDEN: Publish / Submit / "Submit for QC" / "List Product" / "Go Live" /
             any final action that creates a LIVE / active / sellable listing or
             submits for review. A wizard auto-saved DRAFT is acceptable, but the
             run MUST end by clicking "Discard Catalog" so nothing stays pending.

Method (every prior-round lesson carried forward)
-------------------------------------------------
  1. Log in (proven authenticated-WebKit + Akamai-bypass idiom).
  2. Reach Add-SINGLE-Catalog by REAL sidebar nav (guessed URLs only serve the
     SPA shell). Round-6 confirmed the real route:
       /panel/v3/new/cataloging/oinpw/catalogs/single/select-category
  3. Select ONE category (report id/name).
  4. Upload the placeholder image into the mandatory image input. If client
     validation rejects it, report the exact requirement and STOP.
  5. Advance past the image gate to the PRICE step (SAFE next/continue only —
     a strict deny-list blocks Publish/Submit/QC/Go-Live).
  6. Enter ₹150 + minimal required fields; capture the preview DOM + the
     computing XHR (endpoint, request payload, full response). Note category id.
  7. Click "Discard Catalog". Confirm nothing went live. Report end-state.

Output (all gitignored)
-----------------------
  * logs/scraper/preview_capture_<ts>.log
  * logs/scraper/preview_capture_xhrs_<ts>.json   (raw preview/config/compute XHR bodies)
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

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the code)\b", re.I)

# Preview/commission-bearing XHR classifier.
PREVIEW_XHR_RE = re.compile(
    r"commission|referral[-_]?fee|monetization|payout|transfer[-_]?price|"
    r"price[-_]?break|fee[-_]?break|estimate|net[-_]?amount|earning|"
    r"price[-_]?recommend|pricerecommend|smart[-_]?pricing|wdrp|deduction|price[-_]?suggest|"
    r"calculate|preview|pricing|price[-_]?detail|margin|settle|"
    r"fetchduplicatepid|getprice|fetchprice|product[-_]?price", re.I)
CONFIG_XHR_RE = re.compile(
    r"prefetch-supply-data|supplier/config|fetch-registration-status|"
    r"fetch-home|fetch-supplier-products|fetch-growth-overview|fetch-sscat-image", re.I)
CATEGORY_XHR_RE = re.compile(
    r"category|sub[-_]?category|sscat|taxonomy|attribute|fetchCategoryTree", re.I)
IMAGE_XHR_RE = re.compile(r"image|upload|media|asset|signed[-_]?url|gcs|s3", re.I)

COMMISSION_KEY_RE = re.compile(
    r"commission|referral|monetization|payout|net[-_]?amount|payable|earning|"
    r"net[-_]?margin|net[-_]?price|fee|charge|deduction|settle|transfer|rate|wdrp", re.I)
PRICE_KEY_RE = re.compile(
    r"price|mrp|cost|amount|selling|listing[-_]?price|meesho[-_]?price|transfer", re.I)
CATEGORY_KEY_RE = re.compile(r"category|sub[-_]?category|sscat|catalog[-_]?type|product[-_]?type", re.I)

DOM_COMMISSION_RE = re.compile(
    r"(commission|referral fee|you(?:'ll| will) (?:get|receive|earn)|"
    r"net (?:amount|payout|earning)|transfer price|payout|settlement|deduction|wdrp|"
    r"wrong\s*/?\s*defective|after deduction)"
    r"[^0-9₹%]{0,40}(₹\s?\d[\d,]*\.?\d*|\d{1,3}(?:\.\d+)?\s?%)",
    re.I)


def configure_logging():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"preview_capture_{ts}.log"
    logger = logging.getLogger("meesho-preview-capture")
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
    logger.info("Preview-capture probe logfile: %s", log_path)
    return logger, ts


log = logging.getLogger("meesho-preview-capture")


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
        raise HardStop(f"Login did not redirect away from /login. URL={_safe_url(page.url)!r} body={snippet!r}")
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
    "advance": {"reached_price_step": None, "steps_clicked": [], "notes": []},
    "price_entered": None,
    "fields_filled": [],
    "preview": {"visible": None, "dom_commission_hits": [], "dom_text_excerpt": None,
                "category_specific": None, "notes": []},
    "computing_xhr": [],     # the prize: [{url, status, method, request_post_data, ...}]
    "config_xhrs": [],
    "category_xhrs": [],
    "blocked_endpoints": [],
    "discarded": None,
    "end_state": None,
    "hard_stop": None,
}

raw_xhr_bodies: dict[str, Any] = {}
_mode = {"phase": "login"}


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
                if kl == "default_monetization_percent" and isinstance(v, (int, float, str)):
                    findings["account"]["default_monetization_percent"] = v
                if kl == "registration_status" and isinstance(v, str):
                    findings["account"]["registration_status"] = v
                if kl in ("agreement_accepted", "is_agreement_accepted") and isinstance(v, (bool, str)):
                    findings["account"]["agreement_accepted"] = v
                if kl == "required_images_count" and isinstance(v, (int, str)):
                    findings["image_upload"]["required_images_count"] = v
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

    if is_preview or is_config or is_image:
        key = _safe_url(url)
        if key not in raw_xhr_bodies:
            txt = json.dumps(body, default=str)
            raw_xhr_bodies[key] = body if len(txt) <= 200_000 else {
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
        "request_post_data": (post_data[:3000] if isinstance(post_data, str) else None),
        "top_keys": sorted(list(body.keys()))[:50] if isinstance(body, dict) else "[list]",
        "commission_keys": sorted((mined.get("commission") or {}).keys()),
        "price_keys": sorted((mined.get("price") or {}).keys()),
        "commission_sample": dict(list((mined.get("commission") or {}).items())[:20]),
        "price_sample": dict(list((mined.get("price") or {}).items())[:20]),
    }

    # During the price phase, capture EVERY JSON XHR (the computing endpoint may
    # not match the preview regex). Persist its raw body too.
    capture = is_preview and (record["commission_keys"] or record["price_keys"]
                              or _mode["phase"] in ("price", "advance"))
    if _mode["phase"] == "price" and not is_config:
        capture = True
        key = _safe_url(url)
        if key not in raw_xhr_bodies:
            txt = json.dumps(body, default=str)
            raw_xhr_bodies[key] = body if len(txt) <= 200_000 else {
                "_truncated_len": len(txt),
                "_top_keys": sorted(body.keys())[:80] if isinstance(body, dict) else "[list]"}

    if capture:
        findings["computing_xhr"].append(record)
        log.info("PRICE-PHASE XHR [%s] %s %s comm=%s price=%s",
                 _mode["phase"], req.method, _safe_url(url),
                 record["commission_keys"], record["price_keys"])
    elif is_config:
        findings["config_xhrs"].append({"url": record["url"], "status": status,
                                        "commission_keys": record["commission_keys"]})
    elif is_image and _mode["phase"] in ("image", "advance"):
        findings["image_upload"]["upload_xhrs"].append(
            {"url": record["url"], "status": status, "method": req.method})
        log.info("IMAGE XHR [%s] %s %s", _mode["phase"], req.method, _safe_url(url))
    elif is_category and _mode["phase"] in ("nav", "category"):
        findings["category_xhrs"].append({"url": record["url"], "status": status,
                                          "top_keys": record["top_keys"]})


def detect_identifier_from_url(url: str) -> None:
    m = re.search(r"/(?:growth|payments|fulfillment|cataloging|root)/([a-z0-9]{3,12})/", url)
    if m and m.group(1) not in ("new", "root"):
        findings["account"]["identifier"] = findings["account"]["identifier"] or m.group(1)


async def read_dom_preview(page: Page, label: str) -> dict[str, Any]:
    out: dict[str, Any] = {"commission_hits": [], "excerpt": None, "esig_wall": False}
    try:
        txt = await page.locator("body").inner_text(timeout=4000)
    except Exception:  # noqa: BLE001
        return out
    if OTP_HINT_RE.search(txt):
        raise HardStop(f"OTP_REQUIRED — detected on {label}")
    for m in DOM_COMMISSION_RE.finditer(txt):
        out["commission_hits"].append(m.group(0).strip()[:120])
    out["esig_wall"] = bool(re.search(
        r"add signature|e-?signature|sign(?:ature)? is missing|accept.{0,20}agreement", txt, re.I))
    m = re.search(r".{0,140}(commission|payout|transfer|you.{0,3}receive|net amount|wdrp|deduction).{0,260}", txt, re.I)
    if m:
        out["excerpt"] = re.sub(r"\s+", " ", m.group(0)).strip()[:500]
    return out


# ----- Sidebar nav to single-product Add-Catalog (round-6 proven) -----

async def goto_single_select_category(page: Page) -> bool:
    """Reach the single-product create flow. Round 6 proved the real route is
    .../cataloging/<identifier>/catalogs/single/select-category, but we reach it
    by SIDEBAR nav, then fall back to the proven URL only if the SPA is already
    authenticated (the URL works once the app shell + auth cookies are live)."""
    ident = findings["account"]["identifier"] or "oinpw"
    # Try sidebar nav first.
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
                    log.info("Sidebar: opened a Catalogs/Products menu item")
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
                log.info("Sidebar: clicked Add '%s' -> %s", label_txt, _safe_url(page.url))
                if "select-category" in page.url or re.search(r"catalog", page.url, re.I):
                    return True
            except Exception:  # noqa: BLE001
                continue
    # Fallback: the proven direct route (auth shell already loaded → it mounts).
    url = f"https://supplier.meesho.com/panel/v3/new/cataloging/{ident}/catalogs/single/select-category"
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
        await asyncio.sleep(4.0)
        findings["add_catalog"]["reached_via"] = "direct_route_fallback"
        findings["add_catalog"]["url"] = _safe_url(page.url)
        log.info("Fallback direct route -> %s", _safe_url(page.url))
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
                await cand.first.fill("hair", timeout=3000)
                await asyncio.sleep(2.5)
                typed = True
                log.info("Category search filled with 'hair'")
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
        for i in range(min(n, 10)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                name = (await el.inner_text(timeout=1500)).strip()
                if not name or len(name) > 90:
                    continue
                await el.click(timeout=3000)
                await asyncio.sleep(3.5)
                findings["category_selected"]["name"] = name[:90]
                log.info("Selected category option: %s", name[:90])
                return True
            except Exception:  # noqa: BLE001
                continue
    if typed:
        findings["preview"]["notes"].append("Category search typed but no option clickable")
    return False


# ----- Image upload (NEW authorization this round) -----

async def upload_placeholder_image(page: Page) -> bool:
    """Set the placeholder image on the mandatory file input. This is an UPLOAD
    (a wizard step), NOT a publish — fully within the revised guardrail."""
    _mode["phase"] = "image"
    findings["image_upload"]["attempted"] = True
    if not PLACEHOLDER_IMG.exists():
        findings["image_upload"]["rejection_text"] = f"placeholder image missing at {PLACEHOLDER_IMG}"
        return False

    # Some flows need the "Add Product Images" button clicked to reveal the input.
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
        log.warning("No file input present for image upload")
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

    # Wait generously for the async upload (GCS/signed-url round-trip can be slow).
    # Poll for: an upload XHR, OR a rendered thumbnail/preview, OR a now-enabled
    # forward control. Only treat as REJECTED on an EXPLICIT upload-failure toast.
    accepted = False
    for poll in range(8):  # up to ~32s
        await asyncio.sleep(4.0)
        if findings["image_upload"]["upload_xhrs"]:
            accepted = True
            log.info("Image upload XHR observed (poll %d)", poll)
            break
        # Thumbnail / image-preview element present?
        try:
            thumb = page.locator(
                "img[src*='meesho' i], img[src*='blob:' i], "
                "[class*='thumbnail' i], [class*='preview' i] img, [class*='uploaded' i]")
            if await thumb.count():
                for j in range(min(await thumb.count(), 6)):
                    src = await thumb.nth(j).get_attribute("src")
                    if src and ("blob:" in src or "/uploads" in src or "amazonaws" in src or "storage.googleapis" in src):
                        accepted = True
                        log.info("Image thumbnail rendered (src hint) at poll %d", poll)
                        break
            if accepted:
                break
        except Exception:  # noqa: BLE001
            pass
        # A forward control (Next/Continue/Save) appearing implies the gate passed.
        try:
            fwd = page.get_by_role("button", name=SAFE_NEXT_RE)
            if await fwd.count() and await fwd.first.is_visible():
                accepted = True
                log.info("Forward control appeared after upload at poll %d", poll)
                break
        except Exception:  # noqa: BLE001
            pass
        # Explicit failure toast only.
        try:
            txt = await page.locator("body").inner_text(timeout=3000)
        except Exception:  # noqa: BLE001
            txt = ""
        fail_m = re.search(
            r"(upload failed|failed to upload|image upload error|could not upload|"
            r"please (re)?upload|invalid image format|image .{0,15}(rejected|not accepted))"
            r"[^.\n]{0,100}", txt, re.I)
        if fail_m:
            findings["image_upload"]["accepted"] = False
            findings["image_upload"]["rejection_text"] = fail_m.group(0).strip()[:200]
            log.warning("Image EXPLICITLY rejected: %s", findings["image_upload"]["rejection_text"])
            return False

    findings["image_upload"]["accepted"] = accepted
    if not accepted:
        findings["image_upload"]["rejection_text"] = (
            "upload did not confirm within timeout (no upload XHR, no thumbnail, "
            "no forward control) — may need a different file-input or a click to confirm")
    log.info("Image upload accepted=%s upload_xhrs=%d",
             accepted, len(findings["image_upload"]["upload_xhrs"]))
    return accepted


# ----- Advance to price step (SAFE controls only; never the final submit) -----

# Final-submit verbs that create a LIVE/sellable listing or submit for review.
GO_LIVE_DENY_RE = re.compile(
    r"submit|publish|go ?live|list product|submit for qc|send for review|"
    r"send for qc|launch|create catalog|create listing|add catalog\b", re.I)
# Safe wizard step-advance verbs (move to next step, do NOT go live).
SAFE_NEXT_RE = re.compile(r"^\s*(next|continue|proceed|save (and )?(continue|next)|done)\s*$", re.I)


async def price_field_present(page: Page) -> bool:
    for sel in ("input[type='number']",
                "input[name*='price' i]", "input[id*='price' i]",
                "input[placeholder*='price' i]"):
        try:
            loc = page.locator(sel)
            if await loc.count() and await loc.first.is_visible():
                return True
        except Exception:  # noqa: BLE001
            continue
    # Also accept obvious price-step text.
    try:
        txt = await page.locator("body").inner_text(timeout=2000)
        if re.search(r"meesho price|your price|selling price|price details|set price", txt, re.I):
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


async def advance_to_price_step(page: Page, max_steps: int = 6) -> None:
    _mode["phase"] = "advance"
    for step in range(max_steps):
        if findings["hard_stop"]:
            return
        if await price_field_present(page):
            findings["advance"]["reached_price_step"] = True
            log.info("Price field present at step %d — stopping advance", step)
            return
        clicked = False
        cands = [
            page.get_by_role("button", name=SAFE_NEXT_RE),
            page.locator("button").filter(has_text=SAFE_NEXT_RE),
        ]
        for cand in cands:
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
                    if GO_LIVE_DENY_RE.search(label):
                        log.warning("Refusing go-live control '%s' (HARD LINE)", label[:50])
                        continue
                    if not SAFE_NEXT_RE.search(label):
                        continue
                    log.info("Clicking SAFE step-advance '%s' (step %d)", label[:40], step)
                    findings["advance"]["steps_clicked"].append(label[:40])
                    await el.click(timeout=4000)
                    await asyncio.sleep(4.5)
                    clicked = True
                    break
                except Exception:  # noqa: BLE001
                    continue
            if clicked:
                break
        if not clicked:
            try:
                persist_loc = page.get_by_role("button", name=GO_LIVE_DENY_RE)
                if await persist_loc.count():
                    findings["advance"]["notes"].append(
                        "Only a go-live/submit control advances from this step — NOT clicked.")
            except Exception:  # noqa: BLE001
                pass
            findings["advance"]["reached_price_step"] = await price_field_present(page)
            log.info("No safe step-advance at step %d — stopping", step)
            return
    findings["advance"]["reached_price_step"] = await price_field_present(page)


async def fill_minimal_required_fields(page: Page) -> None:
    """Fill obvious required non-price fields (name / required text) so the
    preview compute fires. Conservative: only short text + selects' first option."""
    # Fill a product/style name if present.
    name_cands = [
        page.get_by_placeholder(re.compile(r"product name|style name|title|name", re.I)),
        page.locator("input[name*='name' i], input[id*='name' i]"),
    ]
    for cand in name_cands:
        try:
            if await cand.count() and await cand.first.is_visible():
                await cand.first.fill("Test Placeholder Product", timeout=3000)
                findings["fields_filled"].append("name")
                await asyncio.sleep(0.5)
                break
        except Exception:  # noqa: BLE001
            continue


async def _fill_labeled_number(page: Page, label_re: re.Pattern, value: str) -> bool:
    """Fill a number input identified by its visible label text. The product
    pricing fields (Meesho Price / MRP / Wrong-Defective Returns Price) are
    labelled, not name-attributed — target by label proximity."""
    # Strategy 0: placeholder match (e.g. 'Enter Meesho Price').
    try:
        loc = page.get_by_placeholder(label_re)
        if await loc.count() and await loc.first.is_visible():
            await loc.first.click(timeout=3000)
            await loc.first.fill(value, timeout=3000)
            await loc.first.press("Tab")
            return True
    except Exception:  # noqa: BLE001
        pass
    # Strategy 1: input directly addressed by accessible name.
    try:
        loc = page.get_by_role("spinbutton", name=label_re)
        if await loc.count() and await loc.first.is_visible():
            await loc.first.click(timeout=3000)
            await loc.first.fill(value, timeout=3000)
            await loc.first.press("Tab")
            return True
    except Exception:  # noqa: BLE001
        pass
    # Strategy 2: find the label element, then the nearest following number input.
    try:
        lbl = page.get_by_text(label_re, exact=False)
        cnt = await lbl.count()
        for i in range(min(cnt, 4)):
            el = lbl.nth(i)
            if not await el.is_visible():
                continue
            # number input within the same field container (climb up to 3 ancestors).
            for xp in ("xpath=following::input[@type='number'][1]",
                       "xpath=ancestor::*[self::div or self::label][1]//input[@type='number'][1]",
                       "xpath=ancestor::*[self::div][2]//input[@type='number'][1]"):
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


async def select_a_size(page: Page) -> bool:
    """The Meesho Price / MRP / WDRP / Inventory inputs (product_size_data) only
    render AFTER a Size is selected (they are per-size columns). Open the 'Size'
    dropdown and pick the first option to unlock the price columns. Selecting a
    size is a form-UI action, not a publish."""
    # The size control is input[name='size'] (ant-style combobox, placeholder 'Select').
    size_locators = [
        page.locator("input[name='size']"),
        page.locator("#size, [id*='size' i]"),
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
            # Options render in a portal/listbox. Pick the first concrete one.
            opt = page.locator(
                "[role='option'], .ant-select-item-option, li[class*='option'], "
                "[class*='MenuItem'], [class*='dropdown'] li")
            on = await opt.count()
            log.info("Size dropdown opened, %d options", on)
            for j in range(min(on, 15)):
                o = opt.nth(j)
                try:
                    if not await o.is_visible():
                        continue
                    name = (await o.inner_text(timeout=1500)).strip()
                    if name and 0 < len(name) < 40 and not re.search(r"select", name, re.I):
                        await o.click(timeout=3000)
                        await asyncio.sleep(3.5)
                        log.info("Selected Size option: %s", name[:30])
                        return True
                except Exception:  # noqa: BLE001
                    continue
            # If no listbox options, the size field may accept typed free text.
            try:
                await el.fill("Free Size", timeout=2000)
                await asyncio.sleep(1.5)
                opt2 = page.locator("[role='option'], .ant-select-item-option")
                if await opt2.count():
                    await opt2.first.click(timeout=2500)
                    await asyncio.sleep(3.0)
                    log.info("Selected Size via typed 'Free Size'")
                    return True
            except Exception:  # noqa: BLE001
                pass
        except Exception as exc:  # noqa: BLE001
            log.warning("size locator attempt failed: %s", exc)
            continue
    return False


async def enter_price_and_capture(page: Page) -> None:
    _mode["phase"] = "price"
    # Unlock the price columns by selecting a Size first.
    if await select_a_size(page):
        findings["fields_filled"].append("Size selected (unlocks price columns)")
    await fill_minimal_required_fields(page)
    # Re-dump fields now that price columns may have rendered.
    try:
        fields2 = await page.evaluate(
            """() => Array.from(document.querySelectorAll('input'))
                .map(e => ({t:e.type, n:e.name||'', p:e.placeholder||'',
                            aria:e.getAttribute('aria-label')||'', vis:!!(e.offsetParent)}))
                .filter(f => f.vis).slice(0,60)""")
        findings["preview"]["notes"].append({"fields_after_size": fields2})
        log.info("Fields after size: %s", [f.get("p") or f.get("n") for f in fields2][:30])
    except Exception:  # noqa: BLE001
        pass
    # Fill the three pricing fields from product_size_data by their labels.
    # Meesho Price is the listing price that drives the payout/commission preview.
    filled = []
    if await _fill_labeled_number(page, re.compile(r"^\s*meesho price", re.I), "150"):
        filled.append("Meesho Price=150")
        findings["price_entered"] = 150
        await asyncio.sleep(4.5)
    if await _fill_labeled_number(page, re.compile(r"^\s*mrp", re.I), "300"):
        filled.append("MRP=300")
        await asyncio.sleep(2.0)
    if await _fill_labeled_number(page, re.compile(r"wrong.*defective.*returns? price", re.I), "140"):
        filled.append("WDRP=140")
        await asyncio.sleep(3.5)
    # Fallback: the price cells live in the size table as bare number inputs that
    # appear AFTER the size row is committed. Try the newly-appeared number inputs
    # whose placeholder/aria mentions price, else the first new number inputs in
    # the size table region.
    if not filled:
        try:
            price_inputs = await page.evaluate(
                """() => {
                    const ins = Array.from(document.querySelectorAll('input[type=number], input[inputmode=numeric]'));
                    return ins.map((e,i) => ({i, n:e.name||'', p:e.placeholder||'',
                        aria:e.getAttribute('aria-label')||'', vis:!!e.offsetParent}))
                        .filter(f=>f.vis);
                }""")
            log.info("Visible number inputs: %s", price_inputs)
            findings["preview"]["notes"].append({"visible_number_inputs": price_inputs})
            # Click any number input whose hints mention price/mrp.
            for f in price_inputs:
                hint = f"{f['n']} {f['p']} {f['aria']}".lower()
                if re.search(r"price|mrp", hint) and not re.search(r"pincode|weight|length|width|height", hint):
                    loc = page.locator("input[type=number], input[inputmode=numeric]").nth(f["i"])
                    await loc.fill("150", timeout=2500)
                    await loc.press("Tab")
                    filled.append(f"numinput[{f['i']}]({f['p'] or f['n']})=150")
                    findings["price_entered"] = 150
                    await asyncio.sleep(4.0)
        except Exception as exc:  # noqa: BLE001
            log.warning("price-cell fallback failed: %s", exc)
    findings["fields_filled"].extend(filled)
    log.info("Pricing fields filled: %s", filled)

    filled_any = bool(filled)
    if not filled_any:
        # Fallback: try the generic placeholder route.
        try:
            cand = page.get_by_placeholder(re.compile(r"meesho price|enter price", re.I))
            if await cand.count() and await cand.first.is_visible():
                await cand.first.fill("150", timeout=3000)
                await cand.first.press("Tab")
                filled_any = True
                findings["price_entered"] = 150
                await asyncio.sleep(4.5)
        except Exception:  # noqa: BLE001
            pass
    if not filled_any:
        findings["preview"]["notes"].append(
            "Could not locate the 'Meesho Price' labelled input at the price step")

    await asyncio.sleep(5.0)
    # Screenshot + DOM dump AFTER price entry to capture any payout/commission preview.
    try:
        shot2 = LOG_DIR / "after_price.png"
        await page.screenshot(path=str(shot2), full_page=True)
        log.info("After-price screenshot -> %s", shot2)
        after_txt = await page.locator("body").inner_text(timeout=4000)
        (LOG_DIR / "after_price_dom.txt").write_text(after_txt)
        log.info("After-price DOM -> %d chars", len(after_txt))
    except Exception as exc:  # noqa: BLE001
        log.warning("after-price dump failed: %s", exc)
    dom = await read_dom_preview(page, "create:price")
    findings["preview"]["dom_commission_hits"] = dom["commission_hits"]
    findings["preview"]["dom_text_excerpt"] = dom["excerpt"]
    if dom["esig_wall"]:
        findings["preview"]["notes"].append("e-sig wall text present on price step")
    findings["preview"]["visible"] = bool(
        dom["commission_hits"] or any(x["commission_keys"] for x in findings["computing_xhr"]))


# ----- Discard catalog (MANDATORY at end) -----

# Prefer the explicit "Discard Catalog" control; only fall back to delete/cancel.
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
                # Confirm dialog if any.
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
    findings["preview"]["notes"].append("Discard Catalog control not found — abandoning by nav-away instead")
    return False


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
                findings["preview"]["notes"].append("Could not reach single/select-category")
                log.warning("Add-Catalog single flow NOT reached")
            else:
                _mode["phase"] = "category"
                await asyncio.sleep(2.0)
                await select_one_category(page)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])

                # Diagnostic dump after category select (round-6 showed image gate here).
                try:
                    await asyncio.sleep(2.0)
                    btns = await page.locator("button").evaluate_all(
                        "els => els.map(e => (e.innerText||'').trim()).filter(Boolean).slice(0,40)")
                    findings["preview"]["notes"].append(
                        {"buttons_after_category": btns, "url": _safe_url(page.url)})
                    log.info("Post-category buttons: %s", btns)
                except Exception:  # noqa: BLE001
                    pass

                # NEW: upload placeholder image to pass the mandatory image gate.
                img_ok = await upload_placeholder_image(page)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                if not img_ok:
                    log.warning("Image gate not satisfied: %s",
                                findings["image_upload"]["rejection_text"])
                    findings["preview"]["notes"].append(
                        "Image upload not satisfied — could not advance to price step. "
                        "Requirement: " + str(findings["image_upload"]["rejection_text"]))
                else:
                    # Advance past the image gate to the price step.
                    await advance_to_price_step(page)
                    if findings["hard_stop"]:
                        raise HardStop(findings["hard_stop"])
                    # Diagnostic dump at the post-image step.
                    try:
                        btns2 = await page.locator("button").evaluate_all(
                            "els => els.map(e => (e.innerText||'').trim()).filter(Boolean).slice(0,40)")
                        inputs2 = await page.locator("input").evaluate_all(
                            "els => els.map(e => ({t:e.type, n:e.name||'', p:e.placeholder||''})).slice(0,40)")
                        findings["preview"]["notes"].append(
                            {"buttons_at_price_step": btns2, "inputs_at_price_step": inputs2,
                             "url": _safe_url(page.url)})
                        log.info("Price-step buttons: %s", btns2)
                        log.info("Price-step inputs: %s", inputs2)
                    except Exception:  # noqa: BLE001
                        pass
                    # DEBUG: dump full price-step DOM text + screenshot to understand
                    # where the Meesho Price / MRP / WDRP fields + preview live.
                    try:
                        full_txt = await page.locator("body").inner_text(timeout=4000)
                        dbg = LOG_DIR / "price_step_dom.txt"
                        dbg.write_text(full_txt)
                        log.info("Dumped price-step DOM text -> %s (%d chars)", dbg, len(full_txt))
                        shot = LOG_DIR / "price_step.png"
                        await page.screenshot(path=str(shot), full_page=True)
                        log.info("Screenshot -> %s", shot)
                        # All input/select/contenteditable with surrounding label text.
                        fields = await page.evaluate(
                            """() => Array.from(document.querySelectorAll('input,select,textarea'))
                                .map(e => ({t:e.type||e.tagName, n:e.name||'', p:e.placeholder||'',
                                            aria:e.getAttribute('aria-label')||'',
                                            vis:!!(e.offsetParent), val:(e.value||'').slice(0,20)}))
                                .slice(0,80)""")
                        findings["preview"]["notes"].append({"all_fields_price_step": fields})
                    except Exception as exc:  # noqa: BLE001
                        log.warning("price-step debug dump failed: %s", exc)
                    await enter_price_and_capture(page)
                    if findings["hard_stop"]:
                        raise HardStop(findings["hard_stop"])

                # MANDATORY: discard the catalog so nothing stays pending/live.
                await discard_catalog(page)

            # Final safety: navigate away (abandon). Never submit.
            try:
                _mode["phase"] = "abandon"
                await page.goto(NEUTRAL_URL, wait_until="domcontentloaded", timeout=15_000)
                log.info("Navigated to neutral page. Nothing published.")
            except Exception:  # noqa: BLE001
                pass

            if findings["discarded"]:
                findings["end_state"] = "DISCARDED (Discard Catalog clicked + abandoned)"
            else:
                findings["end_state"] = (
                    "NOT-EXPLICITLY-DISCARDED — abandoned by nav-away; any wizard "
                    "auto-saved DRAFT may remain (no go-live action taken). "
                    "Manual cleanup of the draft may be needed.")

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
    log.info("==== Meesho ADD-CATALOG PREVIEW CAPTURE probe (option-2, image-gate-authorized) @ %s ====",
             datetime.now().isoformat())
    if not PLACEHOLDER_IMG.exists():
        log.error("Placeholder image not found at %s — generate it first", PLACEHOLDER_IMG)
        return 2
    result = asyncio.run(run())
    f = result["findings"]
    raw_path = LOG_DIR / f"preview_capture_xhrs_{ts}.json"
    try:
        raw_path.write_text(json.dumps(result["raw_xhr_bodies"], indent=2, default=str))
        log.info("Raw XHR bodies -> %s", raw_path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not persist raw bodies: %s", exc)

    print("\n========= PREVIEW CAPTURE PROBE SUMMARY =========")
    print(json.dumps(f, indent=2, default=str))
    print("\n--- raw XHR body keys captured ---")
    for url, body in list(result["raw_xhr_bodies"].items())[:30]:
        keys = sorted(body.keys())[:50] if isinstance(body, dict) else "[list]"
        print(f"  {url}  keys={keys}")
    print("================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
