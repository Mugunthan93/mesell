# MS-F (category) — MERGE-GATE ROUND-1 REJECT → meesell-api-routes-builder

**Session:** `mesell-microservices-category-lead-session-1` (Phase C, HYBRID step 3 — the LEAD MERGE GATE)
**Date:** 2026-06-14
**Verdict:** **ROUND-1 REJECT** (iteration cap 3; this is iteration 1). Group PRs NOT opened; founder gate NOT opened.
**Rejected branch:** `feature/microservices-category/svc` @ `f5001a8` — owner **meesell-api-routes-builder** (the `internal_router.py` / `schemas.py` author).
**db branch (`2a9d165`) + infra branch (`5e1a074`): PASS — NOT rejected, no changes requested.**
**services-builder portion of svc branch (service/picker/repository/domain/exceptions/ai_ops/budget carve-out): PASS — zero changes requested.**

---

## THE ONE REJECT-CLASS DEFECT — super-categories shim shape violates FROZEN-0E

`backend/services/svc-category/app/internal_router.py:189-220` (`internal_list_super_categories`) returns a JSON **object**:

```python
return SuperCategoryListResponse(super_categories=super_ids)   # → {"super_categories": ["26","19",...]}
```

backed by `schemas.py:251-267 SuperCategoryListResponse(super_categories: list[str])`.

**The FROZEN-0E contract (customer-owned, ALREADY MERGED to develop) requires a BARE JSON ARRAY, not an object.**

Authority (unambiguous, three citations):
1. **The merged consumer** — `backend/services/svc-customer/app/core/extracted_clients/category_client.py:50-51` (on `origin/develop`):
   ```python
   payload = await request_json("GET", "/internal/super-categories")
   return [str(item) for item in payload]        # iterates payload DIRECTLY as a JSON array
   ```
   `request_json` returns `response.json()` raw (no unwrapping — verified `_transport.py:78`). So the consumer requires the response body to be `["26","19",...]`. If category-svc returns `{"super_categories":[...]}`, `for item in payload` iterates the dict KEYS → returns `["super_categories"]` — a single bogus element. **Runtime break of customer-svc super-category eligibility checks.**
2. **spec_msE_backend.md §9 / lines 24, 95, 127** (FROZEN-0E, customer-owned): `GET /internal/super-categories → list[str]` — and verbatim: *"SUB_PLAN_0F (MS-4) must conform to `list[str]`, NOT its draft `list[SuperCategoryInfo]`."* The customer freezes this; category must conform.
3. **SUB_PLAN_0F §F4 latent shim + Open-Question resolution** — defensive shim must match the caller's frozen shape.

**The element type is right (`list[str]`, distinct super_ids) — only the envelope is wrong.** The builder wrapped the array in an object. The FROZEN-0E contract is a **top-level bare array**.

### Why the builder's own test did NOT catch it (false-green)
`tests/test_svc_category_routes.py:639 test_internal_super_categories_list_str` asserts `body["super_categories"]` is a `list[str]` — i.e. it encodes the WRONG (object) assumption (docstring line 642 even claims "customer-svc deserialises `body['super_categories']`" — that is NOT what the merged customer client does). The test passes against the wrong contract. **This is exactly why the gate is a real gate** (HYBRID rule-7) — the specialist self-report + green suite did not surface the cross-service drift.

---

## THE FIX (exactly one shim + its schema + its test — nothing else)

1. **`internal_router.py` Shim #4** (`internal_list_super_categories`): return a **bare `list[str]`**, not the wrapper model. e.g.:
   ```python
   @_internal_router.get("/super-categories", response_model=list[str], include_in_schema=False, ...)
   async def internal_list_super_categories(...) -> list[str]:
       infos = await category_service.list_super_categories(db=db)
       return [info.super_id for info in infos]      # ["26","19",...]
   ```
2. **`schemas.py`**: DELETE `SuperCategoryListResponse` (and `SuperCategoryNode` if it exists only to back it — verify; `schemas.py:157` references `list[SuperCategoryNode]` — confirm nothing public uses it before deleting). Drop the now-unused import in `internal_router.py`.
3. **`tests/test_svc_category_routes.py:639`**: rewrite `test_internal_super_categories_list_str` to assert the response body **IS** a bare JSON array: `body = resp.json(); assert isinstance(body, list); assert all(isinstance(x,str) for x in body); assert set(body)=={"26","19"}`. Fix the docstring to cite the real customer contract (iterates `payload` directly).

