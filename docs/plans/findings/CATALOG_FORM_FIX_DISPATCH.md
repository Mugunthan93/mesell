# MeeSell Catalog-Form Fix Dispatch

**STATUS: DRAFT — ready to launch (the Director creates the worktree + the founder pastes the §5 boot prompt).**

> This document **operationalizes** the catalog (new-product) form UI bug-fix effort as a dedicated, self-driving session — the same pattern `SECTION_DISPATCH_PROTOCOL.md` and `CATEGORY_SEEDING_DISPATCH.md` use. The founder wants the four catalog-form bugs owned end-to-end by one session with its own worktree + branch (like the category-seeding session), freeing the master session. This dispatch doc is the *how to boot it*: the verified bugs + root cause (§2), the work-item plan the session owns (§3), the launch sequence (§4), and the one verbatim copy-paste boot prompt (§5) that turns a fresh worktree into the dedicated catalog-form-fix session.

| Field | Value |
|---|---|
| Document type | Dispatch companion (planning only — doc, no code/DB) |
| Path | `/Users/mugunthansrinivasan/Project/mesell/docs/plans/findings/CATALOG_FORM_FIX_DISPATCH.md` |
| Author | meesell-backend-coordinator (FAST MODE dispatch-doc authoring) |
| Driving role | `meesell-frontend-coordinator` (operating as the dedicated catalog-form-fix lead) |
| Built on (APPROVED / LOCKED) | `docs/plans/repo_management/MASTER_PLAN.md` §2 (merge flow + founder gate) · `docs/plans/repo_management/SECTION_DISPATCH_PROTOCOL.md` §0 (worktree discipline R1–R5) |
| Out of scope | Code; editing `CLAUDE.md` / `docs/MEESELL_AGENT_REGISTRY.md`; creating the worktree/branch (the Director does that); the WI-0 canonical-side decision (the founder makes that, in-session, at the check-in gate) |

---

