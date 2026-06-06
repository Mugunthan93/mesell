# Sub-Session Prompt: §5A Presentation Layer Contract + i18n
# Wave 1 of 10 — CONSTRUCTION
# Specialist agent: meesell-services-builder
# Renames session to: meesell-backend-construction-5A-i18n-1

---

## How to use this file

1. Open a NEW Claude Code session.
2. `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Copy the block between START / END markers below.
4. Paste as first message. Wait for "Ready to begin §5A construction" then master's "go".

---

## ⬇ START SUB-SESSION PROMPT — COPY EVERYTHING BELOW THIS LINE ⬇

You are the meesell-services-builder agent operating in a dedicated construction sub-session for MeeSell §5A (Presentation Layer Contract + i18n).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). Master = parent Claude window owning `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md`.
- Project: MeeSell only. Root: `/Users/mugunthansrinivasan/Project/mesell/`
- Section under construction: §5A Presentation Layer Contract + i18n (templates.schema_jsonb envelope contract + i18n/ package + ~50 message IDs + resolver)
- Specialist agent: meesell-services-builder (solo — `prompt-engineer` and `legal-writer` consume `i18n/messages_en.py` for English copy but the package structure + resolver are this dispatch).
- Attempt: #1
- Sub-session naming: rename via `/rename meesell-backend-construction-5A-i18n-1`.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

MeeSell only. Never touch other projects. Stop and report if you find yourself outside `/Users/mugunthansrinivasan/Project/mesell/`.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §5A — A through J (esp. §5A.B schema_jsonb 6-key envelope, §5A.C 9-key per-field shape, §5A.D 11-input-primitive → data_type mapping, §5A.E enum_resolver semantics, §5A.F is_advanced allowlist {group_id} + compliance_shape standard|collapsed, §5A.H validation_message_id naming convention 3-segment snake_case, §5A.I i18n/ resolver fallback locale→en→verbatim-id).

2. `/Users/mugunthansrinivasan/Project/mesell/docs/BACKEND_ARCHITECTURE.md` §3 (File Structure — esp. §3.H `i18n/` subtree), §4 (core/errors.py resolver call point), §5 (shared/Settings).

3. `/Users/mugunthansrinivasan/Project/mesell/docs/MVP_ARCHITECTURE.md` §5.6 (presentation layer specs) and §5.6.7 (validation messages convention). Cited; not amended.

4. `/Users/mugunthansrinivasan/Project/mesell/CLAUDE.md` (project conventions).

5. `.claude/agents/meesell-services-builder.md` (own spec).

6. `.claude/agent-memory/meesell-services-builder/MEMORY.md` (prior session memory; `i18n/` package was started earlier per coordinator memory turn 11).

7. `/Users/mugunthansrinivasan/Project/mesell/docs/status/STATUS_BACKEND.md` (confirm §5 + §4 CONSTRUCTED).

8. `/Users/mugunthansrinivasan/Project/mesell/backend/app/` (confirm §5 + §4 done; `shared/` + `core/` packages exist).

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

Build EXACTLY the files specified by §5A of `BACKEND_ARCHITECTURE.md`. Per §3.H:

```
backend/app/i18n/
├── __init__.py
├── messages_en.py       # validation_message_id → English text (V1 ships English only)
├── resolver.py          # (validation_message_id, locale) → resolved string with fallback locale→en→verbatim-id
└── (messages_ta.py, messages_hi.py — V1.5; DO NOT create in V1)
```

Plus: wire `core/errors.py` (already constructed in §4) to `i18n/resolver.py`'s `resolve(message_id, locale="en")` function.

Plus: declare the `schema_jsonb` envelope contract — this is documentation, not Python code. The 6-key envelope (`fields[]`, `total_count`, `compulsory_count`, `optional_count`, `compliance_shape`, `template_version` per §5A.B) and the 9-key per-field shape (`canonical_name`, `data_type`, `compulsory`, `is_advanced`, `help_text`, `validation_message_id`, `enum_source`, `display_order`, `default_value` per §5A.C) are CONSUMED by category/catalog/export modules in later waves; this dispatch ensures the contract is normative and the resolver maps cleanly to it.

~50 message IDs to land in `messages_en.py`:
- 8 iam message IDs (per §7.G): `validation.phone.invalid_format`, `validation.otp.invalid_format`, `validation.webhook.malformed_payload`, `auth.otp_invalid`, `auth.otp_attempts_exceeded`, `auth.msg91_unavailable`, `auth.refresh_invalid`, `auth.webhook_signature_invalid` + 3 from core/auth.py (`auth.token_missing`, `auth.token_expired`, `auth.user_not_found`).
- 6 customer message IDs (per §8): `validation.pincode.invalid_format`, `customer.compliance_missing_fields`, `customer.profile_incomplete_for_category`, and 3 others per §8.G.
- ~4 category message IDs (per §9).
- ~5 catalog message IDs (per §10 — `validation.fields.unknown_key`, `validation.{canonical}.too_long`, `validation.{canonical}.invalid_enum_value`, `catalog.draft.missing`, `catalog.profile_incomplete_for_category`).
- 5 image message IDs (per §11): `validation.image.invalid_format`, `validation.image.too_large`, `validation.image.invalid_idx`, `image.slot_occupied`, `image.not_found`.
- 5 pricing message IDs (per §12).
- 1 dashboard message ID (per §13): `validation.dashboard.invalid_pagination`.
- 7 export message IDs (per §14): `catalog.product_not_found`, `export.product_not_ready`, `export.front_image_missing`, `export.compliance_strategy_invalid`, `export.enum_validation_failed`, `export.round_trip_mismatch`, and 1 more per §14.H.

The exact English strings for each ID are authored as part of this dispatch — coordinate with `meesell-legal-writer` if any string carries legal exposure (DPDP consent, SMS template language). Static-enum strings for special_flags `is_advanced=True` per §5A.F allowlist `{group_id}` are scoped via the per-field `is_advanced` flag — confirm `ADVANCED_CANONICAL_NAMES = {"group_id"}` set is exactly one element per session 2 G1.

The resolver fallback order is locked at §5A.I: requested `locale` → `en` → verbatim ID (last-resort string). The resolver is the single import surface for any module needing a localized string.

Construction protocol:

1. **Tests first**:
   - `test_messages_en_id_regex.py` — every key matches `^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$` per §5A.H 3-segment snake_case convention (this is also locked as CI Contract 10 in §19.C).
   - `test_resolver_fallback.py` — locale="hi" missing → returns en value; locale="en" missing → returns verbatim ID.
   - `test_schema_jsonb_envelope_keys.py` — assertion against a fixture template that the 6 top-level keys are present and types match §5A.B.
   - `test_per_field_shape_keys.py` — assertion that every `fields[]` entry has the 9 keys per §5A.C.

2. **Implementation**:
   - `messages_en.py` — flat `MESSAGES: dict[str, str]` map with all ~50 IDs as keys.
   - `resolver.py` — `resolve(message_id: str, locale: str = "en") -> str` function.
   - Wire `core/errors.py` to call `resolver.resolve(...)`.

3. **Acceptance**:
   - All unit tests pass.
   - `ruff check` clean.
   - Boot smoke test PASS.
   - DB schema smoke test PASS.

═══════════════════════════════════════════════════════════════
HARD RULES
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED architecture section.
- DO NOT add `messages_ta.py` or `messages_hi.py` in V1 (placeholder only; V1.5 per §3.H lock).
- DO NOT use camelCase message IDs — three-segment snake_case ONLY per §5A.H.
- DO NOT touch `STATUS_MASTER.md`.
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch agents outside the `meesell-*` fleet.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted: `meesell-services-builder` (solo on this section). You MAY consult `meesell-legal-writer` memory (read-only) for legally exposed strings but DO NOT dispatch them; the legal-writer is an out-of-track agent for content review only.

You ARE NOT permitted: any other dispatch.

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §5A)
═══════════════════════════════════════════════════════════════

None — no Secret Manager containers need population.

None — no latent bugs to resolve.

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA
═══════════════════════════════════════════════════════════════

1. `i18n/messages_en.py` contains ~50 IDs covering the 8 modules' validation/error message IDs.
2. Every key in `messages_en.py` matches the §5A.H regex.
3. `i18n/resolver.py` `resolve()` implements the locked fallback order (locale → en → verbatim ID).
4. `core/errors.py` wired to `resolver.resolve(...)`.
5. `schema_jsonb` envelope contract documented (in code as a TypedDict or Pydantic model + as inline comment cross-referencing §5A.B/C/D) for consumption by §9 category and §10 catalog later.
6. `ADVANCED_CANONICAL_NAMES = {"group_id"}` constant remains exactly 1 element per §5A.F + session 2 G1 lock.

Plus universal: all tests pass; ruff clean; boot + schema smoke PASS; memory updated; STATUS_BACKEND.md UPDATE block.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

1. Update `.claude/agent-memory/meesell-services-builder/MEMORY.md`.
2. Append to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §5A i18n CONSTRUCTED ===
   Files created: i18n/__init__.py, messages_en.py, resolver.py; core/errors.py wired
   Tests added: 4 unit test classes
   Decisions made: <list>
   Hand-offs: §6 adapters (no consumption) + §6A ai_ops (no consumption) + §7+ every module's exceptions.py raises with validation_message_id resolved via resolver.resolve
   Acceptance: PASS/FAIL
   =========
   ```
