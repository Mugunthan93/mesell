"""Meesho CATALOG EDIT / CREATE commission probe — STRICTLY READ-ONLY.

Goal (founder-redirected commission source, round 3)
----------------------------------------------------
The e-signature wall blocks the referral-fee rate-card AND the per-order
settlement breakdown (rounds 1-2). The founder confirms commission IS exposed
in TWO other surfaces that do NOT require the e-signature:

  1. The catalog EDIT view DISPLAYS the commission for that product.
  2. The catalog CREATE flow shows HOW commission works (a live commission /
     estimated-payout preview as the seller sets the Meesho Price).

This probe:
  A. Logs in (proven authenticated-WebKit + Akamai-bypass idiom, verbatim from
     meesho_settlement_probe.py).
  B. Loads the catalog LISTING, harvests catalog/product ids from the catalog
     listing XHR (NOT guessed — intercepted).
  C. Opens the EDIT view for several products spanning categories/price points,
     intercepts EVERY XHR, and ALSO scrapes the rendered DOM for any commission
     %/₹ shown — capturing commission alongside that product's category +
     Meesho Price.
  D. Enters the CREATE flow ONLY to OBSERVE the commission/estimated-payout
     widget + its endpoint. It NEVER fills a real listing and NEVER submits.

ABSOLUTE GUARDRAIL — ZERO WRITES
--------------------------------
  * READ-ONLY. Navigation + response interception + DOM text reads ONLY.
  * NEVER click Save / Update / Submit / Publish / Confirm / Next-that-persists.
    The script issues ZERO clicks on any mutating control. On the edit view it
    only READS; on the create flow it only OBSERVES the first price-input step.
  * If commission only appears AFTER a submit, STOP before submitting and
    report that fact. Do not submit to reveal it.
  * Hard-stop on OTP / 401 / 403 / 429. 463 tolerated per-URL (recorded).
  * Never log credential values.

Output
------
  * logs/scraper/catalog_commission_<ts>.log (gitignored)
  * stdout JSON summary: agreement state, catalogs discovered (id/name/category/
    price), commission read per product (% and/or ₹), the edit-page commission
    XHR endpoint + response shape, create-flow payout widget observations.
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

SESSION_STOP_CODES = {401, 403, 429}
TOLERATED_BLOCK_CODES = {463}

# How many edit views to open (spaced, paced). Keep small to respect Akamai.
MAX_EDIT_VIEWS = 6

# Candidate catalog-listing pages (read-only). {id} = supplier identifier.
LISTING_PAGES: list[tuple[str, str]] = [
    ("catalogs_root", "https://supplier.meesho.com/panel/v3/new/cataloging/{id}/catalogs"),
    ("catalogs_alt", "https://supplier.meesho.com/panel/v3/new/root/catalogs"),
    ("products_root", "https://supplier.meesho.com/panel/v3/new/cataloging/{id}/products"),
    ("home", "https://supplier.meesho.com/panel/v3/new/growth/{id}/home"),
]
# Candidate create-flow entry points (OBSERVE only — never submit).
CREATE_PAGES: list[tuple[str, str]] = [
    ("create_single", "https://supplier.meesho.com/panel/v3/new/cataloging/{id}/catalog-upload/single"),
    ("create_root", "https://supplier.meesho.com/panel/v3/new/cataloging/{id}/add-catalog"),
    ("create_alt", "https://supplier.meesho.com/panel/v3/new/cataloging/{id}/catalogs/add"),
]

# XHR classifiers.
CATALOG_LIST_RE = re.compile(
    r"catalog|product|sku|listing|inventory|fetch[-_]?catalog|get[-_]?catalog", re.I)
COMMISSION_RE = re.compile(
    r"commission|referral[-_]?fee|monetization|rate[-_]?card|charge|"
    r"payout|earning|net[-_]?amount|settlement|price[-_]?breakup|fee[-_]?breakup|"
    r"estimate|deduction", re.I)
SUPPLIER_CFG_RE = re.compile(r"supplier|config|agreement|signature|registration", re.I)

VALUE_SNAPSHOT_RE = re.compile(
    r"prefetch-supply-data|supplier/config|fetch-registration-status|"
    r"commission|referral|monetization|payout|price[-_]?breakup|fee[-_]?breakup|"
    r"catalog.*detail|product.*detail|estimate|"
    r"fetch-supplier-products|smart-pricing-products|fetchBulkCatalogsListV2",
    re.I,
)
VALUE_KEYS = {
    "default_monetization_percent", "default_monetization_type", "mall_commission_rate",
    "is_agreement_accepted", "agreement_accepted", "supplier_id", "identifier",
    "shipping_charges", "shipping_bracket", "logistic_fee_enabled",
}
# Commission/payout-bearing keys mined from any JSON.
COMMISSION_KEY_RE = re.compile(
    r"commission|referral|monetization|payout|net[-_]?amount|payable|earning|"
    r"net[-_]?margin|net[-_]?price|fee|charge|deduction|settle|rate", re.I)
# Price-bearing keys (to pair commission with the product's Meesho price).
PRICE_KEY_RE = re.compile(
    r"price|mrp|cost|amount|selling|listing[-_]?price|meesho[-_]?price|"
    r"transfer[-_]?price|net[-_]?rate|wrong[-_]?defective", re.I)
# Category-bearing keys.
CATEGORY_KEY_RE = re.compile(r"category|sub[-_]?category|sscat|catalog[-_]?type|product[-_]?type", re.I)

OTP_HINT_RE = re.compile(r"\b(otp|one[-\s]?time\s?password|verify your (mobile|number)|enter the code)\b", re.I)
# Commission shown in DOM text, e.g. "Commission 4%", "Commission: ₹12", "4% commission".
DOM_COMMISSION_RE = re.compile(
    r"(commission|referral fee|you(?:'ll| will) (?:get|receive|earn)|net (?:amount|payout|earning))"
    r"[^0-9₹%]{0,30}(₹\s?\d[\d,]*\.?\d*|\d{1,3}(?:\.\d+)?\s?%)",
    re.I)
DOM_PRICE_RE = re.compile(r"(meesho price|selling price|listed price|price)[^0-9₹]{0,20}(₹\s?\d[\d,]*\.?\d*)", re.I)


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = LOG_DIR / f"catalog_commission_{ts}.log"
    logger = logging.getLogger("meesho-catalog-commission")
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
    logger.info("Catalog-commission probe logfile: %s", log_path)
    return logger


log = logging.getLogger("meesho-catalog-commission")


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
# Capture state
# ---------------------------------------------------------------------------

captured: dict[str, list[dict[str, Any]]] = {
    "catalog_list": [],
    "commission": [],
    "supplier_cfg": [],
}
findings: dict[str, Any] = {
    "supplier_id": None,
    "identifier": None,
    "agreement_accepted": None,
    "monetization": {},
    "config_values": {},
    "catalogs": [],            # [{id, name, category, price, raw_keys}]
    "edit_commission_reads": [],   # [{product_id, category, meesho_price, commission_pct, commission_rupees, source}]
    "edit_commission_xhrs": [],    # [{url, status, top_keys, commission_keys, price_keys, category_keys, sample}]
    "create_widget": {            # what the create flow exposed
        "reached": False,
        "page": None,
        "commission_xhrs": [],
        "dom_commission_hits": [],
        "notes": [],
    },
    "value_snapshots": {},
    "blocked_endpoints": [],
    "hard_stop": None,
}

# Toggle: when navigating the create flow, tag commission XHRs into the widget bucket.
_mode = {"phase": "listing"}  # listing | edit | create


def _walk_extract(obj: Any, out: dict[str, Any], depth: int = 0) -> None:
    """Mine commission/price/category scalars + high-signal config from any JSON."""
    if depth > 9:
        return
    if isinstance(obj, dict):
        for k, v in obj.items():
            kl = k.lower() if isinstance(k, str) else ""
            if isinstance(k, str):
                if COMMISSION_KEY_RE.search(k) and isinstance(v, (int, float, str)):
                    out.setdefault("commission", {}).setdefault(k, v)
                if PRICE_KEY_RE.search(k) and isinstance(v, (int, float, str)):
                    out.setdefault("price", {}).setdefault(k, v)
                if CATEGORY_KEY_RE.search(k) and isinstance(v, (str, int)):
                    out.setdefault("category", {}).setdefault(k, v)
                if k in VALUE_KEYS and isinstance(v, (int, float, str, bool)):
                    findings["config_values"].setdefault(k, v)
                if kl in ("supplier_id", "supplierid") and isinstance(v, (int, str)):
                    findings["supplier_id"] = findings["supplier_id"] or v
                if "agreement" in kl and isinstance(v, bool):
                    findings["agreement_accepted"] = v
                if "monetization" in kl and isinstance(v, (int, float, str)):
                    findings["monetization"][k] = v
            _walk_extract(v, out, depth + 1)
    elif isinstance(obj, list):
        for item in obj[:80]:
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

    if VALUE_SNAPSHOT_RE.search(url):
        try:
            snap = await resp.json()
            txt = json.dumps(snap, default=str)
            if len(txt) <= 80_000:
                findings["value_snapshots"][_safe_url(url)] = snap
            else:
                findings["value_snapshots"][_safe_url(url)] = {
                    "_truncated_len": len(txt),
                    "_top_keys": sorted(snap.keys())[:60] if isinstance(snap, dict) else "[list]",
                }
        except Exception:  # noqa: BLE001
            pass

    bucket = None
    if COMMISSION_RE.search(url):
        bucket = "commission"
    elif CATALOG_LIST_RE.search(url):
        bucket = "catalog_list"
    elif SUPPLIER_CFG_RE.search(url):
        bucket = "supplier_cfg"
    if bucket is None:
        return
    try:
        body = await resp.json()
    except Exception:  # noqa: BLE001
        return

    mined: dict[str, Any] = {}
    _walk_extract(body, mined)
    record = {
        "url": _safe_url(url),
        "status": status,
        "phase": _mode["phase"],
        "top_keys": sorted(list(body.keys()))[:40] if isinstance(body, dict) else "[list]",
        "commission_keys": sorted((mined.get("commission") or {}).keys()),
        "price_keys": sorted((mined.get("price") or {}).keys()),
        "category_keys": sorted((mined.get("category") or {}).keys()),
        "commission_sample": dict(list((mined.get("commission") or {}).items())[:10]),
        "price_sample": dict(list((mined.get("price") or {}).items())[:10]),
        "category_sample": dict(list((mined.get("category") or {}).items())[:10]),
    }
    captured[bucket].append(record)
    if bucket == "commission":
        if _mode["phase"] == "create":
            findings["create_widget"]["commission_xhrs"].append(record)
        else:
            findings["edit_commission_xhrs"].append(record)
        log.info("COMMISSION XHR [%s] %s comm=%s price=%s",
                 _mode["phase"], _safe_url(url), record["commission_keys"], record["price_keys"])
    else:
        log.info("XHR[%s/%s] %s comm=%s", bucket, _mode["phase"], _safe_url(url),
                 record["commission_keys"][:6])


def detect_identifier_from_url(url: str) -> None:
    m = re.search(r"/(?:growth|payments|fulfillment|cataloging)/([a-z0-9]{3,12})/", url)
    if m:
        findings["identifier"] = findings["identifier"] or m.group(1)


async def read_dom_commission(page: Page, label: str) -> dict[str, Any]:
    """Scrape rendered text for commission %/₹ and price (read-only)."""
    out: dict[str, Any] = {"commission_hits": [], "price_hits": []}
    try:
        txt = await page.locator("body").inner_text(timeout=4000)
    except Exception:  # noqa: BLE001
        return out
    for m in DOM_COMMISSION_RE.finditer(txt):
        out["commission_hits"].append(m.group(0).strip()[:80])
    for m in DOM_PRICE_RE.finditer(txt):
        out["price_hits"].append(m.group(0).strip()[:80])
    # e-sig / OTP wall detection
    if OTP_HINT_RE.search(txt):
        raise HardStop(f"OTP_REQUIRED — detected on {label}")
    out["esig_wall"] = bool(re.search(r"add signature|e-?signature|sign(?:ature)? is missing|accept.{0,20}agreement", txt, re.I))
    return out


async def harvest_catalog_ids(page: Page) -> list[str]:
    """Pull product/catalog ids from the catalog_list XHRs already captured + DOM links."""
    ids: list[str] = []
    # From intercepted catalog-list bodies' price/category-bearing records we don't keep raw ids,
    # so read product links from the DOM (anchors to edit/detail pages).
    try:
        hrefs = await page.locator("a").evaluate_all(
            "els => els.map(e => e.getAttribute('href')).filter(Boolean)")
    except Exception:  # noqa: BLE001
        hrefs = []
    for h in hrefs:
        m = re.search(r"(?:catalog|product|edit)[/=-]([0-9]{4,})", h or "")
        if m:
            ids.append(m.group(1))
    # de-dup preserve order
    seen: set[str] = set()
    uniq = [i for i in ids if not (i in seen or seen.add(i))]
    findings["catalogs"] = [{"id": i, "edit_href_seen": True} for i in uniq[:30]]
    return uniq


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
            await asyncio.sleep(4.0)
            detect_identifier_from_url(page.url)
            if findings["hard_stop"]:
                raise HardStop(findings["hard_stop"])
            ident = findings["identifier"] or "kdwec"
            log.info("Using identifier=%s", ident)

            # ---- Phase 1: catalog LISTING (find products to edit) ----
            _mode["phase"] = "listing"
            catalog_ids: list[str] = []
            edit_url_template: str | None = None
            for label, tmpl in LISTING_PAGES:
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                nav = tmpl.replace("{id}", ident)
                log.info("--- listing nav '%s': %s", label, nav)
                try:
                    await page.goto(nav, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                    await asyncio.sleep(6.0)
                    dom = await read_dom_commission(page, label)
                    ids = await harvest_catalog_ids(page)
                    if ids:
                        catalog_ids = ids
                        # remember an edit url pattern derived from a real anchor if present
                        try:
                            hrefs = await page.locator("a").evaluate_all(
                                "els => els.map(e => e.getAttribute('href')).filter(Boolean)")
                        except Exception:  # noqa: BLE001
                            hrefs = []
                        for h in hrefs:
                            if re.search(r"(?:catalog|product|edit)[/=-][0-9]{4,}", h or ""):
                                edit_url_template = h if h.startswith("http") else \
                                    "https://supplier.meesho.com" + (h if h.startswith("/") else "/" + h)
                                break
                        log.info("Found %d candidate product ids on '%s'", len(ids), label)
                        break
                except Exception as exc:  # noqa: BLE001
                    log.warning("listing nav '%s' failed (non-fatal): %s", label, exc)
                await asyncio.sleep(3.0)

            # ---- Phase 2: EDIT views (READ commission, never save) ----
            _mode["phase"] = "edit"
            if edit_url_template:
                # Build per-id edit URLs by substituting the id portion.
                base_id_match = re.search(r"(?:catalog|product|edit)([/=-])([0-9]{4,})", edit_url_template)
                for pid in catalog_ids[:MAX_EDIT_VIEWS]:
                    if findings["hard_stop"]:
                        raise HardStop(findings["hard_stop"])
                    if base_id_match:
                        sep = base_id_match.group(1)
                        old = base_id_match.group(0)
                        new = old.replace(base_id_match.group(2), pid)
                        edit_nav = edit_url_template.replace(old, new)
                    else:
                        edit_nav = edit_url_template
                    log.info("--- EDIT view product %s: %s", pid, _safe_url(edit_nav))
                    try:
                        await page.goto(edit_nav, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                        await asyncio.sleep(6.0)  # dwell for detail XHRs (commission)
                        dom = await read_dom_commission(page, f"edit:{pid}")
                        if dom["commission_hits"] or dom["price_hits"]:
                            findings["edit_commission_reads"].append({
                                "product_id": pid,
                                "dom_commission": dom["commission_hits"],
                                "dom_price": dom["price_hits"],
                                "source": "dom_text",
                            })
                            log.info("EDIT %s DOM commission=%s price=%s", pid,
                                     dom["commission_hits"], dom["price_hits"])
                    except Exception as exc:  # noqa: BLE001
                        log.warning("edit nav %s failed (non-fatal): %s", pid, exc)
                    await asyncio.sleep(4.0)  # pace between edit views
            else:
                findings["create_widget"]["notes"].append(
                    "No edit-url anchor pattern discovered from listing DOM; "
                    "edit views not opened by direct URL.")
                log.warning("No edit URL template discovered — skipping direct edit-view opens")

            # ---- Phase 3: CREATE flow (OBSERVE only, never submit) ----
            _mode["phase"] = "create"
            for label, tmpl in CREATE_PAGES:
                if findings["hard_stop"]:
                    raise HardStop(findings["hard_stop"])
                nav = tmpl.replace("{id}", ident)
                log.info("--- CREATE flow nav '%s': %s", label, nav)
                try:
                    await page.goto(nav, wait_until="domcontentloaded", timeout=LOGIN_NAV_TIMEOUT_MS)
                    await asyncio.sleep(6.0)
                    dom = await read_dom_commission(page, f"create:{label}")
                    findings["create_widget"]["reached"] = True
                    findings["create_widget"]["page"] = _safe_url(nav)
                    if dom["commission_hits"]:
                        findings["create_widget"]["dom_commission_hits"].extend(dom["commission_hits"])
                    if dom.get("esig_wall"):
                        findings["create_widget"]["notes"].append(f"e-sig wall text on {label}")
                    # NOTE: we deliberately do NOT type a price or click Next/Submit.
                    # If commission only appears after entering price+submit, that is
                    # reported as a limitation rather than triggered.
                    log.info("CREATE '%s' dom_commission=%s esig=%s", label,
                             dom["commission_hits"], dom.get("esig_wall"))
                    break  # one create entry point is enough to observe
                except Exception as exc:  # noqa: BLE001
                    log.warning("create nav '%s' failed (non-fatal): %s", label, exc)
                await asyncio.sleep(3.0)

            # ---- Re-check agreement state from snapshots ----
            for url, snap in findings["value_snapshots"].items():
                tmp: dict[str, Any] = {}
                _walk_extract(snap, tmp)

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
    return {"findings": findings, "captured": captured}


def main() -> int:
    configure_logging()
    log.info("==== Meesho CATALOG EDIT/CREATE commission READ-ONLY probe @ %s ====",
             datetime.now().isoformat())
    result = asyncio.run(run())
    f = result["findings"]
    snapshots = f.pop("value_snapshots", {})
    print("\n========= CATALOG COMMISSION PROBE SUMMARY =========")
    print(json.dumps(f, indent=2, default=str))
    print("\n========= VALUE SNAPSHOTS (high-signal config JSON, truncated) =========")
    for url, snap in list(snapshots.items())[:20]:
        print(f"\n--- {url} ---")
        print(json.dumps(snap, indent=2, default=str)[:6000])
    print("\n--- captured XHRs by bucket ---")
    for bucket, items in result["captured"].items():
        print(f"\n[{bucket}] ({len(items)})")
        for it in items[:30]:
            print(f"  {it['status']} [{it['phase']}] {it['url']}")
            if it.get("commission_keys"):
                print(f"       commission_keys: {it['commission_keys']}  sample={it['commission_sample']}")
            if it.get("price_keys"):
                print(f"       price_keys: {it['price_keys']}  sample={it['price_sample']}")
    print("===================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
