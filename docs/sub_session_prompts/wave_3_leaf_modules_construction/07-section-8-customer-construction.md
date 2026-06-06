# Sub-Session Prompt: §8 Module `customer`
# Wave 3 of 10 — CONSTRUCTION (parallel-safe with §9 category)
# Specialist agents: meesell-api-routes-builder + meesell-services-builder
# Renames session to: meesell-backend-construction-8-customer-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy block below between START / END markers.
4. Paste as first message. Wait for "Ready to begin §8 construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-api-routes-builder + meesell-services-builder agents operating in a dedicated construction sub-session for MeeSell §8 (Module `customer`).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning BACKEND_ARCHITECTURE.md.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §8 Module `customer` — 5 endpoints + COMPLIANCE_EXTENSION_MAP
- Specialist agents: meesell-api-routes-builder (router + schemas) + meesell-services-builder (service + repository + domain + exceptions)
- Attempt: #1
- Sub-session naming: `/rename meesell-backend-construction-8-customer-1`

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Stop and report if outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §8 — A through L (esp. §8.B 5 endpoints: 1 GET profile + 3 PATCH base/active-categories/compliance-extension + 1 GET required-fields; §8.C 9-method service surface incl. 3 cross-module surfaces `get_compliance_block` for export / `get_profile_completeness` for dashboard / `assert_eligible_for_super_id` for catalog; §8.D 4-method module-private repository all using `scope_to_user(user_id)`; COMPLIANCE_EXTENSION_MAP enumerates 6 super_ids — Grocery FSSAI compulsory + 5 conditional per §0 premise #7 + §12.1; §8.G 6 CustomerError subclasses; §8.J 5 unit + 2 integration tests).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §4 (core/), §5 (shared/), §5A (i18n/), §9 (category for super_id validation; LOCKED), §7 (iam — CONSTRUCTED Wave 2).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §2.2 (seller_profile DDL), §3.2 (endpoints), §12.1 (compliance extension map), §12.5, §12.6 (CollapsedComplianceStrategy consumed by export — customer doesn't implement it; just stores the 9 standard fields).

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md`.

5. `.claude/agents/meesell-api-routes-builder.md` and `.claude/agents/meesell-services-builder.md`.

6. Memory files for both agents.

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm Wave 1 + Wave 2 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` baseline.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Per §3.C:

```
backend/app/modules/customer/
├── __init__.py
├── router.py            # FastAPI APIRouter; 5 endpoint signatures
├── service.py           # 9-method PUBLIC service surface (5 endpoint-mirror + 3 cross-module + 1 internal recompute)
├── repository.py        # 4-method PRIVATE repository; scope_to_user(user_id) on every method
├── schemas.py           # Pydantic v2 request/response models incl. ProfileBaseRequest, ActiveCategoriesRequest, ComplianceExtensionRequest
├── domain.py            # COMPLIANCE_EXTENSION_MAP frozen dict (6 super_ids) + ComplianceBlock value object
└── exceptions.py        # 6 CustomerError subclasses per §8.G
```

Plus: register `customer_router` in `backend/app/main.py`.

Locked invariants:
- 5 endpoints: `GET /api/v1/profile`, `PATCH /api/v1/profile/base`, `PATCH /api/v1/profile/active-categories`, `PATCH /api/v1/profile/compliance-extension/{super_id}`, `GET /api/v1/profile/required-fields`.
- COMPLIANCE_EXTENSION_MAP = frozen dict of 6 super_ids: 26 Grocery FSSAI compulsory; 5 conditional (Books ISBN, Kids Toys BIS, Home & Kitchen appliance, Beauty license trio, etc.) per §0 premise #7 + `MVP_ARCH §12.1`.
- 3 cross-module service surfaces (locked by §2.D matrix): `get_compliance_block(user_id) -> ComplianceBlock` (consumed by export), `get_profile_completeness(user_id) -> ProfileCompleteness` (consumed by dashboard), `assert_eligible_for_super_id(user_id, super_id) -> None | raises ProfileIncompleteForCategoryError` (consumed by catalog).
- `scope_to_user(user_id)` on every repository method per §4.C — `seller_profile` is owned by customer; reads + writes always tenant-scoped.
- `profile_complete` flag = true iff all 10 base fields are present AND all `active_super_categories`' compulsory extension keys are present; recomputed on every PATCH.
- Eye-Serum case (per §8.J unit test 5): `customer` stores ONLY the 9 standard fields regardless of seller's active categories. The `compliance_shape="collapsed"` lookup is `export`'s concern per §5A.F + `MVP_ARCH §12.6`.
- NO adapter usage (pure CRUD + cache via core/cache.py).
- plan_guard NOT participating in V1.

Construction protocol:

1. **Tests first** per §8.J (5 unit + 2 integration):

   **Unit** (`backend/tests/modules/customer/`):
   - `test_profile_upsert_idempotency` — first PATCH creates row, subsequent PATCH updates same row, returns same `user_id`.
   - `test_pincode_regex_enforcement` — invalid pincodes (5 digits, 7 digits, alphanumeric) → 422 `validation.pincode.invalid_format`.
   - `test_compliance_extension_validation_per_super_id` — Grocery (`super_id=26`) requires `fssai_license_number`; missing → 422 `customer.compliance_missing_fields` with envelope listing missing keys.
   - `test_profile_complete_flag_recomputation` — true iff all 10 base + all active super extensions present; recomputed on every PATCH.
   - `test_eye_serum_case` — customer stores only 9 standard fields regardless of active categories.

   **Integration** (`backend/tests/integration/test_customer_*.py`):
   - `test_full_onboarding_flow` — sign up via §7 OTP verify → first PATCH base → first PATCH active-categories `["26"]` → first PATCH compliance/26 → `/required-fields` shows `profile_complete=true`.
   - `test_cross_module_call` — `catalog.service.create_product` calls `customer.service.assert_eligible_for_super_id(user_id, super_id)`; on profile lacking required extension → 422 `customer.profile_incomplete_for_category`.

2. **Implementation** per §8.B-§8.G with locked signatures.

3. **Acceptance**: tests pass; ruff clean; boot smoke PASS (route count up by 5); schema smoke PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT add a 7th super_id to COMPLIANCE_EXTENSION_MAP without architecture amendment.
- DO NOT skip `scope_to_user(user_id)` on any repository method.
- DO NOT import `app.modules.category.repository` or `app.modules.export.repository` — cross-module access only via `service.py`.
- DO NOT call `adapters/gemini`, `adapters/gcs`, `adapters/msg91`, `adapters/razorpay` — customer has no vendor egress.
- DO NOT implement CollapsedComplianceStrategy — that's §14 export. Customer stores 9 standard fields.
- DO NOT participate in plan_guard (not in V1 customer scope).
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch non-`meesell-*` agents.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted:
- `meesell-api-routes-builder` — owns router.py + schemas.py.
- `meesell-services-builder` — owns service.py + repository.py + domain.py + exceptions.py.

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §8)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. 5 endpoints mounted per §8.B.
2. COMPLIANCE_EXTENSION_MAP frozen dict has exactly 6 super_ids.
3. `scope_to_user(user_id)` present on every repository method (grep-verifiable).
4. 3 cross-module service methods (`get_compliance_block`, `get_profile_completeness`, `assert_eligible_for_super_id`) match locked signatures from §2.D.
5. `profile_complete` flag recomputation logic correct (10 base + active super extensions).
6. 6 CustomerError exceptions per §8.G with `validation_message_id` from §5A.
7. NO adapter imports (grep-verifiable: `from app.adapters` should not appear in modules/customer/).
8. 5 unit + 2 integration tests PASS per §8.J.

