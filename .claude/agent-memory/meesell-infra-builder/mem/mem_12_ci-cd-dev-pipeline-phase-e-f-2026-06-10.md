## CI/CD Dev Pipeline — Phase E + F — 2026-06-10

**docs/DEVOPS_ARCHITECTURE.md authored** (all 13 sections, ~700 lines). This is now the canonical CI/CD doc — if anything in another doc disagrees about pipeline behaviour, this doc wins. Companion to `INFRASTRUCTURE_ARCHITECTURE.md` (infra), `BACKEND_ARCHITECTURE.md §19.G + §20` (CI gates + deploy topology), `INFRASTRUCTURE_PLAYBOOK.md` (manual procedures).

**.github/workflows/ci.yml fully rewritten** — 8 jobs:
- 5 sequential CI gates: unit → smoke → lint → integration → golden_roundtrip, each `if: github.event_name != 'schedule'`
- build job (`gcloud builds submit --no-source --config=cloudbuild.yaml`), runs after the 5 gates on push to main only
- deploy job (IAP-tunneled SSH → kubectl rolling deploy + migration-before-deploy + smoke + auto-rollback)
- nightly job (`if: github.event_name == 'schedule'`, cron `0 1 * * *`), runs `pytest -m "slow or perf"` + `pytest -m "ai_eval"`. GEMINI_API_KEY from `secrets.GEMINI_API_KEY_CI` (low-quota CI-only key, NOT production)

**All errors from the brief table fixed:**
- VM_NAME `meesell-vm` → `meesell-dev`
- `kubectl -n meesell` → `kubectl -n dev`
- REPO `meesell-images` → `meesell-prod-images`
- python-version `3.11` → `3.12`
- Single test job → 5 gates
- Nightly added

**Service container detail (gates 4-5 + nightly):**
- `postgres:16-alpine` mapped 5432:5433 on host (matches `conftest.py` fixture default)
- `valkey/valkey:8-alpine` mapped 6379:6381 on host
- env `TEST_DATABASE_URL` + `TEST_VALKEY_URL` + the regular `DATABASE_URL` + `VALKEY_URL` all point at localhost:5433 / 6381

**APP_ENV literal gotcha — re-emphasized:** the Pydantic Settings model requires `APP_ENV ∈ {development, staging, production}`. CI jobs all set `APP_ENV=development` (NOT `dev`). The Phase D bug I hit there is not allowed to recur.
