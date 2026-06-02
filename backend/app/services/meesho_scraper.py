"""Meesho catalog scraper for competitive price/listing research.

Strategy (see two-stage pipeline):
  1. Reconnaissance: intercept the JSON/XHR responses the SPA fires and
     identify the catalog endpoint at runtime. Endpoints, params and field
     names are NOT hardcoded because Meesho changes them frequently.
  2. Production: drive the page, scroll to trigger pagination, and harvest
     the intercepted JSON, normalising defensively.

Responsible-use guards are built in: India-locale context, jittered rate
limiting, heavy-resource blocking, and a hard stop on bot-block signals
(403/429/challenge). This scraper does NOT bypass authentication or defeat
anti-bot protection — on a hard block it raises ``MeeshoBlockedError`` and the
caller is expected to back off, not escalate. Honour robots.txt and Meesho's
Terms of Use before running, and never collect PII.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Mobile India browser context — Meesho is mobile-first.
_MOBILE_UA = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36"
)

# Defensive field-name candidates — the normaliser tries these in order and
# also keeps the raw record, so a Meesho schema change degrades instead of
# breaking. Confirm/extend from a discovery run (``MeeshoScraper.discover``).
_FIELD_CANDIDATES = {
    "id": ("product_id", "catalog_id", "id", "pid"),
    "name": ("name", "product_name", "display_name", "title"),
    "price": ("price", "selling_price", "min_product_price", "offer_price"),
    "mrp": ("mrp", "original_price", "market_price", "max_product_price"),
    "rating": ("rating", "average_rating", "product_rating"),
    "rating_count": ("rating_count", "num_ratings", "rating_count_str"),
    "shop": ("shop_name", "supplier_name", "seller_name"),
    "image": ("image", "image_url", "primary_image", "thumbnail"),
    "url": ("product_url", "url", "share_url", "slug"),
}


class MeeshoBlockedError(RuntimeError):
    """Raised on a hard bot-block signal so the caller can back off and halt."""


class MeeshoScraperError(RuntimeError):
    """Raised when no usable data could be extracted (not a block)."""


@dataclass
class ScrapeConfig:
    max_items: int = 100
    max_scrolls: int = 20
    headless: bool = True
    proxy: dict | None = None
    base_delay_s: float = 2.5          # jitter added on top, per scroll
    nav_timeout_ms: int = 30_000
    # substring used to recognise the catalog XHR; refine after discovery
    endpoint_hint: str = "/api/"
    block_status: tuple[int, ...] = (403, 429, 503)
    block_markers: tuple[str, ...] = ("captcha", "are you a human", "access denied")


def _jitter(base: float) -> float:
    return base + random.uniform(0.0, 2.0)


def _first(record: dict, keys: tuple[str, ...]):
    for k in keys:
        if k in record and record[k] not in (None, ""):
            return record[k]
    return None


def _normalise(record: dict) -> dict:
    out = {field: _first(record, keys) for field, keys in _FIELD_CANDIDATES.items()}
    out["_raw"] = record
    return out


class MeeshoScraper:
    """Stateless service; one instance is reused across tasks."""

    def __init__(self, config: ScrapeConfig | None = None) -> None:
        self.config = config or ScrapeConfig()

    # -- Stage A: discovery -------------------------------------------------
    async def discover(self, url: str) -> list[dict]:
        """Return candidate JSON responses so the agent can identify the
        catalog endpoint, its params and its field names. Run this once when
        Meesho's structure changes; feed findings back into ScrapeConfig and
        _FIELD_CANDIDATES."""
        from playwright.async_api import async_playwright

        candidates: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.config.headless)
            ctx = await self._context(browser)

            async def on_response(resp):
                if "application/json" not in resp.headers.get("content-type", ""):
                    return
                try:
                    data = await resp.json()
                except Exception:
                    return
                blob = json.dumps(data)[:2000].lower()
                if any(k in blob for k in ("price", "product", "catalog")):
                    candidates.append(
                        {"url": resp.url, "method": resp.request.method, "sample": data}
                    )

            ctx.on("response", on_response)
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded",
                            timeout=self.config.nav_timeout_ms)
            await page.wait_for_timeout(4000)
            await page.mouse.wheel(0, 6000)
            await page.wait_for_timeout(3000)
            await browser.close()
        return candidates

    # -- Stage B: scroll + intercept (robust default) -----------------------
    async def scrape(self, url: str) -> list[dict]:
        from playwright.async_api import async_playwright

        cfg = self.config
        collected: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=cfg.headless)
            ctx = await self._context(browser)
            await self._block_heavy(ctx)

            async def on_response(resp):
                if resp.status in cfg.block_status:
                    raise MeeshoBlockedError(f"HTTP {resp.status} from {resp.url}")
                if cfg.endpoint_hint not in resp.url:
                    return
                if "application/json" not in resp.headers.get("content-type", ""):
                    return
                try:
                    data = await resp.json()
                except Exception:
                    return
                for item in _extract_records(data):
                    collected.append(item)

            ctx.on("response", on_response)
            page = await ctx.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded",
                                timeout=cfg.nav_timeout_ms)
            except MeeshoBlockedError:
                await browser.close()
                raise

            await self._assert_not_challenged(page)

            last_count, scrolls = -1, 0
            while len(collected) < cfg.max_items and scrolls < cfg.max_scrolls:
                await page.mouse.wheel(0, 8000)
                await page.wait_for_timeout(int(_jitter(cfg.base_delay_s) * 1000))
                scrolls += 1
                if len(collected) == last_count:   # no growth -> end or throttle
                    break
                last_count = len(collected)

            await browser.close()

        if not collected:
            raise MeeshoScraperError(
                "No records intercepted — run discover() to refresh endpoint_hint "
                "and field candidates."
            )

        # de-dupe + normalise + trim
        seen, rows = set(), []
        for rec in collected:
            norm = _normalise(rec)
            key = norm["id"] or norm["url"] or json.dumps(rec, sort_keys=True)[:64]
            if key in seen:
                continue
            seen.add(key)
            rows.append(norm)
            if len(rows) >= cfg.max_items:
                break
        return rows

    # -- helpers ------------------------------------------------------------
    async def _context(self, browser):
        return await browser.new_context(
            locale="en-IN",
            timezone_id="Asia/Kolkata",
            viewport={"width": 412, "height": 915},
            device_scale_factor=2.625,
            is_mobile=True,
            has_touch=True,
            user_agent=_MOBILE_UA,
            extra_http_headers={"Accept-Language": "en-IN,en;q=0.9"},
            proxy=self.config.proxy,
        )

    async def _block_heavy(self, ctx) -> None:
        async def handler(route):
            if route.request.resource_type in {"image", "media", "font"}:
                await route.abort()
            else:
                await route.continue_()
        await ctx.route("**/*", handler)

    async def _assert_not_challenged(self, page) -> None:
        body = (await page.content())[:5000].lower()
        if any(m in body for m in self.config.block_markers):
            raise MeeshoBlockedError("Challenge/captcha page detected — halting.")


def _extract_records(data) -> list[dict]:
    """Find the first list-of-dicts inside an arbitrary JSON payload."""
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return value
            if isinstance(value, dict):
                found = _extract_records(value)
                if found:
                    return found
    return []


_scraper: MeeshoScraper | None = None


def get_meesho_scraper() -> MeeshoScraper:
    global _scraper
    if _scraper is None:
        _scraper = MeeshoScraper()
    return _scraper