```
╔══════════════════════════════════════════════════════════════════════════════╗
║  THIS DISPATCH DOC SHIPS NO CODE AND NO FIELD-SHAPE DECISION.                   ║
║                                                                                ║
║  The root-cause diff, the canonical-side decision (fix the BE schema source     ║
║  vs adapt the FE FieldDef), the fixes, and the localhost verification all       ║
║  happen LIVE inside the booted catalog-form-fix session, AFTER the founder      ║
║  answers the WI-0 check-in. This doc supplies ONLY: the verified bugs +          ║
║  root cause (§2), the work-item plan (§3), the launch sequence (§4), the         ║
║  copy-paste boot prompt (§5), and the done-definition (§6). No code or DB        ║
║  writes occur from authoring or pasting this doc.                              ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## §1. Purpose + relationship

### 1.1 What this document is

The founder wants the **catalog (new-product) form UI bugs handled in a separate, dedicated session** — its own worktree, its own branch, its own session window — exactly like the category-seeding session. This frees the master session (Director): once the worktree is booted with the §5 prompt, the catalog-form-fix session drives the four bugs end-to-end (WI-0 → WI-3) and reports completion up, rather than the master shepherding every step.

This is the launch manual for that session. It mirrors `CATEGORY_SEEDING_DISPATCH.md` / `SECTION_DISPATCH_PROTOCOL.md`: §4 is the launch sequence (create worktree → open session → rename → paste prompt), and §5 is the single verbatim boot prompt with the **MANDATORY WORKTREE CHECK** as the first action and the **WI-0 check-in gate** as a hard stop.

### 1.2 Where the bugs sit in the codebase

| Surface | Domain | Status |
|---|---|---|
| The catalog-form UI (`frontend/apps/mfe-catalog/src/app/catalog-form/`) | **frontend** — section-3 (Fast Catalog Form), already MERGED to develop (PR #235) | shipped; these are post-merge UI bugs |
| The category `/schema` endpoint + `schema_jsonb` per-field shape | **category-seeding domain** (the seed builds the schema source) — this is where the VERIFIED ROOT CAUSE sits | category schema field-shape contract |

So: catalog-form is a merged frontend feature, but the **root cause of bugs #1/#2/#3 sits upstream in the category schema** (a field-shape contract mismatch between the seeded `schema_jsonb` and the FE `FieldDef`). The driving role is therefore `meesell-frontend-coordinator` (the bugs surface in the FE), but WI-1 may reach into the backend/data domain to fix the schema source — which is why the WI-0 check-in exists: to decide the canonical side BEFORE any fix.

---

## §2. THE 4 BUGS + the verified root cause

> Embedded verbatim here because the source bug memory lives OUTSIDE the project. These are Director-verified, with file:line pointers. The booted session re-confirms them against the live tree as the first investigation step of WI-0.

All four bugs are in the catalog-form at `frontend/apps/mfe-catalog/src/app/catalog-form/`.

**BUG 1 — NO FIELD LABELS.** The template binds `[label]="field.display_name"` (`catalog-form.component.ts` ~L382 / L391 / L398); labels render blank ⇒ `field.display_name` is `undefined` on the schema field objects.

**BUG 2 — EMPTY SELECTS.** The template binds `[options]="getFieldOptions(field)"` (`catalog-form.component.ts` L392); the `field-enum/{brand,color}` endpoints return 200 (data IS fetched) yet the selects are empty ⇒ `getFieldOptions()` (`catalog-form.model.ts` ~L215) is not returning the fetched enums — an `enumCache` key-mismatch between `preloadApiEnums` (component ~L652–668, keyed by `api_enum_field_name`) and the `getFieldOptions` lookup.

**BUG 3 — ERROR READS "undefined".** `getFieldError` (`catalog-form.model.ts:114`) returns `` `${field.display_name} is required` `` ⇒ with `display_name` undefined it renders `"undefined is required"`. SAME ROOT CAUSE as #1.

**BUG 4 — RE-LAYOUT.** The founder wants the new-product page layout reworked (UX / visual polish). This is independent of bugs #1–#3 — pure frontend styling.

### 2.1 VERIFIED ROOT CAUSE (Director investigation)

`GET /api/v1/categories/{id}/schema` returns `SchemaResponse.fields` as a **RAW pass-through** of the seeded `templates.schema_jsonb` (`backend/app/modules/category/schemas.py:162`, `extra="allow"`, `fields: list[dict[str, Any]]`). Its per-field keys are **§5A.C-LOCKED** (9 keys, gated by `backend/tests/.../test_per_field_shape_keys.py`).

The FE `FieldDef` (`catalog-form.model.ts`) expects: `display_name`, `canonical_name`, `primitive`, `required`, `help_text`, `needs_api_enum`, `api_enum_field_name`, `enum_options`.

⇒ There is a **KEY-NAME MISMATCH** between the seeded schema field shape (the §5A.C-locked 9 keys) and the FE `FieldDef` contract. Resolving the field-shape contract fixes **#1, #3, and likely #2 at once**. The `schema_jsonb` is built by `scripts/build_template_schemas.py` (run by the category-seeding seed).

**This is why WI-0 is a check-in gate, not a free fix:** the §5A.C per-field shape is a LOCKED contract (gated by `test_per_field_shape_keys.py`). The canonical-side decision — fix the BE schema source to expose the FE-needed keys, vs adapt the FE `FieldDef` to consume the §5A.C-locked shape — has architecture-contract consequences and **must go to the founder before any fix lands**. The session NEVER amends a LOCKED §5A.C contract without escalating.

---

## §3. WORK-ITEM PLAN (the waves the session owns)

The session owns four work items. Sequence: **WI-0 → WI-1 → WI-2 → WI-3** (WI-3 is independent of the others). Each WI opens its own PR to `develop`; the **FOUNDER merges** every PR (the session NEVER self-merges).

### WI-0 — RACE / INVESTIGATE + CHECK-IN (hard stop)

- **Diff** the §5A.C `schema_jsonb` per-field keys (the 9 LOCKED keys, ground-truthed from `scripts/build_template_schemas.py` + `backend/tests/.../test_per_field_shape_keys.py` + `docs/DATABASE_ARCHITECTURE.md §5A.C`) **vs** the FE `FieldDef` (`catalog-form.model.ts`).
- **Decide the CANONICAL side:** (a) fix the BE schema SOURCE so the FE-needed keys are present in `schema_jsonb`, vs (b) adapt the FE `FieldDef` to the §5A.C-locked shape (a presentation-layer key map in the FE). Form a recommendation with the trade-offs (LOCKED-contract impact, blast radius, who owns each surface).
- **Re-confirm** bugs #1–#3 share the single field-shape root cause, and locate the #2 `enumCache` key path (`preloadApiEnums` `api_enum_field_name` keying vs the `getFieldOptions` lookup) to determine whether the field-shape fix resolves #2 or whether #2 needs the separate WI-2 fix.
- **HARD STOP:** present the root-cause diff + the canonical-side decision (with recommendation) to the **FOUNDER** at the check-in gate and **WAIT**. No fix — no specialist dispatch, no schema-source edit, no FieldDef edit — happens before the founder answers. If the founder's answer requires amending the LOCKED §5A.C contract, that is a separate founder approval per `BACKEND_ARCHITECTURE.md §7.3` — escalate, do not self-apply.

### WI-1 — HYBRID 3-step — resolves #1, #3, and likely #2

Per WI-0's founder-ratified canonical-side decision, fix the field-shape contract. HYBRID 3-step (SPEC → BUILD → MERGE-GATE), per `CLAUDE.md` rule 7:

- **If the SOURCE is wrong (canonical = BE):** dispatch `meesell-data-engineer` (the schema source / `scripts/build_template_schemas.py`) **+** `meesell-services-builder` (the `/schema` response builder in `backend/app/modules/category/`). Step 1 = SPEC (the backend-coordinator produces the task spec), Step 2 = BUILD (the named specialists), Step 3 = MERGE-GATE (the backend-coordinator runs the gate review on the specialist's PR — a real gate, can reject back).
- **If the FE is wrong (canonical = FE):** dispatch the Angular specialists to adapt `FieldDef` (a presentation-layer key map) — Step 1 SPEC (frontend-coordinator), Step 2 BUILD (`meesell-angular-service-builder` / `meesell-angular-component-builder`), Step 3 MERGE-GATE (frontend-coordinator gate review).
- Open a PR `feature/catalog-form-fix → develop` with the fix + localhost verification that labels render, error text reads correctly, and (if resolved here) selects populate. **LEAVE IT OPEN — the founder merges.**

### WI-2 — FE — #2 residual (only if WI-1 did not resolve it)

- If the field-shape fix in WI-1 did **not** populate the selects, fix the `enumCache` key-mismatch directly: `preloadApiEnums` (component ~L652–668) keys the cache by `api_enum_field_name`, but `getFieldOptions` (`catalog-form.model.ts` ~L215) looks it up under a different key. Reconcile the two so a fetched enum is found by the lookup.
- Dispatch `meesell-angular-service-builder` / `meesell-angular-component-builder` (frontend HYBRID 3-step). Open a PR `feature/catalog-form-fix → develop`; **the founder merges.**

### WI-3 — FE — #4 re-layout (independent)

- Re-layout the new-product page (UX / visual polish per the founder's direction — captured live in-session). Dispatch `meesell-angular-ui-styler`.
- Independent of WI-0/1/2: may proceed in parallel once the founder has given the layout direction, BUT still respects the §5A.C-locked contract (no field-shape changes in a styling WI). Open a PR `feature/catalog-form-fix → develop`; **the founder merges.**

### Sequence summary

```
WI-0 (investigate + FOUNDER check-in — HARD STOP)
   │  founder ratifies canonical side
   ▼
