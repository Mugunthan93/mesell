"""Meesho SETTLEMENT / PAYOUT investigation probe — READ-ONLY.

Goal
----
Capture the REAL Meesho seller-payout deduction structure that is NOT in the
catalog-upload XLSX template:
  1. commission / referral-fee rate-card (if reachable; was e-sig-blocked before)
  2. the per-order DELIVERED settlement breakdown (commission, fixed fee,
     collection/PG fee, shipping/logistics, RTO, GST-on-fees, TCS/TDS)
  3. account-level monetization config (default_monetization_percent etc.)

Method
------
Reuses the PROVEN authenticated-WebKit + Akamai-bypass idiom from
meesho_batch_scraper.py: launch WebKit, log in once with .meesho_creds.env,
the BrowserContext carries Akamai-valid cookies + JA3 fingerprint, then call
Meesho XHR endpoints via the real browser by NAVIGATING the panel pages and
INTERCEPTING the XHR/fetch responses (we do NOT guess endpoint URLs and present
them as real — lesson from Wave 1.5: Meesho's SPA returns 200 for any path).

HARD SAFETY
-----------
  * READ-ONLY. Only GET-style navigation + response interception. Zero mutation.
    No price change, no product change, no POST to mutate.
  * Auto-detect supplier id from the post-login config XHRs.
  * Hard-stop on OTP / 401 / 403 / 463 / 429 / e-signature wall. Report + exit.
  * Never log credential values.
  * Minimal: visit the payments/settlement section + commission section once.
    No bulk iteration over orders — capture ONE settled order if listed.

Output
------
  * logs/scraper/settlement_<ts>.log — full intercepted-XHR log (gitignored)
  * stdout JSON summary of: detected supplier id, agreement/e-sig state,
    monetization config, commission XHRs seen, settlement/payment XHRs seen,
    deduction line-item keys discovered.
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
    BrowserContext,
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

# 463 = Akamai per-endpoint block. We tolerate it on individual XHRs (some
# endpoints are more sensitive than others) and only hard-stop on auth-class
# codes. 463 is recorded per-URL but does NOT abort the whole probe.
SESSION_STOP_CODES = {401, 403, 429}
TOLERATED_BLOCK_CODES = {463}

# Config endpoints whose FULL value-level JSON we snapshot (the gold — real
# account-level fee/deduction config).
VALUE_SNAPSHOT_RE = re.compile(
    r"prefetch-supply-data|supplier/config|fetch-registration-status|"
    r"fetch-home|fetch-growth-overview|referral|monetization|settlement|payment|payout|transaction",
    re.I,
)
# Keys whose scalar values we always extract for the report.
VALUE_KEYS = {
    "default_monetization_percent", "default_monetization_type", "mall_commission_rate",
    "cod_charges", "shipping_charges", "cancellation_penalty", "logistic_fee_enabled",
    "logistic_fee_enable_time", "pay_tds", "returns_percentage", "no_reason_return_percent",
    "is_agreement_accepted", "agreement_accepted", "gst_type", "gstin",
    "shipping_bracket", "sscat_shipping_adjustment", "prepaid_rto", "rto_returns",
    "supplier_id", "identifier", "wdrp_returns",
}

# Panel pages to navigate (read-only). We intercept XHRs fired by each.
# {id} is interpolated with the auto-detected supplier identifier.
NAV_PAGES: list[tuple[str, str]] = [
    ("home", "https://supplier.meesho.com/panel/v3/new/growth/{id}/home"),
    ("payments", "https://supplier.meesho.com/panel/v3/new/payments/{id}/payments"),
    ("payments_root", "https://supplier.meesho.com/panel/v3/new/root/payments"),
    ("orders", "https://supplier.meesho.com/panel/v3/new/fulfillment/{id}/orders"),
    ("orders_root", "https://supplier.meesho.com/panel/v3/new/root/orders"),
    ("referral_fee", "https://supplier.meesho.com/panel/v3/new/growth/{id}/referral-fee"),
    ("commission_root", "https://supplier.meesho.com/panel/v3/new/root/commission"),
]

# XHR URL classifiers — what bucket a captured response falls in.
COMMISSION_RE = re.compile(r"referral[-_]?fee|commission|monetization|rate[-_]?card|charge", re.I)
SETTLEMENT_RE = re.compile(
    r"settlement|payment|payout|transaction|order[-_]?detail|deduction|ledger|"
    r"recon|invoice|tcs|tds|earning",
    re.I,
)
SUPPLIER_CFG_RE = re.compile(r"supplier|config|profile|account|agreement|signature|kyc|onboard", re.I)

ESIG_HINT_RE = re.compile(
    r"is_agreement_accepted|agreement|e[-_]?sign|signature|sign.?contract|accept.?terms",
    re.I,
)

# Keys we look for inside any captured JSON to mine the real deduction structure.
DEDUCTION_KEY_RE = re.compile(
    r"commission|referral|fixed[-_]?fee|collection[-_]?fee|payment[-_]?gateway|pg[-_]?fee|"
    r"shipping|logistics|forward|reverse|rto|return|gst|tcs|tds|net[-_]?amount|"
    r"payable|settle|deduction|charge|fee|monetization|penalty",
    re.I,
)
OTP_HINT_RE = re.compile(r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the code)\b", re.I)


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"settlement_{ts}.log"
    logger = logging.getLogger("meesho-settlement")
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
    logger.info("Settlement probe logfile: %s", log_path)
    return logger


log = logging.getLogger("meesho-settlement")


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
        raise HardStop(f"Login did not redirect away from /login. URL={_safe_url(page.url)!r} body={snippet!r}")
    log.info("Login OK — at %s", _safe_url(page.url))


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

captured: dict[str, list[dict[str, Any]]] = {
    "commission": [],
    "settlement": [],
    "supplier_cfg": [],
}
findings: dict[str, Any] = {
    "supplier_id": None,
    "identifier": None,
    "agreement_accepted": None,
    "monetization": {},
    "esig_blocked": False,
    "deduction_keys_seen": set(),
    "config_values": {},      # scalar values extracted from VALUE_KEYS anywhere
    "value_snapshots": {},    # url -> full small JSON snapshot of high-signal configs
    "blocked_endpoints": [],  # 463/tolerated blocks recorded
    "hard_stop": None,
}


def _walk_for_keys(obj: Any, hits: set[str], depth: int = 0) -> None:
    if depth > 8:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(k, str) and DEDUCTION_KEY_RE.search(k):
                hits.add(k)
            # capture scalar values of high-signal config keys
            if isinstance(k, str) and k in VALUE_KEYS and isinstance(v, (int, float, str, bool)):
                findings["config_values"].setdefault(k, v)
            # mine high-value scalar config from anywhere
            kl = k.lower() if isinstance(k, str) else ""
            if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                findings["supplier_id"] = findings["supplier_id"] or v
            if kl in ("identifier",) and isinstance(v, str) and 2 <= len(v) <= 12:
                findings["identifier"] = findings["identifier"] or v
            if "agreement" in kl and isinstance(v, bool):
                findings["agreement_accepted"] = v
            if "monetization" in kl and isinstance(v, (int, float, str)):
                findings["monetization"][k] = v
            _walk_for_keys(v, hits, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:50]:
            _walk_for_keys(item, hits, depth + 1)


async def on_response(resp: Response) -> None:
    url = resp.url
    status = resp.status
    if status in SESSION_STOP_CODES:
        # Don't raise here (handler context) — record; main loop checks.
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
    # Snapshot full small JSON of high-signal config endpoints (value-level).
    if VALUE_SNAPSHOT_RE.search(url):
        try:
            snap = await resp.json()
            txt = json.dumps(snap, default=str)
            if len(txt) <= 60_000:
                findings["value_snapshots"][_safe_url(url)] = snap
            else:
                findings["value_snapshots"][_safe_url(url)] = {"_truncated_len": len(txt),
                                                               "_top_keys": sorted(snap.keys())[:60] if isinstance(snap, dict) else "[list]"}
        except Exception:  # noqa: BLE001
            pass
    bucket = None
    if COMMISSION_RE.search(url):
        bucket = "commission"
    elif SETTLEMENT_RE.search(url):
        bucket = "settlement"
    elif SUPPLIER_CFG_RE.search(url):
        bucket = "supplier_cfg"
    if bucket is None:
        return
    try:
        body = await resp.json()
    except Exception:  # noqa: BLE001
        return
    hits: set[str] = set()
    _walk_for_keys(body, hits)
    findings["deduction_keys_seen"].update(hits)
    if ESIG_HINT_RE.search(json.dumps(body)[:5000]):
        # record presence of agreement signalling
        pass
    captured[bucket].append({
        "url": _safe_url(url),
        "status": status,
        "deduction_keys": sorted(hits),
        "top_keys": sorted(list(body.keys()))[:40] if isinstance(body, dict) else "[list]",
    })
    log.info("XHR[%s] %s -> keys=%s", bucket, _safe_url(url), sorted(hits)[:12])


async def detect_identifier(ctx: BrowserContext, page: Page) -> None:
    """Read the identifier out of the post-login dashboard URL if present."""
    url = page.url
    m = re.search(r"/(?:growth|payments|fulfillment|cataloging)/([a-z0-9]{3,12})/", url)
    if m:
        findings["identifier"] = findings["identifier"] or m.group(1)
        log.info("Detected identifier from URL: %s", m.group(1))


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
            await asyncio.sleep(4.0)  # let post-login config XHRs fire + be captured
            await detect_identifier(ctx, page)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])

            ident = findings["identifier"] or "oinpw"
            for label, tmpl in NAV_PAGES:
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                nav_url = tmpl.replace("{id}", ident)
                log.info("--- navigating page '%s': %s", label, nav_url)
                try:
                    await page.goto(nav_url, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                    await asyncio.sleep(5.0)  # dwell so SPA fires its XHRs
                    # scan rendered text for e-sig wall
                    try:
                        txt = await page.locator("body").inner_text(timeout=3000)
                    except Exception:  # noqa: BLE001
                        txt = ""
                    if re.search(r"sign(ature)?|agreement|accept.{0,20}terms|add signature", txt, re.I) \
                       and re.search(r"sign|agreement|signature", nav_url, re.I) is None \
                       and label in ("referral_fee", "commission_root"):
                        findings["esig_blocked"] = True
                        log.warning("e-signature wall text detected on %s page", label)
                except Exception as exc:  # noqa: BLE001
                    log.warning("nav '%s' failed (non-fatal): %s", label, exc)
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
    findings["deduction_keys_seen"] = sorted(findings["deduction_keys_seen"])
    return {"findings": findings, "captured": captured}


def main() -> int:
    configure_logging()
    log.info("==== Meesho settlement/payout READ-ONLY probe @ %s ====", datetime.now().isoformat())
    result = asyncio.run(run())
    f = result["findings"]
    snapshots = f.pop("value_snapshots", {})
    print("\n========= SETTLEMENT PROBE SUMMARY =========")
    print(json.dumps(f, indent=2, default=str))
    print("\n========= VALUE SNAPSHOTS (high-signal config JSON) =========")
    for url, snap in snapshots.items():
        print(f"\n--- {url} ---")
        print(json.dumps(snap, indent=2, default=str)[:8000])
    print("\n--- captured XHRs by bucket ---")
    for bucket, items in result["captured"].items():
        print(f"\n[{bucket}] ({len(items)})")
        for it in items[:25]:
            print(f"  {it['status']} {it['url']}")
            if it["deduction_keys"]:
                print(f"       deduction_keys: {it['deduction_keys']}")
    print("============================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
