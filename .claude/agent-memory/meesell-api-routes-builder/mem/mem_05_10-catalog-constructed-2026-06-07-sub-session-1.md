## §10 catalog — CONSTRUCTED 2026-06-07 (sub-session 1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §10 catalog 6 endpoints | reference | POST /products (201); PATCH /products/{id}; POST /products/{id}/autofill; GET /products/{id}/preview; DELETE /products/{id} (204); GET /products/{id}/draft (200 OR 204) |
| §10 X-Autosave header pattern | reference | `Header(alias="x-autosave")` → `_is_autosave(header)` accepts {"true","1","yes"} (case-insensitive); absent OR any other → False |
| §10 autofill audit | reference | router-level `@audit_event("catalog.autofill.invoked")`; PII compromise = SHA-256(description) + 200-char preview lives in service.description_sha256 helper |
| §10 5 distinct path keys (boot integration) | reference | PATCH+DELETE share /products/{id} → 1 path key in _route_map; integration test expects 25 total now (was 20) |
| §10 audit decorators (4 writes, 2 reads) | reference | writes: product.created/updated/deleted + autofill.invoked; reads (preview + draft): NO @audit_event per MVP_ARCH §11.3 read-flood rule |
| §10 rate_limit shapes | reference | create_product 20/h user; product_patch 600/h IP (autosave-friendly); ai_autofill 50/h user; product_preview 600/h IP; product_delete 60/h user; product_draft_read 600/h IP |
| §10 catalog.draft 204 path | reference | router branches on `service.get_draft` returning None → `Response(status_code=204)`; no envelope (per RFC 7231 §6.3.5) |
| §10 PatchProductRequest model_validator | reference | rejects empty body (both `fields` and `status` None) via @model_validator(mode="after") raising ValueError → 422 envelope through §4.F handler |
