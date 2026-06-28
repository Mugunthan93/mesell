## D4 §20.5 CI YAML CONSTRUCTED (2026-06-09, .gitlab-ci.yml)

### Scope
Micro-dispatch `meesell-services-builder` solo. D4 founder-approved Option A: produce `.gitlab-ci.yml` ONLY (the previously-missing CI YAML §20 sub-session never produced). Zero `backend/app/` changes; zero architecture-doc edits (§5.0). On branch `claude/meesell-project-setup-Tl7DS`, no commit (master handles git).

### What I did
Created `/Users/mugunthansrinivasan/Project/mesell/.gitlab-ci.yml` (283 LOC). 6 stages sequential per §19.G, gated via `needs:` chain (unit→smoke→lint→integration→golden_roundtrip):
- **unit** `cd backend && pytest -m "unit"` — dummy env, no services.
- **smoke** `cd backend && pytest -m "smoke"` — boot+schema, `needs:[unit]`.
- **lint** (§16.E HARD RULE, separate build-failing stage, `needs:[smoke]`) — 4 commands, ALL from `backend/`: `lint-imports --config tests/lint/import_rules.toml` (Contracts 1-7) + `python tests/lint/check_scope_to_user.py` (8) + `python tests/lint/check_no_meesho_symbols_outside_export.py` (9) + `python tests/lint/check_message_id_regex.py` (10).
- **integration** `cd backend && pytest -m "integration"` `needs:[lint]` — services `postgres:16` (alias postgres) + `valkey/valkey:8` (alias valkey); `DATABASE_URL=postgresql+asyncpg://meesell:meesell@postgres:5432/meesell_test`, `VALKEY_URL=redis://valkey:6379`.
- **golden_roundtrip** `pytest -m "golden_roundtrip"` `needs:[integration]` — same services.
- **nightly** schedule-only — 2 jobs both `needs:[golden_roundtrip]`: `nightly_slow_perf` (`pytest -m "slow or perf"`, `PYTEST_RUN_SLOW=1`) + `nightly_ai_eval` (`pytest -m "ai_eval"`, `RUN_AI_EVAL=1`, `GEMINI_API_KEY=$GEMINI_API_KEY`).

### Locked patterns / decisions (reusable)
- **Schedule gating idiom:** stages 1-5 use `rules: [{if: schedule → never}, {when: on_success}]`; nightly uses `rules: [{if: schedule → on_success}, {when: never}]`. This keeps MR pipelines off nightly AND keeps nightly from re-running PR-only gates. `$CI_PIPELINE_SOURCE == "schedule"` is the discriminator.
- **All pytest + lint run from `backend/`** via `cd backend && ...` — pytest.ini, import_rules.toml, and the 3 AST scanners all resolve paths relative to backend/.
- **lint-imports invocation is `--config tests/lint/import_rules.toml`** — the TOML uses `[tool.importlinter]` namespace (§19 D-flag); `import-linter>=2.0,<3` already in requirements.txt.
- **base image `python:3.12-slim`**; pip cache `.cache/pip` keyed on `backend/requirements.txt` files-hash so a lock change busts it.
- **YAML anchors:** `.install_deps` (`before_script: pip install -r backend/requirements.txt`) + `.dummy_env` (CI-safe placeholder SECRET_KEY/MSG91_*/REFRESH_TOKEN_PEPPER/RAZORPAY_WEBHOOK_SECRET) merged into jobs via `<<: *anchor`. Real values via `$VAR` CI/CD variables on integration+. NO hard-coded secrets.
- **Dummy-env jobs (unit/smoke/lint)** need no Postgres/Valkey — app Pydantic Settings only require values present/well-formed to import modules.
- Verified: `python3 -c "import yaml; yaml.safe_load(...)"` → YAML VALID + structural asserts (6 stages, anchor merges, needs chain, services, 4 lint commands, schedule gating) all pass.

### Hand-off
- **meesell-infra-builder**: register GitLab nightly schedule (Settings→CI/CD→Pipeline schedules, e.g. cron `0 18 * * *`) so nightly jobs fire; populate 5 protected/masked CI/CD variables (`SECRET_KEY`, `MSG91_API_KEY`/`MSG91_SENDER_ID`/`MSG91_ROUTE`, `REFRESH_TOKEN_PEPPER`, `RAZORPAY_WEBHOOK_SECRET`, `GEMINI_API_KEY`). L2 Secret Manager names align.
- D4 escalation CLOSED.

---
