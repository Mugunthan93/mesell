# Section-Wise Sub-Session Protocol

**Purpose:** This document defines how the master session spawns a sub-session for each LOCKED section of `BACKEND_ARCHITECTURE.md`. There are 26 sections total → 26 sub-sessions. Each section gets ONE dedicated sub-session that performs either CONSTRUCTION (16 code-bearing sections) or VERIFICATION/AUDIT (10 pure-documentation sections). The master session is THIS Claude window (the one that authored the architecture). Each sub-session is a separate Claude session opened specifically to execute one section's work.

**Status:** Locked 2026-06-06 (initial version); amended 2026-06-06 to add VERIFICATION shape covering the 10 non-code-bearing sections (total coverage now 26 of 26 sections).
**Authority:** Master session (founder + master Claude window).
**Applies to:** Construction of `BACKEND_ARCHITECTURE.md` sections §4 through §22A that have code deliverables.

---

## 1. Protocol Overview

### 1.1 Master vs. sub-session roles

| Role | Responsibilities |
|---|---|
| **Master session** | Owns the architecture doc; spawns sub-sessions; reviews completion reports; updates `STATUS_MASTER.md`; coordinates cross-section dependencies; resolves blockers escalated by sub-sessions |
| **Sub-session** | Executes ONE section's construction; dispatches the specialist agent(s); runs acceptance checks; updates `STATUS_BACKEND.md`; reports back to master; NEVER amends LOCKED architecture |

The master session is the ONLY session allowed to amend a LOCKED section. If a sub-session discovers an architectural ambiguity, it STOPS and escalates to master — it does NOT silently rewrite the contract.

### 1.2 The two sub-session shapes

Every one of the 26 sections gets ONE dedicated sub-session. The shape depends on whether the section is code-bearing or pure-documentation.

**Shape 1 — CONSTRUCTION sub-session (16 sections).** Writes code, runs tests, updates STATUS files. Dispatches specialist agents.

**Shape 2 — VERIFICATION sub-session (10 sections).** Writes NO code. Reads the locked section + scans the codebase for compliance. Produces an audit report. Flags non-compliance items back to master for remediation. Does NOT dispatch specialists.

Both shapes follow the same naming convention (§2), reporting protocol (§5), and lock protocol (§7). They differ in the prompt template (§3 for construction; §3A for verification) and the per-section customization table (§4 for construction; §4A for verification).

### 1.2.1 Construction sections (16) — code-bearing

| § | Section | Specialist(s) | Notes |
|---|---|---|---|
| §4 | core/ Cross-Cutting Foundation | auth-builder + services-builder | Middleware chain + auth dep + tenancy + cache + plan_guard + errors |
| §5 | shared/ Foundation Layer | database-builder + services-builder | Engine + session + Valkey factories + config + 13 models registry |
| §5A | Presentation Layer Contract + i18n | services-builder | i18n package + resolver + ~50 message IDs |
| §6 | adapters/ Third-Party Vendor Clients | services-builder | 5 adapter clients (gemini/msg91/gcs/razorpay/langfuse) |
| §6A | AI Operations Layer | services-builder + prompt-engineer (AI track) | ai_ops/ 6-file subtree + 3 workloads |
| §7 | iam module | **auth-builder** (first dispatch target) | 4 V1 auth endpoints + /me + razorpay webhook + Lua EVAL refresh + HMAC-pepper allowlist |
| §8 | customer module | routes-builder + services-builder | 5 endpoints + COMPLIANCE_EXTENSION_MAP |
| §9 | category module | routes-builder + services-builder + category-picker-builder (AI) | 5 endpoints + AI seam via §6A |
| §10 | catalog module | routes-builder + services-builder + prompt-engineer (AI) | 6 endpoints + autofill orchestration + autosave |
| §11 | image module | routes-builder + services-builder + image-precheck-builder (AI) | 2 endpoints + Celery task wrapper |
| §12 | pricing module | routes-builder + services-builder | 1 endpoint + DELETE legacy `services/pricing_engine.py` first |
| §13 | dashboard module | routes-builder + services-builder | 1 endpoint + no repository.py |
| §14 | export module | services-builder + routes-builder | 2 endpoints + 9-step Export Adapter + 15 golden fixtures |
| §18 | Celery jobs | services-builder | celery_app.py wiring + task registration |
| §19 | Test Strategy / CI | services-builder + database-builder | Import-linter TOML + 3 custom AST scanners + pytest fixtures |
| §20 | Deployment Topology | **infra-builder** | K3s YAML manifests + env-var injection + Secret Manager wiring |

### 1.2.2 Verification sections (10) — pure documentation; get an AUDIT sub-session

These 10 sections do NOT need code construction (the code is built BY the construction sections). Each gets a verification sub-session that scans the constructed codebase against the locked section's claims and produces a compliance audit report.

| § | Section | Audit subject | When to run |
|---|---|---|---|
| §0 | Architectural Premises | All 14 founder-locked decisions + D1-D4 honored in code | After all construction waves complete |
| §1 | System Topology | Deployment matches diagram; Valkey DB 0/1/2/3 allocation honored; FastAPI 2 replicas + Celery 2 replicas | After §20 deployment |
| §2 | Module Catalog | Ownership matrix is honored (8 ✓ matrix); per-module write/read tables correct; non-domain layers present | After all 8 domain modules constructed |
| §3 | File Structure | Directory tree matches §3.B; per-module 7-file canonical subtree present (with §13 + §9 exceptions) | After all modules constructed |
| §15 | Cross-Cutting Walkthrough | 10 cross-cutting concerns wired across all modules per the per-module participation matrices | After all modules constructed |
| §16 | Inter-Module Communication Rules | The 8 ✓ matrix is enforced; §16.E TOML import-linter contracts pass; 2 documented exceptions allowlisted | After §19 CI linter constructed |
| §17 | Endpoint Inventory | All 27 contract endpoints + 2 infra endpoints mounted with correct auth/rate-limit/audit attributes | After all modules constructed |
| §21 | Extraction Path | Per-module extraction readiness checklist satisfied; domain.py types are JSON-serializable; service.py surfaces stable | After all modules constructed |
| §22 | Acceptance & Sign-Off | EXECUTE the V1 acceptance checklist; map every Feature 1-9 acceptance criterion to passing tests/behaviour | LAST — after every other section's sub-session reports complete |
| §22A | Risk Register & Mitigations | All 12 mitigations are present in code/architecture; verify no risk is unmitigated | After all modules constructed |

