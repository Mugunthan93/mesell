"""Meesho Commission / Referral-Fee Rate-Card Scraper.

Purpose
-------
Capture Meesho's published category-wise commission (referral-fee) rate-card
from the authenticated supplier panel and write it to:

    backend/app/data/category_commissions.json   (worktree-scoped)

This is PHASE 2 of the commission seeding work (see CATEGORY_SEEDING_ARCHITECTURE.md
§9 Q2 / founder decision D2). Phase 1 (NULL seed) is complete. Phase 2 requires
REAL values captured from Meesho's authenticated supplier panel.

Why this pattern?
-----------------
All Meesho supplier pages are protected by Akamai Edge Security. Plain
httpx/curl receives HTTP 403 or 463. The ONLY proven bypass is to fire API
calls from an authenticated WebKit BrowserContext that has completed a real
browser-based login — the context carries a valid TLS session (JA3/JA4
fingerprint) + auth cookies. This is exactly the pattern proven in
``meesho_batch_scraper.py`` which drained all 3,772 XLSX templates using
``ctx.request.post(...)`` from the same browser context.

Endpoint discovery strategy
---------------------------
Meesho's exact commission/referral-fee API endpoint is NOT publicly documented.
This script discovers it at runtime via network interception:

    1. After login, navigate to candidate referral-fee panel pages.
    2. Intercept ALL outbound requests and filter URLs matching the pattern:
       /referral|commission|fee|charge|rate|pricing/i
    3. Log every matching candidate so the operator can identify the correct one.
    4. If COMMISSION_API_ENDPOINT is set (non-empty), skip discovery and use it
       directly via ctx.request.get() — this is the fast path for subsequent runs.

ENDPOINT_OVERRIDE module constant (see below):
    Set this once the operator has identified the correct endpoint from the
    logged candidate list. Leave as empty string for the first run (discovery
    mode).

DO NOT RUN without founder GO
------------------------------
This script performs a real login to the Meesho supplier panel using the
founder's credentials. It must NOT be executed without explicit founder
authorisation. The dispatch instructions for this session explicitly prohibit
live execution.

Hard stops (§6.4 of PLAYWRIGHT_MCP_REFERENCE)
----------------------------------------------
    - HTTP 401 / 403 / 463 from any Meesho API → abort + report
    - HTTP 429 → abort + report (rate limited)
    - Captcha page detected → abort + report (NEVER solve)
    - Login fails twice → abort + report

Credential handling (§6.5)
---------------------------
    Credentials are loaded from .meesho_creds.env. The path is:
        1. MEESHO_CREDS_FILE env override (for CI/alternate paths)
        2. ~/Project/mesell/.meesho_creds.env (founder's standard creds file)
    NEVER log credentials. NEVER write them to disk. NEVER commit them.

Output
------
    Worktree-scoped path:
        /private/tmp/mesell-wt/category-seeding/backend/app/data/category_commissions.json

    This file is REVIEWED by the data lead before any backfill runs.
    The backfill script (scripts/seed_category_commissions.py) is authored
    separately after founder/data-lead review.

Throttle policy
---------------
    Single sequential request stream. Jittered 2–5 s between page navigations.
    Max 1 request per 2 s. No parallelism. Single browser context.
    This aligns with meesho_batch_scraper.py's proven rate-limit posture.

Run command (do not execute without founder GO)
-----------------------------------------------
    cd /private/tmp/mesell-wt/category-seeding
    python backend/scripts/meesho_commission_scraper.py

    Optional overrides via env:
        MEESHO_CREDS_FILE=/path/to/custom.env \\
        COMMISSION_API_ENDPOINT=https://supplier.meesho.com/api/... \\
        python backend/scripts/meesho_commission_scraper.py
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
# Paths — ALL WORKTREE-SCOPED
# ---------------------------------------------------------------------------

WORKTREE_ROOT = Path("/private/tmp/mesell-wt/category-seeding")

# Creds: env override → founder's standard project path
_CREDS_FILE_OVERRIDE = os.environ.get("MEESHO_CREDS_FILE", "").strip()
CREDS_FILE = (
    Path(_CREDS_FILE_OVERRIDE)
    if _CREDS_FILE_OVERRIDE
    else Path.home() / "Project" / "mesell" / ".meesho_creds.env"
)

# Output: ALWAYS worktree-scoped
COMMISSION_OUTPUT_FILE = (
    WORKTREE_ROOT / "backend" / "app" / "data" / "category_commissions.json"
)
CATEGORY_TREE_FILE = (
    WORKTREE_ROOT / "backend" / "app" / "data" / "meesho_category_tree.json"
)

LOG_DIR = WORKTREE_ROOT / "logs" / "scraper"

# ---------------------------------------------------------------------------
# Meesho constants — inherited from meesho_batch_scraper.py
# ---------------------------------------------------------------------------

SUPPLIER_ID = 4359160
IDENTIFIER = "oinpw"

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"

# ---------------------------------------------------------------------------
# Commission endpoint discovery
# ---------------------------------------------------------------------------

# Operator: once you have identified the correct endpoint from the logged
# candidate list (run 1 discovery mode), set this constant and re-run.
# Leave as empty string for the first run — the script enters discovery mode.
COMMISSION_API_ENDPOINT: str = os.environ.get("COMMISSION_API_ENDPOINT", "").strip()

# Candidate panel navigation URLs to visit for endpoint discovery.
# The script navigates each in turn, intercepts all XHR/fetch requests, and
# logs any whose URL matches the commission pattern.
CANDIDATE_NAV_URLS: list[str] = [
    "https://supplier.meesho.com/panel/v3/new/root/referral-fee",
    "https://supplier.meesho.com/panel/v3/new/growth/{identifier}/referral-fee",
    "https://supplier.meesho.com/panel/v3/new/root/pricing",
    "https://supplier.meesho.com/panel/v3/new/growth/{identifier}/pricing",
    "https://supplier.meesho.com/panel/v3/new/root/commission",
    "https://supplier.meesho.com/panel/v3/new/growth/{identifier}/home",  # dashboard
]

# URL regex for commission/fee endpoint filtering
COMMISSION_URL_PATTERN = re.compile(
    r"/(?:referral|commission|fee|charge|rate|pricing)/",
    re.IGNORECASE,
)

# Also match API paths directly (XHR endpoints rather than page routes)
COMMISSION_API_URL_PATTERN = re.compile(
    r"(?:referral[_-]?fee|commission|referral|pricing|charge|rate)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------

LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000
PAGE_NAV_TIMEOUT_MS = 30_000
API_REQUEST_TIMEOUT_MS = 30_000
NETWORK_WAIT_TIMEOUT_MS = 15_000

# ---------------------------------------------------------------------------
# Throttle
# ---------------------------------------------------------------------------

NAV_JITTER_MIN_S = 2.0   # minimum between-page delay (seconds)
NAV_JITTER_MAX_S = 5.0   # maximum between-page delay (seconds)
REQ_JITTER_MIN_S = 1.0   # minimum between-request delay
REQ_JITTER_MAX_S = 3.0   # maximum between-request delay

# ---------------------------------------------------------------------------
# Hard-stop codes (identical to meesho_batch_scraper.py)
# ---------------------------------------------------------------------------

SESSION_STOP_CODES = {401, 403, 463}
RATE_LIMIT_STOP_CODES = {429}

# Captcha detection markers (page body text)
CAPTCHA_MARKERS = (
    "captcha",
    "are you a human",
    "verify you are human",
    "i am not a robot",
    "recaptcha",
)

BLOCK_MARKERS = (
    "access denied",
    "too many requests",
    "rate limit",
    "forbidden",
) + CAPTCHA_MARKERS

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging() -> logging.Logger:
    """Configure rotating file + stdout logging. No credentials ever logged."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"commission_{timestamp}.log"

    logger = logging.getLogger("meesho-commission")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    logger.propagate = False
    logger.info("Commission scraper log: %s", log_path)
    return logger


