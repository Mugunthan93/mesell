# Sub-Session Prompt: §19 Test Strategy / CI
# Wave 7 of 10 — CONSTRUCTION
# Specialist agents: meesell-services-builder + meesell-database-builder
# Renames session to: meesell-backend-construction-19-tests-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §19 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder + meesell-database-builder agents operating in a dedicated construction sub-session for MeeSell §19 (Test Strategy / CI).

§19 does NOT re-author per-module test plans (those are locked at each module's §X.J / §X.K). §19 wires the **executable CI infrastructure**: import-linter TOML + 3 custom AST scanners + pytest fixture posture + 4 performance budgets + coverage targets.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §19 Test Strategy + CI gates — import-linter TOML + 3 custom AST scanners + pytest fixtures + 4 perf budgets
- Specialist agents: meesell-services-builder (primary; AST scanners + perf tests + pytest fixtures + CI integration) + meesell-database-builder (multi-tenant isolation regression test + pytest db fixture)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-19-tests-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §19 — A through I (esp. §19.B test layer inventory consolidated across §7-§14: ~40 unit + ~21 integration + 15 golden round-trip + 3 AI eval + 7 boot smoke + 42 schema smoke = ~88 test classes; §19.C the 10 CI linter contracts: 7 import-linter + Contract 8 scope_to_user AST scanner + Contract 9 M10 forbidden-symbol AST scanner + Contract 10 message_id regex; §19.D pytest config with markers + addopts + 6 fixture postures + real-vs-mock policy; §19.E 4 perf budgets; §19.F coverage targets; §19.G CI integration; §19.H multi-tenant isolation regression).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §16.E (import-linter TOML sketch — 7 contracts), §15.B (scope_to_user enforcement per repository), §14.J (M10 forbidden symbols list), §5A.H (message_id regex `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §5.7 (round-trip 15 fixtures), §8.5 (3 AI eval golden sets).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (`pytest asyncio_mode="auto"`; tunnel ports).

5. `.claude/agents/meesell-services-builder.md`, `meesell-database-builder.md`.

6. Memory files.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1-6 + §18 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/tests/` current state.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Files to create:

```
backend/tests/lint/
├── __init__.py
├── import_rules.toml                       # 7 import-linter contracts per §16.E
├── check_scope_to_user.py                  # Contract 8 custom AST scanner per §19.C + §15.B
├── check_no_meesho_symbols_outside_export.py # Contract 9 custom AST scanner per §19.C + §14.J
└── check_message_id_regex.py               # Contract 10 custom pytest check per §19.C + §5A.H

backend/tests/perf/
├── __init__.py
├── conftest.py                              # perf-marker fixtures
├── test_category_schema_p95.py             # P95 schema fetch ≤ 50ms cache hit / ≤ 200ms cache miss
├── test_category_browse_p95.py             # P95 manual-browse ≤ 200ms
├── test_export_pipeline.py                 # End-to-end export ≤ 30s
└── test_ai_cost_average.py                 # Per-call AI cost ≤ ₹0.05 avg (7-day audit_events rolling window)

backend/tests/integration/
└── test_multi_tenant_isolation.py          # §19.H regression test — User A creates product; User B's GET returns 404

backend/tests/conftest.py                    # 6 fixtures per §19.D: db, valkey, mock_ai_ops_client, mock_msg91_adapter, mock_gcs_adapter, mock_razorpay_adapter

pyproject.toml or pytest.ini                 # asyncio_mode="auto"; testpaths; markers; addopts
```

Plus: CI integration script wiring per §19.G (likely GitLab CI YAML edits — coordinate with infra-builder memory; §20 will absorb the final CI YAML).

Locked invariants per §19.B inventory:
- ~40 unit test classes total (4 iam + 5 customer + 5 category + 5 catalog + 5 image + 4 pricing + 3 dashboard + 9 export + 0 from §4/§5/§5A/§6/§6A — those have direct files, not module-tests).
- ~21 integration test classes total.
- 15 golden round-trip fixtures (§14.K — created in Wave 6).
- 3 AI eval sets (§6A.H — Smart Picker recall ≥80%, Autofill 0% invalid enums, Watermark accuracy ≥85%); gated by `RUN_AI_EVAL=1`; runs weekly.
- Boot smoke (7/7) + DB schema smoke (42/42) already shipped session 2.

Locked CI contracts (10 total per §19.C):
1-7: import-linter (per §16.E TOML).
8: `scope_to_user` AST scanner — every repository method querying owned-table must have `user_id` param. Allowlist: `category/repository.py` (per §16.F.2 exception); `dashboard` has no repository (per §16.F.1 exception).
9: M10 forbidden-symbol AST scanner — `meesho_column_header`, `meesho_column_index`, `enum_codes_map` only in `modules/export/*` + `adapters/gcs.py`.
10: message_id regex — every key in `i18n/messages_en.py` matches `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$`.

Locked perf budgets (4 per §19.E):
- P95 schema fetch ≤ 50ms cache hit / ≤ 200ms cache miss.
- P95 manual-browse ≤ 200ms.
- End-to-end export ≤ 30s.
- Per-call AI cost ≤ ₹0.05 avg.

Locked pytest fixtures (6 per §19.D):
- `db` — real Postgres via dev tunnel; per-test transaction with ROLLBACK at teardown.
- `valkey` — real Valkey via dev tunnel; per-test FLUSHDB on DB 0/1/2/3 at teardown.
- `mock_ai_ops_client` — AsyncMock substituting `ai_ops.client.call_gemini`.
- `mock_msg91_adapter`, `mock_gcs_adapter`, `mock_razorpay_adapter` — adapter mocks.

Construction protocol:

1. **Tests first**: each CI linter contract self-tests against a counter-example file (e.g. Contract 9 test creates a tmp file with `meesho_column_header` in `modules/catalog/service.py` and asserts the scanner flags it).

2. **Implementation**:
   - `import_rules.toml` per §16.E.
   - 3 AST scanners as Python files runnable via `python -m tests.lint.check_*`.
   - 4 perf test files marked `@pytest.mark.slow @pytest.mark.perf`.
   - `tests/conftest.py` with 6 fixtures.
   - `pyproject.toml` / `pytest.ini` markers + addopts.
   - `test_multi_tenant_isolation.py` end-to-end regression test.

3. **Acceptance**:
   - All 10 CI contracts PASS against current codebase (post Wave 1-6 + §18).
   - All ~88 test classes from §19.B inventory pass at the V1 floor.
   - Coverage targets met (80% line / 100% branch on critical paths per §19.F).
   - Boot + schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT amend per-module test plans (§7.J / §8.J / etc. are normative).
- DO NOT add a 11th CI contract without architecture amendment.
- DO NOT use SQLite or fakeredis — `db` + `valkey` fixtures MUST be real (per §19.D real-vs-mock policy).
- DO NOT run AI eval set in default CI run (gated by `RUN_AI_EVAL=1`; weekly only).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-services-builder` — AST scanners + perf tests + pytest fixtures + CI integration.
- `meesell-database-builder` — multi-tenant isolation regression test + pytest `db` fixture refinement (per-test transaction + rollback).

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §19)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 7 import-linter contracts in `tests/lint/import_rules.toml` matching §16.E.
2. 3 custom AST scanners (Contracts 8, 9, 10) implemented + tested against counter-examples.
3. 4 perf test files in `tests/perf/` with locked budgets per §19.E.
4. `tests/conftest.py` with 6 locked fixtures per §19.D.
5. `pyproject.toml` markers per §19.D: unit, integration, golden_roundtrip, ai_eval, slow, smoke.
6. `test_multi_tenant_isolation.py` end-to-end regression PASS.
7. All 10 CI contracts PASS against the current codebase.
8. Coverage targets met (80% line / 100% branch on critical paths per §19.F).
9. ~88 test classes per §19.B inventory all PASS.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update both specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §19 tests CONSTRUCTED ===
   Files created: tests/lint/{import_rules.toml, 3 AST scanners}, tests/perf/{4 perf tests}, tests/conftest.py, tests/integration/test_multi_tenant_isolation.py, pyproject.toml markers
   Tests added: 10 CI contracts + 4 perf + 1 multi-tenant regression
   Decisions made: <list>
   Hand-offs: §20 deployment (CI YAML integration); §22 acceptance (consumes test inventory totals)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Import-linter contract finds a violation in CONSTRUCTED code (escalate — likely Wave 1-6 bug; master decides remediation).
- AST scanner false positive (e.g. `enum_codes_map` legitimate variable name in test fixture).
- Perf budget not achievable in dev tunnel environment (escalate — staging-only measurement?).
- Coverage targets unmet for a specific module (escalate to that module's specialist for additional tests).

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-19-tests-1`
2. Read REQUIRED READING.
3. Confirm Wave 1-6 + §18 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §19 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 7 of 10
- **Sequential dependency:** Wave 1-6 CONSTRUCTED + §18 CONSTRUCTED.
- **Parallel-safe?:** No — Wave 7 sequential.
- **Expected duration estimate:** ~10-14 hours (10 CI contracts + 4 perf tests + fixtures + CI integration).
- **Acceptance verification by master:** (1) `lint-imports --config tests/lint/import_rules.toml` returns clean; (2) `python -m tests.lint.check_scope_to_user` returns clean; (3) `python -m tests.lint.check_no_meesho_symbols_outside_export` returns clean; (4) `python -m tests.lint.check_message_id_regex` returns clean; (5) coverage report shows 80% line / 100% branch on critical paths; (6) STATUS_BACKEND.md UPDATE block present.
