## MS-C B2 — svc-image route layer (2026-06-13)

### Task summary
Built `backend/services/svc-image/app/router.py` for MS-C Phase 2. 2 public routes verbatim from monolith + 1 /internal callee shim per FROZEN SHIM_CONTRACT §2.6. PR #202 open targeting feature/microservices-image/integration.

### Router composition pattern (svc microservice)
Single `router` object at `app.router`; internal routes go on a private `_internal_router = APIRouter(prefix="/internal", ...)` and are composed via `router.include_router(_internal_router)`. B1's `main.py` does one `app.include_router(router)` and gets all 3 routes. This mirrors the svc-export pattern (`from app.router import router`).

### /internal route auth posture (image callee shim)
- NO `get_current_user` on /internal/* routes — cluster-internal network trust.
- The svc-export worker path uses `_transport.py:set_worker_context` which sets `_bearer_token = None` and only forwards `X-Request-ID`.
- /internal/* routes MUST be marked `include_in_schema=False` to hide from public OpenAPI.
- Tenancy is still enforced: `service.list_images` calls `assert_product_ownership` HTTP shim (Option B).

### FROZEN SHIM_CONTRACT §2.6 field verification (image-specific)
Frozen 5 keys in `ImageSummary`: `image_id`, `idx`, `status`, `signed_url`, `precheck_jsonb`. The monolith `ImageSummary` (backend/app/modules/image/schemas.py) has additional fields (`is_front`, `width`, `height`, `color_space`, `created_at`) — these are NOT part of the frozen contract but are ALSO present. The svc-image router re-uses `ImagesListResponse` from `app.schemas` (B1's schema file). No alias needed — field names match exactly.

### Worktree Model C pattern
- Branch `feature/microservices-image/routes` cut from `feature/microservices-image/integration` (tip 3dc0f91).
- Worktree at `/tmp/mesell-wt/msC-routes`.
- Only staged exact svc-image file + STATUS — NEVER `git add -A`.
- F3 protection applied via `gh api repos/.../branches/.../protection` with `allow_force_pushes=false`, `allow_deletions=false`, `enforce_admins=false`, `restrictions=null`.

### Import paths for svc-image router (confirmed from B1 tree)
```python
from app.core.auth import CurrentUser, get_current_user
from app.core.middleware.audit_mw import audit_event
from app.core.middleware.rate_limit_mw import rate_limit
from app import service as image_service
from app.exceptions import InvalidImageIdxError
from app.schemas import ImageUploadResponse, ImagesListResponse
from app.shared.config import settings
from app.shared.database import get_db
```

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| MS-C B2 svc-image routes 2026-06-13 | project | 2 public + 1 /internal shim; PR #202 open; ruff clean |
| /internal route auth posture | reference | cluster-internal trust; no get_current_user; include_in_schema=False; _internal_router composed via router.include_router |
| svc microservice router composition | reference | _internal_router merged into router via include_router; B1 main.py gets all routes in one include_router call |
| FROZEN §2.6 field parity | reference | 5 keys: image_id, idx, status, signed_url, precheck_jsonb — all match monolith ImageSummary field names exactly; no alias needed |
| svc-image import paths | reference | app.core.auth, app.core.middleware.*, app.service (flat), app.exceptions, app.schemas, app.shared.* |

---