### 1.2.3 Construction sections (16) — code-bearing (detail)

### 1.3 Recommended sub-session sequence (all 26 sections)

Per §22 acceptance + §7 "first dispatch target" lock + dependency ordering. CONSTRUCTION sub-sessions in Waves 1-7; VERIFICATION sub-sessions in Waves 8-9; final acceptance in Wave 10.

| Wave | Shape | Sections | Why this wave order |
|---|---|---|---|
| **Wave 1 — Foundation construction** | CONSTRUCTION | §5 → §4 → §5A → §6 → §6A | shared/ first (every other module imports it), then core/, then i18n, then adapters, then ai_ops |
| **Wave 2 — First domain construction** | CONSTRUCTION | §7 iam | The unblocker — every authenticated route across §8-§14 needs `get_current_user`; auth-builder is the FIRST DISPATCH per §7 + FE-D5 ratification |
| **Wave 3 — Leaf modules in parallel** | CONSTRUCTION | §8 customer + §9 category | Both are leaf on cross-module call graph; can run parallel sub-sessions |
| **Wave 4 — Spine module** | CONSTRUCTION | §10 catalog | Central spine; calls §8 + §9; called by §11 + §12 + §13 + §14 |
| **Wave 5 — Catalog dependents in parallel** | CONSTRUCTION | §11 image + §12 pricing + §13 dashboard | All call catalog; can run in parallel after catalog locks |
| **Wave 6 — Export** | CONSTRUCTION | §14 export | The most cross-module module; needs §8 + §9 + §10 + §11 all done |
| **Wave 7 — Wiring + tests + deployment** | CONSTRUCTION | §18 Celery + §19 Tests + §20 Deployment | After all modules built; final wiring |
| **Wave 8 — Foundation + module audits in parallel** | VERIFICATION | §0, §1, §2, §3, §17 (5 parallel-safe) | Foundation premises audit + topology audit + module catalog audit + file structure audit + endpoint inventory audit. All parallel-safe — read-only audit work. |
| **Wave 9 — Cross-cutting + integration audits in parallel** | VERIFICATION | §15, §16, §21, §22A (4 parallel-safe) | Cross-cutting walkthrough audit + inter-module rules audit + extraction-readiness audit + risk register audit. All parallel-safe. |
| **Wave 10 — Final acceptance** | VERIFICATION | §22 V1 acceptance checklist | LAST — runs against the completed codebase + all 9 prior wave reports; produces the V1 GO/NO-GO sign-off |

Total sub-sessions: 7 construction waves × ~1.5 sections avg = 16 construction sub-sessions, plus 9 verification + 1 final acceptance = 10 verification sub-sessions. **26 sub-sessions total** matching the 26 sections.

Waves 3 + 5 + 8 + 9 can have parallel sub-sessions (rate-limit permitting); other waves are sequential because of code or audit dependencies.

---

## 2. Sub-Session Naming Convention

Each sub-session uses the `/rename` command at the start of its session with a name following the pattern:

```
meesell-backend-construction-<section-slug>-<attempt>
```

Examples:
- `meesell-backend-construction-7-iam-1` (first attempt at §7 iam)
- `meesell-backend-construction-7-iam-2` (second attempt — if first failed acceptance)
- `meesell-backend-construction-10-catalog-1`
- `meesell-backend-construction-14-export-1`
- `meesell-backend-construction-19-tests-1`

The slug is the section's short name from §1.2 table. The attempt counter increments only if a prior attempt did not pass acceptance and needed re-dispatch.

---

## 3. The Prompt Template

Copy this template VERBATIM and fill the placeholders `{{LIKE_THIS}}` for each new sub-session. Do not omit any block — sub-sessions need every section to operate correctly.

