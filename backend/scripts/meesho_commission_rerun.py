"""Meesho Commission Re-Run — Post e-Signature Agreement Check + Discovery.

Session 4 (2026-06-16): Commission Re-Run after founder e-signature completion.

Protocol:
    Step 1 — Confirm is_agreement_accepted=true via prefetch-supply-data.
             If still false: STOP immediately, report exact field values.
    Step 2 — Navigate referral-fee and pricing pages, intercept all XHR with
             broad logging (ALL Meesho-domain requests, not just pattern-matched).
             With agreement accepted, the commission component SHOULD mount and
             fire its XHR.
    Step 3 — If commission XHR found: parse + write category_commissions.json.
             If not found: take screenshot, report what the page shows.

This script is a targeted re-run companion to meesho_commission_scraper.py.
It is more aggressive in:
    - Checking agreement status as a gate (stops cleanly if still false).
    - Logging ALL Meesho-domain XHR (not filtered to commission pattern) to
      catch an endpoint we may not have anticipated.
    - Extended dwell + scroll interactions to trigger lazy-loaded components.
    - Screenshot on failure for evidence.

Hard stops: 401/403/463/429/captcha/login-fail (same as primary scraper).
Credentials: from ~/.meesho_creds.env (never logged).
Output: /private/tmp/mesell-wt/category-seeding/backend/app/data/category_commissions.json
Log: /private/tmp/mesell-wt/category-seeding/logs/scraper/commission_rerun_YYYY-MM-DD_HH-MM.log
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
from playwright.async_api import (
    BrowserContext,
    Page,
    Playwright,
    Request,
    Response,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

WORKTREE_ROOT = Path("/private/tmp/mesell-wt/category-seeding")
CREDS_FILE = Path.home() / "Project" / "mesell" / ".meesho_creds.env"
_CREDS_OVERRIDE = os.environ.get("MEESHO_CREDS_FILE", "").strip()
if _CREDS_OVERRIDE:
    CREDS_FILE = Path(_CREDS_OVERRIDE)

COMMISSION_OUTPUT_FILE = (
    WORKTREE_ROOT / "backend" / "app" / "data" / "category_commissions.json"
)
CATEGORY_TREE_FILE = (
    WORKTREE_ROOT / "backend" / "app" / "data" / "meesho_category_tree.json"
)
LOG_DIR = WORKTREE_ROOT / "logs" / "scraper"

# ---------------------------------------------------------------------------
# Meesho constants
# ---------------------------------------------------------------------------

SUPPLIER_ID = 4359160
IDENTIFIER = "oinpw"
LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
MEESHO_DOMAIN = "supplier.meesho.com"

PREFETCH_URL = f"https://{MEESHO_DOMAIN}/api/container/supplier/prefetch-supply-data"

# Pages to navigate for commission discovery (referral-fee + pricing)
DISCOVERY_PAGES = [
    f"https://{MEESHO_DOMAIN}/panel/v3/new/growth/{IDENTIFIER}/referral-fee",
    f"https://{MEESHO_DOMAIN}/panel/v3/new/growth/{IDENTIFIER}/pricing",
]

# Commission URL pattern — broad: anything with fee/commission/referral/rate/pricing in API path
COMMISSION_PATTERN = re.compile(
    r"(?:referral[_-]?fee|commission|referral|pricing|charge|rate|fee)",
    re.IGNORECASE,
)

# All Meesho-domain API pattern (to log everything from supplier.meesho.com /api/ paths)
MEESHO_API_PATTERN = re.compile(r"supplier\.meesho\.com/api/", re.IGNORECASE)

# ---------------------------------------------------------------------------
# Timeouts / throttle
# ---------------------------------------------------------------------------

LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000
PAGE_NAV_TIMEOUT_MS = 30_000
API_REQUEST_TIMEOUT_MS = 30_000
NAV_JITTER_MIN_S = 2.0
NAV_JITTER_MAX_S = 5.0
REQ_JITTER_MIN_S = 1.0
REQ_JITTER_MAX_S = 3.0

SESSION_STOP_CODES = {401, 403, 463}
RATE_LIMIT_STOP_CODES = {429}
CAPTCHA_MARKERS = ("captcha", "are you a human", "verify you are human", "recaptcha")
BLOCK_MARKERS = ("access denied", "too many requests", "rate limit", "forbidden") + CAPTCHA_MARKERS

# API headers (proven from meesho_batch_scraper.py)
def _api_headers() -> dict[str, str]:
    return {
        "identifier": IDENTIFIER,
        "client-type": "d-web",
        "client-package-version": "1.0.1",
        "supplier-id": str(SUPPLIER_ID),
        "accept": "application/json, text/plain, */*",
    }


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"commission_rerun_{ts}.log"

    logger = logging.getLogger("meesho-commission-rerun")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
    )
    fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.propagate = False
    logger.info("Re-run log: %s", log_path)
    return logger


log = logging.getLogger("meesho-commission-rerun")


def _safe_url(url: str) -> str:
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}"
    except Exception:
        return "<url-parse-error>"


# ---------------------------------------------------------------------------
# Hard stop
# ---------------------------------------------------------------------------

class HardStopError(RuntimeError):
    """Raised on 401/403/463/429/captcha/login-fail. Never retry on this."""


def _check_status(status: int, label: str) -> None:
    if status in SESSION_STOP_CODES:
        raise HardStopError(
            f"HTTP {status} from {label} — Akamai/auth block. Abort + investigate."
        )
    if status in RATE_LIMIT_STOP_CODES:
        raise HardStopError(
            f"HTTP {status} from {label} — rate limited. Stop immediately."
        )


async def detect_block(page: Page) -> None:
    url = page.url
    for token in ("captcha", "/error", "/blocked", "access-denied"):
        if token in url:
            raise HardStopError(f"Block URL token detected: {_safe_url(url)}")
    try:
        body_text = (
            await page.locator("body").inner_text(timeout=3_000) or ""
        ).lower()
    except Exception:
        return
    for marker in CAPTCHA_MARKERS:
        if marker in body_text:
            raise HardStopError(
                f"CAPTCHA detected (marker={marker!r}). NEVER solve. Abort + report."
            )
    for marker in BLOCK_MARKERS:
        if marker in body_text:
            raise HardStopError(f"Block marker in page body: {marker!r}")


async def jitter(min_s: float = NAV_JITTER_MIN_S, max_s: float = NAV_JITTER_MAX_S) -> None:
    delay = random.uniform(min_s, max_s)
    await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------

def load_creds() -> tuple[str, str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Creds file not found: {CREDS_FILE}")
    load_dotenv(CREDS_FILE)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    log.info("Credentials loaded (not logged)")
    return user, pwd


# ---------------------------------------------------------------------------
# Login (identical pattern to meesho_batch_scraper.py)
# ---------------------------------------------------------------------------

async def perform_login(page: Page, username: str, password: str) -> None:
    log.info("Navigating to login: %s", LOGIN_URL)
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await jitter(1.5, 2.5)
    await detect_block(page)

    user_field = None
    for build in [
        lambda: page.get_by_placeholder(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_label(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_role("textbox", name=re.compile(r"email|mobile", re.I)),
        lambda: page.locator("input[type='text']").first,
    ]:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=5_000)
            user_field = loc
            break
        except Exception:
            continue
    if user_field is None:
        raise HardStopError("Could not locate username field on login page")
    await user_field.fill(username)
    await jitter(0.8, 1.5)

    pwd_field = None
    for build in [
        lambda: page.get_by_placeholder(re.compile(r"password", re.I)),
        lambda: page.get_by_label(re.compile(r"password", re.I)),
        lambda: page.locator("input[type='password']").first,
    ]:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=5_000)
            pwd_field = loc
            break
        except Exception:
            continue
    if pwd_field is None:
        raise HardStopError("Could not locate password field on login page")
    await pwd_field.fill(password)
    await jitter(0.8, 1.5)

    submit = None
    for build in [
        lambda: page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ]:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=5_000)
            submit = loc
            break
        except Exception:
            continue
    if submit is None:
        raise HardStopError("Could not locate submit button on login page")

    log.info("Submitting login form (credentials not logged)")
    await submit.click()

    try:
        await page.wait_for_url(lambda u: "login" not in u, timeout=LOGIN_NAV_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        snippet = ""
        try:
            snippet = (await page.locator("body").inner_text(timeout=2_000))[:300]
        except Exception:
            pass
        raise HardStopError(
            f"Login did not redirect away from /login. "
            f"URL={_safe_url(page.url)!r} body={snippet!r}"
        )
    await page.wait_for_load_state("domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await detect_block(page)
    log.info("LOGIN OK — current URL: %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Step 1: Agreement status check
# ---------------------------------------------------------------------------

async def check_agreement_status(ctx: BrowserContext) -> dict[str, Any]:
    """Navigate the home page and intercept prefetch-supply-data response.

    Using page navigation to fire the XHR naturally (rather than ctx.request.post
    which may receive HTTP 500 due to missing request body format or session tokens).
    The home page fires prefetch-supply-data automatically on load.
    """
    log.info("=== STEP 1: Checking agreement status via home page navigation ===")

    agreement_body: dict[str, Any] = {}
    agreement_event = asyncio.Event()

    async def _capture_prefetch(response: Response) -> None:
        if "prefetch-supply-data" in response.url and response.status == 200:
            try:
                body = await response.json()
                agreement_body.update(body if isinstance(body, dict) else {"_raw": body})
                log.info("prefetch-supply-data intercepted from page navigation — keys: %s", list(agreement_body.keys()))
                agreement_event.set()
            except Exception as exc:
                log.warning("Could not parse prefetch-supply-data JSON: %s", exc)
                agreement_event.set()

    ctx.on("response", _capture_prefetch)

    page = await ctx.new_page()
    try:
        home_url = f"https://{MEESHO_DOMAIN}/panel/v3/new/growth/{IDENTIFIER}/home"
        log.info("Navigating to home page to trigger prefetch-supply-data: %s", home_url)
        try:
            await page.goto(home_url, wait_until="domcontentloaded", timeout=PAGE_NAV_TIMEOUT_MS)
        except PlaywrightTimeoutError:
            log.warning("Home page nav timeout — continuing")

        await detect_block(page)

        # Wait up to 10s for the prefetch response to be captured
        try:
            await asyncio.wait_for(agreement_event.wait(), timeout=10.0)
        except asyncio.TimeoutError:
            log.warning("Timed out waiting for prefetch-supply-data response — will check what was captured")

        # Also try networkidle
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except PlaywrightTimeoutError:
            pass

    finally:
        ctx.remove_listener("response", _capture_prefetch)
        try:
            await page.close()
        except Exception:
            pass

    body = agreement_body
    if not body:
        log.warning("prefetch-supply-data was NOT captured from home page navigation. Will try ctx.request.post as fallback.")
        # Fallback: try direct POST with content-type
        try:
            resp = await ctx.request.post(
                PREFETCH_URL,
                headers={**_api_headers(), "content-type": "application/json"},
                data=json.dumps({"supplierIds": [SUPPLIER_ID]}),
                timeout=API_REQUEST_TIMEOUT_MS,
            )
            if resp.status == 200:
                body = await resp.json()
                if isinstance(body, dict):
                    agreement_body.update(body)
                    log.info("prefetch-supply-data fallback POST succeeded — keys: %s", list(body.keys()))
            else:
                log.warning("prefetch-supply-data fallback POST returned HTTP %d", resp.status)
        except Exception as exc:
            log.warning("prefetch-supply-data fallback failed: %s", exc)

    log.info("prefetch-supply-data top-level keys: %s", list(body.keys()) if isinstance(body, dict) else type(body).__name__)

    # Extract the supplier sub-object (structure varies: may be body.supplier or body.data.supplier)
    supplier: dict[str, Any] = {}
    if isinstance(body, dict):
        supplier = body.get("supplier", body.get("data", {}).get("supplier", body))

    agreement_fields: dict[str, Any] = {}
    all_keys_flat: dict[str, Any] = {}

    def _flatten(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                flat_key = f"{prefix}.{k}" if prefix else k
                all_keys_flat[flat_key] = v
                _flatten(v, flat_key)

    _flatten(body)

    # Collect agreement-relevant fields
    agreement_keywords = (
        "agreement", "signature", "esign", "e_sign", "monetization",
        "referral", "commission", "enable_referral", "onboard",
    )
    for flat_key, val in all_keys_flat.items():
        key_lower = flat_key.lower()
        if any(kw in key_lower for kw in agreement_keywords):
            agreement_fields[flat_key] = val
            log.info("  AGREEMENT FIELD: %s = %r", flat_key, val)

    # Key field: is_agreement_accepted
    is_accepted = all_keys_flat.get("is_agreement_accepted")
    if is_accepted is None:
        # Try nested paths
        for flat_key, val in all_keys_flat.items():
            if "is_agreement_accepted" in flat_key.lower():
                is_accepted = val
                break

    default_monetization = all_keys_flat.get(
        "default_monetization_percent",
        all_keys_flat.get("supplier.default_monetization_percent"),
    )
    enable_referral_v3 = all_keys_flat.get(
        "enable_referral_v3",
        all_keys_flat.get("supplier.enable_referral_v3"),
    )

    log.info("Agreement check result:")
    log.info("  is_agreement_accepted       = %r", is_accepted)
    log.info("  default_monetization_percent = %r", default_monetization)
    log.info("  enable_referral_v3           = %r", enable_referral_v3)
    log.info("  All agreement-related fields: %s", agreement_fields)

    return {
        "is_agreement_accepted": is_accepted,
        "default_monetization_percent": default_monetization,
        "enable_referral_v3": enable_referral_v3,
        "all_agreement_fields": agreement_fields,
        "raw_body_keys": list(body.keys()) if isinstance(body, dict) else str(type(body)),
    }


# ---------------------------------------------------------------------------
# Step 2: Discovery — broad intercept of ALL Meesho-domain API calls
# ---------------------------------------------------------------------------

class BroadInterceptor:
    """Intercepts ALL requests to supplier.meesho.com/api/ paths.

    More aggressive than the primary scraper's COMMISSION_PATTERN filter —
    logs everything so we do not miss the commission endpoint regardless of
    what it's called.
    """

    def __init__(self, ctx: BrowserContext) -> None:
        self._ctx = ctx
        self.all_api_requests: list[dict[str, Any]] = []
        self.commission_candidates: list[dict[str, Any]] = []
        self.captured_responses: list[dict[str, Any]] = []

    async def __aenter__(self) -> "BroadInterceptor":
        self._ctx.on("request", self._on_request)
        self._ctx.on("response", self._on_response)
        return self

    async def __aexit__(self, *_: Any) -> None:
        self._ctx.remove_listener("request", self._on_request)
        self._ctx.remove_listener("response", self._on_response)

    def _on_request(self, request: Request) -> None:
        url = request.url
        if MEESHO_API_PATTERN.search(url):
            entry = {
                "url": _safe_url(url),
                "method": request.method,
                "resource_type": request.resource_type,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            self.all_api_requests.append(entry)
            log.info("[API-REQUEST] %s %s", request.method, _safe_url(url))

            if COMMISSION_PATTERN.search(url):
                self.commission_candidates.append(entry)
                log.info("[COMMISSION-CANDIDATE] %s %s", request.method, _safe_url(url))

    def _on_response(self, response: Response) -> None:
        url = response.url
        if MEESHO_API_PATTERN.search(url):
            asyncio.ensure_future(self._capture_body(response, url))

    async def _capture_body(self, response: Response, url: str) -> None:
        status = response.status
        safe = _safe_url(url)
        try:
            body = await response.json()
            is_commission = bool(COMMISSION_PATTERN.search(url))
            entry = {
                "url": safe,
                "status": status,
                "is_commission_candidate": is_commission,
                "body_keys": list(body.keys()) if isinstance(body, dict) else f"[list len={len(body)}]",
                "body_preview": json.dumps(body, ensure_ascii=False)[:800],
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            self.captured_responses.append(entry)
            if is_commission:
                log.info("[COMMISSION-RESPONSE] %s — status=%d keys=%s", safe, status, entry["body_keys"])
                log.info("  BODY PREVIEW: %s", entry["body_preview"][:400])
            else:
                log.info("[API-RESPONSE] %s — status=%d keys=%s", safe, status, entry["body_keys"])
        except Exception:
            # Not JSON or already consumed — log URL + status only
            log.info("[API-RESPONSE-NOJSON] %s — status=%d", safe, status)


async def discover_with_interaction(
    ctx: BrowserContext,
    interceptor: BroadInterceptor,
) -> None:
    """Navigate referral-fee + pricing pages with extended interaction.

    - 15s dwell (vs 5s before) to allow lazy XHR components to mount.
    - Scroll to bottom to trigger lazy loading.
    - Wait for networkidle (best-effort).
    - Capture full body text as evidence regardless of outcome.
    """
    log.info("=== STEP 2: Discovery with extended interaction ===")

    for nav_url in DISCOVERY_PAGES:
        page = await ctx.new_page()
        try:
            log.info("Navigating to: %s", nav_url)
            try:
                await page.goto(
                    nav_url,
                    wait_until="domcontentloaded",
                    timeout=PAGE_NAV_TIMEOUT_MS,
                )
            except PlaywrightTimeoutError:
                log.warning("Navigation timeout for %s — continuing with partial load", nav_url)

            await detect_block(page)
            log.info("Page loaded: %s", _safe_url(page.url))

            # Extended dwell: 15 seconds (vs 5 before) for lazy components
            log.info("Dwelling 15s for lazy XHR components to mount...")
            await asyncio.sleep(5)

            # Scroll to bottom to trigger lazy loading
            try:
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                log.info("Scrolled to bottom")
            except Exception as exc:
                log.debug("Scroll failed (non-fatal): %s", exc)

            await asyncio.sleep(5)

            # Scroll back up (some SPAs fire XHR on scroll events)
            try:
                await page.evaluate("window.scrollTo(0, 0)")
            except Exception:
                pass

            await asyncio.sleep(5)

            # Wait for networkidle
            try:
                await page.wait_for_load_state("networkidle", timeout=12_000)
                log.info("networkidle reached")
            except PlaywrightTimeoutError:
                log.info("networkidle timeout (normal for SPA — continuing)")

            # Capture page body text as evidence
            body_text = ""
            try:
                body_text = await page.locator("body").inner_text(timeout=5_000)
                body_text_lower = body_text.lower()
            except Exception:
                body_text = "<could not capture>"
                body_text_lower = ""

            log.info("Page body text (first 500 chars): %s", body_text[:500])

            # Check for commission table
            has_table = "commission" in body_text_lower or "referral fee" in body_text_lower or "rate" in body_text_lower
            has_signature_modal = "e-signature" in body_text_lower or "add signature" in body_text_lower or "signature is missing" in body_text_lower
            has_rate_table_html = False

            try:
                tables = await page.locator("table").count()
                rate_rows = await page.locator("tr").count()
                has_rate_table_html = tables > 0
                log.info("DOM tables found: %d, tr elements: %d", tables, rate_rows)
            except Exception:
                pass

            log.info(
                "Page analysis for %s: has_commission_text=%s, has_signature_modal=%s, has_html_table=%s",
                nav_url,
                has_table,
                has_signature_modal,
                has_rate_table_html,
            )

            if has_signature_modal:
                log.warning(
                    "E-SIGNATURE MODAL STILL PRESENT on %s — is_agreement_accepted may still be false",
                    nav_url,
                )

            # Take a screenshot regardless (evidence)
            screenshot_path = LOG_DIR / f"screenshot_{nav_url.split('/')[-1]}_{datetime.now().strftime('%H%M%S')}.png"
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
                log.info("Screenshot saved: %s", screenshot_path)
            except Exception as exc:
                log.warning("Screenshot failed: %s", exc)

        except HardStopError:
            await page.close()
            raise
        except Exception as exc:
            log.warning("Discovery page %s failed: %s", nav_url, exc)
        finally:
            try:
                await page.close()
            except Exception:
                pass

        # Between pages
        await jitter(NAV_JITTER_MIN_S, NAV_JITTER_MAX_S)

    log.info(
        "=== DISCOVERY COMPLETE: %d API requests logged, %d commission candidates, %d responses captured ===",
        len(interceptor.all_api_requests),
        len(interceptor.commission_candidates),
        len(interceptor.captured_responses),
    )
    log.info("All API request URLs observed:")
    for r in interceptor.all_api_requests:
        log.info("  %s %s", r["method"], r["url"])


# ---------------------------------------------------------------------------
# Commission body parser (same logic as primary scraper)
# ---------------------------------------------------------------------------

def parse_commission_body(body: Any, source_url: str) -> list[dict[str, Any]]:
    captured_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    rows: list[Any] = []
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict):
        for key in (
            "data", "categories", "items", "results", "rows",
            "referralFees", "commissions", "fees", "rateCard", "rate_card",
            "referral_fees", "commission_rates",
        ):
            if key in body and isinstance(body[key], list):
                rows = body[key]
                log.info("Unwrapped from top-level key %r (%d rows)", key, len(rows))
                break
        if not rows:
            for k, v in body.items():
                if isinstance(v, dict):
                    for ik in ("data", "items", "rows", "fees", "categories"):
                        if ik in v and isinstance(v[ik], list):
                            rows = v[ik]
                            log.info("Unwrapped from nested [%r][%r] (%d rows)", k, ik, len(rows))
                            break
                if rows:
                    break
        if not rows:
            log.warning("No row list found; storing raw body. Top-level keys: %s", list(body.keys()))
            results.append({
                "meesho_category": "_UNKNOWN_STRUCTURE_",
                "commission_pct": None,
                "source_url": source_url,
                "captured_at_note": captured_at,
                "raw_entry": body,
            })
            return results

    log.info("Parsing %d rows", len(rows))
    rate_keys = (
        "commission_rate", "referral_fee", "fee_percentage", "commission_percentage",
        "rate", "percentage", "value", "commissionRate", "referralFee",
        "feePercentage", "commissionPercentage", "commission", "fee",
    )
    cat_name_keys = (
        "category", "name", "category_name", "super_category", "super_name",
        "categoryName", "superCategory", "superName", "level", "group",
        "display_name", "displayName", "label",
    )

    for raw in rows:
        if not isinstance(raw, dict):
            continue
        cat = ""
        for k in cat_name_keys:
            if k in raw and raw[k]:
                cat = str(raw[k]).strip()
                break
        pct: float | None = None
        for k in rate_keys:
            if k in raw and raw[k] is not None:
                try:
                    pct = float(raw[k])
                    break
                except (ValueError, TypeError):
                    pass
        if not cat:
            cat = "_MISSING_CATEGORY_NAME_"
        results.append({
            "meesho_category": cat,
            "commission_pct": pct,
            "source_url": source_url,
            "captured_at_note": captured_at,
            "raw_entry": raw,
        })
    log.info("Parsed %d rate-card entries", len(results))
    return results


# ---------------------------------------------------------------------------
# Category tree loader
# ---------------------------------------------------------------------------

def load_category_tree() -> list[dict[str, Any]]:
    if not CATEGORY_TREE_FILE.exists():
        raise FileNotFoundError(f"Category tree not found: {CATEGORY_TREE_FILE}")
    data = json.loads(CATEGORY_TREE_FILE.read_text(encoding="utf-8"))
    leaves = [c for c in data.get("categories", []) if c.get("is_leaf")]
    log.info("Loaded %d leaf entries from category tree", len(leaves))
    return leaves


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------

def write_output(
    rate_card: list[dict[str, Any]],
    source_url: str,
    agreement_status: dict[str, Any],
    all_api_requests: list[dict[str, Any]],
    commission_candidates: list[dict[str, Any]],
    captured_responses: list[dict[str, Any]],
    status_note: str,
) -> None:
    captured_at = datetime.now(timezone.utc).isoformat()
    output: dict[str, Any] = {
        "_meta": {
            "artifact_version": "0.3.0-RERUN",
            "status": status_note,
            "capture_date": captured_at,
            "capture_agent": "meesell-scraper-maintainer (sonnet)",
            "capture_session": "commission-rerun v0.3.0 (post-esignature re-run)",
            "agreement_status_at_capture": agreement_status,
            "source_url": source_url,
            "rate_card_rows_captured": len(rate_card),
            "total_leaves_in_tree": 3772,
            "total_super_categories": 30,
            "all_api_requests_observed": all_api_requests,
            "commission_candidates_found": commission_candidates,
            "captured_responses": captured_responses,
            "note": (
                "Re-run after founder e-signature completion. "
                "is_agreement_accepted checked as Step 1. "
                "Broad intercept of ALL Meesho API calls logged."
            ),
        },
        "rate_card": rate_card,
        "proposed_leaf_mapping": [],
        "unmatched_super_categories": [],
        "ambiguity_notes": [],
    }

    COMMISSION_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMISSION_OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Output written: %s", COMMISSION_OUTPUT_FILE)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def run_rerun(pw: Playwright) -> dict[str, Any]:
    user, pwd = load_creds()
    leaves = load_category_tree()

    log.info("Launching WebKit (headless=True)")
    browser = await pw.webkit.launch(headless=True)
    ctx = await browser.new_context(
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        viewport={"width": 1440, "height": 900},
    )
    ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
    ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)

    result: dict[str, Any] = {
        "agreement_status": {},
        "is_agreement_accepted": None,
        "commission_endpoint": None,
        "rate_card_rows": 0,
        "status": "not_started",
        "aborted": False,
        "abort_reason": None,
    }

    try:
        # --- Login ---
        login_page = await ctx.new_page()
        try:
            await perform_login(login_page, user, pwd)
        finally:
            await login_page.close()

        # --- Step 1: Agreement check ---
        agreement = await check_agreement_status(ctx)
        result["agreement_status"] = agreement
        is_accepted = agreement.get("is_agreement_accepted")
        result["is_agreement_accepted"] = is_accepted

        log.info("=" * 60)
        log.info("AGREEMENT GATE CHECK: is_agreement_accepted = %r", is_accepted)
        log.info("=" * 60)

        if is_accepted is False or is_accepted == "false":
            # STOP: e-signature has NOT been registered
            msg = (
                f"STOP: is_agreement_accepted is still {is_accepted!r}. "
                f"The e-signature did NOT register. "
                f"default_monetization_percent={agreement.get('default_monetization_percent')!r}, "
                f"enable_referral_v3={agreement.get('enable_referral_v3')!r}. "
                f"Founder must complete the e-signature flow in the browser-based supplier panel."
            )
            log.error(msg)
            result["status"] = "STOPPED_AGREEMENT_STILL_FALSE"
            result["abort_reason"] = msg

            write_output(
                rate_card=[],
                source_url="not_reached",
                agreement_status=agreement,
                all_api_requests=[],
                commission_candidates=[],
                captured_responses=[],
                status_note="STOPPED: is_agreement_accepted=false — e-signature not registered",
            )
            return result

        if is_accepted is None:
            log.warning(
                "is_agreement_accepted field NOT FOUND in prefetch-supply-data response. "
                "Proceeding with discovery anyway — field may have moved in API schema."
            )
        else:
            log.info(
                "AGREEMENT CONFIRMED: is_agreement_accepted=%r — proceeding to commission discovery",
                is_accepted,
            )

        # --- Step 2: Discovery with broad intercept ---
        await jitter(NAV_JITTER_MIN_S, NAV_JITTER_MAX_S)

        async with BroadInterceptor(ctx) as interceptor:
            await discover_with_interaction(ctx, interceptor)

            all_api_reqs = interceptor.all_api_requests
            candidates = interceptor.commission_candidates
            responses = interceptor.captured_responses

        log.info(
            "Discovery complete: %d API requests, %d commission candidates, %d responses",
            len(all_api_reqs),
            len(candidates),
            len(responses),
        )

        # --- Step 3: Parse any captured commission responses ---
        rate_card: list[dict[str, Any]] = []
        commission_endpoint = None

        commission_responses = [r for r in responses if r.get("is_commission_candidate")]

        if commission_responses:
            log.info("=== COMMISSION RESPONSES FOUND: %d ===", len(commission_responses))
            for cr in commission_responses:
                log.info("  Commission response URL: %s", cr["url"])
                log.info("  Body keys: %s", cr["body_keys"])
                log.info("  Body preview: %s", cr["body_preview"][:400])
                try:
                    body = json.loads(cr["body_preview"])
                    entries = parse_commission_body(body, cr["url"])
                    if entries and entries[0].get("meesho_category") != "_UNKNOWN_STRUCTURE_":
                        rate_card = entries
                        commission_endpoint = cr["url"]
                        log.info(
                            "=== HARVEST SUCCESS: %d rate-card rows from %s ===",
                            len(entries),
                            cr["url"],
                        )
                        break
                except Exception as exc:
                    log.warning("Parse attempt failed for %s: %s", cr["url"], exc)
        else:
            log.warning(
                "No commission-pattern API responses captured. "
                "All %d non-commission API responses: see log above.",
                len(responses),
            )
            # Log all captured response URLs + keys for operator review
            for r in responses:
                log.info("  [ALL-RESPONSES] %s — keys=%s", r["url"], r["body_keys"])

        result["commission_endpoint"] = commission_endpoint
        result["rate_card_rows"] = len(rate_card)

        if rate_card:
            status_note = f"CAPTURED — {len(rate_card)} rate-card rows from {commission_endpoint}"
        elif is_accepted:
            status_note = (
                "DISCOVERY_COMPLETE_NO_COMMISSION_XHR — agreement accepted but no commission "
                "API XHR fired. See all_api_requests_observed in _meta for full list."
            )
        else:
            status_note = "STOPPED_AGREEMENT_UNKNOWN — is_agreement_accepted not found in API"

        result["status"] = status_note

        write_output(
            rate_card=rate_card,
            source_url=commission_endpoint or "not_discovered",
            agreement_status=agreement,
            all_api_requests=all_api_reqs,
            commission_candidates=candidates,
            captured_responses=responses,
            status_note=status_note,
        )

    except HardStopError as exc:
        log.error("HARD STOP: %s", exc)
        result["aborted"] = True
        result["abort_reason"] = str(exc)
        result["status"] = "HARD_STOP"
        raise
    finally:
        try:
            await ctx.close()
        except Exception:
            pass
        try:
            await browser.close()
        except Exception:
            pass

    return result


async def amain() -> int:
    configure_logging()
    log.info("==== Meesho Commission Re-Run starting at %s ====", datetime.now(timezone.utc).isoformat())
    log.info("Worktree: %s", WORKTREE_ROOT)
    log.info("Creds:    %s", CREDS_FILE)
    log.info("Output:   %s", COMMISSION_OUTPUT_FILE)

    try:
        async with async_playwright() as pw:
            result = await run_rerun(pw)
    except HardStopError as exc:
        log.error("Run aborted (hard stop): %s", exc)
        return 1
    except KeyboardInterrupt:
        log.warning("Interrupted")
        return 130
    except Exception as exc:
        log.exception("Unexpected failure: %s", exc)
        return 1

    print("\n========= COMMISSION RE-RUN SUMMARY =========")
    print(f"is_agreement_accepted : {result.get('is_agreement_accepted')!r}")
    print(f"commission_endpoint   : {result.get('commission_endpoint')!r}")
    print(f"rate_card_rows        : {result.get('rate_card_rows')}")
    print(f"status                : {result.get('status')}")
    if result.get("aborted"):
        print(f"ABORTED               : {result.get('abort_reason')}")
    print("==============================================")

    if result.get("status") == "STOPPED_AGREEMENT_STILL_FALSE":
        return 2  # Distinct exit code: agreement not accepted
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
