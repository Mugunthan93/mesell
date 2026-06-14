# feature_smart_picker_route-flag-guard.md

## Session header
Session: mesell-smart-picker-backend-session-1
Date: 2026-06-11
Agent: meesell-api-routes-builder
Branch: feature/smart-picker/backend
Worktree: /tmp/mesell-wt/smart-picker-backend

## Files touched
- `backend/app/shared/config.py` — MODIFY: Added `FEATURE_SMART_PICKER_ENABLED: bool = True` under new "Feature flags" group
- `backend/app/modules/category/router.py` — MODIFY: Added flag guard at suggest_categories function entry; added imports HTTPException, status (fastapi), settings (shared.config)
- `backend/tests/integration/test_suggest_flag_404.py` — NEW: 5 smoke tests

## What was done

### Config addition (config.py)
Added to `backend/app/shared/config.py` after the `APP_ENV` field, in a new "Feature flags" group.
Field: `FEATURE_SMART_PICKER_ENABLED: bool = True` (NOT in REQUIRED_FIELDS — has a default, not a required secret).

### Router modification (router.py)
Added at function entry of `suggest_categories`, AFTER auth resolves, BEFORE service call:
```python
if not settings.FEATURE_SMART_PICKER_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Smart Picker is disabled in this environment",
    )
```
Added imports: `HTTPException`, `status` from `fastapi`; `settings` from `app.shared.config`.

### Conformance verification results

§9.E schemas.py — PASS (no drift)
- SuggestQuery.q: Field(min_length=1, max_length=500) matches spec
- CategorySuggestion: all 7 fields match spec
- SuggestResponse: {suggestions(max_length=5), fallback_offered:bool} matches spec

§9.G exceptions.py — MINOR NORMALIZATION NOTE (no change made)
- CategoryNotFoundError/FieldEnumNotFoundError use 3-segment validation_message_ids
  per §5A.H convention, not the 2-segment shorthand in §9.G prose. Documented
  deliberate normalization in exceptions.py docstring. NOT changed.
- SuggestQueryInvalidError.validation_message_id matches spec exactly. PASS.

§9.B.1 route contract — PASS (no drift)
response_model, Depends, rate_limit decorator, q param bounds all verified.

## Test results
5 tests PASS / 0 failed, 0.08s
Ruff: 0 errors on all 3 modified files
Commit: 6a107ca on branch feature/smart-picker/backend

## Open items
- .env.example + k8s ConfigMaps need FEATURE_SMART_PICKER_ENABLED added (infra lead owns)
- §9.G 2-segment vs 3-segment normalization gap should get a founder ruling

## Cross-feature gotchas
- First FEATURE_*_ENABLED flag in codebase — no prior pattern. Used HTTPException(404) at function entry (after auth, before service).
- Guard must be AFTER auth resolves so 401 fires for unauthenticated callers even when feature is disabled.
- Config path: FEATURE_PLAN.md template says backend/app/config.py — WRONG. Correct: backend/app/shared/config.py per §5.D lock. Lead audit pre-corrected this in dispatch brief.
- Remove flag + guard when feature ships to main (Master Plan §3.2 anti-debt rule).

## Next-session brief
Flag guard in and tested. Parallel work: services-builder (service.py flow), database-builder (repository.py + trigram P95 benchmark). After all three dispatches: backend lead runs full integration suite and opens group PR. test_suggest_flag_404.py test 4 (flag-enabled path) is infra-gated but passes in CI as a non-flag-guard confirmation.