```
You are the {{SPECIALIST_AGENT_NAME}} agent operating in a dedicated construction sub-session for MeeSell §{{SECTION_NUMBER}} ({{SECTION_NAME}}).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: SUB-SESSION (construction). The master session is the parent Claude window that authored `docs/BACKEND_ARCHITECTURE.md`. You execute; master reviews and orchestrates.
- Project: MeeSell (and ONLY MeeSell). Project root: /Users/mugunthansrinivasan/Project/mesell/
- Section under construction: §{{SECTION_NUMBER}} {{SECTION_NAME}}
- Specialist agent: {{SPECIALIST_AGENT_NAME}}
- Attempt: #{{ATTEMPT_NUMBER}}
- Sub-session naming: rename this session to `meesell-backend-construction-{{SECTION_SLUG}}-{{ATTEMPT_NUMBER}}` using `/rename`.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

You are working ONLY on the MeeSell project. DO NOT read, write, or reference any file outside `/Users/mugunthansrinivasan/Project/mesell/`. Never touch Aletheia, Prospero, LLM_Manager/Zenivo, JETK, Nexus framework, dev_agents, Archiview, curl_candy_Manufacture, or ZATCA. If you find yourself looking at a path that does not start with `/Users/mugunthansrinivasan/Project/mesell/`, STOP and report to master.

═══════════════════════════════════════════════════════════════
REQUIRED READING (read in this exact order)
═══════════════════════════════════════════════════════════════

1. `docs/BACKEND_ARCHITECTURE.md` §{{SECTION_NUMBER}} (your construction contract — the section under construction). This is normative. Build EXACTLY against the locked contract.

2. `docs/BACKEND_ARCHITECTURE.md` §{{UPSTREAM_DEPENDENCIES}} (the upstream sections this section depends on — already LOCKED). You consume their contracts; you do NOT amend them.

3. `docs/MVP_ARCHITECTURE.md` §{{MVP_ARCH_REFERENCES}} (the upstream DATA-track contracts — DDL, AI pipeline, etc.). Cited; not amended.

4. `CLAUDE.md` (project conventions section — Python 3.12, async SQLAlchemy, Pydantic v2, ruff, pytest asyncio_mode="auto").

5. `.claude/agents/{{SPECIALIST_AGENT_NAME}}.md` (your own spec).

6. `.claude/agent-memory/{{SPECIALIST_AGENT_NAME}}/MEMORY.md` (your prior session memory).

7. `docs/status/STATUS_BACKEND.md` (current backend track state).

8. `backend/app/` current on-disk state — confirm clean baseline (per §0.E lock: 9 mounted routes; 42/42 + 7/7 tests). If the baseline does NOT match this state, STOP and escalate to master.

═══════════════════════════════════════════════════════════════
CONSTRUCTION SCOPE
═══════════════════════════════════════════════════════════════

You build EXACTLY the files specified by §{{SECTION_NUMBER}} of `BACKEND_ARCHITECTURE.md`. The locked file list for this section:

{{FILE_LIST_FROM_SECTION_3.C_OR_SECTION_3.D_3.E_3.F_3.G_3.H_3.I}}

Construction protocol:

1. **Tests first** for every public surface (service methods, repository methods, route handlers). Write tests against the locked contract BEFORE writing implementation. Tests must reference the §{{SECTION_NUMBER}}.J test plan locks.

2. **Implementation second**. Build to the locked signatures (do NOT change them). Locked signatures are normative: parameter order, types, defaults, return shape — all immutable for V1.

3. **Acceptance verification** at the end:
   - All unit tests pass.
   - All integration tests pass against real Postgres + Valkey via dev tunnel (mocked vendors where appropriate per the section's test plan).
   - Import-linter contracts pass (§19 enforcement).
   - Linter clean (`ruff check`).
   - Type checker clean (`mypy` if configured).
   - Boot smoke test continues to pass (`tests/test_app_boot_integration.py`).
   - DB schema smoke test continues to pass (`tests/test_database.py`).

═══════════════════════════════════════════════════════════════
HARD RULES — WHAT YOU MAY NOT DO
═══════════════════════════════════════════════════════════════

- DO NOT amend any LOCKED section of `BACKEND_ARCHITECTURE.md`. If the contract is ambiguous, STOP and escalate to master.
- DO NOT change the locked function signatures from §{{SECTION_NUMBER}}.C / .D / .E / .F / .G / .H. V1 signatures are immutable.
- DO NOT introduce new cross-module call sites. The §2.D matrix locks 8 ✓ allowed calls; you may consume the ones authorized for §{{SECTION_NUMBER}}, never invent new ones.
- DO NOT import another module's `repository.py`, `schemas.py`, `router.py`, or `tasks.py` (per §16.C Rules 2-7).
- DO NOT import `adapters.gemini` directly — use `ai_ops.client.call_gemini` via §6A.C (per §3.G + §16.E Contract 2).
- DO NOT touch `STATUS_MASTER.md` (master session owns it).
- DO NOT touch any project outside MeeSell.
- DO NOT dispatch agents outside the `meesell-*` fleet.
- DO NOT continue past a test failure — fix the implementation OR escalate to master.

═══════════════════════════════════════════════════════════════
SPECIALIST DISPATCH PERMISSION
═══════════════════════════════════════════════════════════════

You ARE permitted to dispatch the following specialist agents during this construction:

{{ALLOWED_SPECIALIST_AGENTS_FOR_THIS_SECTION}}

You ARE NOT permitted to dispatch:
- `meesell-backend-coordinator` (the master session owns coordinator dispatches)
- Any non-`meesell-*` agent (nexus:*, general-purpose, Explore, etc.)
- Specialists for OTHER sections (e.g. if you are §7 iam, you may not dispatch §10 catalog's services-builder for catalog work)

═══════════════════════════════════════════════════════════════
PENDING SECRETS & LATENT BUGS (PER §{{SECTION_NUMBER}})
═══════════════════════════════════════════════════════════════

{{SECRETS_TO_POPULATE_DURING_THIS_DISPATCH}}

{{LATENT_BUGS_TO_RESOLVE_DURING_THIS_DISPATCH}}

═══════════════════════════════════════════════════════════════
ACCEPTANCE CRITERIA (you MUST meet ALL before reporting done)
═══════════════════════════════════════════════════════════════

{{SECTION_SPECIFIC_ACCEPTANCE_CHECKLIST}}

Plus the universal acceptance criteria:

1. All section-specific files listed in §3 subtree exist and compile.
2. All section-specific tests from §{{SECTION_NUMBER}}.J pass.
3. Import-linter contracts pass for files touched.
4. `ruff check` clean.
5. Boot smoke test still passes (`pytest backend/tests/test_app_boot_integration.py`).
6. DB schema smoke test still passes (`pytest backend/tests/test_database.py`).
7. Memory file (`.claude/agent-memory/{{SPECIALIST_AGENT_NAME}}/MEMORY.md`) updated with construction outcome.
8. `STATUS_BACKEND.md` updated with a construction-completion entry following the locked entry format from `=== UPDATE: <date> — §{{SECTION_NUMBER}} CONSTRUCTED ===`.

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

When acceptance is fully met:

1. Update `.claude/agent-memory/{{SPECIALIST_AGENT_NAME}}/MEMORY.md` with construction outcome (files created, tests added, decisions made, blockers encountered, hand-offs to next section).

2. Append an UPDATE block to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §{{SECTION_NUMBER}} {{SECTION_NAME}} CONSTRUCTED ===

   Files created: <list>
   Tests added: <list with counts>
   Decisions made: <list of non-obvious choices>
   Hand-offs to next section: <list of what downstream sections will need>
   Acceptance: <PASS or FAIL with reason>
   =========
   ```

3. Report back to master with the final summary (under 400 words):
   - Section number + name + your specialist agent name.
   - Files created (count + paths).
   - Tests added (count + pass/fail).
   - Acceptance criteria status (PASS or FAIL per criterion).
   - Any decisions made that weren't locked in the architecture (flagged as "MASTER REVIEW NEEDED" if material).
   - Hand-offs queued for the next section.
   - "Construction complete. Standing by for master review and next dispatch."

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS (STOP AND REPORT TO MASTER)
═══════════════════════════════════════════════════════════════

You MUST stop and escalate if any of the following:

- The locked contract is ambiguous (e.g. a signature has two reasonable interpretations).
- A locked dependency you need is missing or broken (e.g. §5.B `get_db` not yet implemented when you are doing §7 iam).
- A test failure that you cannot resolve without changing a locked signature.
- A cross-module call site you need is NOT in the §2.D matrix.
- A secret you need is NOT YET POPULATED in Secret Manager and the locked deployment topology does not provide a workaround.
- An import-linter rule prevents code you believe is required by the architecture.
- The on-disk baseline differs from §0.E (someone else modified it; potential conflict).
- ANY rate-limit, quota, or token-budget concern that risks blocking acceptance.

