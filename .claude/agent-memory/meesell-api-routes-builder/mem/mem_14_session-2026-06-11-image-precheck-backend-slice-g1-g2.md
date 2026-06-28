## Session: 2026-06-11 — image-precheck backend slice G1/G2

### Task summary
Added FEATURE_IMAGE_PRECHECK_ENABLED flag (G1) and router gates (G2) for the
image precheck feature. The image module was already fully built on develop;
this session adds the 2 missing feature-flag surfaces only.

### G1 config addition (config.py)
Added to `backend/app/shared/config.py` adjacent to FEATURE_SMART_PICKER_ENABLED:
```python
FEATURE_IMAGE_PRECHECK_ENABLED: bool = True
```
Same dev-true/staging-false comment posture; references FEATURE_PLAN.md D2 + 3 staging gates.

### G2 POST guard (router.py upload_image handler)
```python
if not settings.FEATURE_IMAGE_PRECHECK_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Image upload is disabled in this environment",
    )
```
Placed at TOP of handler, BEFORE idx validation and BEFORE service call.

### G2 GET guard (router.py list_images handler)
```python
if not settings.FEATURE_IMAGE_PRECHECK_ENABLED:
    return ImagesListResponse(images=[])
```
Placed at TOP of handler, BEFORE service call. Returns 200 + empty list (NOT 404) —
read-only endpoint; sellers may have legacy images. Per D2: do NOT 404 the GET.

### ImageSummary required fields gotcha
`signed_url: str` and `created_at: datetime` are NON-OPTIONAL in the as-built schema.
When constructing sentinel ImageSummary in tests: must provide a real string URL and
a real datetime (timezone-aware). Cannot pass None.

### Flag gate test pattern (image-specific)
- stub auth via `dependency_overrides[get_current_user] = _stub_get_current_user`
- patch at `app.modules.image.router.settings` (module-qualified, not `app.shared.config.settings`)
- POST uses multipart: `files={"file": ...}, data={"idx": "1"}`
- GET uses stub service return to distinguish "flag guard empty" from "service empty"
- Env vars required for FATAL check: all 13 REQUIRED_FIELDS must be set (use test-sentinel values)

### Files touched
- `backend/app/shared/config.py` (MODIFIED — G1 flag)
- `backend/app/modules/image/router.py` (MODIFIED — G2 POST + GET guards + imports)
- `backend/tests/modules/image/test_flag_gate.py` (NEW — 4 tests)

### Test results
- 4/4 new flag-gate tests PASS
- 11/11 tests/modules/image/ standalone (4 new + 7 pre-existing) PASS
- Ruff: clean
- Commits: 4444dce (feat) + de96aca (test) on feature/image-precheck/backend, pushed

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| image-precheck G1/G2 2026-06-11 | project | flag + router gates + 4 tests PASS; 2 commits pushed |
| ImageSummary non-optional fields | reference | signed_url:str and created_at:datetime are required (no None) |
| Flag gate test env setup | reference | All 13 REQUIRED_FIELDS must be set (even test-sentinel) for config to pass |
| GET-when-flag-OFF = 200+empty NOT 404 | reference | D2 contract: list endpoint is read-only; sellers may have legacy images |

---
