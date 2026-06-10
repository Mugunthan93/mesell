# Memory — meesell-image-precheck-builder

## Agent Identity
Image pre-check specialist for MeeSell. Owns the 5-check pipeline: JPEG/PNG, RGB vs CMYK, resolution ≥ 1500×1500, white-BG heuristic, watermark detection (Gemini Vision). Decentralized memory ecosystem.

## Initial State
No prior memories. First task will populate this file.

## MEMORY.md
(Index of memory files — populated as agent works)

## §11 5-step precheck pipeline — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-11-image-1)

| Memory key | type | content |
| ---------- | ---- | ------- |
| 5-step pipeline location | reference | backend/app/modules/image/tasks.py — sync helpers (_check_jpeg / _check_color_space / _check_resolution / _check_white_background) + async _check_watermark + aggregator _run_precheck_pipeline; Celery task image_precheck_task is the @shared_task wrapper |
| Step 1 — JPEG check | reference | Pillow Image.open(BytesIO).load() → require img.format in ("JPEG", "JPG"); returns (jpeg_valid, pillow_image_or_None) for downstream reuse without second open |
| Step 2 — color space map | reference | RGB/RGBA → "RGB"; CMYK → "CMYK"; L/LA → "Gray"; anything else (palette etc.) → "Gray" (treated non-compliant); only "RGB" passes the deterministic gate |
| Step 3 — resolution | reference | width >= 1500 AND height >= 1500 per MVP_ARCH §5.3 |
| Step 4 — white background heuristic (V1 simple) | reference | 4-corner sampling (5x5 px patches at each corner); converts non-RGB modes to RGB defensively; per-channel avg threshold 235/255 for ALL 4 corners; threshold configurable as constant — ready for golden-eval tuning |
| Step 5 — watermark vision | reference | ai_ops.client.call_gemini(AICallContext(workload="watermark", user_id), "watermark.v1", {}, image_bytes=...); parses {has_watermark, confidence} on success; "skipped_budget" / "uncertain" fallbacks per §6A.F + §11.J |
| Watermark is INFORMATIONAL not blocking (founder ruling) | reference | deterministic_checks_pass property excludes watermark; final_status="ready" iff 4 deterministic steps pass; budget exhaustion → status STILL "ready" (sellers not penalised for budget they didn't cause) |
| Direct ORM audit write pattern | reference | _emit_precheck_completed_audit uses AsyncSessionLocal() + AuditEvent(event_type="image.precheck.completed", entity_type="product_image", entity_id=image_id, metadata_jsonb={precheck_jsonb, final_status, emitted_at}); drops on failure with warning — locked exception to audit_mw post-commit per §15.E |
| Celery retry semantics | reference | @shared_task(max_retries=2, retry_backoff=True); GcsAdapterError from download_bytes triggers self.retry(exc=exc); 3 attempts total |
| Pipeline returns tuple (precheck_jsonb_dict, final_status) | reference | precheck_jsonb shape: {jpeg_valid, color_space, resolution_pass, white_background, watermark_check, watermark_confidence} — 5 §11.G keys + watermark_confidence; integration test int #1 verifies these 5 keys |
| §19 golden eval target | reference | 30 images, 50/50 watermarked/clean, accuracy ≥ 85% per MVP_ARCH §8.5; fixtures live in tests/eval/watermark/fixtures.json (to be created); ai_ops.eval.run_eval("watermark") is the invocation path |
