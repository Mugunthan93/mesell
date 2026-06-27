## §10 catalog — CONSTRUCTED 2026-06-07 (sub-session 1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §10 catalog service surface (10 methods) | reference | route-internal: create_product / patch_product / autofill_product / get_preview / soft_delete / get_draft; cross-module: assert_product_ownership / get_product_for_export / list_products / get_validation_summary |
| §10 ProductNotFoundError uniform collapse | reference | repository.find_by_id collapses (non-existent | cross-tenant | soft-deleted) → None; service raises ProductNotFoundError uniformly — no leak between cases |
| §10 plan_guard wiring (D5 — service-level) | reference | create_product: plan_guard("product_count", db=db) FIRST → category.assert_category_exists → customer.assert_eligible_for_super_id → catalog select/create → insert; autofill_product: plan_guard("ai_autofill_hourly") |
| §10 schema-driven validation (D3 — 3-segment IDs) | reference | dispatch through schema field's data_type + primitive + enum_resolver; unknown→`validation.fields.unknown_key`; text_short>100→`validation.{canonical}.too_long`; static enum miss→`validation.{canonical}.invalid_enum_value`; category enum via `category.service.get_field_enum`; multi-violation→first drives validation_message_id, rest in `details: list[str]` |
| §10 product_drafts wrapper (D1 — applied) | reference | draft_jsonb = {"fields": <merged>, "autosave_count": N}; saved_at→last_updated; legacy rows coerce to autosave_count=1; repository._unwrap_draft_payload is the canonical reader |
| §10 audit_mw coalesce regex deviation (D2) | reference | `_AUTOSAVE_PATH = ^/api/v1/products/[0-9a-fA-F-]+/(draft|autosave)/?$` does NOT match `PATCH /products/{id}`; audit row writes per PATCH (no coalescing in V1); §4.G amendment queued — NOT a §10 blocker |
| §10 graceful fallback symmetry | reference | autofill_product handles BOTH `BudgetExceededError` raise AND `AIResponse.parsed.fallback_offered=True` AND empty `parsed.fields` — all 3 → `AutofillResponse(suggestions={}, applied={}, fallback_offered=True)` with HTTP 200 |
| §10 ai_suggestions persistence | reference | overwrite (not merge) per call — each Auto-fill replaces ai_suggestions_jsonb with the full payload; history lives in audit_events |
| §10 autofill confidence default (D4) | reference | _DEFAULT_AUTOFILL_CONFIDENCE=0.9 — above the 0.85 auto-apply floor; emission IS the confidence signal (prompt instructs model to omit unsure fields) |
| §10 default catalog name (D5) | reference | `{user_id_last4_hex}-Drafts-{YYYYMMDD-HHMM}` — uses user_id-last-4 instead of phone-last-4 to avoid hot-path DB read; UX layer may rewrite |
| §10 super_id resolution | reference | _resolve_super_id_for_category(category_id) reads `schema["super_id"]` from category.fetch_schema cache; defensive return None skips the eligibility gate |
| §10 cross-module surface stability | reference | assert_product_ownership / get_product_for_export / list_products / get_validation_summary form the V1.5 gRPC interface per §10.K — the 4 RPCs |
| §10 image/pricing forward-compat | reference | get_preview and get_product_for_export defensively try `from app.modules import image` — empty image_urls/refs when §11 not yet present (parallel-dispatch safe) |