log = logging.getLogger("meesho-commission")


def _safe_url(url: str) -> str:
    """Return URL with query string stripped — avoids leaking signed tokens."""
    try:
        p = urlparse(url)
        return f"{p.scheme}://{p.netloc}{p.path}"
    except Exception:  # noqa: BLE001
        return "<url-parse-error>"


# ---------------------------------------------------------------------------
# Credential loading
# ---------------------------------------------------------------------------


def load_creds() -> tuple[str, str]:
    """Load MEESHO_USERNAME / MEESHO_PASSWORD from the creds file.

    NEVER logs credential values. Raises clearly on missing file or missing keys.
    """
    if not CREDS_FILE.exists():
        raise FileNotFoundError(
            f"Credentials file not found: {CREDS_FILE}\n"
            "Create it with:\n"
            "  MEESHO_USERNAME=<phone-or-email>\n"
            "  MEESHO_PASSWORD=<password>\n"
            "Or set MEESHO_CREDS_FILE env var to point at an alternate path."
        )
    load_dotenv(CREDS_FILE)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError(
            "MEESHO_USERNAME and/or MEESHO_PASSWORD missing in creds file. "
            f"File path: {CREDS_FILE}"
        )
    # Deliberate: do NOT log user or pwd
    log.info("Credentials loaded from: %s", CREDS_FILE)
    return user, pwd


# ---------------------------------------------------------------------------
# Category tree loader (for mapping step)
# ---------------------------------------------------------------------------


def load_category_tree() -> list[dict[str, Any]]:
    """Load all leaf entries from meesho_category_tree.json (worktree copy)."""
    if not CATEGORY_TREE_FILE.exists():
        raise FileNotFoundError(f"Category tree not found: {CATEGORY_TREE_FILE}")
    data = json.loads(CATEGORY_TREE_FILE.read_text(encoding="utf-8"))
    leaves = [c for c in data.get("categories", []) if c.get("is_leaf")]
    log.info("Loaded %d leaf entries from category tree", len(leaves))
    return leaves