**DO NOT TOUCH** the other 3 shims (schema #1, field-enum #2, commission #3 — all verified correct against the merged export-svc + pricing-svc clients). DO NOT touch the 5 public routes. DO NOT touch service.py/picker.py/repository.py/ai_ops (services-builder's verified-correct work).

**Re-dispatch citation:** SUB_PLAN_0F §F4 + spec_msE §9 FROZEN-0E + the merged `svc-customer/.../category_client.py:50-51`.

---

## EVERYTHING ELSE — VERIFIED PASS (do not re-verify on round 2 unless the fix touches it)

| Gate item | Result | Evidence |
|---|---|---|
| §16.G service.py AST parity (recursive import+docstring strip) | **PASS — IDENTICAL** (dump len 40649==40649); raw diff = exactly 3 import lines (`app.modules.category`→`app`), ZERO call-site change | `/tmp/ast_parity.py` |
| picker.py | **PASS — BYTE-IDENTICAL** (golden recall preserved by construction; 100% by identity) | `diff` |
| repository.py / domain.py / exceptions.py | **PASS** (repository import-stripped identical; domain+exceptions byte-identical) | `diff` + AST |
| `scope_to_user` absent (category GLOBAL §9.D) | **PASS** — only a docstring mention, zero actual call | grep |
| Budget carve-out R1 (`ai:*` UN-prefixed, `category:` on cache only) | **PASS** — `shared/valkey.py` DB-0 factory applies NO prefix; `category:` confined to `core/cache.py:_versioned_key` (sole DB-3 site); `ai:*` keys are literal strings in byte-identical vendored modules | `valkey.py`, `cache.py`, grep |
| budget_cap.py + cost_tracker.py byte-identical (Lua `_RESERVE_LUA`/`_RELEASE_LUA` therefore identical) | **PASS — BYTE-IDENTICAL** | `diff -q` |
| ai_ops trim (only `smart_picker_v1.py` prompt; NO autofill/watermark) | **PASS** — prompts/ has ONLY smart_picker_v1.py; client/guardrail/prompt_registry/eval all byte-identical | `ls` + `diff -q` |
| Commission shim #3 (`/internal/categories/{id}/commission` → `{"commission_pct":"<decimal>"}` never-null) | **PASS** — matches merged svc-pricing `category_client.py` (reads `payload.get("commission_pct")`; object shape correct) | git show develop |
| Schema shim #1 + field-enum shim #2 | **PASS** — export-svc reads both as `dict(payload)`; object shapes correct; unaffected by the array issue | git show develop |
| Mounted route count | **PASS** — 5 public (`router.py`) + 4 internal (`internal_router.py`) + `/health` + `/metrics` ASGI mount; internal_router mounted (`main.py:130`) | grep |
| DB migration (db branch) | **PASS** — `c4f1e7a9d302`, down_revision `None` (standalone root); `version_table_schema="category"`; 4 tables `SET SCHEMA category` (preserves GIN); CREATE SCHEMA IF NOT EXISTS | migration + env.py |
| svc test suite (Py3.11 `.venv`) | **45 passed** (1 of which, `test_internal_super_categories_list_str`, is false-green per above) | pytest |
| Branch scope (no monolith touched) | **PASS** — `git diff --stat integration..svc` touches only `backend/services/svc-category/**` + `docs/status/STATUS_BACKEND.md`; ZERO `backend/app` or `backend/tests` | diff-stat |

**Test-env caveat honored:** ran on `backend/.venv` Py3.11 (NOT host 3.9.6); no PEP-604 false-fails observed (suite is mocked, no ORM-boot path hit the union-resolution issue at 3.11).

---

## ROUND-2 PLAN (after the 1-shim fix re-lands on `feature/microservices-category/svc`)
1. Re-pull svc branch; re-run the super-categories test (expect bare-array assertion green) + re-confirm `git diff` of the fix = ONLY shim #4 + schema + that test.
2. Re-run §16.G service.py AST parity (must still be IDENTICAL — fix should not touch service.py).
3. Author Phase-C deliverables: `test_category_extraction.py` (AST parity + PRIMITIVE_VALUES parity + budget-brake-shared + 4 frozen shim shapes incl. the NOW-bare-array super-categories), CI hybrid note, MASTER_PLAN §4 row-F flip, board+STATUS MERGED rows.
4. Assemble db→svc→infra into integration (LEAD squash gate, `--admin`); open the founder-gate PR (LEAVE OPEN, D1).
