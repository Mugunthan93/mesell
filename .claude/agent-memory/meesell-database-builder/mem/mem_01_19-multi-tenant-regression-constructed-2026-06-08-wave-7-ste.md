## §19 multi-tenant regression CONSTRUCTED (2026-06-08, Wave 7 step 2)

### Scope
Sub-session `meesell-backend-construction-19-tests-1` — co-acted with meesell-services-builder. My portion: §19.H multi-tenant isolation regression test + review/refinement of the §19.D `db` pytest fixture posture.

### What I did (database-builder side — §19.D + §19.H)

#### tests/integration/test_multi_tenant_isolation.py (§19.H — 278 LOC)
- 4 attack vectors as separate test methods per `TestMultiTenantIsolation`:
  1. `test_user_b_cannot_get_user_a_product_preview` — Vector 1 (direct GET).
  2. `test_user_b_list_excludes_user_a_products` — Vector 2 (list endpoint leakage).
  3. `test_user_b_cannot_patch_user_a_product` — Vector 3 (autosave PATCH cross-user).
  4. `test_user_b_cannot_upload_image_to_user_a_product` — Vector 4 (image upload cross-user).
- Seeds via direct ORM INSERT (no OTP flow): `_create_user(phone)` + `_create_product(user_id)` — both helpers live in the test module so they stay co-located with their consumers.
- `app.core.auth.issue_access_token(user_id, plan)` mints the User B JWT; sent as `Authorization: Bearer ...` header.
- Asserts 404 (preferred per §15.B "leaks no info") OR 403 (acceptable as no-leak); only 200/204 would indicate a §15.B Layer 1 / Layer 2 breach.
- Picks a seeded leaf category via `SELECT id FROM categories WHERE is_leaf = true LIMIT 1` so the test holds regardless of which super_id is used. Skips with `pytest.skip` if no leaf category is seeded.
- Each test consumes all 5 mock adapter fixtures (`mock_msg91_adapter`, `mock_ai_ops_client`, `mock_gcs_adapter`, `mock_razorpay_adapter`) so the test surface is the HTTP authorization layer alone — vendor calls are deterministic.

#### tests/conftest.py `db` fixture posture (§19.D — review only)
- The pre-existing `db` fixture in `tests/conftest.py` already implements the §19.D LOCKED posture: real Postgres via dev tunnel + per-test transaction begin + ROLLBACK at teardown + NullPool engine per test (function-loop-bound). The fixture's loop_scope="function" + NullPool pattern correctly handles pytest-asyncio 0.24's function-scoped event loop without cross-loop Future attachment errors.
- **No changes needed** — the existing fixture matches the §19.D contract verbatim. The services-builder side appended the 5 NEW fixtures (`valkey`, `mock_ai_ops_client`, `mock_msg91_adapter`, `mock_gcs_adapter`, `mock_razorpay_adapter`); my review confirmed they don't conflict with the existing `db` / `db_engine` / `db_session` / `client` / `auth_client` / `use_live_valkey` / `dev_engine` fixtures.
- The `valkey` fixture (new) builds on `use_live_valkey` (existing) and adds an explicit 4-DB FLUSHDB teardown — the §19.D "per-test FLUSHDB on DB 0/1/2/3" requirement.

### Decisions made (database-builder side)
1. **Direct ORM INSERT for test users + products.** The §19.H test surface is the HTTP authorization layer (§15.B Layer 1 + Layer 2), NOT the OTP issuance pipeline (§7.B). Using `app.core.auth.issue_access_token` directly + ORM INSERT keeps the test bounded; the OTP flow is exercised separately in §7.J unit tests.
2. **Skip-not-error on missing leaf category.** If `SELECT FROM categories WHERE is_leaf = true LIMIT 1` returns empty, the test SKIPS rather than ERRORS — acknowledges the seed loader hasn't been invoked yet without blocking the entire test pipeline.
3. **404 OR 403 acceptable.** §15.B explicitly prefers 404 (no info leak) but the architecture isn't strict on the exact status. Accept either; only 200/204 fail the test. Documented inline in the assertion message.

### Tests
- 4 multi-tenant integration test methods collected cleanly via `pytest --co`.
- Execution requires the dev SSH tunnel (autossh → gcp-nexus:5433/6381) — currently down (tunnel state confirmed via `nc -zv localhost 5433` → "Connection refused"). Test PARSING + COLLECTION verified clean. Run verification deferred to master post-tunnel-restoration.

### Acceptance status (database-builder portion)

| # | Criterion | Status |
|---|---|---|
| 1 | §19.H 4 attack vectors enumerated as separate test methods | ✅ |
| 2 | §19.D `db` fixture matches LOCKED posture (real PG + per-test tx + ROLLBACK) | ✅ preserved unchanged |
| 3 | Multi-tenant regression PASSES against current codebase | ⏸ DEFERRED — tunnel down; awaiting infra restoration |

### Hand-offs queued
- **meesell-infra-builder**: restore dev SSH tunnel so master can verify multi-tenant regression.
- **Master**: post-tunnel verification of all 4 vectors. Expected outcome — all 4 PASS (the §15.B 3-layer defense was constructed in §10 + §11 + §13 + §14 sub-sessions and verified in those sub-sessions' own §X.J integration tests; this regression is the consolidated cross-cutting sentinel).

---
