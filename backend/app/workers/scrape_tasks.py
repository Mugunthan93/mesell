"""Celery tasks for Meesho competitive-research scraping."""

import asyncio
import logging

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_scrape(url: str, max_items: int, endpoint_hint: str | None) -> dict:
    from app.services.meesho_scraper import (
        MeeshoBlockedError,
        MeeshoScraperError,
        MeeshoScraper,
        ScrapeConfig,
    )

    cfg = ScrapeConfig(max_items=max_items)
    if endpoint_hint:
        cfg.endpoint_hint = endpoint_hint
    scraper = MeeshoScraper(cfg)

    rows = await scraper.scrape(url)
    return {"url": url, "count": len(rows), "products": rows}


@celery_app.task(name="meesho.scrape_search", bind=True, max_retries=2)
def scrape_search(self, url: str, max_items: int = 100,
                  endpoint_hint: str | None = None) -> dict:
    """Scrape a Meesho search/category URL for competitive research.

    Retries with exponential-ish backoff on transient errors; on a hard
    bot-block (MeeshoBlockedError) it gives up immediately rather than
    hammering the target.
    """
    from app.services.meesho_scraper import MeeshoBlockedError, MeeshoScraperError

    try:
        return asyncio.run(_run_scrape(url, max_items, endpoint_hint))
    except MeeshoBlockedError as exc:
        logger.warning(f"meesho.scrape_search blocked for {url}: {exc}")
        return {"url": url, "count": 0, "products": [], "blocked": True,
                "reason": str(exc)}
    except MeeshoScraperError as exc:
        logger.error(f"meesho.scrape_search no data for {url}: {exc}")
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))
    except Exception as exc:
        logger.exception(f"meesho.scrape_search({url}) failed: {exc}")
        raise self.retry(exc=exc, countdown=30 * (self.request.retries + 1))


async def _run_discover(url: str) -> dict:
    from app.services.meesho_scraper import MeeshoScraper

    candidates = await MeeshoScraper().discover(url)
    # strip large samples to URLs + methods for a compact, loggable result
    return {
        "url": url,
        "candidates": [{"url": c["url"], "method": c["method"]} for c in candidates],
    }


@celery_app.task(name="meesho.discover")
def discover(url: str) -> dict:
    """One-off reconnaissance to refresh the catalog endpoint hint."""
    return asyncio.run(_run_discover(url))
