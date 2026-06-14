"""svc-category — standalone category tree + Smart Picker + schema microservice.

Extracted from the monolith ``app.modules.category`` subtree per
``docs/plans/microservices_migration/SUB_PLAN_0F_category_extraction.md`` +
backend-coordinator ``spec_msF_backend.md``.

The pipeline logic (``service.py`` / ``picker.py`` / ``repository.py`` /
``domain.py`` / ``exceptions.py``) is preserved BYTE-FOR-BYTE from the
monolith per BACKEND_ARCHITECTURE.md §16.G (call-site preservation —
ABSOLUTE).  The ONLY changes are import lines: the intra-module paths
``app.modules.category.{picker,repository,domain,exceptions}`` are mechanically
flattened to ``app.{picker,repository,domain,exceptions}``.  The ai_ops import
strings are UNCHANGED (``from app.ai_ops import client as ai_client``;
``call_gemini(ctx, "smart_picker.v1", ...)``) — the package is VENDORED, the
import path is identical (§16.G).  ``picker.py`` / ``domain.py`` /
``exceptions.py`` travel byte-identical (zero import rewires).

VENDORED (byte-identical copies):
  * ``app.ai_ops.*`` — TRIMMED to the smart_picker path (client, budget_cap,
    cost_tracker, guardrail, prompt_registry, eval + ONLY
    prompts/smart_picker_v1.py; NOT autofill/watermark).  The ₹500/day budget
    brake reaches the SHARED Valkey DB 0 + ``public.audit_events`` — the
    ``ai:*`` keyspace stays UN-prefixed/global (F3.c / R1).
  * ``app.core.*`` + the 6-middleware chain — local JWT (D7), read-through
    cache (DB 3, ``category:``-prefixed), smart_picker plan-guard.
  * ``app.i18n.*`` — the schema contract lib (PRIMITIVE_VALUES zero-drift, F5).
  * ``app.adapters.{gemini,langfuse}`` — the ai_ops transport boundary.
  * ``app.shared.{config,database,valkey}`` + the 5 ORM models (3 bound to the
    ``category`` schema; audit_event + user bound to ``public``).

category has ZERO outbound domain calls (pure callee) — it authors NO HTTP
shim client.  It is a CALLEE for export / catalog / pricing via the
``/internal/*`` shims (api-routes-builder's ``internal_router.py``).
"""
