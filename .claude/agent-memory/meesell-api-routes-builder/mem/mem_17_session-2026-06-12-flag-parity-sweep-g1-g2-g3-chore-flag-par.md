## Session: 2026-06-12 — flag-parity sweep G1/G2/G3 (chore/flag-parity)

### Task summary
Wired 3 missing V1 feature flags + in-handler route guards + flag-404 tests.
Branch: chore/flag-parity (worktree /tmp/mesell-wt/flag-parity).
9 tests across 3 files — all PASS. 2 commits pushed.

### G1 price-calculator (pricing/router.py)
Added `FEATURE_PRICE_CALCULATOR_ENABLED: bool = True` to config.py §3.2 after FEATURE_AI_AUTOFILL_ENABLED.
Added `HTTPException, status` + `settings` imports to pricing/router.py (were absent).
In-handler guard BEFORE service call:
```python
if not settings.FEATURE_PRICE_CALCULATOR_ENABLED:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Price Calculator is disabled in this environment",
    )
```
Test file: tests/modules/pricing/test_feature_flag.py (3 tests, @unit marker).
Patch surface: `app.modules.pricing.router.settings`.

### G2 dashboard (dashboard/router.py)
Added `FEATURE_TRACKING_DASHBOARD_ENABLED: bool = True` to config.py §3.2.
Added `HTTPException, status` + `settings` imports to dashboard/router.py.
In-handler guard BEFORE service call. R1 RULING: GET/read endpoint gets 404 — the read IS the feature
(D3 kill-switch). Guard comment explains this divergence from "writes only get 404" convention.
Test file: tests/modules/dashboard/test_feature_flag.py (3 tests, @unit marker).
Patch surface: `app.modules.dashboard.router.settings`.

### G3 live-preview (catalog/router.py)
Added `FEATURE_LIVE_PREVIEW_ENABLED: bool = False` to config.py §3.2.
DEFAULT FALSE — the ONLY V1 flag that ships default-False; all others default True.

CRITICAL JUDGMENT CALL: HTTPException does NOT carry a custom `code` field.
The _http_exception_handler in core/errors.py always sets `code = f"http.{exc.status_code}"`.
To emit the spec-required `{"code": "feature.live_preview.disabled"}`, must use MeesellError directly.
MeesellError.__init__ accepts `code: str | None` as a per-instance override.
Pattern used:
```python
from app.core.errors import MeesellError
# ...
if not settings.FEATURE_LIVE_PREVIEW_ENABLED:
    raise MeesellError(
        code="feature.live_preview.disabled",
        status_code=404,
        detail="Preview unavailable",
    )
```
This goes through _meesell_error_handler which emits the §4.F envelope with `code = "feature.live_preview.disabled"`.
R3 RULING HONORED: no new core/feature_flags.py; MeesellError is the codebase's existing coded-error mechanism.

Test file: tests/integration/test_live_preview_flag_404.py (3 tests; no @unit marker — placed in integration/).
R4: test_preview_returns_404_with_default_flag does NOT patch the flag — default IS False, so 404 is the default.
The `code` field is verified explicitly: `assert body.get("code") == "feature.live_preview.disabled"`.

### HTTPException vs MeesellError for coded errors — decision table (LOCKED PATTERN)
| Need | Use |
|---|---|
| Simple 404 flag guard (no custom code) | HTTPException(status_code=404, detail="...") |
| Coded 404 flag guard (custom code field) | MeesellError(code="...", status_code=404, detail="...") |
The _http_exception_handler hardcodes `code = "http.{status_code}"`. Only MeesellError escapes this.

### Config comment style (locked for §3.2 flag block)
```
# FEATURE_XYZ_ENABLED: dev default True/False; staging default False
# (staging gate conditions from FEATURE_PLAN.md Decision D2 or D3).
# Route path returns 404 when False per Master Plan §3.2 backend protocol.
# Note if default False: DEFAULT FALSE — the only / one of few V1 flags that ships default-False.
FEATURE_XYZ_ENABLED: bool = True/False
```

### Pre-existing reds observed
None encountered in isolation runs. (Gate-1 unit RED on develop tip is pre-existing per D-2 note
in audit memo — not caused by this sweep.)

### Commits
- a61c864 feat(flags): price-calc + dashboard + live-preview flags + guards — flag-parity G1/G2/G3
- 41b654d test(flags): flag-404 tests x3 — flag-parity G1/G2/G3
- Pushed to origin/chore/flag-parity

### Memory entry index (new entries)
| Entry | Type | Summary |
|---|---|---|
| flag-parity sweep 2026-06-12 | project | G1/G2/G3: 3 flags + 3 guards + 9 tests; 2 commits pushed on chore/flag-parity |
| HTTPException vs MeesellError for coded errors | reference | Use MeesellError when spec requires custom `code` field; HTTPException always emits `code="http.N"` |
| FEATURE_LIVE_PREVIEW_ENABLED default-False | reference | ONLY V1 flag that ships default-False; test 1 verifies default WITHOUT patching the flag |
| R1 GET-route 404 (dashboard kill-switch) | reference | dashboard list_products IS the feature — R1 mandates 404 on GET, not just writes |

---
