"""scrape_category.py — single-category scrape entrypoint for the category change monitor.

Design: Q2 = Option (b) — hybrid projection
    LIVE (one rate-limited ctx.request.post per category):
        shipping_slab  — shipping_charges + gst_percentage from getTransferPrice
        cost_fields    — transfer_price, platform_fee (the monetisation inputs)
    CORPUS (no network call, read-only committed data files):
        compliance_fields — from backend/app/data/category_attributes.json
        banned_words      — from backend/app/data/banned_words.json

The four dimensions are assembled into a ``dimensions_jsonb`` projection and
stored as a ``category_snapshots`` DB row.

content_hash contract
---------------------
SHA-256 hex over the CANONICALIZED dimensions projection:
    json.dumps(dimensions, sort_keys=True, separators=(",", ":"))
where ``dimensions`` is the dict of the four dimensions ONLY — no ``_meta``,
no timestamps, no blob_uri.  An unchanged scrape of the same category yields a
byte-identical hash, which diff_category_rules.py uses as a cheap short-circuit.

This is the SAME exclusion discipline as diff_pricing_lookup.py's
``generated_at`` exclusion: volatile metadata fields are never part of the hash.

Safety harness
--------------
Reused VERBATIM from meesho_batch_scraper.py:
    load_creds(), perform_login() (Akamai-valid WebKit context)
    SUPPLIER_ID, IDENTIFIER, _api_headers()
    AbortFlag / AkamaiBlockedError / _is_akamai_reason()
    >= 2s jittered rate-limit between any two Meesho API calls
    headless=True WebKit
    Hard stop on 403 / 429 / captcha / 2 login failures (halt + surface, NO retry storm)
    .meesho_creds.env ONLY, read-only

Exit codes
----------
    0  — OK; snapshot written; DB row inserted
    1  — Corpus error (missing category_attributes.json / banned_words.json)
    2  — Hard stop (403 / 429 / Akamai block)
    3  — Login failed after 2 attempts
    4  — DB insert failed
    5  — Invalid arguments

NO live tests may call this module's live path.  Tests MUST mock ctx.request
entirely.  See backend/tests/test_scrape_category.py.

CLI usage (operator, manual run after creds rotation):
    backend/.venv/bin/python backend/scripts/scrape_category.py <category_id> [--db-url URL]

    category_id: UUID string matching categories.id (maps to meesho_leaf_id to look up
                 the sscat_id for the getTransferPrice call)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # mesell/
CREDS_FILE = PROJECT_ROOT / ".meesho_creds.env"
LOG_DIR = PROJECT_ROOT / "logs" / "scraper"
SNAPSHOT_BASE = PROJECT_ROOT / "data" / "snapshots"

# Committed corpus files (read-only; never scraped)
CATEGORY_ATTRS_FILE = PROJECT_ROOT / "backend" / "app" / "data" / "category_attributes.json"
BANNED_WORDS_FILE = PROJECT_ROOT / "backend" / "app" / "data" / "banned_words.json"

# ---------------------------------------------------------------------------
# Tunables (mirrored from meesho_batch_scraper.py — do not diverge)
# ---------------------------------------------------------------------------

SUPPLIER_ID = 4359160
IDENTIFIER = "oinpw"

# Rate limit: >= 2s between any two Meesho API calls (policy: <= 1 req / 2s)
RATE_LIMIT_JITTER_MIN_S = 2.0
RATE_LIMIT_JITTER_MAX_S = 4.0

API_TIMEOUT_MS = 30_000
LOGIN_NAV_TIMEOUT_MS = 45_000
LOGIN_ACTION_TIMEOUT_MS = 20_000

LOGIN_URL = "https://supplier.meesho.com/panel/v3/new/root/login"
TRANSFER_PRICE_URL = (
    "https://supplier.meesho.com/api/cataloging/singleCatalogUpload/getTransferPrice"
)

# Hard-stop HTTP status codes (Akamai / auth / rate-limit blocks)
SESSION_STOP_CODES = {401, 403, 463}
RATE_LIMIT_STOP_CODES = {429}

# Captcha markers in page body text
_CAPTCHA_MARKERS = ("captcha", "i am not a robot", "are you human", "cf-challenge")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


def _configure_logging(category_id: str) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"scrape_category_{category_id[:8]}_{ts}.log"

    logger = logging.getLogger(f"scrape-category-{category_id[:8]}")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    fh = RotatingFileHandler(log_path, maxBytes=2_000_000, backupCount=2)
    fh.setFormatter(fmt)
    fh.setLevel(logging.INFO)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    sh.setLevel(logging.INFO)
    logger.addHandler(sh)

    logger.propagate = False
    return logger


# ---------------------------------------------------------------------------
# Auth harness — VERBATIM reuse from meesho_batch_scraper.py
# (load_creds, perform_login, AbortFlag, AkamaiBlockedError, _is_akamai_reason,
#  _api_headers are copied verbatim to keep this module self-contained and avoid
#  import-time side-effects from the batch scraper module-level ABORT singleton)
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

    @property
    def aborted(self) -> bool:
        return self._aborted

    @property
    def reason(self) -> str | None:
        return self._reason


class AkamaiBlockedError(RuntimeError):
    """Raised when Meesho/Akamai returns a session-stop status (401/403/463/429).

    Halts the entire run — requires operator investigation, not a retry.
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


