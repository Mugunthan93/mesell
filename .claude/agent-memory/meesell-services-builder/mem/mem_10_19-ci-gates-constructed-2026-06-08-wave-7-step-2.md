## §19 CI gates CONSTRUCTED (2026-06-08, Wave 7 step 2)

### Scope
Sub-session `meesell-backend-construction-19-tests-1`. Solo dispatch acting as both meesell-services-builder (primary — AST scanners + perf tests + pytest fixtures + CI integration) AND meesell-database-builder (per-test transaction `db` fixture posture review + multi-tenant isolation regression). Wave 7 step 2 per founder's sequential plan.

### What I did
- **7 import-linter contracts** (`backend/tests/lint/import_rules.toml`, 1247 LOC): expressed §16.E's 7 logical contracts as **27 per-source sub-contracts** because import-linter v2's `forbidden` contract structurally rejects pairs that share descendants (e.g. `source=app.modules.iam` + `forbidden=app.modules.iam.repository`). Per-source expansion: Contract 1 → 8 sub-contracts (one per domain module excluding own repository); Contract 4 → 8 (own schemas); Contract 7 → 8 (own router + tasks); Contracts 2, 3, 5 stay single. Intra-module self-import allowlist (`__init__.py` router re-exports + intra-module router→service / service→repository / service→tasks / service→schemas chains) added via `ignore_imports` + `unmatched_ignore_imports_alerting = "none"` so cross-module enforcement stays sharp while legitimate intra-module loads pass. Final result: **27 kept / 0 broken** against live codebase.