Plus universal: ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update both specialists' memory files.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §8 customer CONSTRUCTED ===
   Files created: modules/customer/{7 files}; main.py mount
   Tests added: 5 unit + 2 integration
   Decisions made: <list>
   Hand-offs: §10 catalog (consumes assert_eligible_for_super_id), §13 dashboard (consumes get_profile_completeness), §14 export (consumes get_compliance_block)
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Founder ruling needed on a 7th super_id.
- Pincode regex ambiguity (international vs Indian-only — locked at Indian 6-digit per `MVP_ARCH`).
- ComplianceBlock value object shape conflict with §14 export's expectations.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-8-customer-1`
2. Read REQUIRED READING.
3. Confirm Wave 1 + Wave 2 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §8 construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 3 of 10
- **Sequential dependency:** Wave 1 + Wave 2 complete (§5, §4, §5A, §6, §6A, §7).
- **Parallel-safe?:** Yes — runs in parallel with §9 category (08-section-9-category-construction.md). Both are leaf modules with no cross-module dependency between them.
- **Expected duration estimate:** ~8-10 hours.
- **Acceptance verification by master:** (1) `grep -c "scope_to_user" backend/app/modules/customer/repository.py` matches number of repo methods (4); (2) COMPLIANCE_EXTENSION_MAP has exactly 6 keys; (3) `grep -r "from app.adapters" backend/app/modules/customer/` returns nothing; (4) tests pass; (5) STATUS_BACKEND.md UPDATE block present.