Escalation format:
```
ESCALATION TO MASTER — §{{SECTION_NUMBER}} construction
Trigger: <which trigger fired>
Context: <2-3 sentences>
Question: <what you need master to decide>
Proposed alternatives: <2-3 options if applicable>
```

═══════════════════════════════════════════════════════════════
END OF SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. Renaming the session via `/rename meesell-backend-construction-{{SECTION_SLUG}}-{{ATTEMPT_NUMBER}}`.
2. Reading the REQUIRED READING list above in order.
3. Confirming the on-disk baseline matches §0.E.
4. Reporting "Context loaded. Ready to begin §{{SECTION_NUMBER}} construction." to master.

WAIT for master's "go" before writing any code or running any dispatch.
```

---

## 4. Per-Section Customization Table

Use this table to fill the placeholders in §3 above for each new sub-session prompt.

| § | Section name | Section slug | Specialist | Upstream deps (LOCKED sections to read) | MVP_ARCH refs | Pending secrets | Latent bugs |
|---|---|---|---|---|---|---|---|
| §4 | core/ Cross-Cutting Foundation | `4-core` | `meesell-services-builder` + `meesell-auth-builder` | §0, §1, §3, §5 | §10.4 (multi-tenancy), §11 (audit) | — | — |
| §5 | shared/ Foundation Layer | `5-shared` | `meesell-database-builder` + `meesell-services-builder` | §0, §1, §3 | §2 (DDL), §10 (deployment) | — | — |
| §5A | Presentation Layer Contract + i18n | `5A-i18n` | `meesell-services-builder` | §3, §4, §5 | §5.6 (presentation layer), §5.6.7 (validation messages) | — | — |
| §6 | adapters/ Vendor Clients | `6-adapters` | `meesell-services-builder` | §0, §3, §5 | §10.8 (GCS layout) | — | — |
| §6A | AI Operations Layer | `6A-aiops` | `meesell-services-builder` + `meesell-prompt-engineer` (AI track) | §0.H (F3), §4, §5, §6 | §5 (AI pipeline), §8 (AI ops), §9.7 (guardrails) | `langfuse-secret-key` | — |
| §7 | iam module | `7-iam` | `meesell-auth-builder` (sole owner) | §0.C, §0.F (D1-D4), §4 (core/auth), §5.D (JWT vars), §6.C (msg91), §6.E (razorpay) | §10.3 (JWT claims), §11.3 (audit), §11.7 | `refresh-token-pepper`, `razorpay-webhook-secret` | — |
| §8 | customer module | `8-customer` | `meesell-api-routes-builder` + `meesell-services-builder` | §4 (core), §5, §5A, §9 (category for super_id validation) | §2.2 (DDL), §3.2 (endpoints), §12.1, §12.5, §12.6 | — | — |
| §9 | category module | `9-category` | `meesell-api-routes-builder` + `meesell-services-builder` + `meesell-category-picker-builder` (AI track) | §0.G §12.3, §0.G §12.4, §4, §5, §6A | §5.1 (Smart Picker), §6 (caching), §7 (search) | — | — |
| §10 | catalog module | `10-catalog` | `meesell-api-routes-builder` + `meesell-services-builder` + `meesell-prompt-engineer` (AI track) | §4 (core), §5, §5A, §6A, §8 (customer.assert_eligible), §9 (category.fetch_schema) | §2.4 (DDL), §3.4, §5.2 (Autofill), §11.4 (autosave), §11.6 (drafts), §12.4 | — | — |
| §11 | image module | `11-image` | `meesell-api-routes-builder` + `meesell-services-builder` + `meesell-image-precheck-builder` (AI track) | §4 (core), §5, §6.D (gcs), §6A, §10 (catalog.assert_product_ownership) | §0 #3 (4-slot rule), §2.5 (DDL), §5.3 (precheck), §10.8 (GCS layout) | — | — |
| §12 | pricing module | `12-pricing` | `meesell-api-routes-builder` + `meesell-services-builder` | §0.E (latent bug), §4 (core), §5, §9 (category.get_commission), §10 (catalog.assert_product_ownership) | §2.5 (DDL), §3.4 | — | **`services/pricing_engine.py` — DELETE first per §12.A** |
| §13 | dashboard module | `13-dashboard` | `meesell-api-routes-builder` + `meesell-services-builder` | §4 (core), §5, §8 (customer.get_profile_completeness), §10 (catalog.list_products) | §3.4 | — | — |
| §14 | export module | `14-export` | `meesell-services-builder` (heavy) + `meesell-api-routes-builder` (endpoints) | §0.G §12.2, §0.G §12.6, §0.H M10, §4, §5, §6.D (gcs), §6A.E (Layer 2), §8 (customer.get_compliance_block), §9 (category.fetch_schema + get_field_enum), §10 (catalog.get_product_for_export), §11 (image.get_image_bytes) | §5.5 (Export Adapter entire), §5.7 (round-trip + 15 fixtures), §11.7 | — | — |
| §18 | Background Jobs (Celery) | `18-celery` | `meesell-services-builder` | §3.I (workers/celery_app.py), §3.C tasks.py, §5.C (Valkey factories), §11 (image task), §14 (export task) | — | — | — |
| §19 | Test Strategy / CI | `19-tests` | `meesell-services-builder` + `meesell-database-builder` | §16.E (import-linter TOML), §15.B (scope_to_user enforcement), §14.J (M10), §5A.H (message_id regex) | §5.7 (round-trip 15 fixtures), §8.5 (3 AI eval golden sets) | — | — |
| §20 | Deployment Topology V1 | `20-deployment` | `meesell-infra-builder` | §1.B (topology), §5.D (env vars), §6A.F (LangFuse), §4.G (CORS) | §10 (deployment), §10.8 (GCS) | All 3 pending secrets get populated here | — |

---

## 3A. The VERIFICATION Prompt Template

Copy this template VERBATIM for the 10 audit sub-sessions. Fill the placeholders `{{LIKE_THIS}}`.

```
You are operating in a dedicated VERIFICATION sub-session for MeeSell §{{SECTION_NUMBER}} ({{SECTION_NAME}}).

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: VERIFICATION SUB-SESSION (audit/compliance). The master session is the parent Claude window that authored `docs/BACKEND_ARCHITECTURE.md`. You audit; master reviews findings and orchestrates remediation.
- Project: MeeSell (and ONLY MeeSell). Project root: /Users/mugunthansrinivasan/Project/mesell/
- Section under verification: §{{SECTION_NUMBER}} {{SECTION_NAME}}
- Sub-session naming: rename to `meesell-backend-verification-{{SECTION_SLUG}}-{{ATTEMPT_NUMBER}}` via `/rename`.

