## Session mesell-image-precheck-backend-session-1 — 2026-06-11

### Files touched
- `backend/app/shared/config.py` — MODIFY: Added `FEATURE_IMAGE_PRECHECK_ENABLED: bool = True`
  adjacent to `FEATURE_SMART_PICKER_ENABLED` (~line 185), same dev-true/staging-false comment
  posture referencing FEATURE_PLAN.md D2. Includes staged-promotion gate description (3 gates).
- `backend/app/modules/image/router.py` — MODIFY: Added `HTTPException`, `status` to fastapi
  imports; added `from app.shared.config import settings`; added POST guard (404-when-OFF)
  at top of `upload_image` handler BEFORE idx validation; added GET guard (empty-list 200-when-OFF)
  at top of `list_images` handler BEFORE service call.
- `backend/tests/modules/image/test_flag_gate.py` — NEW: 4 flag-gate tests (see below).

### Commits
- `4444dce` feat(image): FEATURE_IMAGE_PRECHECK_ENABLED flag + router gates — image-precheck backend slice G1/G2
  Files: config.py + router.py
- `de96aca` test(image): flag-gate tests — image-precheck backend slice
  Files: test_flag_gate.py (new)
- Pushed to origin/feature/image-precheck/backend

### Locked decisions
- G1 flag field: `FEATURE_IMAGE_PRECHECK_ENABLED: bool = True` — mirrors FEATURE_SMART_PICKER_ENABLED
  exactly (same field posture, same comment style, same `bool = True` default).
- G2 POST guard: `if not settings.FEATURE_IMAGE_PRECHECK_ENABLED: raise HTTPException(404, ...)`
  placed BEFORE `if idx not in (1, 2, 3, 4)` — flag check fires before any validation or service call.
- G2 GET guard: `if not settings.FEATURE_IMAGE_PRECHECK_ENABLED: return ImagesListResponse(images=[])`
  placed BEFORE `return await image_service.list_images(...)` — empty list 200, NOT 404, per D2.
- Guard pattern: request-time settings read (inside handler body), NOT import-time. Matches
  category/router.py:117 canonical pattern.
- No changes to main.py (router already mounted), ORM, service, schemas, exceptions.

### Test results
- 4 new flag-gate tests: ALL PASS
- 7 pre-existing unit tests: ALL PASS
- 11/11 in tests/modules/image/ standalone (excluding integration which needs live DB)
- Ruff: clean on all 3 files

### Open items
- G3 (docs): V1_FEATURE_SPEC.md §F5 amendment (6→4 images, 60→40MB cap) is a lead-direct docs
  amendment owned by meesell-backend-coordinator in the same PR. NOT a routes-builder concern.
- Integration tests (test_integration.py, 3 tests) need live DB + GCS + Celery — not addressable
  without infra. Pre-existing; unchanged by this session.
- precheck_smoke eval fixtures (tests/eval/precheck_smoke/) — AI track scope, not backend.

### Blockers carried
None. G1 and G2 are complete and tested.

### Next-step recommendation
Coordinator STEP 3 merge-gate review: verify G1+G2 acceptance criteria against the spec,
confirm test count (4 new + 7 existing = 11 pass), open PR feature/image-precheck/backend →
feature/image-precheck (or directly to develop per the D/F Model-C resolution in coordinator memo).

### Hand-off to
meesell-backend-coordinator (HYBRID STEP 3 gate)
