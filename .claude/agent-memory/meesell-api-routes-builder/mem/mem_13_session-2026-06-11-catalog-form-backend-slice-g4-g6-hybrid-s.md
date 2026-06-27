## Session: 2026-06-11 — catalog-form backend slice G4 + G6 (HYBRID STEP 2b)

### Task summary
Authored the `/autofill` 404 flag guard (G4) and two test files (G6 routes-builder half):
`backend/tests/unit/test_catalog_routes.py` (7 tests) + `backend/tests/integration/test_ai_autofill_integration.py` (5 tests).

### G4 guard implementation (locked pattern)

File: `backend/app/modules/catalog/router.py`

New imports added:
```python
from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.shared.config import settings
```

Guard inside `autofill_product` handler (first statement, after FastAPI resolves auth dep):
```python
if not settings.FEATURE_AI_AUTOFILL_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="AI Auto-fill is disabled in this environment",
    )
```

This EXACTLY matches the smart-picker pattern in `category/router.py:117` (canonical guard for all feature-flagged routes in MeeSell V1).

### Guard pattern rule (locked)
- Import `settings` at module level (`from app.shared.config import settings`).
- Read `settings.FEATURE_XXX` inside the handler body (not as a default argument or module-level constant).
- This makes the guard monkeypatch-friendly: `monkeypatch.setattr(_config_module.settings, "FEATURE_XXX", False)` works per-request because the attribute read happens at call time, not at import time.
- Pattern reference: `app/modules/category/router.py:68` (import) + `:117` (guard).

### Unit route test pattern (G6 novelty)

The `/autofill 404 when disabled` test requires auth to succeed (otherwise auth rejects first and you get 401 instead of 404). Pattern:
```python
from app.core.auth import CurrentUser, get_current_user
fake_user = CurrentUser(user_id=uuid4(), plan="free")  # CurrentUser has ONLY user_id + plan (not phone)

async def _fake_auth():
    return fake_user

_production_app.dependency_overrides[get_current_user] = _fake_auth
# ... test ...
_production_app.dependency_overrides.pop(get_current_user, None)  # ALWAYS restore in finally
```

For the "flag=True → service enters → assert not 404" test, also override `get_db` to prevent DB hit, and monkeypatch the first service method (e.g. `assert_product_ownership`) to raise a known non-404 exception (e.g. 403) so you can distinguish "flag guard 404" from "service 404":
```python
from app.shared.database import get_db

async def _fake_db():
    yield AsyncMock()

_production_app.dependency_overrides[get_db] = _fake_db
```

### CurrentUser shape (CRITICAL)
`CurrentUser` is a frozen dataclass with ONLY 2 fields:
```python
@dataclass(frozen=True)
class CurrentUser:
    user_id: UUID
    plan: Literal["free"]
```
NO `phone` field. Discovered during test run — TypeError otherwise.

### Integration test seed gotchas (CRITICAL — VARCHAR limits)
When seeding `templates` + `categories` in integration tests:
- `templates.parser_version`: `VARCHAR(8)` — use <= 8 chars (e.g. `"af1.0"`, NOT `"autofill-integ-1.0"`)
- `categories.meesho_leaf_id`: `VARCHAR(16)` — use <= 16 chars (e.g. `"AF-INTEG-001"`, NOT `"AUTOFILL-INTEG-001"`)
- `categories.super_id`: `VARCHAR(8)` — use <= 8 chars (e.g. `"99"`)
- `categories.super_name`: `VARCHAR(64)` — fine for typical test names
- `templates.schema_hash`: `String(64)` — fine for typical test hashes
- `categories.path`: `Text` — no limit
- `categories.leaf_name`: `String(255)` — fine

Ref: see dashboard integration test `test_dashboard_list_flow.py` pattern (uses `parser_version="dash1.0"`).

### Integration test mock boundary (ai-autofill)
Mock at `catalog_service.ai_client.call_gemini` (the module-qualified reference inside the catalog service). Also stub `catalog_service.enforce_plan_limit` if running without a live Valkey:
```python
async def _fake_call_gemini(ctx, prompt_id, *, prompt_vars, allowed_enums):
    return SimpleNamespace(parsed={"fields": {"fabric": "Cotton"}, "fallback_offered": False})

monkeypatch.setattr(catalog_service.ai_client, "call_gemini", _fake_call_gemini)

async def _noop_plan_guard(*args, **kwargs):
    return None

monkeypatch.setattr(catalog_service, "enforce_plan_limit", _noop_plan_guard)
```

### Test results
- Unit tests/unit: 37/37 PASS (30 pre-existing from services-builder + 7 new route tests)
- Integration test_ai_autofill_integration.py: 5/5 PASS (substrate available on laptop)
- Ruff: all clean, line-length 100

### Files touched
- `backend/app/modules/catalog/router.py` (MODIFIED — G4 flag guard + 2 imports)
- `backend/tests/unit/test_catalog_routes.py` (CREATED — 7 unit tests)
- `backend/tests/integration/test_ai_autofill_integration.py` (CREATED — 5 integration tests)
- `docs/status/STATUS_BACKEND.md` (MODIFIED — UPDATE block appended)

### Git commits (on feature/catalog-form/backend)
- 2678040 feat(catalog): /autofill 404 flag guard — catalog-form backend slice G4
- 79ae93d test(catalog): route + autofill integration tests — catalog-form backend slice G6
- Pushed to origin/feature/catalog-form/backend

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| catalog-form G4 flag guard 2026-06-11 | project | /autofill 404 guard added; router.py:~218; matches smart-picker pattern; settings read at request-time |
| Feature flag guard pattern (locked) | reference | `if not settings.FEATURE_XXX: raise HTTPException(404)`; import settings at module level; read inside handler body — NOT as default arg |
| CurrentUser shape (locked) | reference | Frozen dataclass: ONLY user_id + plan — no phone field |
| Route test auth-bypass pattern | reference | dependency_overrides[get_current_user] = lambda: fake_user; always pop in finally |
| Integration seed VARCHAR limits | reference | parser_version VARCHAR(8); meesho_leaf_id VARCHAR(16); super_id VARCHAR(8) — use short strings |
| Integration mock boundary (ai) | reference | monkeypatch catalog_service.ai_client.call_gemini + catalog_service.enforce_plan_limit |

---
