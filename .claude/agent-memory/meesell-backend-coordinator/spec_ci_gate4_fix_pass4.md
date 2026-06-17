# SPEC — CI Gate-4 (integration) test-harness fix — PASS 4 (FINAL — the actual exit-0 target)

**Authored:** 2026-06-11 by `meesell-backend-coordinator` (Rule 7 STEP 1).
**Predecessor:** PR #108 (pass 3) MERGED to develop — squash SHA `61e7d17`. Pass-3: `35f/135p/8s/14e -> 5f/174p/13s/0e`.
**Session token:** `mesell-ci-gate4-fix-session-4`. **Branch:** `fix/ci-gate4-integration-pass4` from `origin/develop` (tip post-#108 `61e7d17`). **Worktree:** `/tmp/mesell-wt/ci-gate4-pass4`.
**Named specialist:** `meesell-services-builder` (opus) — FOURTH round, deepest saga context. (Light enough for api-routes-builder, but services-builder owns the pricing test-data semantics and the isolation saga — continuity wins.)
**This is the FINAL pass.** After #108, `pytest -m integration` exits non-zero on EXACTLY 5 reds: 4 x is_leaf (BE-CAT-ISLEAF-1) + 1 x pricing last-calc (BE-PRICING-LASTCALC-TX-1). Both are TEST-SIDE fixes (classification below). Resolving them makes Gate-4 reach exit 0 (modulo justified BE-SEED-1 skips) on the next develop->main re-fire.

## CLASSIFICATION (test-stale vs app-bug) — coordinator ruling, authoritative

### A. is_leaf (4 tests) — TEST-STALE. Fix the TEST. NOT an app bug.
- The 4 failing tests (`test_user_b_cannot_get_user_a_product_preview`, `test_user_b_list_excludes_user_a_products`, `test_user_b_cannot_patch_user_a_product`, `test_user_b_cannot_upload_image_to_user_a_product` in `tests/integration/test_multi_tenant_isolation.py`) ALL route through ONE helper `_make_product`, which has ONE stale line (L91):
      select(Category.id).where(Category.is_leaf.is_(True)).limit(1)
- `Category.is_leaf` DOES NOT EXIST on the ORM model (`app/shared/models/category.py`). The model has `leaf_name`, `meesho_leaf_id`, `super_id`, `path`, `template_id` — and NO `is_leaf` boolean.
- AUTHORITATIVE BASIS (BACKEND_ARCHITECTURE.md §9 + the model docstring "3,772 Meesho leaf nodes"): the `categories` table is a FLAT table of LEAF NODES ONLY. There is no parent/non-leaf row concept in V1 — every row IS a leaf. There is therefore NO discriminator column by design, and the §-spec does NOT require one. The test's own comment confirms the intent: "Pick any leaf category — the §15.B contract holds regardless of which."
- The ONLY `is_leaf` artifact in the repo is `backend/app/data/meesho_category_tree.json` — confirmed DEAD CODE (legacy burn-rebuild leftover, referenced by zero .py files, per knowledge-sync memory). It is NOT the live schema.
- VERDICT: adding an `is_leaf` property to the model to satisfy a stale test would be inventing schema to match a test, which inverts the authority order (§-docs are authoritative, not tests). The test is stale; the app is correct.
- EXACT FIX: in `tests/integration/test_multi_tenant_isolation.py` L91, change
      select(Category.id).where(Category.is_leaf.is_(True)).limit(1)
  to
      select(Category.id).limit(1)
  (every row is a leaf, so the predicate is redundant AND references a non-existent column). The L94-95 `if cat_row is None: pytest.skip(...)` guard stays as-is (handles the no-seed case). Single line. Clears all 4 tests.
- NOTE: the same `Category.is_leaf` appears twice in `tests/perf/test_category_schema_p95.py` (L60, L98) — those are `@pytest.mark.slow`/`@pytest.mark.perf` (Nightly job, NOT in the Gate-4 `-m integration` set). OPTIONAL to fix in the same PR for hygiene (same one-line edit x2). If included, PR-note it; if deferred, note BE-CAT-ISLEAF-1 lives on only in the Nightly perf file. RECOMMENDED: fix them too (identical edit) so the ticket fully closes.

### B. pricing last-calc (1 test) — TEST-STALE. Fix the TEST. NOT an app bug.
- `tests/integration/test_pricing_persistence.py::test_get_last_calc_returns_most_recent` (L190-263).
- The app behaviour under test (append-only INSERT, ORDER BY created_at DESC LIMIT 1) is CORRECT. The test is coupled to PostgreSQL transaction-bound `NOW()` for distinct `created_at` across its 3 `db_session.commit()` calls (test comment L196-199). Under the pass-3 SAVEPOINT isolation those 3 commits release savepoints inside ONE outer transaction, so all 3 share the outer txn's `NOW()` -> identical `created_at` -> nondeterministic `ORDER BY created_at DESC` -> the `seller_price == 150.00` assertion is flaky/wrong.
- Was already RED before pass-3 (IntegrityError) -> red-to-red, not a regression introduced by pass 3.
- The "most-recent-wins" INTENT must be preserved.
- EXACT FIX (minimal, test-data correction — stays inside the test file fence): after the 3-calc loop and BEFORE the `get_last_calc` assertion, explicitly stamp the 3 persisted rows with distinct, monotonically-increasing `created_at` values so the ORDER BY is deterministic under the single-transaction savepoint harness. Concretely:
      # Savepoint isolation shares the outer txn's NOW() across all 3 commits,
      # so created_at is identical -> force distinct timestamps to make
      # ORDER BY created_at DESC deterministic (intent: most-recent-wins).
      from datetime import datetime, timedelta, timezone
      rows_in_order = result.scalars().all()  # already fetched ASC by seller_price-correlated insert order
      base = datetime(2026, 1, 1, tzinfo=timezone.utc)
      # Map each row to a monotonically increasing created_at by its seller_price
      # (110 -> base+0s, 120 -> base+1s, 150 -> base+2s) so the 50% calc is newest.
      ts_by_price = {Decimal("110.00"): base, Decimal("120.00"): base + timedelta(seconds=1), Decimal("150.00"): base + timedelta(seconds=2)}
      for r in rows_in_order:
          r.created_at = ts_by_price[r.seller_price]
      await db_session.flush()
  Then the existing `get_last_calc` assertion (latest.seller_price == Decimal("150.00")) holds deterministically.
  - ACCEPTABLE ALTERNATIVE (specialist's call if cleaner): set `created_at` inline at insert time by passing it through the service path is NOT possible (service stamps it), so the post-hoc UPDATE-via-ORM-attribute + flush above is the minimal in-fence approach. Do NOT change the repository `ORDER BY` (that is app code, out of fence; a created_at-tiebreak in the repo is a legitimate V1.5 robustness improvement tracked under BE-PRICING-LASTCALC-TX-1 but is NOT required for Gate-4 exit-0 and must NOT land in this test-only pass).
  - Keep the `assert len(rows) == 3` append-only assertion and the `seller_prices == [110,120,150]` assertion UNCHANGED — they are correct and orthogonal to the timestamp issue.

## 2. Fence (LOCKED MAY touch) — exactly 2 test files (+ STATUS append)
- `backend/tests/integration/test_multi_tenant_isolation.py` (L91 is_leaf -> drop predicate)
- `backend/tests/integration/test_pricing_persistence.py` (test_get_last_calc_returns_most_recent: distinct created_at stamping)
- OPTIONAL (recommended, PR-noted): `backend/tests/perf/test_category_schema_p95.py` (L60, L98 same is_leaf one-liner) — closes BE-CAT-ISLEAF-1 fully. If touched, fence = 3 test files.
- `docs/status/STATUS_BACKEND.md` (append-only close-out block).

## 3. MUST NOT touch
ci.yml; pytest.ini (§19.D); `backend/app/**` (NO is_leaf property added to the model — test is stale, app is correct; NO repository ORDER BY tiebreak in this pass — that is V1.5 BE-PRICING-LASTCALC-TX-1); alembic; conftest.py (pass-3 owns — the isolation harness is correct and final); any other test file.

## 4. Verification gate (THE actual Gate-4 target — finally)
`cd backend && pytest -m integration -v` with CI env shape (pass-3 substrate) -> **exit 0** with ONLY BE-SEED-1 skips remaining (13 skips expected, same as pass-3). ZERO failures, ZERO errors. PR evidence: BEFORE (5f/174p/13s/0e, origin/develop @ 61e7d17 same substrate) -> AFTER (0f / 179p / 13s / 0e — the 5 reds become 5 passes; skip count unchanged). Show the 5 newly-green test names. Confirm no app/ci.yml/pytest.ini/conftest diff.

## 5. PR + merge-gate (STEP 3)
Branch `fix/ci-gate4-integration-pass4` from origin/develop (61e7d17); worktree `/tmp/mesell-wt/ci-gate4-pass4`; PR -> develop (standalone CI hotfix, D1 N/A); template fully filled, N/A explicit, no placeholders; commit footer `Session: mesell-ci-gate4-fix-session-4`. STEP-3 checklist: diff confined to §2 fence; is_leaf predicate dropped (not is_leaf-property-added); pricing created_at stamping preserves the 2 unchanged assertions; before/after exit-0 evidence; §19.D + §2.D + §16 preserved; §17 stays 28; no FE/AI/data memo; CI-not-on-develop note. After merge: squash + delete branch (API DELETE) + clean worktree + board MERGED + STATUS block + notify infra "Gate-4 READY TO RE-FIRE — full exit-0 reached."

## 6. Tickets reconciled by this pass
- BE-CAT-ISLEAF-1 — CLOSED by §1.A (test was stale; no app change). If perf file deferred, ticket stays OPEN only for the Nightly perf file (1 one-line edit) — recommend closing fully here.
- BE-PRICING-LASTCALC-TX-1 — the Gate-4-blocking symptom CLOSED by §1.B test edit. A residual V1.5 NOTE remains (repository ORDER BY created_at has no tiebreak; two prod calcs in the same millisecond would order nondeterministically) — tracked as a V1.5 robustness follow-up, NOT a V1 blocker, NOT fixed in this test-only pass.
