## §11 image router — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-11-image-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| §11 image router (2 endpoints) | reference | POST /api/v1/products/{id}/images — 202 ACCEPTED, multipart/form-data (UploadFile + Form idx), @rate_limit(scope="image_upload", limit=10, window=60), @audit_event("image.upload.received"); GET /api/v1/products/{id}/images — 200 OK, @rate_limit(scope="image_list", limit=600, window=3600), NO audit (read-only polling) |
| §11 image schemas (3 models) | reference | ImageUploadResponse {image_id, gcs_path, status="pending", idx 1-4, enqueued_task_id}; ImageSummary {image_id, idx, status, signed_url, precheck_jsonb, is_front, width, height, color_space, created_at}; ImagesListResponse {images: list[ImageSummary]} — extra="forbid" on all |
| §11 idx Form() coercion (route-layer fail-fast) | reference | FastAPI Form() default cannot enforce [1,4] range; router fails fast with InvalidImageIdxError BEFORE catalog.assert_product_ownership round-trip — saves DB query on malformed clients; service ALSO re-validates as defence-in-depth |
| §11 multipart upload pattern | reference | file: Annotated[UploadFile, File(description=...)], idx: Annotated[int, Form(description=...)] = 0 — V1 direct multipart through FastAPI; V1.5 may move to direct-to-GCS PUT per §11.M + MVP_ARCH §10.8 |
| §11 boot test route count: 27 → 31 actual | reference | test_app_boot_integration expects 27 distinct path keys (1 image path shared POST + GET); actual app.routes is 31 because each (path, method) is its own APIRoute object — _route_map() helper deduplicates by path key |
