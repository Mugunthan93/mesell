"""Meesho Bulk Catalog Upload — HYBRID Playwright + httpx batch scraper.

Why hybrid?
-----------
The previous httpx-only implementation hit ``HTTP 463`` (Akamai bot-detect)
immediately. Meesho's supplier panel is fronted by Akamai which validates the
full client fingerprint — TLS handshake (JA3), HTTP/2 SETTINGS frame, header
order, and cookies. Plain ``httpx`` calls cannot fake that.

The Google Cloud Storage bucket holding the XLSX templates is **not** behind
Akamai. So the new pipeline is:

    1. Launch WebKit, log in once, keep the session/context alive.
    2. For each leaf:
       a. ``ctx.request.post(...)`` — Playwright sends the API call from the
          real browser, inheriting cookies + fingerprint. Akamai sees a real
          browser and allows it.
       b. The API responds with a 180-second pre-signed GCS URL.
       c. ``httpx.AsyncClient.get(template_url)`` downloads the XLSX bytes —
          GCS has no Akamai protection.
    3. Run scrape_one tasks in parallel under a semaphore. They all share the
       SAME browser context (cookies + fingerprint), but Playwright's
       ``APIRequestContext`` is async-safe for concurrent requests.

This avoids both the brittle UI navigation of the original WebKit scraper AND
the Akamai block of the pure-httpx attempt.

State & failure semantics
-------------------------
  * ``backend/scripts/.scrape_state.json`` — ``completed`` (set of slugs),
    ``failed`` (list of {slug, reason, ts}). Completed slugs are skipped on
    subsequent runs; failures are retried.
  * 401 / 403 / 463 from Meesho API — Akamai or auth block. STOP the entire
    batch immediately; log so the operator can investigate.
  * 429 — rate limited. STOP the batch.
  * Any other API error — log + mark single leaf failed, continue.
  * GCS 4xx/5xx — log + mark single leaf failed, continue (likely the 180s
    signed URL expired in flight).

Concurrency
-----------
``MAX_CONCURRENCY`` semaphore caps simultaneous in-flight scrape_one tasks.
Each task does one POST + one GET. The browser context is shared.

Logging goes to ``logs/scraper/batch_{YYYY-MM-DD_HH-MM}.log`` and stdout.
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
from collections import defaultdict
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv
from playwright.async_api import (
    APIResponse,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/mugunthansrinivasan/Project/mesell")
CREDS_FILE = PROJECT_ROOT / ".meesho_creds.env"
CATEGORY_TREE_FILE = PROJECT_ROOT / "backend" / "app" / "data" / "meesho_category_tree.json"
STATE_FILE = PROJECT_ROOT / "backend" / "scripts" / ".scrape_state.json"
TEMPLATE_DIR = PROJECT_ROOT / "data" / "meesho_templates"
LOG_DIR = PROJECT_ROOT / "logs" / "scraper"

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

SUPPLIER_ID = 4359160
IDENTIFIER = "oinpw"
TOTAL_LEAVES = 3772       # full universe (kept in sync with category tree)
JITTER_MIN_S = 0.5        # min post-success jitter (seconds) — legacy, unused in SAFE_MODE
JITTER_MAX_S = 2.0        # max post-success jitter (seconds) — legacy, unused in SAFE_MODE

# === SPRINT MODE — finish all remaining in <2hr (2026-06-04) ===
# Previous "short-session safe mode" got blocked overnight after an 18-min
# extended break. The pattern that WORKED was a 27-second 5-parallel test that
# ran clean with 0 blocks. The problem was LONG sessions with breaks, not raw
# parallel speed. New strategy: ONE session, 5 parallel workers via
# asyncio.gather + Semaphore(5), no breaks, drain all remaining in ~40 min.
SAFE_MODE = False                      # disable all human-simulation breaks
BATCH_SIZE = 3000                      # cover all remaining (~2,202)
MAX_CONCURRENCY = 5                    # parallel workers (proven safe in earlier test)
LEAF_DELAY_MIN_S = 1.5                 # tighter pacing per worker
LEAF_DELAY_MAX_S = 4.0
SESSION_MAX_LEAVES = 99999             # disabled (one session)
SESSION_MAX_DURATION_S = 99999         # disabled
SESSION_REST_MIN_S = 0                 # disabled
SESSION_REST_MAX_S = 0                 # disabled
MICRO_PAUSE_EVERY = 99999              # DISABLED
MICRO_PAUSE_MIN_S = 30.0               # unused
MICRO_PAUSE_MAX_S = 90.0                # unused
COFFEE_BREAK_EVERY = 99999             # DISABLED
COFFEE_BREAK_MIN_S = 180.0             # unused
COFFEE_BREAK_MAX_S = 420.0             # unused
EXTENDED_BREAK_EVERY = 99999           # DISABLED
EXTENDED_BREAK_MIN_S = 900.0           # unused
EXTENDED_BREAK_MAX_S = 1500.0          # unused
RELOGIN_EVERY = 99999                  # DISABLED
RELOGIN_EVERY_S = 99999                # DISABLED
UI_VISIT_DASHBOARD_EVERY = 99999       # DISABLED
UI_VISIT_CATALOGS_EVERY = 99999        # DISABLED

# UI camouflage URLs (visited periodically to look like a real seller browsing)
UI_DASHBOARD_URL = "https://supplier.meesho.com/panel/v3/new/growth/oinpw/home"
UI_CATALOGS_URL = "https://supplier.meesho.com/panel/v3/new/cataloging/oinpw/catalogs"

# Overall run safety caps
WALL_CLOCK_CAP_S = 2 * 3600         # 2-hour hard cap (sprint mode)
MAX_CONSECUTIVE_FAILURES = 5        # slightly more tolerant of transient failures
CONSECUTIVE_FAILURE_CAP = MAX_CONSECUTIVE_FAILURES  # alias for SAFE_MODE clarity
PROGRESS_LOG_INTERVAL = 50          # log progress every N completed leaves

# Network timeouts (ms for Playwright, seconds for httpx)
TEMPLATE_API_TIMEOUT_MS = 30_000
GCS_DOWNLOAD_TIMEOUT_S = 60.0
LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000

# Endpoints
LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
BULK_TEMPLATE_URL = (
    "https://supplier.meesho.com/api/cataloging/bulkCatalogUpload/fetchBulkUploadTemplate"
)

# Hard-stop status codes (Akamai or auth block).
# 463 is Meesho/Akamai's non-standard "unauthorized call / token missing" reply.
SESSION_STOP_CODES = {401, 403, 463}
RATE_LIMIT_STOP_CODES = {429}


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"batch_{timestamp}.log"

    logger = logging.getLogger("meesho-batch")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    fh = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)

    logger.propagate = False
    logger.info("Batch logfile: %s", log_path)
    return logger


log = logging.getLogger("meesho-batch")


# ---------------------------------------------------------------------------
# Cross-task abort flag
# ---------------------------------------------------------------------------


class AbortFlag:
    """Coroutine-safe flag tripped on hard stops (Akamai / auth / 429)."""

    def __init__(self) -> None:
        self._aborted = False
        self._reason: str | None = None

    def trip(self, reason: str) -> None:
        if not self._aborted:
            self._aborted = True
            self._reason = reason
            log.error("ABORT flag set: %s", reason)

    def reset(self) -> None:
        """Clear the abort state — used between short sessions for soft stops
        like consecutive_failure_cap, so a new session can start fresh.
        Hard Akamai blocks (caught at the outer loop) do NOT reset."""
        self._aborted = False
        self._reason = None

    @property
    def aborted(self) -> bool:
        return self._aborted

    @property
    def reason(self) -> str | None:
        return self._reason


ABORT = AbortFlag()


class AkamaiBlockedError(RuntimeError):
    """Raised when Meesho/Akamai returns a session-stop status (401/403/463/429).

    Halts the entire run — not just the current session. The block needs
    operator investigation (likely IP-level), not a retry.
    """


def _is_akamai_reason(reason: str | None) -> bool:
    """True if an ABORT reason indicates an Akamai/auth/rate-limit block."""
    if not reason:
        return False
    lowered = reason.lower()
    return (
        "akamai" in lowered
        or "session_or_akamai_block" in lowered
        or "rate limited" in lowered
        or "rate_limited" in lowered
    )


# ---------------------------------------------------------------------------
# State / category tree / creds I/O
# ---------------------------------------------------------------------------


def load_creds() -> tuple[str, str]:
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Credentials file missing: {CREDS_FILE}")
    load_dotenv(CREDS_FILE)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    return user, pwd


def load_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {"completed": [], "failed": [], "last_run_at": None}
    try:
        return json.loads(STATE_FILE.read_text())
    except json.JSONDecodeError as exc:
        log.error("State file is corrupt (%s) — starting empty", exc)
        return {"completed": [], "failed": [], "last_run_at": None}


_state_lock = asyncio.Lock()


async def save_state(state: dict[str, Any]) -> None:
    async with _state_lock:
        STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False))


def load_category_tree() -> list[dict[str, Any]]:
    if not CATEGORY_TREE_FILE.exists():
        raise FileNotFoundError(
            f"Category tree not found at {CATEGORY_TREE_FILE}. "
            "It should have been generated by the API-based discovery step."
        )
    data = json.loads(CATEGORY_TREE_FILE.read_text())
    leaves = [c for c in data.get("categories", []) if c.get("is_leaf")]
    for leaf in leaves[:5]:
        if "leaf_id" not in leaf or "leaf_name" not in leaf:
            raise RuntimeError(
                f"Category tree entries are missing `leaf_id`/`leaf_name`. "
                f"Offending entry: {leaf}"
            )
    return leaves


def pick_next_batch(
    leaves: list[dict[str, Any]],
    state: dict[str, Any],
    batch_size: int,
) -> list[dict[str, Any]]:
    """Pick up to ``batch_size`` leaves whose slugs aren't yet completed.

    SAFE_MODE: shuffle within each super-category, then randomize the order of
    super-categories themselves. This makes traffic look like a seller browsing
    naturally rather than walking a deterministic tree.
    """
    completed = set(state.get("completed", []))
    remaining = [leaf for leaf in leaves if leaf["slug"] not in completed]

    if SAFE_MODE:
        buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for leaf in remaining:
            super_cat = leaf["path"][0] if leaf.get("path") else "_unknown_"
            buckets[super_cat].append(leaf)
        for super_cat in buckets:
            random.shuffle(buckets[super_cat])
        super_cats_shuffled = list(buckets.keys())
        random.shuffle(super_cats_shuffled)
        ordered: list[dict[str, Any]] = []
        for super_cat in super_cats_shuffled:
            ordered.extend(buckets[super_cat])
        return ordered[:batch_size]

    return remaining[:batch_size]


# ---------------------------------------------------------------------------
# Playwright login (async port of meesho_template_scraper.perform_login)
# ---------------------------------------------------------------------------


async def perform_login(page: Page, username: str, password: str) -> None:
    """Log in to supplier.meesho.com.

    After this returns, the parent ``BrowserContext`` carries the auth cookies
    (including HttpOnly ones) which subsequent ``ctx.request.post(...)`` calls
    automatically include.
    """
    log.info("Navigating to login URL")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await asyncio.sleep(random.uniform(1.5, 2.5))

    # Username
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
        raise RuntimeError("Could not locate username field on login page")

    log.info("Filling username")
    await user_field.fill(username)
    await asyncio.sleep(random.uniform(0.8, 1.4))

    # Password
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
        raise RuntimeError("Could not locate password field on login page")

    log.info("Filling password")
    await pwd_field.fill(password)
    await asyncio.sleep(random.uniform(0.8, 1.4))

    # Submit
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
        raise RuntimeError("Could not locate login submit button")

    log.info("Submitting login form")
    await submit.click()

    try:
        await page.wait_for_url(
            lambda u: "login" not in u, timeout=LOGIN_NAV_TIMEOUT_MS
        )
    except PlaywrightTimeoutError:
        body_text = ""
        try:
            body_text = await page.locator("body").inner_text(timeout=2_000)
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError(
            f"Login did not redirect away from /login. URL={page.url!r} "
            f"body-snippet={body_text[:300]!r}"
        )

    await page.wait_for_load_state("domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    log.info("Login OK — current URL: %s", page.url)


# ---------------------------------------------------------------------------
# Per-leaf scrape
# ---------------------------------------------------------------------------


def _api_headers(supplier_id: int, identifier: str) -> dict[str, str]:
    """Extra headers Meesho's bulk-template endpoint expects.

    Playwright handles cookies, user-agent, accept-language etc. automatically
    — we only need to layer in Meesho's app-specific signalling headers.
    """
    return {
        "identifier": identifier,
        "client-type": "d-web",
        "client-package-version": "1.0.1",
        "supplier-id": str(supplier_id),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
    }


def _extract_template_url(body: dict[str, Any]) -> str | None:
    return (
        body.get("template_url")
        or (body.get("data") or {}).get("template_url")
        or body.get("url")
        or (body.get("data") or {}).get("url")
    )


def _host_of(url: str) -> str:
    """Just the host of a URL — for logging without leaking signed query strings."""
    try:
        from urllib.parse import urlparse

        return urlparse(url).netloc or "?"
    except Exception:  # noqa: BLE001
        return "?"


async def scrape_one(
    ctx: BrowserContext,
    gcs_client: httpx.AsyncClient,
    leaf: dict[str, Any],
    supplier_id: int,
    identifier: str,
) -> tuple[bool, str | None, int]:
    """Fetch the signed URL via Playwright, then download bytes via httpx.

    Returns ``(ok, reason, bytes_written)``.
    """
    slug = leaf["slug"]
    output_path = TEMPLATE_DIR / f"{slug}.xlsx"

    if ABORT.aborted:
        return False, f"aborted_before_start: {ABORT.reason}", 0

    log.info("[%s] starting (leaf_id=%s)", slug, leaf.get("leaf_id"))

    payload = {
        "sub_sub_category_id": leaf["leaf_id"],
        "sub_sub_category_name": leaf["leaf_name"],
        "scale_id": 1,
        "source": "EXTERNAL",
        "supplier_id": supplier_id,
        "identifier": identifier,
    }

    # Step 1 — POST via the browser context (passes Akamai)
    try:
        resp: APIResponse = await ctx.request.post(
            BULK_TEMPLATE_URL,
            headers=_api_headers(supplier_id, identifier),
            data=payload,
            timeout=TEMPLATE_API_TIMEOUT_MS,
        )
    except PlaywrightTimeoutError:
        log.warning("[%s] template API timed out", slug)
        return False, "template_api_timeout", 0
    except Exception as exc:  # noqa: BLE001
        log.exception("[%s] template API request error: %s", slug, exc)
        return False, f"template_api_error: {exc.__class__.__name__}", 0

    status_code = resp.status
    if status_code in SESSION_STOP_CODES:
        body_preview = ""
        try:
            body_preview = (await resp.text())[:200]
        except Exception:  # noqa: BLE001
            pass
        reason = (
            f"Akamai or auth block (HTTP {status_code}) — investigate. "
            f"Body: {body_preview!r}"
        )
        ABORT.trip(reason)
        return False, f"session_or_akamai_block: {status_code}", 0
    if status_code in RATE_LIMIT_STOP_CODES:
        ABORT.trip(f"rate limited (HTTP {status_code})")
        return False, f"rate_limited: {status_code}", 0
    if status_code >= 400:
        body_preview = ""
        try:
            body_preview = (await resp.text())[:200]
        except Exception:  # noqa: BLE001
            pass
        log.warning("[%s] template API HTTP %d: %s", slug, status_code, body_preview)
        return False, f"template_api_http_{status_code}", 0

    try:
        body = await resp.json()
    except Exception as exc:  # noqa: BLE001
        log.warning("[%s] template API returned non-JSON: %s", slug, exc)
        return False, "template_api_non_json", 0

    template_url = _extract_template_url(body)
    if not template_url:
        log.warning(
            "[%s] template_url missing from API body — keys=%s",
            slug,
            list(body.keys()),
        )
        return False, "template_url_missing", 0

    log.info("[%s] got pre-signed URL (host=%s)", slug, _host_of(template_url))

    # Step 2 — GCS download via httpx (no Akamai)
    try:
        r = await gcs_client.get(
            template_url,
            timeout=GCS_DOWNLOAD_TIMEOUT_S,
            headers={"accept": "*/*"},
        )
        r.raise_for_status()
    except httpx.HTTPStatusError as exc:
        log.warning("[%s] GCS download HTTP %d", slug, exc.response.status_code)
        return False, f"gcs_http_{exc.response.status_code}", 0
    except httpx.RequestError as exc:
        log.warning("[%s] GCS download request error: %s", slug, exc)
        return False, f"gcs_request_error: {exc.__class__.__name__}", 0
    except Exception as exc:  # noqa: BLE001
        log.exception("[%s] unexpected GCS error: %s", slug, exc)
        return False, f"gcs_unexpected: {exc}", 0

    size = len(r.content)
    if size == 0:
        return False, "download_zero_bytes", 0

    output_path.write_bytes(r.content)
    log.info("[%s] saved=%s size=%d", slug, output_path, size)

    # Mild per-task jitter to avoid synchronised bursts. In SAFE_MODE the
    # main loop applies a much longer per-leaf delay (3-8s) so we skip this
    # to avoid stacking two separate sleeps.
    if not SAFE_MODE:
        await asyncio.sleep(random.uniform(JITTER_MIN_S, JITTER_MAX_S))

    return True, None, size


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


async def worker(
    sem: asyncio.Semaphore,
    ctx: BrowserContext,
    gcs_client: httpx.AsyncClient,
    leaf: dict[str, Any],
    supplier_id: int,
    identifier: str,
    state: dict[str, Any],
    summary: dict[str, Any],
) -> None:
    async with sem:
        if ABORT.aborted:
            log.info("[%s] skipped — abort flag set", leaf["slug"])
            return
        ok, reason, size = await scrape_one(
            ctx, gcs_client, leaf, supplier_id, identifier
        )
        if ok:
            state.setdefault("completed", []).append(leaf["slug"])
            summary["completed"] += 1
            summary["consecutive_failures"] = 0
            summary.setdefault("downloads", []).append(
                {
                    "slug": leaf["slug"],
                    "leaf_id": leaf.get("leaf_id"),
                    "size_bytes": size,
                }
            )
        else:
            state.setdefault("failed", []).append(
                {
                    "slug": leaf["slug"],
                    "reason": reason,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
            summary["failed"] += 1
            summary["consecutive_failures"] = summary.get("consecutive_failures", 0) + 1
            if summary["consecutive_failures"] >= MAX_CONSECUTIVE_FAILURES:
                ABORT.trip(
                    f"consecutive_failure_cap: {summary['consecutive_failures']} "
                    f"failures in a row (last reason: {reason})"
                )
        state["last_run_at"] = datetime.now(timezone.utc).isoformat()
        await save_state(state)

        # SPRINT MODE: per-worker jitter INSIDE the semaphore so workers keep
        # the slot only for the actual work + small pacing gap. With 5 workers
        # and 1.5-4s jitter, effective wall-clock per leaf ≈ (api+gcs)/5 + jitter.
        if not SAFE_MODE:
            await asyncio.sleep(random.uniform(LEAF_DELAY_MIN_S, LEAF_DELAY_MAX_S))


async def _ui_camouflage_visit(
    ctx: BrowserContext, url: str, wait_min_s: float, wait_max_s: float, label: str
) -> None:
    """Open a fresh page, navigate to a supplier-panel URL, sit there a bit, close.

    Uses the same authenticated context so no re-login is triggered. Failures
    are non-fatal — we just log and continue (we don't want a UI hiccup to
    abort the entire 12-hour run).
    """
    page: Page | None = None
    try:
        page = await ctx.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
        wait_s = random.uniform(wait_min_s, wait_max_s)
        log.info("UI camouflage: visited %s — dwelling %.1fs", label, wait_s)
        await asyncio.sleep(wait_s)
    except Exception as exc:  # noqa: BLE001
        log.warning("UI camouflage visit to %s failed (non-fatal): %s", label, exc)
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:  # noqa: BLE001
                pass


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    if m:
        return f"{m}m{s:02d}s"
    return f"{s}s"


async def run_session(
    pw: Playwright,
    session_num: int,
    remaining_leaves: list[dict[str, Any]],
    user: str,
    pwd: str,
    state: dict[str, Any],
    summary: dict[str, Any],
    overall_started_monotonic: float,
    leaves_done_total_before: int,
) -> int:
    """One short session: fresh login, scrape up to SESSION_MAX_LEAVES, exit.

    Returns count of leaves processed in this session (success+fail).

    Raises:
        AkamaiBlockedError: if Meesho/Akamai returns a session-stop status —
            the entire run must halt for operator investigation.
    """
    log.info(
        "=== Starting session #%d (overall %d/%d done, remaining queue=%d) ===",
        session_num,
        leaves_done_total_before,
        TOTAL_LEAVES,
        len(remaining_leaves),
    )
    session_started = time.monotonic()
    leaves_this_session = 0

    log.info("[session #%d] Launching fresh WebKit browser (headless)", session_num)
    browser = await pw.webkit.launch(headless=True)
    ctx = await browser.new_context(
        locale="en-IN",
        timezone_id="Asia/Kolkata",
        viewport={"width": 1440, "height": 900},
    )
    ctx.set_default_timeout(LOGIN_ACTION_TIMEOUT_MS)
    ctx.set_default_navigation_timeout(LOGIN_NAV_TIMEOUT_MS)

    try:
        # Fresh login for this session
        page = await ctx.new_page()
        try:
            await perform_login(page, user, pwd)
        except Exception as exc:  # noqa: BLE001
            # Login failure could be Akamai blocking the /login page itself.
            # Treat as hard block so the operator can investigate.
            msg = str(exc).lower()
            if "access denied" in msg or "403" in msg or "akamai" in msg:
                log.error(
                    "[session #%d] Login appears blocked by Akamai: %s",
                    session_num,
                    exc,
                )
                raise AkamaiBlockedError(f"login_blocked: {exc}") from exc
            raise
        await page.close()
        log.info("[session #%d] Login OK", session_num)

        # SPRINT MODE: skip warm-up dashboard visit — the 27-sec 5-parallel
        # test that worked clean had no warm-up. Every second counts.
        if SAFE_MODE:
            await _ui_camouflage_visit(
                ctx, UI_DASHBOARD_URL, 6.0, 12.0,
                f"session #{session_num} warm-up dashboard",
            )
            await asyncio.sleep(random.uniform(5.0, 15.0))

        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async with httpx.AsyncClient(
            http2=False,
            follow_redirects=True,
        ) as gcs_client:
            # SPRINT MODE: fire ALL leaves as parallel tasks under a
            # Semaphore(MAX_CONCURRENCY). The semaphore caps in-flight tasks
            # to MAX_CONCURRENCY=5; the rest queue up. asyncio.gather awaits
            # everything. The 27-sec 5-parallel test proved this pattern
            # works clean. ABORT flag inside worker() short-circuits remaining
            # tasks if Akamai trips.
            already_completed = set(state.get("completed", []))
            todo = [
                leaf for leaf in remaining_leaves
                if leaf["slug"] not in already_completed
            ]
            log.info(
                "[session #%d] Firing %d parallel tasks (concurrency=%d)",
                session_num,
                len(todo),
                MAX_CONCURRENCY,
            )

            # Wall-clock cap watchdog — trips ABORT if the run exceeds the cap
            async def _wall_clock_watchdog() -> None:
                while not ABORT.aborted:
                    overall_elapsed = time.monotonic() - overall_started_monotonic
                    if overall_elapsed >= WALL_CLOCK_CAP_S:
                        ABORT.trip(
                            f"wall-clock cap reached ({overall_elapsed:.0f}s >= "
                            f"{WALL_CLOCK_CAP_S}s)"
                        )
                        return
                    await asyncio.sleep(10.0)

            # Progress logger — runs every PROGRESS_LOG_INTERVAL seconds
            async def _progress_logger() -> None:
                last_done = 0
                while not ABORT.aborted:
                    await asyncio.sleep(30.0)
                    done = summary["completed"]
                    delta = done - last_done
                    last_done = done
                    overall_elapsed_now = time.monotonic() - overall_started_monotonic
                    rate_s_per_leaf = (
                        overall_elapsed_now / done if done > 0 else 0.0
                    )
                    overall_done = leaves_done_total_before + done
                    remaining_total = TOTAL_LEAVES - overall_done
                    eta_s = remaining_total * rate_s_per_leaf
                    pct = 100.0 * overall_done / TOTAL_LEAVES if TOTAL_LEAVES else 0.0
                    log.info(
                        "Progress: %d/%d completed (%.1f%%), elapsed: %s, "
                        "rate: %.1fs/leaf, last-30s: +%d, ETA: %s",
                        overall_done,
                        TOTAL_LEAVES,
                        pct,
                        _fmt_duration(overall_elapsed_now),
                        rate_s_per_leaf,
                        delta,
                        _fmt_duration(eta_s),
                    )

            watchdog_task = asyncio.create_task(_wall_clock_watchdog())
            progress_task = asyncio.create_task(_progress_logger())

            try:
                tasks = [
                    asyncio.create_task(
                        worker(
                            sem,
                            ctx,
                            gcs_client,
                            leaf,
                            SUPPLIER_ID,
                            IDENTIFIER,
                            state,
                            summary,
                        )
                    )
                    for leaf in todo
                ]
                await asyncio.gather(*tasks, return_exceptions=False)
            finally:
                watchdog_task.cancel()
                progress_task.cancel()
                try:
                    await watchdog_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
                try:
                    await progress_task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass

            leaves_this_session = summary["completed"] + summary["failed"]

            # If Akamai/auth/rate-limit block tripped: halt the entire run.
            if ABORT.aborted and _is_akamai_reason(ABORT.reason):
                raise AkamaiBlockedError(ABORT.reason or "akamai_block")
    finally:
        try:
            await ctx.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            await browser.close()
        except Exception:  # noqa: BLE001
            pass

    session_dur_min = (time.monotonic() - session_started) / 60.0
    log.info(
        "=== Session #%d done: %d leaves in %.1f min ===",
        session_num,
        leaves_this_session,
        session_dur_min,
    )
    return leaves_this_session


async def run_all(pw: Playwright) -> dict[str, Any]:
    """Outer driver: loop short sessions with rests until done, capped, or blocked."""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    leaves = load_category_tree()
    state = load_state()

    summary: dict[str, Any] = {
        "completed": 0,
        "failed": 0,
        "skipped": 0,
        "total_remaining": 0,
        "downloads": [],
        "consecutive_failures": 0,
        "sessions_run": 0,
        "leaves_done_at_start": len(state.get("completed", [])),
    }

    user, pwd = load_creds()

    leaves_done_at_start = len(state.get("completed", []))
    log.info(
        "Short-session mode: total_leaves=%d, already_completed=%d, "
        "remaining=%d, supplier_id=%d, identifier=%s",
        len(leaves),
        leaves_done_at_start,
        len(leaves) - leaves_done_at_start,
        SUPPLIER_ID,
        IDENTIFIER,
    )
    log.info(
        "Session caps: max_leaves=%d, max_duration=%ds, rest=%d-%ds, "
        "leaf_delay=%.1f-%.1fs, wall_clock_cap=%ds",
        SESSION_MAX_LEAVES,
        SESSION_MAX_DURATION_S,
        SESSION_REST_MIN_S,
        SESSION_REST_MAX_S,
        LEAF_DELAY_MIN_S,
        LEAF_DELAY_MAX_S,
        WALL_CLOCK_CAP_S,
    )

    overall_started_monotonic = time.monotonic()
    session_num = 0

    while True:
        # Compute remaining each iteration (state is mutated by workers)
        remaining = pick_next_batch(leaves, state, BATCH_SIZE)
        if not remaining:
            log.info("All leaves complete — nothing left to do.")
            break

        leaves_done_total = len(state.get("completed", []))
        if leaves_done_total >= TOTAL_LEAVES:
            log.info("Reached TOTAL_LEAVES=%d — done.", TOTAL_LEAVES)
            break

        overall_elapsed = time.monotonic() - overall_started_monotonic
        if overall_elapsed >= WALL_CLOCK_CAP_S:
            log.info(
                "Overall wall-clock cap (%ds) reached — halting cleanly",
                WALL_CLOCK_CAP_S,
            )
            break

        session_num += 1
        try:
            await run_session(
                pw,
                session_num,
                remaining,
                user,
                pwd,
                state,
                summary,
                overall_started_monotonic,
                leaves_done_total,
            )
        except AkamaiBlockedError as exc:
            log.error(
                "Akamai/auth block during session #%d: %s — halting entire run "
                "for investigation",
                session_num,
                exc,
            )
            summary["aborted_reason"] = f"akamai_block: {exc}"
            break

        summary["sessions_run"] = session_num

        # If a soft abort tripped (e.g. consecutive_failure_cap), break out —
        # do NOT auto-restart, because we don't know if it's an early Akamai
        # signal masquerading as random failures.
        if ABORT.aborted and not _is_akamai_reason(ABORT.reason):
            log.error(
                "Soft-abort during session #%d (reason=%s) — halting run",
                session_num,
                ABORT.reason,
            )
            summary["aborted_reason"] = ABORT.reason
            break

        leaves_done_total = len(state.get("completed", []))
        if leaves_done_total >= TOTAL_LEAVES:
            log.info("Reached TOTAL_LEAVES=%d after session #%d", TOTAL_LEAVES, session_num)
            break

        # Rest between sessions
        rest_s = random.uniform(SESSION_REST_MIN_S, SESSION_REST_MAX_S)
        log.info(
            "Resting %.1f min before session #%d (overall done: %d/%d)",
            rest_s / 60.0,
            session_num + 1,
            leaves_done_total,
            TOTAL_LEAVES,
        )
        await asyncio.sleep(rest_s)

    completed_set = set(state.get("completed", []))
    summary["total_remaining"] = sum(
        1 for leaf in leaves if leaf["slug"] not in completed_set
    )
    summary["leaves_done_at_end"] = len(completed_set)
    summary["sessions_run"] = session_num

    if ABORT.aborted:
        log.error("Run aborted due to: %s", ABORT.reason)
        summary.setdefault("aborted_reason", ABORT.reason)

    return summary


async def amain() -> int:
    configure_logging()
    log.info(
        "==== Meesho hybrid (Playwright+httpx) batch scraper starting at %s ====",
        datetime.now().isoformat(),
    )
    started = datetime.now(timezone.utc)
    try:
        async with async_playwright() as pw:
            summary = await run_all(pw)
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        return 130
    except Exception as exc:  # noqa: BLE001
        log.exception("Batch run failed: %s", exc)
        return 1

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()

    log.info(
        "Batch summary: completed=%d failed=%d skipped=%d total_remaining=%d elapsed=%.1fs",
        summary["completed"],
        summary["failed"],
        summary["skipped"],
        summary["total_remaining"],
        elapsed,
    )
    print("\n========= BATCH SUMMARY =========")
    print(f"sessions_run    : {summary.get('sessions_run', 0)}")
    print(f"completed       : {summary['completed']}")
    print(f"failed          : {summary['failed']}")
    print(f"skipped         : {summary['skipped']}")
    print(f"total_remaining : {summary['total_remaining']}")
    print(f"elapsed_seconds : {elapsed:.1f}")
    if summary.get("downloads"):
        print("\nDownloaded:")
        for d in summary["downloads"]:
            print(f"  {d['slug']}  leaf_id={d['leaf_id']}  size={d['size_bytes']}B")
    if ABORT.aborted:
        print(f"\nABORTED         : {ABORT.reason}")
    print("=================================")
    return 0


def main() -> int:
    return asyncio.run(amain())


if __name__ == "__main__":
    sys.exit(main())