- **Contract 8 — `scope_to_user` AST scanner** (`tests/lint/check_scope_to_user.py`, 244 LOC): walks every public method in `app/modules/{customer,catalog,image,pricing,export}/repository.py` and asserts `user_id` is in the signature. Allowlist via `SCANNED_MODULES` constant (excludes `iam` (users IS the principal per §15.B special-case), `category` (global tables per §16.F.2), `dashboard` (no repository per §16.F.1)). `KNOWN_DEVIATIONS` frozenset documents `app.modules.pricing.repository.insert_calc` as the one pre-existing exception (tenancy upstream via `catalog.assert_product_ownership` per the function's own docstring).

- **Contract 9 — M10 forbidden-symbol AST scanner** (`tests/lint/check_no_meesho_symbols_outside_export.py`, 242 LOC): walks `app/**/*.py` (excluding `app/modules/export/**` + `app/adapters/gcs.py` per §14.J + §15.F) checking 4 AST node kinds — `ast.Name`, `ast.Attribute`, `ast.keyword`, `ast.arg` — for the 3 forbidden symbols (`meesho_column_header` / `meesho_column_index` / `enum_codes_map`). Docstring string literals NOT walked per L_export_M10_AST_scanner spec line. `KNOWN_DOCSTRING_HITS` frozenset documents 6 pre-existing string-literal mentions (3 in `app/shared/models/template.py` JSON-shape docstring + 3 in `app/modules/export/{schemas,__init__}.py` docstrings) for forward-compat documentation.

- **Contract 10 — i18n message_id regex scanner** (`tests/lint/check_message_id_regex.py`, 152 LOC): loads `app.i18n.messages_en.VALIDATION_MESSAGES` at runtime and asserts every key matches §5A.H regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`. Reports 55 keys all PASS against current registry. The existing `tests/test_messages_en_id_regex.py` continues to provide belt-and-braces parametrised coverage.

- **4 pytest wrappers** (`tests/lint/test_*.py`, 73-171 LOC each): `test_import_contracts.py` runs `lint-imports` via subprocess with venv-binary auto-discovery (resolves `lint-imports` via `shutil.which` then `sys.prefix/{bin,Scripts}/lint-imports`); the other 3 wrappers invoke their scanners in-process and include counter-example tests (synthetic temp directories with a violating `repository.py` / `service.py`).

- **6 §19.D pytest fixtures** appended to `backend/tests/conftest.py` (existing 343 LOC → 621 LOC): `valkey` (real per-test connection to all 4 logical DBs (0/1/2/3) via dev tunnel, FLUSHDB on teardown, returns `dict[name, Redis]`), `mock_ai_ops_client` (AsyncMock for `call_gemini` patched on source + 4 consumers), `mock_msg91_adapter` (AsyncMock for `send_otp` patched on source + iam consumers), `mock_gcs_adapter` (in-memory `dict[str, bytes]` backing the 4 GCS async surfaces, patched on source + 4 image/export consumers), `mock_razorpay_adapter` (MagicMock for `verify_webhook_signature`). The pre-existing `db` fixture already implements the §19.D per-test transaction + ROLLBACK pattern — preserved unchanged.

- **4 performance test files** (`tests/perf/`, 74-152 LOC each + 152 LOC conftest with `assert_p95_within_budget` / `assert_value_within_budget` helpers): `test_category_schema_p95.py` (cache hit ≤ 50 ms / miss ≤ 200 ms), `test_category_browse_p95.py` (≤ 200 ms), `test_export_pipeline.py` (≤ 30 s), `test_ai_cost_average.py` (≤ ₹0.05 over 7-day audit_events rolling window). All marked `@pytest.mark.slow + @pytest.mark.perf`. **Suite-wide skip via `pytest_collection_modifyitems` hook** in `tests/perf/conftest.py` — gates BEFORE fixture instantiation (the `db` fixture connects at fixture setup), so fast-lane PR runs skip the suite cleanly without DB-connect errors.

- **Multi-tenant isolation regression** (`tests/integration/test_multi_tenant_isolation.py`, 278 LOC): 4 attack vectors per §19.H + §15.B as separate test methods inside `TestMultiTenantIsolation`. Direct ORM INSERT to build User A / User B (bypassing OTP per §19.D fixture posture); `app.core.auth.issue_access_token` mints the User B JWT; the 4 vectors exercise GET preview / list / PATCH autosave / POST image-upload as User B against User A's product. Asserts 404 (preferred) or 403 (acceptable) — both are no-leak outcomes per §15.B 3-layer defense.

- **`backend/pytest.ini` markers** + addopts per §19.D: 7 markers registered (`unit`, `integration`, `golden_roundtrip`, `ai_eval`, `slow`, `smoke`, `perf`); `--strict-markers --strict-config -ra` added. `asyncio_default_fixture_loop_scope = session` preserved (load-bearing for the `dev_engine` pattern). `testpaths = tests` preserved.

- **`backend/requirements.txt`** appended `import-linter>=2.0,<3`.

### Decisions made (FLAGGED — for master review at hand-off)

1. **TOML namespace fork from §16.E sketch.** §16.E uses bare `[importlinter]` for clarity; the runtime import-linter package requires `[tool.importlinter]` (per `importlinter.adapters.user_options.TomlFileUserOptionReader` line 90). Implementation uses runtime-required namespace; semantic count of "7 import-linter contracts" preserved via per-source expansion. **No architecture-doc edit per §5.0 — documented inline in the TOML header comment.**

2. **Per-source expansion of Contracts 1, 4, 7.** import-linter v2's `forbidden` contract rejects source/forbidden pairs that share descendants. Expanded as: Contract 1 → 8 sub-contracts (one per source module); Contract 4 → 8; Contract 7 → 8. **Semantic count remains "7 logical contracts" per §19.C.** Documented inline. Suggest §19.C amendment NOTE for future readers ("Contracts 1/4/7 implemented as N=8 per-source sub-contracts each — see import_rules.toml header").

3. **`KNOWN_DEVIATIONS` allowlist for Contract 8.** `pricing.repository.insert_calc` lacks `user_id` because the `pricing_calcs` table FKs on `product_id`, and the tenancy gate is enforced upstream at `catalog.assert_product_ownership` per the function's own docstring (lines 8-11). Added to the scanner's allowlist with inline citation. **NO modification to §12 LOCKED CONSTRUCTED code per §5.0 + §18-precedent ("don't touch other sub-sessions' LOCKED code unless necessary").** Suggest V1.5 ticket: widen `insert_calc` signature to accept `user_id: UUID` for defence-in-depth.

4. **L_iam_1 NOT addressed in §19.** The latent says `core/auth.py` raises 2-segment IDs (e.g. `auth.token_missing`) but i18n + §5A.H regex require 3-segment. Contract 10 scans `app.i18n.messages_en.VALIDATION_MESSAGES` keys (all 55 PASS), NOT the runtime ID strings raised by exceptions. The 2-segment exception IDs WILL produce missing-key resolver fallbacks at runtime per §5A.I (which logs WARNING and returns the verbatim ID — a degraded UX but not a crash). **Out of §19 scope per the construction prompt's "DO NOT amend per-module test plans" rule + §5.0.** Already in latent backlog as L_iam_1.

5. **L_iam_2 V0-rot cleanup PARTIAL.** `tests/test_config.py` (5 failures) + `tests/test_worker_db_isolation.py` (3 V0-rot failures referencing `app.database`, `async_session_maker`, `app.services.image_processor`) NOT remediated in this sub-session — tunnel was down for the duration so failure causes can't be confirmed. **Recommend §20 sub-session pick up V0-rot cleanup once §20 deployment dispatch goes out.**

6. **Tunnel down during sub-session.** `nc -zv localhost 5433` returned `Connection refused` throughout the session — autossh process exists (PID 82990 → `gcp-nexus` alias) but the forwarding was not active. Boot smoke (`test_app_boot_integration`) + schema smoke (`test_database`) + new multi-tenant regression COULD NOT be exercised. Lint suite (18 PASS), perf suite (5 skip), 92 non-DB tests verified. **Master must re-run boot+schema+multi-tenant after tunnel restoration to close §19 acceptance.**

### Tests added (in this sub-session)
- **18 pytest tests under `tests/lint/`**: 1 import-linter wrapper (2 sub-asserts) + 4 scope_to_user wrapper + 6 M10 forbidden-symbol wrapper + 6 message_id regex wrapper — ALL PASS in 0.31s.
- **5 perf tests under `tests/perf/`**: ALL SKIP cleanly per `PYTEST_RUN_SLOW=1` gate. `PYTEST_RUN_SLOW=1` invocation will exercise the 4 budgets — requires tunnel + V1.5 export-pipeline seed harness for the 30s budget test.
- **4 multi-tenant integration tests under `tests/integration/`**: collected cleanly; will exercise the 4 §15.B attack vectors once tunnel is restored.

### Acceptance status

| # | Criterion | Status |
|---|---|---|
| 1 | 7 import-linter contracts in `tests/lint/import_rules.toml` matching §16.E | ✅ 27 kept / 0 broken |
| 2 | 3 custom AST scanners (Contracts 8, 9, 10) + counter-example tests | ✅ all 3 scan PASS; counter-examples flag synthetic violations |
| 3 | 4 perf test files in `tests/perf/` with locked budgets per §19.E | ✅ 4 files, skip cleanly under PR gate |
| 4 | `tests/conftest.py` with 6 locked fixtures per §19.D | ✅ all 6 in place (`db` pre-existed, 5 new appended) |
| 5 | `pytest.ini` markers per §19.D + `perf` | ✅ 7 markers + addopts |
| 6 | `test_multi_tenant_isolation.py` 4 attack vectors | ✅ written, awaiting tunnel for run |
| 7 | All 10 CI contracts PASS against current codebase | ✅ Contracts 1-10 all PASS (Contracts 1-7: 27 sub-contracts kept; Contracts 8-10: scanners exit 0) |
| 8 | Coverage targets met (80% line / 100% branch on critical paths) | ⏸ DEFERRED — coverage harness requires tunnel for integration tests |
| 9 | ~88 test classes per §19.B inventory all PASS | ⏸ DEFERRED — DB-dependent tests cannot run without tunnel |
| 10 | Universal: ruff clean | ✅ (3 auto-fixed) |

### Hand-offs queued
- **§20 deployment sub-session**: pick up L_iam_2 V0-rot cleanup (5 `test_config.py` failures + 3 `test_worker_db_isolation.py` failures); wire the CI YAML to invoke the 4 `pytest -m` stages per §19.G; populate the 3 PENDING Secret Manager secrets (`refresh-token-pepper`, `razorpay-webhook-secret`, `langfuse-secret-key`).
- **meesell-infra-builder**: restore the dev tunnel (autossh) so master can verify §19 acceptance criteria #8 + #9.
- **V1.5 tickets queued** (D-flags for master ratification): (a) §19.C amendment NOTE on per-source expansion of Contracts 1/4/7; (b) widen `pricing.repository.insert_calc` signature to accept `user_id: UUID` (defence-in-depth); (c) L_iam_1 resolution — migrate `core/auth.py` exception IDs from 2-segment to 3-segment per §5A.H.

---
