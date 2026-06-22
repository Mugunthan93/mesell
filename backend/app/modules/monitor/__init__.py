"""``monitor`` — category change monitor backend module (Wave 2 Unit C).

Owner specialist: ``meesell-services-builder`` (the dedupe-gate Celery task
+ gate orchestration). Part of the category change monitor feature
(``feature/category-monitor``).

Seam (Wave boundary — HARD)
---------------------------
This module owns ONLY the Wave-2 Unit-C **dedupe gate → scrape → diff →
STORE VERDICT** slice:

  - ``tasks.py``      — thin synchronous Celery wrapper (``monitor.scrape_category``)
  - ``service.py``    — the three-guard gate orchestration (TTL reuse,
                        atomic in-flight claim, scrape + diff)
  - ``repository.py`` — PRIVATE DB reads (latest/prior snapshot, category
                        scrape inputs)
  - ``exceptions.py`` — ``CategoryNotFoundError``

It consumes two LIVE Wave-2 contracts:
  - ``scripts.scrape_category.scrape_category`` (Unit A — live-Meesho path;
    MOCKED in every test, live scrape gated on agreement + creds)
  - ``scripts.diff_category_rules.diff_category_snapshot`` (Unit B — pure
    stdlib diff engine)

and the Wave-1 ORM model ``app.shared.models.category_snapshot.CategorySnapshot``.

DELIBERATELY OUT OF SCOPE (Wave 4, NOT built here):
  - fan-out to subscribers / ``category_subscription`` reads
  - notification-table writes
  - catalog flag updates
On a BLOCK verdict the gate logs a WARNING and STOPS — it never fans out.
"""

from __future__ import annotations

from app.modules.monitor.exceptions import CategoryNotFoundError

__all__ = [
    "CategoryNotFoundError",
]