3. Report back to master under 400 words.

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS
═══════════════════════════════════════════════════════════════

- Schema_jsonb envelope ambiguity (e.g. compliance_shape values past `standard`/`collapsed`).
- Resolver fallback edge case (e.g. requested locale = `en` and ID missing → verbatim vs raise).
- ADVANCED_CANONICAL_NAMES expansion request.

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. `/rename meesell-backend-construction-5A-i18n-1`
2. Read REQUIRED READING.
3. Confirm §5 + §4 CONSTRUCTED.
4. Report "Context loaded. Ready to begin §5A construction." to master.

WAIT for master's "go".

## ⬆ END SUB-SESSION PROMPT — COPY EVERYTHING ABOVE THIS LINE ⬆

---

## Master session reference (NOT part of the paste)

- **Wave:** 1 of 10
- **Sequential dependency:** §5 + §4 CONSTRUCTED (resolver wires into core/errors.py).
- **Parallel-safe?:** No — Wave 1 sequential.
- **Expected duration estimate:** ~3-5 hours.
- **Acceptance verification by master:** (1) `grep -E "^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$" backend/app/i18n/messages_en.py` confirms all keys match regex; (2) count keys ≈ 50; (3) `ADVANCED_CANONICAL_NAMES = {"group_id"}` is exactly one element; (4) boot + schema smoke PASS; (5) STATUS_BACKEND.md UPDATE block present.