You write NO production code. You produce an audit report.

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

Same as construction sub-sessions — MeeSell only. Read /Users/mugunthansrinivasan/Project/mesell/ files only. Touch no project outside MeeSell.

═══════════════════════════════════════════════════════════════
REQUIRED READING (in order)
═══════════════════════════════════════════════════════════════

1. `docs/BACKEND_ARCHITECTURE.md` §{{SECTION_NUMBER}} (the section being audited — this is the spec; codebase MUST honor it).
2. `docs/BACKEND_ARCHITECTURE.md` §{{RELATED_SECTIONS}} (the sections whose code is being audited against §{{SECTION_NUMBER}}'s claims).
3. `docs/status/STATUS_BACKEND.md` — confirm prior wave sub-sessions reported CONSTRUCTED.
4. `docs/status/STATUS_MASTER.md` — confirm prior wave milestones reached.
5. `backend/app/` — the constructed codebase you are auditing.
6. `backend/tests/` — the tests you are auditing.

═══════════════════════════════════════════════════════════════
VERIFICATION SCOPE
═══════════════════════════════════════════════════════════════

You audit the codebase against the locked claims of §{{SECTION_NUMBER}}. Your deliverable is a compliance report — NOT code.

Audit checklist for this section:

{{SECTION_SPECIFIC_AUDIT_CHECKLIST}}

Plus the universal verification checks:

1. No regressions — `pytest backend/tests/test_app_boot_integration.py` still passes.
2. No regressions — `pytest backend/tests/test_database.py` still passes.
3. All import-linter contracts pass.
4. STATUS_BACKEND.md has CONSTRUCTED entries for every prior-wave section this audit depends on.

═══════════════════════════════════════════════════════════════
HARD RULES — WHAT YOU MAY NOT DO
═══════════════════════════════════════════════════════════════

- DO NOT write production code. Verification sub-sessions are READ-ONLY against `backend/app/`.
- DO NOT amend any LOCKED section of `BACKEND_ARCHITECTURE.md`. If audit finds the contract itself is wrong, STOP and escalate to master.
- DO NOT dispatch construction specialists (`meesell-services-builder`, `meesell-auth-builder`, etc.). Verification does not dispatch.
- DO NOT modify the codebase to fix non-compliance — you REPORT non-compliance; master decides remediation.
- DO NOT touch STATUS_MASTER.md (master owns).
- DO NOT touch any project outside MeeSell.

You MAY:
- Read any file under /Users/mugunthansrinivasan/Project/mesell/.
- Run `grep`, `find`, `pytest --collect-only`, `ruff check --no-fix`, `mypy`, and other read-only inspection tools.
- Run the import-linter and report which contracts pass/fail.
- Run the §22 acceptance checklist queries (read-only).
- Append an audit-report entry to `STATUS_BACKEND.md` (per §5.3 below).

═══════════════════════════════════════════════════════════════
DELIVERABLE FORMAT — Audit Report
═══════════════════════════════════════════════════════════════

Produce a markdown audit report following this structure:

```
# §{{SECTION_NUMBER}} {{SECTION_NAME}} Audit Report
**Date:** YYYY-MM-DD
**Auditor sub-session:** meesell-backend-verification-{{SECTION_SLUG}}-{{ATTEMPT_NUMBER}}
**Overall verdict:** PASS | PARTIAL | FAIL

## Audit checklist results

| # | Check | Status | Evidence |
|---|---|---|---|
| 1 | <check from audit checklist> | PASS / FAIL / N/A | <grep result, test name, file path, line number> |
| ... | | | |

## Non-compliance findings (if any)

For each failure:
- **Finding:** <one-line description>
- **Locked claim:** <quote from §{{SECTION_NUMBER}}>
- **Actual code:** <grep result or file:line>
- **Severity:** CRITICAL | HIGH | MEDIUM | LOW
- **Recommended remediation:** <what construction sub-session needs to amend>

## Verdict rationale

<2-3 sentences explaining the overall verdict>

## Hand-back to master

<list of items master must orchestrate: re-dispatch construction sub-sessions, amend architecture, etc.>
```

═══════════════════════════════════════════════════════════════
HAND-OFF PROTOCOL
═══════════════════════════════════════════════════════════════

When audit completes:

1. Save the audit report at `docs/audits/§{{SECTION_NUMBER}}_{{SECTION_SLUG}}_audit_<YYYY-MM-DD>.md`.

2. Append a one-paragraph UPDATE block to `docs/status/STATUS_BACKEND.md`:
   ```
   === UPDATE: <YYYY-MM-DD> — §{{SECTION_NUMBER}} {{SECTION_NAME}} AUDITED ===

   Verdict: PASS / PARTIAL / FAIL
   Critical findings: <count>
   Audit report: docs/audits/§{{SECTION_NUMBER}}_{{SECTION_SLUG}}_audit_<YYYY-MM-DD>.md
   Hand-back to master: <list>
   =========
   ```

3. Report back to master (under 300 words):
   - Section + verdict.
   - Critical/high findings summary.
   - Recommended remediation.
   - "Audit complete. Standing by for master decision."

═══════════════════════════════════════════════════════════════
ESCALATION TRIGGERS (STOP AND REPORT TO MASTER)
═══════════════════════════════════════════════════════════════

- The locked claim being audited is itself ambiguous (e.g. §X.B states "every PATCH endpoint emits audit event" but does not specify the event name — the audit cannot reach a verdict).
- A prior-wave construction section is missing or unconstructed (audit cannot run against missing code).
- Audit finds the locked contract is technically impossible (e.g. §X claims a behaviour that physically cannot be implemented in V1 stack).
- More than 5 critical findings (escalate before continuing — likely systemic issue requiring construction re-dispatch).

Escalation format same as construction sub-sessions.

═══════════════════════════════════════════════════════════════
END OF VERIFICATION SUB-SESSION PROMPT
═══════════════════════════════════════════════════════════════

Begin by:
1. Renaming the session: `/rename meesell-backend-verification-{{SECTION_SLUG}}-{{ATTEMPT_NUMBER}}`
2. Reading the REQUIRED READING list.
3. Confirming prior-wave construction sections have CONSTRUCTED entries in STATUS_BACKEND.md.
4. Reporting "Audit context loaded. Ready to begin §{{SECTION_NUMBER}} verification." to master.

WAIT for master's "go" before running any audit queries.
```

---

## 4A. Per-Section Verification Customization Table

Use this table to fill the placeholders for each of the 10 audit sub-sessions.

| § | Section name | Slug | Related sections (whose code is audited) | Section-specific audit checklist |
|---|---|---|---|---|
| §0 | Architectural Premises | `0-premises` | All — every constructed section | (1) 14 founder-locked decisions honored in code; (2) D1-D4 verifiable (D1: no .legacy.py.bak files exist; D2: `ADVANCED_CANONICAL_NAMES = {"group_id"}` exactly; D3: §3.4 amendment applied; D4: no specialist code in master-session history); (3) 27-endpoint count verifiable via `grep -r "@router\." backend/app/modules/`; (4) 13-table baseline matches Alembic head `f31c75438e61`; (5) Backend tree clean-state baseline preserved; (6) All 6 philosophy commitments visible in code (M7 enum guardrail · M9 i18n · M10 Meesho leak rules · F3 3-layer guardrail · F4 9-not-12 compliance · F5 every field has help_text) |
| §1 | System Topology | `1-topology` | §20 deployment | (1) FastAPI 2 replicas + Celery 2 replicas per K3s manifest; (2) Valkey DB 0/1/2/3 allocation honored in `shared/valkey.py`; (3) Postgres at head `f31c75438e61` + 13 tables; (4) GCS bucket layout `meesell-images/{user_id}/...` + `meesell-exports/{user_id}/...`; (5) Traefik ingress + cert-manager on `studio.mesell.xyz`; (6) Gemini + MSG91 + Razorpay + LangFuse egress endpoints reachable from FastAPI |
| §2 | Module Catalog | `2-modules` | All 8 domain modules + 5 non-domain layers | (1) All 8 modules + 5 non-domain layers exist in `backend/app/`; (2) 8 ✓ cross-module matrix honored (no `✗` cell crossed); (3) per-module owned-table writes match (e.g. only `customer` writes `seller_profile`); (4) per-module global-table reads match (only `category` reads `templates`/`categories`/`field_enum_values`/`field_aliases`); (5) Dashboard has NO `repository.py`; (6) Category repository has NO `user_id` parameter; (7) Adapters consumed only by enumerated modules |
| §3 | File Structure | `3-files` | §16 inter-module rules | (1) `backend/app/` tree matches §3.B; (2) Each domain module has the 7-file canonical subtree (exception: dashboard 5 files; iam/customer/category/pricing/dashboard have no tasks.py); (3) `core/` 6 files + middleware subdir per §3.D; (4) `shared/` 4 files + models/ per §3.E; (5) `adapters/` 5 files per §3.F; (6) `ai_ops/` 6 files per §3.G; (7) `i18n/` package per §3.H; (8) `workers/celery_app.py` per §3.I; (9) `tests/` mirrors `app/` per §3.J |
| §15 | Cross-Cutting Walkthrough | `15-crosscutting` | §4, §6A, §7-§14 | (1) Multi-tenancy 3-layer defense present (scope_to_user in 7 repositories + assert_product_ownership cross-call + GCS path prefix); (2) Caching `core/cache.py` is sole Valkey access; (3) pg_trgm GIN indexes live; (4) Audit middleware + 7 documented direct-write exceptions implemented; (5) AI Ops single import surface (`ai_ops.client.call_gemini`) + 3 workloads + 3-layer guardrail + ₹500 cap + graceful fallback per workload; (6) Plan_guard 4 resources enforced; (7) FE-D5 refresh allowlist HMAC + Lua EVAL working; (8) CSRF posture verified (no CSRF middleware); (9) Observability `request_id` + Prometheus + LangFuse all firing; (10) i18n ~50 message IDs populated |
| §16 | Inter-Module Rules | `16-rules` | §19 CI linter | (1) 8 allowed cross-module calls present in code; (2) `repository.py` PRIVATE — no cross-module imports; (3) `schemas.py` PRIVATE — no cross-module imports; (4) `adapters.gemini` ONLY consumed via `ai_ops.client`; (5) `ai_ops.*` ONLY consumed by category/catalog/image; (6) `router.py` + `tasks.py` never cross-module imported (only main.py + celery_app.py register them); (7) Dashboard no-repository exception allowlisted; (8) Category no-user_id exception allowlisted; (9) All 7 import-linter contracts + 3 custom AST scanners pass in CI |
| §17 | Endpoint Inventory | `17-endpoints` | All 8 domain modules + §7 infrastructure | (1) All 27 contract endpoints mounted (verifiable via OpenAPI `/openapi.json` + `app.routes`); (2) 2 infrastructure endpoints mounted (`/me` + `/webhooks/razorpay`); (3) Each endpoint has the locked auth posture (22 JWT / 2 cookie / 2 none / 1 HMAC); (4) Each endpoint has the locked rate-limit decorator; (5) Each endpoint emits the locked audit event (or is in the documented NONE / direct-write set); (6) Plan_guard resources locked at §4.E enforced on the 3 plan-gated endpoints |
| §21 | Extraction Path | `21-extraction` | All 8 domain modules | (1) Every cross-module `domain.py` return type is JSON-serializable (no UUID/datetime/Decimal without conversion); (2) Every `service.py` public method has a stable signature (no `**kwargs`, no positional-only without defaults); (3) `core/extracted_clients/` directory does NOT exist in V1 (V1.5 landing zone — must be empty); (4) Per-module extraction readiness: data-layer migration plan documented in section's §K; (5) §21 8-step extraction order documented + consistent with §16.H |
| §22A | Risk Register | `22A-risks` | All 8 domain modules + §6A + §15 + §19 | (1) All 12 risk mitigations present in code/architecture: R1 3-layer guardrail · R2 server-side pagination + cache · R3 ComplianceStrategy dispatch · R4 round-trip golden fixtures · R5 wizard step progress bar (frontend; backend wizard_step_count populated) · R6 onboarding shows FSSAI requirement · R7 alias reverse map (`field_aliases.for_xlsx_export = TRUE`) · R8 isolation regression tests + scope_to_user linter · R9 fallback to PG on cache miss · R10 daily ₹500 cap + per-workload fallback · R11 HMAC pepper + Lua EVAL · R12 pricing_engine.py deletion path locked; (2) No risk is left unmitigated |
| §22 | Acceptance & Sign-Off | `22-acceptance` | All 26 sections + 8 prior verification audits | EXECUTE the full V1 acceptance checklist from §22.B: (F1) Auth/OTP — 4 endpoints + /me + razorpay capture; (F2) Smart Picker — top-5 with guardrails + fallback; (F3) Catalog wizard — 6 endpoints + autosave + draft recovery; (F4) AI Auto-fill — Layer 2 retry + 200 graceful fallback; (F5) Image precheck — 5-step Celery pipeline + watermark informational-not-blocking; (F6) Preview — composes 3 modules; (F7) Price Calculator — P&L + 3 alert codes; (F8) Dashboard — paginated + profile_completeness; (F9) XLSX Export — 9-step pipeline + 15 golden fixtures pass + Layer 3 guardrail; (cross-cutting) 27 endpoints + ~50 i18n + 10 CI gates + multi-tenant isolation + 4 perf budgets + 3 Secret Manager populated + 80%/100% coverage + 3 AI eval sets pass; this is the GO/NO-GO sign-off |

---

## 5. Reporting Back Protocol

When a sub-session completes (or escalates), the master session receives the report and must:

### 5.0 NON-NEGOTIABLE — Architecture-doc edit prohibition (founder-ratified 2026-06-07)

Sub-sessions **MUST NOT edit `docs/BACKEND_ARCHITECTURE.md`** under any circumstance. This rule is absolute and admits no exceptions. The architecture doc is the LOCKED construction contract and may be amended **only** through the §5.2 path "Bug in the locked contract" where **master** performs the amendment after **founder** ratification.

**Required escalation when a sub-session discovers a dependency conflict, prose error, or any condition that would seem to motivate amending the architecture doc:**

1. Sub-session STOPS construction immediately. Does NOT touch `docs/BACKEND_ARCHITECTURE.md`.
2. Sub-session writes a SHORT escalation note to its sub-session memory or status capture: section + sub-section + exact conflict description + proposed amendment.
3. Sub-session reports back to master with verdict `ESCALATE` (not PASS, not FAIL) and the escalation note.
4. Master surfaces the conflict to founder with options.
5. Founder rules.
6. If founder ratifies the amendment: **master** edits the architecture doc with an `**AMENDMENT YYYY-MM-DD**` block under the affected sub-section, then re-dispatches the sub-session to continue.
7. If founder rejects the amendment: master directs the sub-session to implement the spec as locked (with any newly-coordinated cross-section work that the original spec actually required).

**One-time historical exception (§13.A.1, founder-ratified 2026-06-07 post hoc):** the `meesell-backend-construction-13-dashboard-1` sub-session edited the architecture doc and self-attributed founder ruling. The technical amendment was sound and was post-ratified by the founder; the process violation was documented in STATUS_MASTER Master Decisions Log. This rule (§5.0) is the codified guardrail so the same path cannot be taken again. Any future sub-session that edits `docs/BACKEND_ARCHITECTURE.md` directly will have its work **rolled back unconditionally**, even if the technical change is correct — the protocol violation is treated as a hard failure.

**Scope of this prohibition:** `docs/BACKEND_ARCHITECTURE.md` only. Sub-sessions ARE permitted (per protocol §5.1) to write `docs/status/STATUS_BACKEND.md` (append-only, no header restructure), their own sub-session memory file, code files in `backend/app/modules/<section>/`, and routine touch points (`app/main.py`, `app/workers/celery_app.py`, etc.) per the section dispatch prompt.

### 5.1 If acceptance PASSED

1. Run the universal acceptance checks (re-verify on master's side):
   - `grep -c "^STATUS: LOCKED" docs/BACKEND_ARCHITECTURE.md` — should still be 26
   - `pytest backend/tests/test_app_boot_integration.py` — should still pass
   - `pytest backend/tests/test_database.py` — should still pass
   - `cat docs/status/STATUS_BACKEND.md | tail -50` — should contain the new construction-completion entry
2. Update `docs/status/STATUS_MASTER.md`:
   - Update the "Last update" line to mention this section's construction
   - Update the BACKEND row to reflect the new code-level state (e.g. "iam module CONSTRUCTED" added to the LOCKED architecture state)
   - Append a Master Decisions Log entry: `=== UPDATE: <date> — §X {{section_name}} CONSTRUCTED ===` with the high-level summary
3. Save a memory entry to `.claude/agent-memory/nexus-level-0-director/` for cross-session continuity.
4. Determine the next dispatch target per the §1.3 wave sequence.
5. Report back to founder: "§X complete. Ready to dispatch next §Y or wave Z?"

### 5.1A If verification verdict is PASS

1. Read the audit report at `docs/audits/§X_<slug>_audit_<date>.md`.
2. Re-verify spot-check on 2-3 audit checklist items master picks randomly.
3. Update `docs/status/STATUS_MASTER.md`:
   - Update "Last update" line to mention the audit
   - Append Master Decisions Log entry: `=== UPDATE: <date> — §X {{section_name}} AUDIT PASS ===`
4. Determine the next sub-session per the §1.3 wave sequence.
5. If this was Wave 10 (§22 acceptance) and the verdict is PASS → backend V1 is signed off; report to founder.

### 5.1B If verification verdict is PARTIAL or FAIL

1. Read the non-compliance findings.
2. For each finding:
   - If **construction bug** (code does not honor the locked contract) → dispatch the responsible construction sub-session as attempt #N+1 with the audit finding as the fix scope.
   - If **architecture ambiguity** (the locked claim cannot be unambiguously verified) → master amends the LOCKED section with an `**AMENDMENT YYYY-MM-DD**` block, then re-dispatches the verification sub-session.
   - If **out-of-scope risk** (audit finds a real V1 problem not foreseen) → escalate to founder for ruling on V1 vs V1.5 scope decision.
3. Re-dispatch the verification sub-session as attempt #N+1 after remediation.

### 5.2 If acceptance FAILED or sub-session ESCALATED

1. Do NOT update STATUS_MASTER.md as "complete" — flag as in-flight.
2. Read the sub-session's failure or escalation summary.
3. Decide:
   - **Bug in implementation** → ask the sub-session to fix and re-run acceptance (attempt #2).
   - **Bug in the locked contract** → master AMENDS the LOCKED section (the only allowed amendment path), records the amendment as an "AMENDMENT YYYY-MM-DD" block under the affected sub-section, then re-dispatches the sub-session.
   - **Cross-section blocker** → master coordinates the blocking section's construction first, then re-dispatches.
   - **External blocker** (e.g. a Secret Manager container truly not provisionable) → master escalates to founder for ruling.

---

## 6. Parallel Dispatch & Rate-Limit Posture

Some waves allow parallel sub-sessions:

- **Wave 3 (§8 customer + §9 category)** — leaf modules; no cross-module dependency between them; can run parallel
- **Wave 5 (§11 image + §12 pricing + §13 dashboard)** — all call catalog (which is locked by now); can run parallel

Master session is responsible for:
- Coordinating starts (kick off N parallel sub-sessions at the same wave)
- Tracking completions (each sub-session reports independently; master accumulates)
- Resolving conflicts (if two parallel sub-sessions touch the same shared file like `app/main.py` for router registration, master serializes the registration step)

For rate-limit health:
- Default cadence is **one sub-session at a time** unless the founder explicitly authorizes parallel
- Parallel sub-sessions consume independent Claude session contexts; the founder's overall quota must accommodate
- If founder runs N>1 parallel sub-sessions, master tracks them via the sub-session naming convention and the §5.1 acceptance check sequence; first one to report acceptance triggers master's first STATUS_MASTER update

---

## 7. Lock Protocol for Construction Phase

The architecture lock protocol (per master directive 2026-06-06) carries through to construction with one extension:

A section is **CONSTRUCTED** when:
1. The architecture's §X.J test plan is implemented and passing.
2. The universal acceptance checks pass.
3. STATUS_BACKEND.md carries a `=== UPDATE: ... §X CONSTRUCTED ===` entry.
4. STATUS_MASTER.md BACKEND row reflects the new construction milestone.
5. Memory files (specialist + master) are updated.

The architecture's STATUS line remains `LOCKED (2026-06-05)` or `LOCKED (2026-06-06)` — it does NOT change to "CONSTRUCTED". The construction milestone lives in STATUS_BACKEND.md and STATUS_MASTER.md only.

If a section is amended during construction (per §5.2 case "bug in the locked contract"), the architecture's STATUS line stays LOCKED and an inline `**AMENDMENT YYYY-MM-DD — <reason>:**` block is added under the affected sub-section. The amendment is the audit trail; the section is not unlocked.

---

## 8. Example: First Dispatch Prompt (§7 iam)

Filling in the template for the first construction sub-session — `meesell-backend-construction-7-iam-1`:

```
You are the meesell-auth-builder agent operating in a dedicated construction sub-session for MeeSell §7 (iam module).

[... full template from §3 with placeholders filled:
  SPECIALIST_AGENT_NAME = meesell-auth-builder
  SECTION_NUMBER = 7
  SECTION_NAME = iam module
  SECTION_SLUG = 7-iam
  ATTEMPT_NUMBER = 1
  UPSTREAM_DEPENDENCIES = §0.C, §0.F (D1-D4), §4 (core/auth), §5.D (JWT vars), §6.C (msg91), §6.E (razorpay)
  MVP_ARCH_REFERENCES = §10.3, §11.3, §11.7
  FILE_LIST_FROM_SECTION_3 = backend/app/modules/iam/{router.py, service.py, repository.py, schemas.py, domain.py, exceptions.py}
                              + backend/app/core/auth.py (the get_current_user dep — §4.B)
                              + backend/app/core/middleware/auth_mw.py
                              + backend/app/i18n/messages_en.py (8 iam-specific message IDs)
  ALLOWED_SPECIALIST_AGENTS = (none — meesell-auth-builder works solo on iam)
  SECRETS_TO_POPULATE = `refresh-token-pepper`, `razorpay-webhook-secret` — coordinate with meesell-infra-builder before constructing
  LATENT_BUGS = (none for iam)
  SECTION_SPECIFIC_ACCEPTANCE_CHECKLIST = §7.J 4 unit + 3 integration test classes (refresh allowlist write on verify, refresh validation 4 cases, logout idempotency + cookie clear, constant-time comparison, full silent-refresh flow, logout revocation, replay-attack mitigation)
... ]
```

The master session pastes the filled template into the new sub-session window (or hands it to the founder to paste). The sub-session boots, loads context, and reports "Ready to begin §7 construction."

---

## 9. Construction Wave Tracking

Master session maintains the wave tracking in `STATUS_MASTER.md` under the BACKEND row:

```
| BACKEND | ... | 🟢 CONSTRUCTION IN PROGRESS · Architecture 100% LOCKED · Wave 1/8: §5 shared CONSTRUCTED · §4 core/ CONSTRUCTED · §5A i18n CONSTRUCTED · §6 adapters CONSTRUCTED · §6A ai_ops CONSTRUCTED · Wave 2/8: §7 iam IN-FLIGHT (sub-session meesell-backend-construction-7-iam-1) |
```

As waves complete, master updates the row in place. When all 8 waves complete, the row flips to `✅ V1 CONSTRUCTION COMPLETE`.

---

## 10. Document Maintenance

This protocol is maintained by the master session. Amendments to the protocol itself:
- Master appends an `=== AMENDMENT: <YYYY-MM-DD> ===` block at the end of this document
- The amendment is announced in the next STATUS_MASTER.md Master Decisions Log entry
- Sub-sessions follow the latest version of this protocol at dispatch time
- A sub-session may NOT modify this protocol — only master amends.

---

**End of protocol.**