# ---------------------------------------------------------------------------
# Block / captcha detection
# ---------------------------------------------------------------------------


async def detect_block(page: Page) -> None:
    """Raise hard stop if a captcha or block page is detected.

    Checks URL tokens and body text. Called after each navigation.
    """
    url = page.url
    for token in ("captcha", "/error", "/blocked", "access-denied"):
        if token in url:
            raise HardStopError(f"Block URL detected: {_safe_url(url)}")

    body_text = ""
    try:
        body_text = (
            await page.locator("body").inner_text(timeout=3_000) or ""
        ).lower()
    except Exception:  # noqa: BLE001
        return

    for marker in CAPTCHA_MARKERS:
        if marker in body_text:
            raise HardStopError(
                f"CAPTCHA detected (marker={marker!r}). "
                "NEVER attempt to solve CAPTCHAs. Abort and report to data-engineer."
            )
    for marker in BLOCK_MARKERS:
        if marker in body_text:
            raise HardStopError(f"Block marker detected in page body: {marker!r}")


# ---------------------------------------------------------------------------
# Hard stop
# ---------------------------------------------------------------------------


class HardStopError(RuntimeError):
    """Raised on any condition that requires immediate abort.

    Hard stops (per PLAYWRIGHT_MCP_REFERENCE §6.4):
        - HTTP 401/403/463 (Akamai or auth block)
        - HTTP 429 (rate limited)
        - Captcha page
        - Login failure
    Do NOT catch this exception to continue — surface to operator.
    """


def _check_status(status: int, context_label: str) -> None:
    """Raise HardStopError for session-stop or rate-limit HTTP status codes."""
    if status in SESSION_STOP_CODES:
        raise HardStopError(
            f"HTTP {status} from {context_label} — Akamai or auth block. "
            "Stop run, investigate, do not retry automatically."
        )
    if status in RATE_LIMIT_STOP_CODES:
        raise HardStopError(
            f"HTTP {status} from {context_label} — rate limited. "
            "Stop run immediately. Wait before retrying."
        )


# ---------------------------------------------------------------------------
# Throttle helper
# ---------------------------------------------------------------------------


async def jitter(min_s: float = NAV_JITTER_MIN_S, max_s: float = NAV_JITTER_MAX_S) -> None:
    """Async sleep with randomized jitter to stay well under 1 req/2s."""
    delay = random.uniform(min_s, max_s)
    log.debug("Throttle: sleeping %.2fs", delay)
    await asyncio.sleep(delay)


# ---------------------------------------------------------------------------
# Login (ported from meesho_batch_scraper.py perform_login)
# ---------------------------------------------------------------------------


