# QA SPEC — `test_iam_logout_idempotency` D2 event-loop fix

**Author:** `meesell-qa-coordinator` (session `mesell-qa-wave-image-ai-coord-session-1`)
**Specialist:** `meesell-backend-test-writer` (sonnet)
**Filed against:** inter-lead request to backend-coordinator (board row, qa-image-ai RE-GATE PR #431 finding)
**Date:** 2026-06-27
**Type:** pre-existing bug fix (NOT a qa-wave PR) — goes straight to `develop` via a `fix/` branch.

---

## 1. One-line task summary

Make both async tests in `test_iam_logout_idempotency.py` consume the loop-scoped `valkey` conftest fixture instead of calling the `get_valkey_otp()` process-singleton inline, eliminating the latent `Event loop is closed` (D2 bug class) at setup in a combined `pytest -m integration` run.

---

## 2. File to edit

`backend/tests/modules/iam/test_iam_logout_idempotency.py`

**ONLY this file.** No source, no conftest, no other test. Tests-only diff.

---

## 3. Root cause (why this is owed)

Both test functions take `use_live_valkey` as a parameter but then hand-roll their own client in the body:

```python
from app.shared import valkey as _vk_mod
valkey = await _vk_mod.get_valkey_otp()
```

`get_valkey_otp()` returns the module-level `_otp_client` **singleton**, which retains a `redis.asyncio` connection bound to a *previously closed* event loop. When these tests run inside one combined `pytest -m integration` process (CI Gate-4 style), that singleton is reused across function loops -> `RuntimeError: Event loop is closed` at setup. This is the same D2 bug class that rejected PR #431 and PR #435. Non-failing today (surfaces only as a non-failing GC warning under the current `filterwarnings` config) but a latent landmine that a `filterwarnings` tightening or a test reorder would flip to a hard ERROR.

The `valkey` fixture in `backend/tests/conftest.py` (defined ~L702-755, `loop_scope="function"`) already solves this: it builds on `use_live_valkey` (which monkeypatches the `app.shared.valkey` factories to per-call function-loop clients) and yields properly-scoped, per-test-flushed clients.

---

## 4. CRITICAL ground-truth correction (do NOT skip)

**The `valkey` conftest fixture yields a DICT of per-DB clients, NOT a single client.** Confirmed at `conftest.py` L745 `yield clients`, where `clients` is keyed:

```python
valkey["otp"]      # DB 0 — OTP / rate-limit / session / refresh   <- the one this test needs
valkey["broker"]   # DB 1
valkey["results"]  # DB 2
valkey["cache"]    # DB 3
```

`get_valkey_otp()` returns the **DB-0 OTP** client. The service calls in this test (`verify_otp_and_issue_tokens(..., valkey=...)`, `revoke_refresh_token(token, ...)`) and the raw `.set()`/`.get()` calls all expect that single DB-0 client. Therefore the in-body binding must be **`valkey["otp"]`**, NOT `valkey` directly.

> If you bind `valkey` (the dict) directly to `.set()` / pass it as `valkey=valkey`, the test fails with `AttributeError: 'dict' object has no attribute 'set'`. Bind the OTP client to a local (the SPEC uses `vk`) — do not reuse the name `otp`, which already names the OTP *code* string in test 1.

---

## 5. Exact diff

### Test 1 — `test_logout_first_call_revokes_then_second_call_is_noop`

**Signature (L28-30):**
```python
# OLD
async def test_logout_first_call_revokes_then_second_call_is_noop(
    db, use_live_valkey
):
# NEW
async def test_logout_first_call_revokes_then_second_call_is_noop(
    db, valkey
):
```

**Body (L32-34) — remove the inline import + singleton call, bind the OTP client:**
```python
# OLD (L32-34)
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
# NEW
    vk = valkey["otp"]
```

**Then replace every remaining use of the old local `valkey` with `vk`:**
- L40: `await valkey.set(f"otp:{phone}", payload, ex=300)` -> `await vk.set(f"otp:{phone}", payload, ex=300)`
- L43: `phone=phone, otp=otp, client_ip="192.0.2.10", db=db, valkey=valkey` -> `... db=db, valkey=vk`
- L48: `assert await valkey.get(allowlist_key) is not None` -> `assert await vk.get(allowlist_key) is not None`
- L51: `first = await iam_service.revoke_refresh_token(refresh_token, valkey)` -> `... revoke_refresh_token(refresh_token, vk)`
- L54: `assert await valkey.get(allowlist_key) is None` -> `assert await vk.get(allowlist_key) is None`
- L61: `second = await iam_service.revoke_refresh_token(refresh_token, valkey)` -> `... revoke_refresh_token(refresh_token, vk)`
- L66: `third = await iam_service.revoke_refresh_token(None, valkey)` -> `... revoke_refresh_token(None, vk)`

All assertions stay byte-identical — only the client identifier changes.

### Test 2 — `test_logout_with_unknown_token_does_not_raise`

**Signature (L71):**
```python
# OLD
async def test_logout_with_unknown_token_does_not_raise(use_live_valkey):
# NEW
async def test_logout_with_unknown_token_does_not_raise(valkey):
```

**Body (L73-76) — KEEP the `issue_refresh_token` import; remove the valkey-module import + singleton call; bind the OTP client:**
```python
# OLD (L73-76)
    from app.core.auth import issue_refresh_token
    from app.shared import valkey as _vk_mod

    valkey = await _vk_mod.get_valkey_otp()
    bogus = issue_refresh_token()  # well-formed but never registered
# NEW
    from app.core.auth import issue_refresh_token

    vk = valkey["otp"]
    bogus = issue_refresh_token()  # well-formed but never registered
```

- L79: `result = await iam_service.revoke_refresh_token(bogus, valkey)` -> `... revoke_refresh_token(bogus, vk)`

### Net effect
- Both signatures: `use_live_valkey` -> `valkey`.
- Both `from app.shared import valkey as _vk_mod` imports REMOVED.
- Both `valkey = await _vk_mod.get_valkey_otp()` calls REMOVED, replaced by `vk = valkey["otp"]`.
- Every body reference to the old local `valkey` -> `vk`.
- Zero assertion changes. Zero behavior changes. The `@pytest.mark.integration` + `@pytest.mark.asyncio` `pytestmark` (L25) stays.

---

## 6. Validation commands (paste output in the PR)

```bash
# 1. The file as a UNIT — must be 2 passed / 0 failed / 0 error.
cd /Users/mugunthansrinivasan/Project/mesell/backend && python3 -m pytest tests/modules/iam/test_iam_logout_idempotency.py -v --tb=short

# 2. Combined integration run — must show 0 errors (no "Event loop is closed").
cd /Users/mugunthansrinivasan/Project/mesell/backend && \
  python3 -m pytest -m integration --ignore=backend/tests/scripts -q 2>&1 | tail -5
```

**Exit criteria (measurable):**
- Command 1: **2 passed, 0 failed, 0 error.**
- Command 2: the tail shows **0 errors** — specifically NO `RuntimeError: Event loop is closed` attributable to `test_iam_logout_idempotency`. The combined run's pass/skip totals must not regress vs the pre-fix baseline.

> Requires the dev DB/Valkey tunnel (`db` + `valkey` are real per §19.D — no SQLite/fakeredis) and a `*_test` `TEST_DATABASE_URL`. If the combined run is environment-blocked, disclose it and paste command 1's unit result + the static diff confirmation.

---

## 7. Branch / PR / commit

- **Branch:** `fix/qa-image-ai-iam-logout-d2/backend`, cut from `develop`.
- **PR target:** `develop` **directly** (this is a pre-existing bug fix, not a qa-wave lane -> NOT a `feature/qa-wave-N/integration` PR; short `fix/` PR straight to develop).
- **Commit message:** `fix(tests): reuse valkey fixture in test_iam_logout_idempotency (D2 event-loop fix)`
- Co-author trailer per repo convention.

---

## 8. Gate boxes the reviewer will check

- [ ] Both commands' output pasted in the PR (command 1 = 2 passed; command 2 = 0 errors).
- [ ] Diff is tests-only — exactly one file, `test_iam_logout_idempotency.py`; no source/conftest edits.
- [ ] `valkey["otp"]` used (NOT the bare dict) — no `AttributeError`.
- [ ] Both `_vk_mod` imports + `get_valkey_otp()` calls removed.
- [ ] No assertion removed/weakened — assertion count unchanged; no assertion-free test introduced.
- [ ] `TEST_DATABASE_URL` `_resolved_db.endswith("_test")` guard untouched (conftest not in diff).
- [ ] No real external calls introduced.