def load_creds() -> tuple[str, str]:
    """Load Meesho credentials from .meesho_creds.env.

    Only OUR own .meesho_creds.env file is read (gitignored, project root).
    NEVER reads from environment variables or any other source.
    """
    if not CREDS_FILE.exists():
        raise FileNotFoundError(f"Credentials file missing: {CREDS_FILE}")
    from dotenv import load_dotenv  # type: ignore[import]

    load_dotenv(CREDS_FILE)
    user = os.environ.get("MEESHO_USERNAME", "").strip()
    pwd = os.environ.get("MEESHO_PASSWORD", "").strip()
    if not user or not pwd:
        raise RuntimeError("MEESHO_USERNAME / MEESHO_PASSWORD missing in creds file")
    return user, pwd


async def perform_login(page: Any, username: str, password: str) -> None:  # type: ignore[type-arg]
    """Log in to supplier.meesho.com — VERBATIM from meesho_batch_scraper.py.

    After this returns, the parent BrowserContext carries the auth cookies
    (including HttpOnly ones) which subsequent ctx.request.post(...) calls
    automatically include.
    """
    import re as _re

    from playwright.async_api import TimeoutError as PlaywrightTimeoutError  # type: ignore[import]

    log = logging.getLogger(f"scrape-category")
    log.info("Navigating to login URL")
    await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
    await asyncio.sleep(random.uniform(1.5, 2.5))

    # Username
    user_field = None
    user_candidates = [
        lambda: page.get_by_placeholder(_re.compile(r"email.*mobile", _re.I)),
        lambda: page.get_by_label(_re.compile(r"email.*mobile", _re.I)),
        lambda: page.get_by_role("textbox", name=_re.compile(r"email|mobile", _re.I)),
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

    await user_field.fill(username)
    await asyncio.sleep(random.uniform(0.8, 1.4))

    # Password
    pwd_field = None
    pwd_candidates = [
        lambda: page.get_by_placeholder(_re.compile(r"password", _re.I)),
        lambda: page.get_by_label(_re.compile(r"password", _re.I)),
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

    await pwd_field.fill(password)
    await asyncio.sleep(random.uniform(0.8, 1.4))

    # Submit
    submit = None
    submit_candidates = [
        lambda: page.get_by_role("button", name=_re.compile(r"log\s*in|sign\s*in", _re.I)),
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


def _api_headers() -> dict[str, str]:
    """Meesho supplier panel API headers — VERBATIM from meesho_batch_scraper.py."""
    return {
        "identifier": IDENTIFIER,
        "client-type": "d-web",
        "client-package-version": "1.0.1",
        "supplier-id": str(SUPPLIER_ID),
        "content-type": "application/json;charset=UTF-8",
        "accept": "application/json, text/plain, */*",
    }


# ---------------------------------------------------------------------------
# Corpus projection helpers
# (Option b — no network call; read committed corpus files)
# ---------------------------------------------------------------------------


def _load_compliance_fields(category_name: str | None = None) -> dict[str, Any]:
    """Project compliance_fields from the committed category_attributes.json corpus.

    Uses the category name as the lookup key with a fallback to ``_default``.
    No network call is made.  If the corpus file is missing this is a fatal error
    (exit 1 at the caller level).
    """
    if not CATEGORY_ATTRS_FILE.exists():
        raise FileNotFoundError(
            f"Corpus file missing: {CATEGORY_ATTRS_FILE}. "
            "Cannot project compliance_fields without the committed corpus."
        )
    corpus: dict[str, Any] = json.loads(CATEGORY_ATTRS_FILE.read_text(encoding="utf-8"))
    # Try exact name match, then fall back to _default
    if category_name and category_name in corpus:
        return dict(corpus[category_name])
    return dict(corpus.get("_default", {"required": [], "optional": []}))


def _load_banned_words() -> dict[str, Any]:
    """Project banned_words from the committed banned_words.json corpus.

    No network call is made.  Returns the full banned-words structure.
    If the corpus file is missing this is a fatal error (exit 1 at caller level).
    """
    if not BANNED_WORDS_FILE.exists():
        raise FileNotFoundError(
            f"Corpus file missing: {BANNED_WORDS_FILE}. "
            "Cannot project banned_words without the committed corpus."
        )
    return json.loads(BANNED_WORDS_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Live projection helpers (one rate-limited ctx.request.post per category)
# ---------------------------------------------------------------------------


async def _fetch_transfer_price(
    ctx: Any,  # playwright BrowserContext
    sscat_id: str,
    abort: AbortFlag,
    log: logging.Logger,
) -> dict[str, Any]:
    """POST getTransferPrice for the category's sscat_id.

    Rate limit: caller MUST sleep >= RATE_LIMIT_JITTER_MIN_S before calling this.

    Returns a dict with keys: transfer_price, shipping_charges, gst_percentage,
    platform_fee.  Raises AkamaiBlockedError on 403/429/463/401.
    """
    body = json.dumps(
        {
            "sscat_id": sscat_id,
            "gst_percentage": None,
            "price": 100,
            "supplier_id": SUPPLIER_ID,
            "duplicate_pid": None,
            "gst_type": "ENROLMENT",
        }
    )
    resp = await ctx.request.post(
        TRANSFER_PRICE_URL,
        headers=_api_headers(),
        data=body,
        timeout=API_TIMEOUT_MS,
    )
    status = resp.status

    if status in SESSION_STOP_CODES or status in RATE_LIMIT_STOP_CODES:
        reason = f"session_or_akamai_block:status={status}"
        abort.trip(reason)
        raise AkamaiBlockedError(
            f"Hard stop: getTransferPrice returned HTTP {status} for sscat_id={sscat_id!r}"
        )

    resp_body: dict[str, Any] = {}
    try:
        resp_body = await resp.json()
    except Exception:  # noqa: BLE001
        try:
            text = await resp.text()
            lower = text.lower()
            if any(m in lower for m in _CAPTCHA_MARKERS):
                abort.trip("captcha_detected")
                raise AkamaiBlockedError("CAPTCHA detected — refuse to solve; halting")
        except AkamaiBlockedError:
            raise
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError(
            f"getTransferPrice returned HTTP {status} with non-JSON body for sscat_id={sscat_id!r}"
        )

    # Extract the fields we care about
    data = resp_body.get("data") or resp_body
    return {
        "transfer_price": float(data.get("transfer_price", data.get("transferPrice", 0))),
        "shipping_charges": int(data.get("shipping_charges", data.get("shippingCharges", 0))),
        "gst_percentage": int(data.get("gst_percentage", data.get("gstPercentage", 0))),
        "platform_fee": float(data.get("platform_fee", data.get("platformFee", 0))),
    }


# ---------------------------------------------------------------------------
# content_hash computation
# ---------------------------------------------------------------------------


def compute_content_hash(dimensions: dict[str, Any]) -> str:
    """Compute the SHA-256 hex hash over the canonicalized dimensions projection.

    Canonical form: json.dumps(dimensions, sort_keys=True, separators=(",", ":"))
    Only the four rule dimensions are hashed — no _meta, no timestamps, no blob_uri.
    This is the same exclusion discipline as diff_pricing_lookup.py's generated_at
    exclusion: volatile metadata never participates in the change-detector hash.

    An unchanged scrape of the same category will yield a byte-identical hash,
    which diff_category_rules.py uses as a cheap short-circuit (no diff needed).
    """
    canonical = json.dumps(dimensions, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Snapshot I/O
# ---------------------------------------------------------------------------


def _snapshot_date_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def write_snapshot_blob(
    category_id: str,
    dimensions: dict[str, Any],
    content_hash: str,
    snapshot_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Write raw blob + sidecar .meta.json to data/snapshots/<YYYY-MM-DD>/.

    Returns (blob_path, meta_path).  Creates the directory if needed.
    Follows the RETENTION_CATEGORY_MONITOR.md §2.2 audit-trail convention.
    """
    date_str = _snapshot_date_str()
    out_dir = snapshot_dir or (SNAPSHOT_BASE / date_str)
    out_dir.mkdir(parents=True, exist_ok=True)

    blob_path = out_dir / f"cat_{category_id}.json"
    meta_path = out_dir / f"cat_{category_id}.meta.json"

    blob_path.write_text(
        json.dumps(dimensions, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    meta = {
        "category_id": category_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": content_hash,
        "source_url": TRANSFER_PRICE_URL,
        "snapshot_version": "1",
    }
    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return blob_path, meta_path


# ---------------------------------------------------------------------------
# DB insert
# ---------------------------------------------------------------------------


async def insert_snapshot_row(
    db_url: str,
    category_id: str,
    content_hash: str,
    dimensions: dict[str, Any],
    blob_uri: str | None = None,
) -> None:
    """Insert a category_snapshots row into the database.

    Uses SQLAlchemy async + the W1 CategorySnapshot ORM model.

    IMPORTANT: Only call this with a TEST_DATABASE_URL (ending in _test) in tests.
    NEVER target the live meesell dev DB (it holds 3,772 categories of real data).

    The caller is responsible for ensuring the DB exists and has run migrations up
    to the Wave-1 schema (category_snapshots table must exist).
    """
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.pool import NullPool

    # Import the ORM model from the shared models package on this branch
    try:
        import sys as _sys
        from pathlib import Path as _Path

        _proj_root = _Path(__file__).resolve().parents[2]
        _backend_dir = _proj_root / "backend"
        if str(_backend_dir) not in _sys.path:
            _sys.path.insert(0, str(_backend_dir))
        from app.shared.models.category_snapshot import CategorySnapshot  # type: ignore[import]
    except ImportError as exc:
        raise ImportError(
            "Cannot import CategorySnapshot model. Ensure the W1 schema branch is active "
            "and backend/ is on sys.path."
        ) from exc

    engine = create_async_engine(db_url, poolclass=NullPool)
    try:
        async with AsyncSession(engine, expire_on_commit=False) as session:
            async with session.begin():
                row = CategorySnapshot(
                    category_id=uuid.UUID(category_id),
                    captured_at=datetime.now(timezone.utc),
                    content_hash=content_hash,
                    dimensions_jsonb=dimensions,
                    blob_uri=blob_uri,
                )
                session.add(row)
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Main public entry point: scrape_category()
# ---------------------------------------------------------------------------


async def scrape_category(
    category_id: str,
    sscat_id: str,
    category_name: str | None = None,
    db_url: str | None = None,
    snapshot_dir: Path | None = None,
    *,
    _ctx: Any = None,  # injected in tests to mock ctx.request
    log: logging.Logger | None = None,
) -> dict[str, Any]:
    """Scrape + project a single Meesho category and write the snapshot.

    Args:
        category_id:    UUID string of the category row in the ``categories`` table.
        sscat_id:       Meesho sscat_id (the leaf ID used by getTransferPrice).
        category_name:  Human-readable name (used as compliance_fields corpus key).
        db_url:         SQLAlchemy async DB URL.  If None, skips the DB insert
                        (useful for dry-run / fixture-only tests).
        snapshot_dir:   Override for the snapshot output directory (used in tests to
                        write to a tmp path instead of data/snapshots/).
        _ctx:           Playwright BrowserContext for ctx.request.post calls.
                        MUST be provided when db_url is set and the live path is needed.
                        Tests inject a mock object here — see test_scrape_category.py.
        log:            Logger (created from category_id if not provided).

    Returns:
        A dict with keys:
            dimensions      — the four-dimension projection dict
            content_hash    — SHA-256 hex hash of the dimensions
            blob_path       — Path to written raw blob
            meta_path       — Path to written .meta.json sidecar
            db_inserted     — bool; True if DB row was inserted

    Raises:
        AkamaiBlockedError  — on 403 / 429 / Akamai block (caller should exit 2)
        FileNotFoundError   — if corpus files are missing (caller should exit 1)
        RuntimeError        — other protocol / login errors
    """
    if log is None:
        log = _configure_logging(category_id)

    abort = AbortFlag()

    log.info(
        "scrape_category: category_id=%s sscat_id=%s name=%r",
        category_id,
        sscat_id,
        category_name,
    )

    # --- CORPUS projection (no network call) ---
    log.info("Loading compliance_fields from corpus (no network call)")
    compliance_fields = _load_compliance_fields(category_name)

    log.info("Loading banned_words from corpus (no network call)")
    banned_words = _load_banned_words()

    # --- LIVE projection (one rate-limited POST) ---
    if _ctx is not None:
        # Rate-limit jitter before the live call
        jitter = random.uniform(RATE_LIMIT_JITTER_MIN_S, RATE_LIMIT_JITTER_MAX_S)
        log.info(
            "Rate-limit sleep %.2fs before getTransferPrice call (sscat_id=%s)",
            jitter,
            sscat_id,
        )
        await asyncio.sleep(jitter)

        log.info("Fetching getTransferPrice for sscat_id=%s", sscat_id)
        price_data = await _fetch_transfer_price(_ctx, sscat_id, abort, log)
    else:
        # _ctx not provided — dry-run mode (no live call, no DB insert)
        log.warning(
            "No BrowserContext provided (_ctx=None). Skipping live getTransferPrice call. "
            "Dry-run mode: shipping_slab and cost_fields will be empty."
        )
        price_data = {
            "transfer_price": 0.0,
            "shipping_charges": 0,
            "gst_percentage": 0,
            "platform_fee": 0.0,
        }

    # --- Assemble dimensions projection ---
    dimensions: dict[str, Any] = {
        "compliance_fields": compliance_fields,
        "shipping_slab": {
            "shipping_charges": price_data["shipping_charges"],
            "gst_percentage": price_data["gst_percentage"],
        },
        "banned_words": banned_words,
        "cost_fields": {
            "transfer_price": price_data["transfer_price"],
            "platform_fee": price_data["platform_fee"],
            "sscat_id": sscat_id,
        },
    }

    # --- Compute content_hash (over canonicalized dimensions ONLY) ---
    content_hash = compute_content_hash(dimensions)
    log.info("content_hash: %s", content_hash)

    # --- Write snapshot blob + .meta.json ---
    blob_path, meta_path = write_snapshot_blob(
        category_id, dimensions, content_hash, snapshot_dir=snapshot_dir
    )
    log.info("Snapshot written: %s", blob_path)
    log.info("Meta sidecar written: %s", meta_path)

    # --- DB insert ---
    db_inserted = False
    if db_url is not None:
        log.info("Inserting category_snapshots row for category_id=%s", category_id)
        await insert_snapshot_row(
            db_url=db_url,
            category_id=category_id,
            content_hash=content_hash,
            dimensions=dimensions,
            blob_uri=None,  # blob_uri set to NULL until GCS upload (INFRA-owned)
        )
        db_inserted = True
        log.info("DB row inserted OK")

    return {
        "dimensions": dimensions,
        "content_hash": content_hash,
        "blob_path": blob_path,
        "meta_path": meta_path,
        "db_inserted": db_inserted,
    }


# ---------------------------------------------------------------------------
# Async wrapper: scrape_category_with_auth()
# Used for live CLI runs (not in tests — tests mock _ctx)
# ---------------------------------------------------------------------------


async def _amain(category_id: str, sscat_id: str, category_name: str | None, db_url: str | None) -> int:
    """CLI entry point — performs full auth + live scrape."""
    from playwright.async_api import async_playwright  # type: ignore[import]

    log = _configure_logging(category_id)

    try:
        username, password = load_creds()
    except (FileNotFoundError, RuntimeError) as exc:
        log.error("Credentials error: %s", exc)
        return 5

    login_attempts = 0
    async with async_playwright() as pw:
        browser = await pw.webkit.launch(headless=True, slow_mo=100)
        try:
            ctx = await browser.new_context()
            page = await ctx.new_page()

            # Login with max 2 attempts (per hard-stop policy)
            while login_attempts < 2:
                try:
                    await perform_login(page, username, password)
                    break
                except RuntimeError as exc:
                    login_attempts += 1
                    log.warning("Login attempt %d failed: %s", login_attempts, exc)
                    if login_attempts >= 2:
                        log.error("Login failed after 2 attempts — halting")
                        return 3

            abort = AbortFlag()
            try:
                result = await scrape_category(
                    category_id=category_id,
                    sscat_id=sscat_id,
                    category_name=category_name,
                    db_url=db_url,
                    _ctx=ctx,
                    log=log,
                )
            except AkamaiBlockedError as exc:
                log.error("Hard stop (Akamai/429/403): %s", exc)
                return 2
            except FileNotFoundError as exc:
                log.error("Corpus file missing: %s", exc)
                return 1

        finally:
            await browser.close()

    log.info(
        "Done. blob=%s content_hash=%s db_inserted=%s",
        result["blob_path"],
        result["content_hash"],
        result["db_inserted"],
    )
    return 0


# ---------------------------------------------------------------------------
# CLI entry
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Scrape a single Meesho category and write a snapshot row."
    )
    parser.add_argument("category_id", help="UUID of the category (categories.id)")
    parser.add_argument("sscat_id", help="Meesho sscat_id (leaf ID for getTransferPrice)")
    parser.add_argument("--category-name", default=None, help="Human-readable category name")
    parser.add_argument("--db-url", default=None, help="SQLAlchemy async DB URL for row insert")
    args = parser.parse_args()

    exit_code = asyncio.run(
        _amain(
            category_id=args.category_id,
            sscat_id=args.sscat_id,
            category_name=args.category_name,
            db_url=args.db_url,
        )
    )
    sys.exit(exit_code)
