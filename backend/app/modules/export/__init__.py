"""``export`` module — Meesho XLSX export per §14.

V1 surface:
* ``service.initiate_export`` (POST /products/{id}/export-xlsx) — 6-step
  request flow per §14.B.1.
* ``service.get_export`` (GET /exports/{id}) — 4-step polling flow per
  §14.B.2.
* ``tasks.export_xlsx_task`` (Celery worker; task name ``"export.xlsx"``)
  — the 9-step Export Adapter pipeline per §14.E.

This module is **the most-cross-module module in the codebase** per the
§2.D matrix — it CONSUMES catalog / customer / category / image via their
service surfaces, but NO other module imports from
``app.modules.export.*``.  Cross-module reads of export status (V1.5
dashboard elevation) will go through ``service.summary``.

Philosophy M10 enforcement (§14.J)
----------------------------------
The three symbols ``meesho_column_header``, ``meesho_column_index`` and
``enum_codes_map`` exist ONLY inside this subtree (plus
``adapters/gcs.py`` write paths).  §19 import-linter contract 9 (AST
scanner) is the structural enforcement.

The ``export_router`` symbol (added by the parallel api-routes-builder
dispatch — POST + GET handlers in ``router.py``) is re-exported here for
``app/main.py`` to mount with ``app.include_router(export_router)``.
"""

from app.modules.export.router import router as export_router

__all__ = ["export_router"]