async def perform_login(page: Page, username: str, password: str) -> None:
    """Log in to supplier.meesho.com via WebKit.

    After this returns, the parent BrowserContext carries auth cookies
    (including HttpOnly ones). Subsequent ctx.request.get/post() calls
    automatically inherit them — this is what bypasses Akamai.

    On failure: raises HardStopError.
    Credentials are NOT logged at any point.
    """
    log.info("Navigating to login URL: %s", LOGIN_URL)
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await jitter(1.5, 2.5)
    await detect_block(page)

    # --- Username field ---
    user_field = None
    user_candidates = [
        lambda: page.get_by_placeholder(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_label(re.compile(r"email.*mobile", re.I)),
        lambda: page.get_by_role("textbox", name=re.compile(r"email|mobile", re.I)),
        lambda: page.locator("input[type='text']").first,
    ]
    for build in user_candidates:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=5_000)
            user_field = loc
            break
        except Exception:  # noqa: BLE001
            continue
    if user_field is None:
        raise HardStopError("Could not locate username field on login page — page may have changed")

    await user_field.fill(username)
    await jitter(0.8, 1.5)

    # --- Password field ---
    pwd_field = None
    pwd_candidates = [
        lambda: page.get_by_placeholder(re.compile(r"password", re.I)),
        lambda: page.get_by_label(re.compile(r"password", re.I)),
        lambda: page.locator("input[type='password']").first,
    ]
    for build in pwd_candidates:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=5_000)
            pwd_field = loc
            break
        except Exception:  # noqa: BLE001
            continue
    if pwd_field is None:
        raise HardStopError("Could not locate password field on login page — page may have changed")

    await pwd_field.fill(password)
    await jitter(0.8, 1.5)

    # --- Submit ---
    submit = None
    submit_candidates = [
        lambda: page.get_by_role("button", name=re.compile(r"log\s*in|sign\s*in", re.I)),
        lambda: page.locator("button[type='submit']").first,
    ]
    for build in submit_candidates:
        try:
            loc = build()
            await loc.wait_for(state="visible", timeout=5_000)
            submit = loc
            break
        except Exception:  # noqa: BLE001
            continue
    if submit is None:
        raise HardStopError("Could not locate login submit button — page may have changed")

    log.info("Submitting login form (credentials not logged)")
    await submit.click()

    try:
        await page.wait_for_url(
            lambda u: "login" not in u, timeout=LOGIN_NAV_TIMEOUT_MS
        )
    except PlaywrightTimeoutError:
        body_snippet = ""
        try:
            body_snippet = (await page.locator("body").inner_text(timeout=2_000))[:300]
        except Exception:  # noqa: BLE001
            pass
        raise HardStopError(
            f"Login did not redirect away from /login. "
            f"URL={_safe_url(page.url)!r} body-snippet={body_snippet!r}"
        )

    await page.wait_for_load_state("domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await detect_block(page)
    log.info("Login OK — current URL: %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Network interception — candidate request collector
# ---------------------------------------------------------------------------


class NetworkInterceptor:
    """Collects XHR/fetch requests matching the commission URL pattern.

    Usage:
        async with NetworkInterceptor(ctx) as interceptor:
            # ... navigate pages ...
            candidates = interceptor.candidates
    """

    def __init__(self, ctx: BrowserContext) -> None:
        self._ctx = ctx
        self.candidates: list[dict[str, Any]] = []
        self.responses: list[dict[str, Any]] = []  # captured JSON response bodies

    async def __aenter__(self) -> "NetworkInterceptor":
        self._ctx.on("request", self._on_request)
        self._ctx.on("response", self._on_response)
        return self

    async def __aexit__(self, *_: Any) -> None:
        self._ctx.remove_listener("request", self._on_request)
        self._ctx.remove_listener("response", self._on_response)

    def _on_request(self, request: Request) -> None:
        url = request.url
        if COMMISSION_API_URL_PATTERN.search(url):
            entry = {
                "url": _safe_url(url),
                "method": request.method,
                "resource_type": request.resource_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.candidates.append(entry)
            log.info(
                "[CANDIDATE] %s %s (type=%s)",
                request.method,
                _safe_url(url),
                request.resource_type,
            )

    def _on_response(self, response: Response) -> None:
        url = response.url
        if COMMISSION_API_URL_PATTERN.search(url) and response.status == 200:
            # Schedule async body capture — cannot await in sync callback
            asyncio.ensure_future(self._capture_response_body(response, url))

    async def _capture_response_body(self, response: Response, url: str) -> None:
        """Attempt to capture JSON body of a matched response."""
        try:
            body = await response.json()
            entry = {
                "url": _safe_url(url),
                "status": response.status,
                "body_keys": list(body.keys()) if isinstance(body, dict) else f"[list len={len(body)}]",
                "body_preview": json.dumps(body)[:500],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self.responses.append(entry)
            log.info(
                "[RESPONSE CAPTURED] %s — keys=%s",
                _safe_url(url),
                entry["body_keys"],
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("[RESPONSE] Could not parse JSON from %s: %s", _safe_url(url), exc)


# ---------------------------------------------------------------------------
# Commission API fetch (direct mode — endpoint known)
# ---------------------------------------------------------------------------


async def fetch_commission_direct(
    ctx: BrowserContext,
    endpoint: str,
) -> dict[str, Any]:
    """Fetch the commission JSON from a known endpoint via the browser context.

    The context carries the authenticated session (cookies + TLS fingerprint),
    so Akamai sees a real browser request.

    Returns the parsed JSON body. Raises HardStopError on bad status codes.
    """
    headers = {
        "identifier": IDENTIFIER,
        "client-type": "d-web",
        "client-package-version": "1.0.1",
        "supplier-id": str(SUPPLIER_ID),
        "accept": "application/json, text/plain, */*",
    }
    log.info("Fetching commission data from endpoint: %s", _safe_url(endpoint))
    resp = await ctx.request.get(
        endpoint,
        headers=headers,
        timeout=API_REQUEST_TIMEOUT_MS,
    )
    _check_status(resp.status, endpoint)
    if resp.status >= 400:
        body_preview = ""
        try:
            body_preview = (await resp.text())[:300]
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError(
            f"Commission API returned HTTP {resp.status} from {_safe_url(endpoint)}: "
            f"{body_preview!r}"
        )
    body = await resp.json()
    log.info(
        "Commission API response received — top-level keys: %s",
        list(body.keys()) if isinstance(body, dict) else f"[list, len={len(body)}]",
    )
    return body


# ---------------------------------------------------------------------------
# Discovery mode — navigate candidate URLs and intercept requests
# ---------------------------------------------------------------------------


async def discover_commission_endpoint(
    ctx: BrowserContext,
    interceptor: NetworkInterceptor,
) -> None:
    """Navigate all candidate URLs with the interceptor active.

    Every matching XHR/fetch URL is logged. The operator reads the log to
    identify the correct commission endpoint, then sets COMMISSION_API_ENDPOINT.
    """
    log.info("=== DISCOVERY MODE: visiting %d candidate URLs ===", len(CANDIDATE_NAV_URLS))
    page = await ctx.new_page()
    try:
        for raw_url in CANDIDATE_NAV_URLS:
            # Interpolate identifier into parameterised URLs
            url = raw_url.replace("{identifier}", IDENTIFIER)
            log.info("Navigating to candidate page: %s", url)
            try:
                await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=PAGE_NAV_TIMEOUT_MS,
                )
                await detect_block(page)
                # Dwell to allow XHR calls to fire
                await jitter(NAV_JITTER_MIN_S, NAV_JITTER_MAX_S)
                # Also wait for network to settle
                try:
                    await page.wait_for_load_state("networkidle", timeout=10_000)
                except PlaywrightTimeoutError:
                    pass  # networkidle is best-effort; candidates may still fire XHR later
            except HardStopError:
                raise
            except Exception as exc:  # noqa: BLE001
                log.warning("Navigation to %s failed (non-fatal): %s", url, exc)
            await jitter(NAV_JITTER_MIN_S, NAV_JITTER_MAX_S)
    finally:
        await page.close()

    log.info(
        "=== DISCOVERY COMPLETE: %d candidate requests found, %d JSON responses captured ===",
        len(interceptor.candidates),
        len(interceptor.responses),
    )
    for i, entry in enumerate(interceptor.candidates, start=1):
        log.info(
            "  CANDIDATE %d: %s %s (type=%s)",
            i,
            entry["method"],
            entry["url"],
            entry["resource_type"],
        )
    for i, entry in enumerate(interceptor.responses, start=1):
        log.info(
            "  RESPONSE %d: %s — keys=%s — preview=%s",
            i,
            entry["url"],
            entry["body_keys"],
            entry["body_preview"][:200],
        )


# ---------------------------------------------------------------------------
# Commission JSON parser
# ---------------------------------------------------------------------------


def parse_commission_body(
    body: dict[str, Any] | list[Any],
    source_url: str,
) -> list[dict[str, Any]]:
    """Parse the commission API response into a normalised rate-card list.

    Returns a list of entries with shape:
        {
            "meesho_category": str,
            "commission_pct": float | null,
            "source_url": str,
            "captured_at_note": str,
            "raw_entry": <original entry for audit>
        }

    Because the exact API shape is unknown until first capture, this function
    implements a best-effort multi-key strategy:
        - Tries common top-level keys: data, categories, items, results, rows
        - Within each entry tries commission_rate, referral_fee, fee_percentage,
          commission_percentage, rate, percentage, value
        - Tries common category-name keys: category, name, category_name,
          super_category, level, group

    Any unrecognised structure is returned as-is in raw_entry for the operator
    to map manually.
    """
    captured_at = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []

    # Normalise: unwrap common envelope keys
    rows: list[Any] = []
    if isinstance(body, list):
        rows = body
    elif isinstance(body, dict):
        for key in ("data", "categories", "items", "results", "rows", "referralFees",
                    "commissions", "fees", "rateCard", "rate_card"):
            if key in body and isinstance(body[key], list):
                rows = body[key]
                log.info("Unwrapped commission data from top-level key: %r (%d rows)", key, len(rows))
                break
        if not rows:
            # Try one more level of nesting
            for key, val in body.items():
                if isinstance(val, dict):
                    for inner_key in ("data", "items", "rows", "fees"):
                        if inner_key in val and isinstance(val[inner_key], list):
                            rows = val[inner_key]
                            log.info(
                                "Unwrapped commission data from nested key [%r][%r] (%d rows)",
                                key, inner_key, len(rows),
                            )
                            break
                if rows:
                    break
        if not rows:
            # Body itself might be the map — treat as a single structured entry
            log.warning(
                "Could not find a list of rows in commission response. "
                "Storing raw body for manual review. Top-level keys: %s",
                list(body.keys()),
            )
            results.append({
                "meesho_category": "_UNKNOWN_STRUCTURE_",
                "commission_pct": None,
                "source_url": source_url,
                "captured_at_note": captured_at,
                "raw_entry": body,
            })
            return results
    else:
        log.warning("Unexpected commission body type: %s", type(body).__name__)
        return results

    log.info("Parsing %d rows from commission response", len(rows))

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

    for raw_entry in rows:
        if not isinstance(raw_entry, dict):
            log.debug("Skipping non-dict row: %r", raw_entry)
            continue

        category_name: str = ""
        for k in cat_name_keys:
            if k in raw_entry and raw_entry[k]:
                category_name = str(raw_entry[k]).strip()
                break

        commission_pct: float | None = None
        for k in rate_keys:
            if k in raw_entry and raw_entry[k] is not None:
                try:
                    commission_pct = float(raw_entry[k])
                    break
                except (ValueError, TypeError):
                    pass

        if not category_name:
            log.warning("Row has no recognisable category name key. Raw: %r", raw_entry)
            category_name = "_MISSING_CATEGORY_NAME_"

        results.append({
            "meesho_category": category_name,
            "commission_pct": commission_pct,
            "source_url": source_url,
            "captured_at_note": captured_at,
            "raw_entry": raw_entry,
        })

    log.info("Parsed %d rate-card entries", len(results))
    return results


# ---------------------------------------------------------------------------
# Category tree mapping
# ---------------------------------------------------------------------------


def propose_leaf_mapping(
    rate_card: list[dict[str, Any]],
    leaves: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """Propose a best-effort mapping from rate-card entries to tree super-categories.

    Matching strategy (case-insensitive):
        1. Exact match on rate-card category name vs leaf path[0] (super-category name)
        2. Contains match (rate-card name contained in super-category name or vice versa)
        3. No match → unmatched list

    Returns:
        (mapping_list, unmatched_super_ids)

    The mapping list entries have shape:
        {
            "rate_card_category": str,
            "commission_pct": float | null,
            "matched_super_ids": [str, ...],
            "matched_super_names": [str, ...],
            "leaf_count_covered": int,
            "match_confidence": "exact" | "partial" | "none",
            "ambiguity_flag": bool,
            "ambiguity_note": str | null,
        }

    IMPORTANT: This is a PROPOSED mapping. The data lead and founder MUST
    review before any backfill runs. The 5 overlapping super-category clusters
    (Personal Care, Home, Kids, Automotive, Office/Craft) require explicit
    founder disambiguation (documented in CATEGORY_SEEDING_COMMISSION_CAPTURE.md §5.3).
    """
    # Build super-category index from tree
    super_cat_index: dict[str, dict[str, Any]] = {}  # super_id → {name, leaf_count}
    for leaf in leaves:
        super_id = leaf.get("super_id", "?")
        super_name = leaf.get("path", ["?"])[0] if leaf.get("path") else "?"
        if super_id not in super_cat_index:
            super_cat_index[super_id] = {"name": super_name, "leaf_count": 0}
        super_cat_index[super_id]["leaf_count"] += 1

    # Track which super_ids are claimed by at least one rate-card entry
    claimed_super_ids: set[str] = set()

    mapping: list[dict[str, Any]] = []
    for entry in rate_card:
        rc_cat = entry["meesho_category"].lower()
        commission_pct = entry["commission_pct"]

        matched_super_ids: list[str] = []
        matched_super_names: list[str] = []
        confidence = "none"

        for super_id, info in super_cat_index.items():
            tree_name = info["name"].lower()
            if rc_cat == tree_name:
                matched_super_ids.append(super_id)
                matched_super_names.append(info["name"])
                confidence = "exact"
            elif rc_cat in tree_name or tree_name in rc_cat:
                matched_super_ids.append(super_id)
                matched_super_names.append(info["name"])
                if confidence != "exact":
                    confidence = "partial"

        leaf_count = sum(
            super_cat_index[sid]["leaf_count"]
            for sid in matched_super_ids
            if sid in super_cat_index
        )
        ambiguity = len(matched_super_ids) > 1
        claimed_super_ids.update(matched_super_ids)

        mapping.append({
            "rate_card_category": entry["meesho_category"],
            "commission_pct": commission_pct,
            "source_url": entry["source_url"],
            "captured_at_note": entry["captured_at_note"],
            "matched_super_ids": matched_super_ids,
            "matched_super_names": matched_super_names,
            "leaf_count_covered": leaf_count,
            "match_confidence": confidence,
            "ambiguity_flag": ambiguity,
            "ambiguity_note": (
                f"Multiple super-categories match this rate-card entry: "
                f"{matched_super_names}. Founder must confirm which apply."
                if ambiguity else None
            ),
        })

    # Unmatched super_ids
    unmatched = [
        f"super_id={sid} ({info['name']}, {info['leaf_count']} leaves)"
        for sid, info in super_cat_index.items()
        if sid not in claimed_super_ids
    ]

    log.info(
        "Mapping summary: %d rate-card entries → %d super-cats matched, %d unmatched",
        len(rate_card),
        len(claimed_super_ids),
        len(unmatched),
    )
    if unmatched:
        log.warning("Unmatched super-categories (need manual mapping or disambiguation):")
        for u in unmatched:
            log.warning("  UNMATCHED: %s", u)

    return mapping, unmatched


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------


def write_commission_json(
    rate_card: list[dict[str, Any]],
    mapping: list[dict[str, Any]],
    unmatched: list[str],
    source_url: str,
    discovery_candidates: list[dict[str, Any]],
    discovery_responses: list[dict[str, Any]],
) -> None:
    """Write the structured commission JSON to the worktree output path.

    Overwrites the existing placeholder. The resulting file is the input
    for data-lead review before scripts/seed_category_commissions.py is authored.
    """
    captured_at = datetime.now(timezone.utc).isoformat()
    output = {
        "_meta": {
            "artifact_version": "0.2.0-CAPTURED",
            "status": "CAPTURED — awaiting data-lead + founder review before backfill",
            "capture_date": captured_at,
            "capture_agent": "meesell-scraper-maintainer (sonnet)",
            "capture_session": "commission-scraper v0.2.0",
            "authorising_architecture": (
                "docs/plans/architecture/CATEGORY_SEEDING_ARCHITECTURE.md §9 Q2 (D2 Phase 2)"
            ),
            "target_output_column": "categories.commission_pct (NUMERIC(5,2) nullable)",
            "intended_use": (
                "Input to scripts/seed_category_commissions.py for idempotent backfill "
                "of categories.commission_pct after founder accuracy review"
            ),
            "source_url": source_url,
            "capture_method": (
                "Authenticated WebKit BrowserContext (Playwright) — "
                "ctx.request.get() riding browser TLS fingerprint + auth cookies "
                "(proven Akamai bypass, identical to meesho_batch_scraper.py pattern)"
            ),
            "coverage_pct": (
                round(100.0 * len(rate_card) / 50, 1) if rate_card else 0
            ),
            "rate_card_rows_captured": len(rate_card),
            "leaf_rows_mappable": sum(
                m["leaf_count_covered"] for m in mapping if m["match_confidence"] != "none"
            ),
            "total_leaves_in_tree": 3772,
            "total_super_categories": 30,
            "total_categories": 234,
            "granularity_note": (
                "Meesho publishes commission at super-category or category (Level 1/Level 2) "
                "granularity — NOT at leaf level. Exact granularity confirmed from captured data."
            ),
            "parser_version": "meesell-scraper-maintainer v0.2.0",
            "disambiguation_required": (
                "5 overlapping super-category clusters need founder confirmation: "
                "(1) Personal Care [super_ids 14,37,88,39,19,36], "
                "(2) Home [12,24,30], "
                "(3) Kids [13,25], "
                "(4) Automotive [18,73], "
                "(5) Office/Craft [66,76]. "
                "See CATEGORY_SEEDING_COMMISSION_CAPTURE.md §5.3."
            ),
            "next_action_required": (
                "Data-lead reviews rate_card + proposed_leaf_mapping. "
                "Founder confirms disambiguation_required clusters. "
                "Then: author scripts/seed_category_commissions.py for idempotent backfill."
            ),
            "backfill_script_when_ready": "scripts/seed_category_commissions.py (not yet authored)",
            "discovery_candidates_log": discovery_candidates,
            "discovery_responses_log": discovery_responses,
        },
        "rate_card": rate_card,
        "proposed_leaf_mapping": mapping,
        "unmatched_super_categories": unmatched,
        "ambiguity_notes": [
            m for m in mapping if m.get("ambiguity_flag")
        ],
    }

    COMMISSION_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    COMMISSION_OUTPUT_FILE.write_text(
        json.dumps(output, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("Commission JSON written to: %s", COMMISSION_OUTPUT_FILE)
    log.info(
        "Summary: %d rate-card rows, %d mapping entries, %d unmatched super-categories",
        len(rate_card),
        len(mapping),
        len(unmatched),
    )


# ---------------------------------------------------------------------------
# Main scrape flow
# ---------------------------------------------------------------------------


async def run_commission_scrape(pw: Playwright) -> dict[str, Any]:
    """Main orchestration: login → intercept OR direct fetch → parse → write.

    Returns a summary dict for the operator.
    """
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

    summary: dict[str, Any] = {
        "mode": "direct" if COMMISSION_API_ENDPOINT else "discovery",
        "endpoint_used": COMMISSION_API_ENDPOINT or None,
        "rate_card_rows": 0,
        "mapping_entries": 0,
        "unmatched_count": 0,
        "output_path": str(COMMISSION_OUTPUT_FILE),
        "discovery_candidates": [],
        "discovery_responses": [],
        "aborted": False,
        "abort_reason": None,
    }

    try:
        # Step 1: Login
        login_page = await ctx.new_page()
        try:
            await perform_login(login_page, user, pwd)
        except HardStopError:
            raise
        finally:
            await login_page.close()

        # Step 2: Fetch commission data
        rate_card_entries: list[dict[str, Any]] = []
        source_url: str = COMMISSION_API_ENDPOINT or "discovery-intercepted"
        discovery_candidates: list[dict[str, Any]] = []
        discovery_responses: list[dict[str, Any]] = []

        if COMMISSION_API_ENDPOINT:
            # --- DIRECT MODE: endpoint already known ---
            log.info("Direct mode: using endpoint %s", _safe_url(COMMISSION_API_ENDPOINT))
            await jitter(REQ_JITTER_MIN_S, REQ_JITTER_MAX_S)
            body = await fetch_commission_direct(ctx, COMMISSION_API_ENDPOINT)
            rate_card_entries = parse_commission_body(body, COMMISSION_API_ENDPOINT)

        else:
            # --- DISCOVERY MODE: intercept all requests ---
            log.info(
                "Discovery mode: no endpoint set. "
                "Will navigate candidate pages and log intercepted requests. "
                "After this run, check the log for CANDIDATE lines, identify the "
                "correct commission endpoint, set COMMISSION_API_ENDPOINT, and re-run."
            )
            async with NetworkInterceptor(ctx) as interceptor:
                await discover_commission_endpoint(ctx, interceptor)
                discovery_candidates = interceptor.candidates
                discovery_responses = interceptor.responses

            summary["discovery_candidates"] = discovery_candidates
            summary["discovery_responses"] = discovery_responses

            if discovery_responses:
                # Best-effort: try to parse the first captured JSON response
                log.info(
                    "Discovery mode: attempting best-effort parse of %d captured responses",
                    len(discovery_responses),
                )
                for resp_entry in discovery_responses:
                    try:
                        raw_body = json.loads(resp_entry["body_preview"])
                        candidate_entries = parse_commission_body(
                            raw_body, resp_entry["url"]
                        )
                        if candidate_entries:
                            rate_card_entries = candidate_entries
                            source_url = resp_entry["url"]
                            log.info(
                                "Best-effort parse succeeded from %s: %d entries",
                                resp_entry["url"],
                                len(candidate_entries),
                            )
                            break
                    except Exception as exc:  # noqa: BLE001
                        log.debug("Best-effort parse failed for %s: %s", resp_entry["url"], exc)

            if not rate_card_entries:
                log.warning(
                    "Discovery mode: no commission data parsed from intercepted responses. "
                    "Review the log for CANDIDATE lines and set COMMISSION_API_ENDPOINT "
                    "for the next run."
                )

        # Step 3: Propose mapping
        mapping: list[dict[str, Any]] = []
        unmatched: list[str] = []
        if rate_card_entries:
            mapping, unmatched = propose_leaf_mapping(rate_card_entries, leaves)

        # Step 4: Write output
        write_commission_json(
            rate_card=rate_card_entries,
            mapping=mapping,
            unmatched=unmatched,
            source_url=source_url,
            discovery_candidates=discovery_candidates,
            discovery_responses=discovery_responses,
        )

        summary.update({
            "rate_card_rows": len(rate_card_entries),
            "mapping_entries": len(mapping),
            "unmatched_count": len(unmatched),
            "endpoint_used": source_url,
        })

    except HardStopError as exc:
        log.error("HARD STOP: %s", exc)
        summary["aborted"] = True
        summary["abort_reason"] = str(exc)
        raise
    finally:
        try:
            await ctx.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await browser.close()
        except Exception:  # noqa: BLE001
            pass

    return summary


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


async def amain() -> int:
    configure_logging()
    log.info(
        "==== Meesho Commission Rate-Card Scraper starting at %s ====",
        datetime.now(timezone.utc).isoformat(),
    )
    log.info("Worktree root: %s", WORKTREE_ROOT)
    log.info("Creds file:    %s", CREDS_FILE)
    log.info("Output path:   %s", COMMISSION_OUTPUT_FILE)
    log.info("Mode:          %s", "direct" if COMMISSION_API_ENDPOINT else "discovery")
    if COMMISSION_API_ENDPOINT:
        log.info("Endpoint:      %s", _safe_url(COMMISSION_API_ENDPOINT))

    started = datetime.now(timezone.utc)

    try:
        async with async_playwright() as pw:
            summary = await run_commission_scrape(pw)
    except HardStopError as exc:
        log.error("Run aborted (hard stop): %s", exc)
        return 1
    except KeyboardInterrupt:
        log.warning("Interrupted by operator")
        return 130
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected failure: %s", exc)
        return 1

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    print("\n========= COMMISSION SCRAPER SUMMARY =========")
    print(f"mode              : {summary['mode']}")
    print(f"endpoint_used     : {summary['endpoint_used']}")
    print(f"rate_card_rows    : {summary['rate_card_rows']}")
    print(f"mapping_entries   : {summary['mapping_entries']}")
    print(f"unmatched_supcats : {summary['unmatched_count']}")
    print(f"output_path       : {summary['output_path']}")
    print(f"elapsed_s         : {elapsed:.1f}")
    if summary.get("aborted"):
        print(f"ABORTED           : {summary['abort_reason']}")
    if summary.get("discovery_candidates"):
        print(f"\nDiscovery candidates ({len(summary['discovery_candidates'])} requests):")
        for c in summary["discovery_candidates"]:
            print(f"  {c['method']} {c['url']}")
    if summary.get("discovery_responses"):
        print(f"\nCaptured JSON responses ({len(summary['discovery_responses'])}):")
        for r in summary["discovery_responses"]:
            print(f"  {r['url']} — keys={r['body_keys']}")
    print("==============================================")
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