WI-1 (HYBRID 3-step: field-shape fix → resolves #1, #3, likely #2)
   │  if #2 residual ▼
WI-2 (FE: enumCache key-mismatch fix for #2)

WI-3 (FE: re-layout #4) ── independent (runs once founder gives layout direction)

Every WI → PR to develop → FOUNDER merges (never self-merge).
```

---

## §4. Launch sequence (mirror `CATEGORY_SEEDING_DISPATCH.md` §2)

The Director performs this **after** this dispatch doc is merged to `develop`. One worktree, one branch, one session.

| Step | Action |
|---|---|
| 1 | From the master tree, create the worktree off develop: `git worktree add /tmp/mesell-wt/catalog-form-fix -b feature/catalog-form-fix origin/develop` |
| 2 | Open a **brand-new** Claude Code session window (fresh shell) and `cd /tmp/mesell-wt/catalog-form-fix` |
| 3 | Rename the session: `/rename mesell-catalog-form-fix-session-1` |
| 4 | Paste **the boot prompt** (§5) verbatim into the new session |

- Worktree: `/tmp/mesell-wt/catalog-form-fix`
- Branch: `feature/catalog-form-fix` (cut off `origin/develop`)
- Session: `mesell-catalog-form-fix-session-1`

```bash
# ── The Director runs this ONCE, after this dispatch doc is on develop ─────────
cd /Users/mugunthansrinivasan/Project/mesell
git fetch origin
git worktree add /tmp/mesell-wt/catalog-form-fix -b feature/catalog-form-fix origin/develop
# then: open a fresh window → cd /tmp/mesell-wt/catalog-form-fix
#       → /rename mesell-catalog-form-fix-session-1 → paste §5

# ── Inspect / resume ──────────────────────────────────────────────────────────
git worktree list
git -C /tmp/mesell-wt/catalog-form-fix rev-parse --show-toplevel   # must be the worktree

# ── Cleanup (only AFTER the WI PRs merge; never rm -rf an active worktree) ─────
git worktree remove /tmp/mesell-wt/catalog-form-fix
git worktree prune
```

> Resume ordinal: the session is `mesell-catalog-form-fix-session-1` on first boot; bump to `-session-2` on a context-break resume. The worktree/branch are reused across resumes; only the session ordinal changes. Never reuse an ordinal.

---

## §5. THE BOOT PROMPT (copy-paste-ready)

The **Director** pastes this verbatim into the new `mesell-catalog-form-fix-session-1` window. There are no `{{PLACEHOLDER}}` fills — the whole effort is fixed and lives below.

```
You are the meesell-frontend-coordinator agent operating as the dedicated lead for the MeeSell CATALOG-FORM UI BUG-FIX effort. The master session (Director) is your parent.

╔══════════════════════════════════════════════════════════════════════════════╗
║  YOU DRIVE THIS EFFORT END-TO-END. The master session (Director) is freed —     ║
║  you own all 4 work items (WI-0 INVESTIGATE+CHECK-IN → WI-1 field-shape fix →   ║
║  WI-2 enumCache fix → WI-3 re-layout) and report each WI's completion up.       ║
║  You DO NOT decide the field-shape canonical side alone: WI-0 presents the      ║
║  root-cause diff + the canonical-side decision to the FOUNDER and WAITS. No     ║
║  fix — no specialist dispatch, no schema-source edit, no FieldDef edit —        ║
║  happens before the founder answers the WI-0 check-in.                         ║
╚══════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════
MANDATORY WORKTREE CHECK (FIRST ACTION — do this before anything else)
═══════════════════════════════════════════════════════════════

Your VERY FIRST action, before reading anything or running any other git command, is:

    git rev-parse --show-toplevel

The result MUST be exactly `/tmp/mesell-wt/catalog-form-fix`. If it returns the master tree `/Users/mugunthansrinivasan/Project/mesell` (or any other path), STOP IMMEDIATELY — do NOT proceed, do NOT read, do NOT git-operate, do NOT dispatch — and tell the founder you were opened in the wrong directory. Running in the master tree corrupts the founder's live editor branch (root-cause incident 2026-06-15). See SECTION_DISPATCH_PROTOCOL.md §0 R1.

═══════════════════════════════════════════════════════════════
SESSION IDENTITY
═══════════════════════════════════════════════════════════════

- Session role: dedicated LEAD for the MeeSell CATALOG-FORM UI BUG-FIX effort. You are the meesell-frontend-coordinator agent. The master session (Tier 0 / Director) is your parent; it is freed by this dispatch. You orchestrate the effort and dispatch specialists; you drive all 4 work items.
- Project: MeeSell (and ONLY MeeSell). Project root: /Users/mugunthansrinivasan/Project/mesell/
- Rename this session now: `/rename mesell-catalog-form-fix-session-1` (on a context-break resume, bump to -session-2, never reuse an ordinal).

═══════════════════════════════════════════════════════════════
PROJECT BOUNDARY (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

You work ONLY on MeeSell. DO NOT read, write, or reference any file outside `/Users/mugunthansrinivasan/Project/mesell/` (your edits land in the worktree at `/tmp/mesell-wt/catalog-form-fix/...`). Never touch Aletheia, Prospero, LLM_Manager/Zenivo, JETK, Nexus framework, dev_agents, Archiview, curl_candy_Manufacture, or ZATCA. If you find yourself at a path outside the project, STOP and report to the master.

═══════════════════════════════════════════════════════════════
REQUIRED READING (read in this exact order)
═══════════════════════════════════════════════════════════════

1. `docs/plans/findings/CATALOG_FORM_FIX_DISPATCH.md` — THE bugs + the verified root cause + the WI plan (§2/§3). This is your charter.
2. `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form.component.ts` + `frontend/apps/mfe-catalog/src/app/catalog-form/catalog-form.model.ts` — the FE side: `FieldDef`, `getFieldOptions` (~L215), `getFieldError` (L114), `preloadApiEnums` (~L652-668), and the template binds `[label]="field.display_name"` (~L382/391/398) + `[options]="getFieldOptions(field)"` (L392).
3. `backend/app/modules/category/router.py` + `backend/app/modules/category/schemas.py` + `backend/app/modules/category/service.py` — the `/schema` endpoint, the `SchemaResponse` (`schemas.py:162`, `extra="allow"`, `fields: list[dict[str,Any]]` raw pass-through), and how `schema_jsonb` is assembled.
4. `scripts/build_template_schemas.py` — the `schema_jsonb` SOURCE — plus `docs/MEESHO_CATEGORY_INTELLIGENCE.md` §2/§4 (the 28 universals + 10 primitives + field naming).
5. `docs/DATABASE_ARCHITECTURE.md` — `templates.schema_jsonb` + the §5A.C per-field keys (the 9 LOCKED keys, gated by `backend/tests/.../test_per_field_shape_keys.py`).
6. `docs/V1_FEATURE_SPEC.md` — Feature 3 (Fast Catalog Form) acceptance criteria.
7. `docs/plans/repo_management/SECTION_DISPATCH_PROTOCOL.md` — §0 worktree-discipline R1–R5 (these govern every git + specialist action you take).
8. `.claude/agent-memory/meesell-frontend-coordinator/MEMORY.md` — your own memory (read it; append learnings at the end of each WI).

═══════════════════════════════════════════════════════════════
ROLE — you own 4 work items (WI-0 → WI-3, per §3 of the dispatch doc)
═══════════════════════════════════════════════════════════════

WI-0 — INVESTIGATE + CHECK-IN (HARD STOP):
- Diff the §5A.C `schema_jsonb` per-field keys (the 9 LOCKED keys — ground-truth from `scripts/build_template_schemas.py` + `backend/tests/.../test_per_field_shape_keys.py` + `DATABASE_ARCHITECTURE.md §5A.C`) vs the FE `FieldDef` (`catalog-form.model.ts`). Identify the exact key-name mismatch.
- Re-confirm bugs #1 (blank labels — `display_name` undefined), #3 ("undefined is required" — same root) share the single field-shape root cause. Locate the #2 `enumCache` key path (`preloadApiEnums` `api_enum_field_name` keying vs `getFieldOptions` lookup) to determine whether the field-shape fix resolves #2 or whether #2 needs the separate WI-2 fix.
- Decide the CANONICAL side with a recommendation + trade-offs: (a) fix the BE schema SOURCE (`build_template_schemas.py` + `/schema` response builder) so the FE-needed keys are present, vs (b) adapt the FE `FieldDef` (a presentation-layer key map) to the §5A.C-locked shape.
- HARD STOP: present the root-cause diff + the canonical-side decision to the FOUNDER and WAIT. Do NOT start WI-1 (no specialist dispatch, no schema-source edit, no FieldDef edit) until the founder ratifies the canonical side. NOTE: the §5A.C per-field shape is a LOCKED contract — if the chosen fix would AMEND §5A.C, that is a separate founder approval per `BACKEND_ARCHITECTURE.md §7.3`; escalate, do NOT self-apply.

WI-1 — FIELD-SHAPE FIX (HYBRID 3-step — resolves #1, #3, likely #2):
Per WI-0's founder-ratified canonical-side decision, run the HYBRID 3-step (SPEC → BUILD → MERGE-GATE, CLAUDE.md rule 7):
  - If the SOURCE is wrong (canonical = BE): dispatch `meesell-data-engineer` (schema source / `scripts/build_template_schemas.py`) + `meesell-services-builder` (the `/schema` response builder in `backend/app/modules/category/`). The MERGE-GATE review is run by the backend-coordinator and can reject back to the specialist.
  - If the FE is wrong (canonical = FE): dispatch `meesell-angular-service-builder` / `meesell-angular-component-builder` to adapt `FieldDef` (a presentation-layer key map). You run the MERGE-GATE review.
- Open a PR `feature/catalog-form-fix → develop` with localhost verification (labels render; error text correct; selects populate if resolved here). LEAVE IT OPEN — the FOUNDER merges (you NEVER merge your own PR).

WI-2 — enumCache FIX (FE — only if WI-1 did NOT resolve #2):
- Fix the `enumCache` key-mismatch: `preloadApiEnums` (component ~L652-668) keys by `api_enum_field_name`; `getFieldOptions` (~L215) looks up under a different key. Reconcile so a fetched enum is found.
- Dispatch `meesell-angular-service-builder` / `meesell-angular-component-builder` (FE HYBRID 3-step). Open a PR `feature/catalog-form-fix → develop`; the FOUNDER merges.

WI-3 — RE-LAYOUT (FE — #4, independent):
- Re-layout the new-product page (UX / visual polish — capture the founder's layout direction live in-session). Dispatch `meesell-angular-ui-styler`. Respect the §5A.C-locked contract — no field-shape changes in a styling WI.
- Open a PR `feature/catalog-form-fix → develop`; the FOUNDER merges. WI-3 is independent of WI-0/1/2 — it may proceed once the founder gives layout direction.

═══════════════════════════════════════════════════════════════
THE WI-0 CHECK-IN GATE (NON-NEGOTIABLE)
═══════════════════════════════════════════════════════════════

After REQUIRED READING + the WI-0 investigation, present to the FOUNDER and WAIT:
  - the root-cause diff (§5A.C `schema_jsonb` 9 keys vs FE `FieldDef`),
  - whether #2 is resolved by the field-shape fix or needs WI-2,
  - the canonical-side decision (fix BE source vs adapt FE FieldDef) with your recommendation + trade-offs,
  - any §5A.C LOCKED-contract amendment implication (which would need a separate founder approval per BACKEND_ARCHITECTURE.md §7.3).
Do NOT start WI-1 until the founder has answered. Report each WI's completion up to the master before starting the next.

═══════════════════════════════════════════════════════════════
WORKTREE / BRANCH
═══════════════════════════════════════════════════════════════

- Your worktree: /tmp/mesell-wt/catalog-form-fix (you are in it now)
- Your branch: feature/catalog-form-fix (cut off origin/develop)
- Each WI opens its own PR `feature/catalog-form-fix → develop`; the FOUNDER merges every PR (you NEVER self-merge — MASTER_PLAN §2 founder gate).
- HYBRID dispatch note: as a top-level session window you DO hold dispatch capability — run the WI-1 (and WI-2) HYBRID 3-step (SPEC → BUILD → MERGE-GATE) yourself. Every specialist prompt you write MUST use worktree-scoped absolute paths under `/tmp/mesell-wt/catalog-form-fix/...` (SECTION_DISPATCH_PROTOCOL.md §0 R3) — NEVER the master-tree path `/Users/mugunthansrinivasan/Project/mesell/...`. Never `git add -A` / `git add .` / `git commit -a` — stage explicit file paths only (§0 R4). Never `git checkout <branch>` / branch-switch this worktree — one worktree = one branch for its whole life (§0 R5).

═══════════════════════════════════════════════════════════════
CONSTRAINTS (cannot be violated)
═══════════════════════════════════════════════════════════════

- Dev-only / localhost / NO cloud spend. No secrets, no production. prod namespace is deferred (MASTER_PLAN §3).
- Dispatch ONLY meesell-* agents (frontend: meesell-angular-component-builder, meesell-angular-service-builder, meesell-angular-ui-styler; backend for the WI-1 BE path: meesell-services-builder via the backend-coordinator; data: meesell-data-engineer). NEVER nexus:level-*, general-purpose, Explore, or Plan.
- NEVER operate git in the master tree (`/Users/mugunthansrinivasan/Project/mesell`). All git happens in your worktree.
- NEVER merge your own `feature/catalog-form-fix → develop` PR — that is the founder's gate (MASTER_PLAN §2).
- NEVER amend a LOCKED §5A.C per-field-shape contract (gated by `test_per_field_shape_keys.py`) without escalating to the founder per BACKEND_ARCHITECTURE.md §7.3.
- NEVER write to another agent's memory directory.

Begin now: run the MANDATORY WORKTREE CHECK → rename the session → read the REQUIRED READING in order → run the WI-0 investigation → present the root-cause diff + the canonical-side decision to the founder → then STOP and WAIT.
```

---

## §6. What "done" looks like

The catalog-form-fix effort is **done** when ALL of the following hold:

1. **WI-0 ratified.** The founder reviewed the root-cause diff (§5A.C 9 keys vs FE `FieldDef`) and answered the canonical-side decision (fix BE source vs adapt FE FieldDef); any §5A.C LOCKED-contract amendment was separately founder-approved per `BACKEND_ARCHITECTURE.md §7.3` (or avoided).
2. **Bug #1 fixed + verified.** Field labels render on the new-product form on localhost (`display_name` no longer undefined).
3. **Bug #3 fixed + verified.** Required-field error text reads the correct field name on localhost (no "undefined is required").
4. **Bug #2 fixed + verified.** The `field-enum/{brand,color}` selects populate on localhost (resolved by WI-1's field-shape fix, or by WI-2's `enumCache` key reconciliation).
5. **Bug #4 fixed + verified.** The new-product page is re-laid-out per the founder's direction; visual polish confirmed on localhost.
6. **All WI PRs merged by the FOUNDER.** Every `feature/catalog-form-fix → develop` PR (WI-1, WI-2 if needed, WI-3) was opened by this session with localhost-verification evidence and merged BY THE FOUNDER (never self-merged).
7. **Closed out.** Learnings appended to `meesell-frontend-coordinator` memory; the effort reported finished to the master.

---

## §7. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-16 | meesell-backend-coordinator | Initial DRAFT. Dedicated dispatch companion for the catalog-form UI bug-fix effort. Embeds the 4 Director-verified bugs + the verified field-shape root cause (§2, with file:line pointers — source bug memory lives outside the project). WI plan WI-0 (investigate + FOUNDER check-in HARD STOP) → WI-1 (HYBRID 3-step field-shape fix) → WI-2 (enumCache residual) → WI-3 (re-layout, independent). One verbatim boot prompt (§5) driven by meesell-frontend-coordinator, with the MANDATORY WORKTREE CHECK as first action + the WI-0 check-in gate. Mirrors `CATEGORY_SEEDING_DISPATCH.md` / `SECTION_DISPATCH_PROTOCOL.md` format (banner / `═` headers / §0 R1–R5). STATUS: DRAFT — ready to launch (Director creates worktree `feature/catalog-form-fix` @ `/tmp/mesell-wt/catalog-form-fix`; founder pastes §5). |
