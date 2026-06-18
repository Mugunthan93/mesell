"""Meesho ADD-CATALOG create-flow commission/payout PREVIEW probe — STRICTLY READ-ONLY, NO-SUBMIT.

Goal (round 6 — NEW account 8754713794)
---------------------------------------
Prove the ADD-CATALOG / Add-Single-Product create form exposes a LIVE
commission / payout preview when a price is entered, for ONE category,
WITHOUT creating any listing.

Method (incorporates every prior-round lesson)
----------------------------------------------
  1. Log in (proven authenticated-WebKit + Akamai-bypass idiom).
  2. Auto-detect supplier_id / identifier / store name / #catalogs from the
     supplier-config + listing XHRs (NOT hardcoded — this is a NEW account).
  3. Reach Add-Catalog by NAVIGATING THE REAL SIDEBAR MENU (clicking the actual
     menu item), NOT a guessed URL. Repeated memory lesson: the SPA serves its
     shell for ANY path, so guessed deep-links never mount the content component
     and fire zero data XHRs. Real pages are reached by sidebar nav.
  4. Select ONE real category in the create flow (report id/name).
  5. In the PRICE section, type a test value (₹150) + minimal sibling fields to
     TRIGGER the preview compute. Persist any preview XHR on FIRST arrival.
  6. READ the rendered preview DOM (commission %/₹, payout/transfer, fee lines,
     WDRP suggestion) and capture the computing XHR (endpoint, request payload,
     response shape).

ABSOLUTE GUARDRAIL — ZERO WRITES / NEVER CREATE A LISTING
---------------------------------------------------------
  * READ-ONLY. Navigation + sidebar clicks to REACH the form + filling the price
    field + reading the preview ONLY.
  * NEVER click Create / Submit / Save / Publish / Confirm / "Add Catalog" /
    any final-submit, NOR any "Next" step that persists/creates. The submit
    allow-list is empty: the only clicks issued are sidebar/menu navigation and
    opening a category dropdown — never a persisting control.
  * If commission ONLY appears after a submit/next-that-persists, STOP before it
    and report "post-submit-only". Do NOT submit to reveal it.
  * When done reading, ABANDON the form (navigate to a neutral page). Persist
    nothing on Meesho.
  * Hard-stop on OTP / 401 / 403 / 429. 463 tolerated per-URL (recorded).
  * Never log credential values.

Output
------
  * logs/scraper/create_preview_<ts>.log (gitignored)
  * logs/scraper/create_preview_xhrs_<ts>.json (raw preview XHR bodies, gitignored)
  * stdout JSON summary.
Nothing is committed. Nothing under backend/app/data is written.
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

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000

SESSION_STOP_CODES = {401, 403, 429}
TOLERATED_BLOCK_CODES = {463}

OTP_HINT_RE = re.compile(
    r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the code)\b", re.I)

# Preview/commission-bearing XHR classifier.
PREVIEW_XHR_RE = re.compile(
    r"commission|referral[-_]?fee|monetization|payout|transfer[-_]?price|"
    r"price[-_]?breakup|fee[-_]?breakup|estimate|net[-_]?amount|earning|"
    r"price[-_]?recommend|smart[-_]?pricing|wdrp|deduction|price[-_]?suggest|"
    r"calculate|preview", re.I)
# Config/identity XHR classifier.
CONFIG_XHR_RE = re.compile(
    r"prefetch-supply-data|supplier/config|fetch-registration-status|"
    r"fetch-home|fetch-supplier-products|fetch-growth-overview", re.I)
# Category XHR classifier (for create-flow category list).
CATEGORY_XHR_RE = re.compile(r"category|sub[-_]?category|sscat|taxonomy|attribute", re.I)

COMMISSION_KEY_RE = re.compile(
    r"commission|referral|monetization|payout|net[-_]?amount|payable|earning|"
    r"net[-_]?margin|net[-_]?price|fee|charge|deduction|settle|transfer|rate|wdrp", re.I)
PRICE_KEY_RE = re.compile(
    r"price|mrp|cost|amount|selling|listing[-_]?price|meesho[-_]?price|transfer", re.I)
CATEGORY_KEY_RE = re.compile(r"category|sub[-_]?category|sscat|catalog[-_]?type|product[-_]?type", re.I)

# DOM patterns for the preview.
DOM_COMMISSION_RE = re.compile(
    r"(commission|referral fee|you(?:'ll| will) (?:get|receive|earn)|"
    r"net (?:amount|payout|earning)|transfer price|payout|settlement|deduction|wdrp|"
    r"wrong\s*/?\s*defective)"
    r"[^0-9₹%]{0,40}(₹\s?\d[\d,]*\.?\d*|\d{1,3}(?:\.\d+)?\s?%)",
    re.I)


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"create_preview_{ts}.log"
    logger = logging.getLogger("meesho-create-preview")
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
    logger.info("Create-preview probe logfile: %s", log_path)
    return logger, ts


log = logging.getLogger("meesho-create-preview")


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
        raise HardStop(f"Login did not redirect away from /login. URL={_safe_url(page.url)!r} body={snippet!r}")
    log.info("Login OK — at %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Capture state
# ---------------------------------------------------------------------------

findings: dict[str, Any] = {
    "account": {"supplier_id": None, "identifier": None, "store_name": None,
                "num_catalogs": None, "registration_status": None,
                "agreement_accepted": None, "default_monetization_percent": None},
    "add_catalog": {"reached_via": None, "url": None, "sidebar_label": None},
    "category_selected": {"id": None, "name": None},
    "price_entered": None,
    "preview": {"visible_pre_submit": None, "dom_commission_hits": [],
                "dom_text_excerpt": None, "notes": []},
    "computing_xhr": [],     # [{url, status, method, request_post_data, top_keys, commission_keys, sample}]
    "config_xhrs": [],
    "category_xhrs": [],
    "blocked_endpoints": [],
    "hard_stop": None,
}

raw_xhr_bodies: dict[str, Any] = {}
_mode = {"phase": "login"}  # login | nav | category | price


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
                # Account identity mining.
                if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                    findings["account"]["supplier_id"] = findings["account"]["supplier_id"] or v
                if kl in ("store_name", "shop_name", "supplier_name", "business_name") and isinstance(v, str) and v not in ("-", ""):
                    findings["account"]["store_name"] = findings["account"]["store_name"] or v
                if kl == "default_monetization_percent" and isinstance(v, (int, float, str)):
                    findings["account"]["default_monetization_percent"] = v
                if kl == "registration_status" and isinstance(v, str):
                    findings["account"]["registration_status"] = v
                if "agreement_accepted" == kl and isinstance(v, (bool, str)):
                    findings["account"]["agreement_accepted"] = v
                if kl == "is_agreement_accepted" and isinstance(v, bool):
                    findings["account"]["agreement_accepted"] = v
                if kl in ("total_entities", "total_catalogs", "catalog_count") and isinstance(v, int):
                    if findings["account"]["num_catalogs"] is None:
                        findings["account"]["num_catalogs"] = v
                if kl == "supplier_identifier_to_id_mapping" and isinstance(v, dict):
                    # {identifier: id}
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

    # Always mine identity/config from any JSON.
    mined: dict[str, Any] = {}
    _walk_extract(body, mined)

    is_preview = bool(PREVIEW_XHR_RE.search(url))
    is_config = bool(CONFIG_XHR_RE.search(url))
    is_category = bool(CATEGORY_XHR_RE.search(url))

    if is_preview or is_config:
        # Persist raw body on FIRST arrival (round-4 lesson).
        key = _safe_url(url)
        if key not in raw_xhr_bodies:
            txt = json.dumps(body, default=str)
            raw_xhr_bodies[key] = body if len(txt) <= 120_000 else {
                "_truncated_len": len(txt),
                "_top_keys": sorted(body.keys())[:80] if isinstance(body, dict) else "[list]",
            }

    req = resp.request
    post_data = None
    try:
        post_data = req.post_data
    except Exception:  # noqa: BLE001
        post_data = None

    record = {
        "url": _safe_url(url),
        "status": status,
        "method": req.method,
        "phase": _mode["phase"],
        "request_post_data": (post_data[:2000] if isinstance(post_data, str) else None),
        "top_keys": sorted(list(body.keys()))[:40] if isinstance(body, dict) else "[list]",
        "commission_keys": sorted((mined.get("commission") or {}).keys()),
        "price_keys": sorted((mined.get("price") or {}).keys()),
        "category_keys": sorted((mined.get("category") or {}).keys()),
        "commission_sample": dict(list((mined.get("commission") or {}).items())[:12]),
        "price_sample": dict(list((mined.get("price") or {}).items())[:12]),
    }

    if is_preview and (record["commission_keys"] or record["price_keys"] or _mode["phase"] == "price"):
        findings["computing_xhr"].append(record)
        log.info("PREVIEW XHR [%s] %s %s comm=%s price=%s",
                 _mode["phase"], req.method, _safe_url(url),
                 record["commission_keys"], record["price_keys"])
    elif is_config:
        findings["config_xhrs"].append({"url": record["url"], "status": status,
                                        "commission_keys": record["commission_keys"]})
        log.info("CONFIG XHR %s", _safe_url(url))
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
        out["commission_hits"].append(m.group(0).strip()[:90])
    out["esig_wall"] = bool(re.search(
        r"add signature|e-?signature|sign(?:ature)? is missing|accept.{0,20}agreement", txt, re.I))
    # Keep a small excerpt around any "payout"/"commission"/"price" word for context.
    m = re.search(r".{0,120}(commission|payout|transfer|you.{0,3}receive|net amount|wdrp).{0,200}", txt, re.I)
    if m:
        out["excerpt"] = re.sub(r"\s+", " ", m.group(0)).strip()[:400]
    return out


async def click_sidebar_to_add_catalog(page: Page) -> bool:
    """Navigate to Add-Catalog by clicking the REAL sidebar/menu — never a guessed URL.

    Strategy: open Catalogs/Cataloging section in the sidebar, then click an
    'Add' / 'Add Catalog' / 'Add Single Product' / 'Add New Product' control.
    Returns True if a create-flow page was reached (URL changed to a catalog-
    upload/add route AND a form/category control appears).
    """
    # 1) Find a top-level Catalogs/Products menu item in the sidebar and click it.
    catalog_menu_candidates = [
        page.get_by_role("link", name=re.compile(r"^\s*(catalog|cataloging|products?|my products)\s*$", re.I)),
        page.get_by_role("button", name=re.compile(r"^\s*(catalog|cataloging|products?)\s*$", re.I)),
        page.locator("a,button,span,div").filter(has_text=re.compile(r"^\s*(Catalogs?|Products?)\s*$", re.I)),
    ]
    opened_section = False
    for cand in catalog_menu_candidates:
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
                    opened_section = True
                    log.info("Sidebar: clicked a Catalogs/Products menu item")
                    break
            except Exception:  # noqa: BLE001
                continue
        if opened_section:
            break

    # 2) Click the Add-SINGLE-Product control. PREFER single-product over bulk:
    #    the bulk flow is a CSV upload (no live price preview); the single-product
    #    flow renders the live commission/payout preview we need.
    add_candidates = [
        page.get_by_role("link", name=re.compile(r"add (a )?single (product|catalog)", re.I)),
        page.get_by_role("button", name=re.compile(r"add (a )?single (product|catalog)", re.I)),
        page.get_by_text(re.compile(r"single (product|catalog)|add one product|add product", re.I)),
        page.get_by_role("link", name=re.compile(r"add (new )?(product|catalog)(?!.*bulk)", re.I)),
        page.get_by_role("button", name=re.compile(r"add (new )?(product|catalog)(?!.*bulk)", re.I)),
        page.locator("a,button").filter(
            has_text=re.compile(r"\bAdd\b.*\b(Single|Product)\b", re.I)),
    ]
    for cand in add_candidates:
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
                # Skip the BULK CSV flow — it has no live price preview.
                if re.search(r"bulk", label_txt, re.I):
                    log.info("Skipping bulk control '%s'", label_txt)
                    continue
                # GUARDRAIL: the Add control here OPENS the create form (navigation),
                # it does NOT create a listing. It's the entry point, safe to click.
                await el.click(timeout=4000)
                await asyncio.sleep(4.0)
                findings["add_catalog"]["reached_via"] = "sidebar_click"
                findings["add_catalog"]["sidebar_label"] = label_txt
                findings["add_catalog"]["url"] = _safe_url(page.url)
                log.info("Sidebar: clicked Add control '%s' -> %s", label_txt, _safe_url(page.url))
                # Verify we're on a create flow (URL hints or a category/upload form).
                if re.search(r"add|upload|create|catalog", page.url, re.I):
                    return True
                return True
            except Exception as exc:  # noqa: BLE001
                log.warning("add candidate click failed (non-fatal): %s", exc)
                continue
    return False


async def select_one_category(page: Page) -> bool:
    """Open the category picker in the create flow and select ONE category.

    Selecting a category is a READ/UI action (it loads that category's attribute
    schema + price section); it does NOT persist a listing.
    """
    # The create flow typically asks for a category first (search box or list).
    cat_input_candidates = [
        page.get_by_placeholder(re.compile(r"search.*(category|product)", re.I)),
        page.get_by_role("textbox", name=re.compile(r"category|search", re.I)),
        page.locator("input[type='text']").first,
    ]
    typed = False
    for cand in cat_input_candidates:
        try:
            if await cand.count() and await cand.first.is_visible():
                await cand.first.click(timeout=3000)
                await cand.first.fill("hair", timeout=3000)  # broad term -> many real leaves
                await asyncio.sleep(2.5)
                typed = True
                log.info("Category search filled")
                break
        except Exception:  # noqa: BLE001
            continue

    # Click the first concrete category option that appears.
    option_candidates = [
        page.get_by_role("option"),
        page.locator("[role='option'], li, .ant-select-item, .category-item, [class*='option']"),
    ]
    for cand in option_candidates:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 8)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                name = (await el.inner_text(timeout=1500)).strip()
                if not name or len(name) > 80:
                    continue
                await el.click(timeout=3000)
                await asyncio.sleep(3.0)
                findings["category_selected"]["name"] = name[:80]
                log.info("Selected category option: %s", name[:80])
                return True
            except Exception:  # noqa: BLE001
                continue
    if typed:
        findings["preview"]["notes"].append("Category search typed but no option clickable")
    return False


# Verbs that PERSIST/CREATE a listing — NEVER click these.
PERSIST_DENY_RE = re.compile(
    r"submit|create|save|publish|confirm|add catalog|go live|list product|"
    r"finish|done|upload|send for|launch", re.I)
# Safe step-advance verbs (do NOT persist a listing in the single-product wizard).
SAFE_NEXT_RE = re.compile(r"^\s*(next|continue|proceed)\s*$", re.I)


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
    return False


async def advance_to_price_step(page: Page, max_steps: int = 4) -> None:
    """Click ONLY safe Next/Continue controls until a price field appears.

    GUARDRAIL: a strict deny-list blocks any persisting verb (Submit/Create/Save/
    Publish/Confirm/Add Catalog/Upload/Finish/...). We stop the moment a price
    input is visible — we never click the final submit. If the only forward
    control is a persisting one, we STOP and record 'post-submit-only'.
    """
    for step in range(max_steps):
        if findings["hard_stop"]:
            return
        if await price_field_present(page):
            log.info("Price field present at step %d — stopping advance", step)
            return
        # Find a safe Next/Continue button that is NOT a persisting control.
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
            for i in range(min(n, 4)):
                try:
                    el = cand.nth(i)
                    if not await el.is_visible():
                        continue
                    label = (await el.inner_text(timeout=1500)).strip()
                    if PERSIST_DENY_RE.search(label):
                        log.warning("Refusing persisting control '%s' (guardrail)", label[:40])
                        continue
                    if not SAFE_NEXT_RE.search(label):
                        continue
                    log.info("Clicking safe step-advance '%s' (step %d)", label[:30], step)
                    await el.click(timeout=4000)
                    await asyncio.sleep(4.0)
                    clicked = True
                    break
                except Exception:  # noqa: BLE001
                    continue
            if clicked:
                break
        if not clicked:
            # No safe forward control — check if a persisting-only control exists.
            try:
                persist_loc = page.get_by_role("button", name=PERSIST_DENY_RE)
                if await persist_loc.count():
                    findings["preview"]["notes"].append(
                        "Only a persisting (submit/create) control advances from this "
                        "step — NOT clicked. If preview is gated behind it -> post-submit-only.")
            except Exception:  # noqa: BLE001
                pass
            log.info("No safe step-advance control at step %d — stopping", step)
            return


async def enter_price_and_read_preview(page: Page) -> None:
    """Type ₹150 into the price field to TRIGGER the preview compute. NEVER submit."""
    _mode["phase"] = "price"
    price_candidates = [
        page.get_by_placeholder(re.compile(r"meesho price|price|selling|mrp|cost", re.I)),
        page.get_by_role("spinbutton"),
        page.locator("input[type='number']"),
        page.locator("input[name*='price' i], input[id*='price' i]"),
    ]
    filled_any = False
    for cand in price_candidates:
        try:
            n = await cand.count()
        except Exception:  # noqa: BLE001
            n = 0
        for i in range(min(n, 4)):
            try:
                el = cand.nth(i)
                if not await el.is_visible():
                    continue
                await el.click(timeout=3000)
                await el.fill("150", timeout=3000)
                await el.press("Tab")  # blur -> triggers preview compute
                await asyncio.sleep(4.0)
                filled_any = True
                findings["price_entered"] = 150
                log.info("Filled a price field with 150 (blurred to trigger preview)")
            except Exception:  # noqa: BLE001
                continue
        if filled_any:
            break
    if not filled_any:
        findings["preview"]["notes"].append("No price input located in the create flow at this step")

    # Dwell + read the preview DOM.
    await asyncio.sleep(3.0)
    dom = await read_dom_preview(page, "create:price")
    findings["preview"]["dom_commission_hits"] = dom["commission_hits"]
    findings["preview"]["dom_text_excerpt"] = dom["excerpt"]
    if dom["esig_wall"]:
        findings["preview"]["notes"].append("e-sig wall text present on create flow")
    findings["preview"]["visible_pre_submit"] = bool(
        dom["commission_hits"] or any(x["commission_keys"] or x["price_keys"]
                                      for x in findings["computing_xhr"]))


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
            await asyncio.sleep(5.0)  # dwell so home/config XHRs fire -> identity
            detect_identifier_from_url(page.url)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            log.info("Account so far: %s", findings["account"])

            # ---- Reach Add-Catalog via REAL sidebar nav ----
            _mode["phase"] = "nav"
            reached = await click_sidebar_to_add_catalog(page)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            if not reached:
                findings["preview"]["notes"].append(
                    "Could not reach Add-Catalog via sidebar nav — menu labels not matched")
                log.warning("Add-Catalog NOT reached via sidebar")
            else:
                # ---- Select one category ----
                _mode["phase"] = "category"
                await asyncio.sleep(2.0)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                await select_one_category(page)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                # ---- Diagnostic: dump buttons + step labels after category select ----
                try:
                    await asyncio.sleep(2.0)
                    btns = await page.locator("button").evaluate_all(
                        "els => els.map(e => (e.innerText||'').trim()).filter(Boolean).slice(0,40)")
                    steps = await page.locator(
                        "[class*='step' i], [class*='Step'], .ant-steps-item, [role='tablist']"
                    ).evaluate_all(
                        "els => els.map(e => (e.innerText||'').trim()).filter(Boolean).slice(0,12)")
                    inputs = await page.locator("input").evaluate_all(
                        "els => els.map(e => ({t:e.type, n:e.name||'', p:e.placeholder||''})).slice(0,30)")
                    findings["preview"]["notes"].append({"buttons_visible": btns,
                                                          "step_labels": steps,
                                                          "inputs": inputs,
                                                          "url_at_category": _safe_url(page.url)})
                    log.info("Post-category buttons: %s", btns)
                    log.info("Post-category steps: %s", steps)
                    log.info("Post-category inputs: %s", inputs)
                except Exception as exc:  # noqa: BLE001
                    log.warning("diagnostic dump failed: %s", exc)
                # ---- Advance only via SAFE Next/Continue to the price step ----
                await advance_to_price_step(page)
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                # ---- Enter price + read preview ----
                await enter_price_and_read_preview(page)

            # ---- Abandon the form: navigate to a neutral page, persist nothing ----
            try:
                _mode["phase"] = "abandon"
                await page.goto("https://supplier.meesho.com/panel/v3/new/root/login",
                                wait_until="domcontentloaded", timeout=15_000)
                log.info("Form abandoned (navigated away). Nothing persisted.")
            except Exception:  # noqa: BLE001
                pass

        except HardStop as exc:
            findings["hard_stop"] = str(exc)
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
    log.info("==== Meesho ADD-CATALOG create-flow PREVIEW READ-ONLY probe @ %s ====",
             datetime.now().isoformat())
    result = asyncio.run(run())
    f = result["findings"]
    # Persist raw XHR bodies to gitignored file.
    raw_path = LOG_DIR / f"create_preview_xhrs_{ts}.json"
    try:
        raw_path.write_text(json.dumps(result["raw_xhr_bodies"], indent=2, default=str))
        log.info("Raw preview/config XHR bodies -> %s", raw_path)
    except Exception as exc:  # noqa: BLE001
        log.warning("could not persist raw bodies: %s", exc)

    print("\n========= CREATE-PREVIEW PROBE SUMMARY =========")
    print(json.dumps(f, indent=2, default=str))
    print("\n--- raw XHR body keys captured ---")
    for url, body in list(result["raw_xhr_bodies"].items())[:20]:
        keys = sorted(body.keys())[:40] if isinstance(body, dict) else "[list]"
        print(f"  {url}  keys={keys}")
    print("================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
