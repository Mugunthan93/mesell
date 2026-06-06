# Frontend Feature Sub-Session — Base Bootstrap Prompt

**This document is the SHARED BASE for all 6 frontend feature sub-sessions** (auth, onboarding, profile, dashboard, catalog, cross-cutting).

Per-session prompts (`docs/SESSION_PROMPTS_FEATURE_<NAME>.md`) reference this base and add session-specific scope. Do NOT bootstrap a session with just this base — pair it with the session-specific prompt.

---

## Common bootstrap structure (every session prompt embeds this pattern)

Every per-session bootstrap prompt has the same shape:
1. Identity declaration (which sub-session)
2. Master + relationship to other sessions
3. Mandatory reads on first action
4. Scope (IN) — what this session owns
5. Scope (OUT — defer to other sessions)
6. Agent dispatch rights
7. Communication protocol with master + sibling sessions
8. First action

Per-session prompts override 1, 4, 5, 6, 8; inherit 2, 3, 7 from this base.

---

## Universal master + sibling map (inherited by every session)

```
MASTER: meesell-frontend-coordinator session
   ├─ Design system sub-session (active; FE-D11) — owns docs/DESIGN_SYSTEM_ARCHITECTURE.md
   │
   ├─ auth sub-session (FE-D12 grouping)         — owns features/auth/ + features/landing/
   ├─ onboarding sub-session                     — owns features/onboarding/
   ├─ profile sub-session                        — owns features/profile/
   ├─ dashboard sub-session                      — owns features/dashboard/
   ├─ catalog sub-session                        — owns features/{smart-picker, catalog-form, images, preview, pricing, export}/
   └─ cross-cutting sub-session                  — owns app/core/ + app/shared/
```

Each sub-session corresponds to a future Phase 2 MF remote per FE-D13.

---

## Universal mandatory reads (every session reads these on first action)

1. **Your own STATUS file** — `docs/status/STATUS_FEATURE_<YOUR-SESSION>.md` (read first to see prior state)
2. **docs/FRONTEND_ARCHITECTURE.md** — the full construction contract, fully LOCKED:
   - §0 Premises (founder rulings FE-D1 through FE-D13)
   - §2 Feature Catalog (your responsibility scope per the sub-session ownership map)
   - §3 File Structure (your code root; uniform 7-file pattern per §3.D)
   - §4 core/ Cross-Cutting Foundation (LOCKED — you CONSUME but do not modify unless you are the cross-cutting session)
   - §5 shared/ (LOCKED — you CONSUME but do not modify unless you are the cross-cutting session)
   - §5A Design System (PARTIAL LOCK — values pending design system sub-session; you consume CSS custom properties)
   - §17 Service-Component Communication Rules (NO cross-feature imports; only @core/* + @shared/* + @design-system/* allowed)
   - §18 11 Primitives + Form Renderer (LOCKED — catalog session implements; other sessions reference)
   - §19 Test Strategy & Performance Budget
   - §23 Route Inventory (your routes)
   - The per-feature section that locks YOUR feature contract (§7 auth, §9 dashboard, §10 smart-picker, §11 catalog-form, §12 images, §13 preview, §14 pricing, §15 export — your session-specific prompt names which)
3. **docs/MVP_ARCHITECTURE.md** — DATA track's source of truth (read §2 DDL + §3 API + §11 hand-off contracts for the endpoints your feature consumes)
4. **docs/BACKEND_ARCHITECTURE.md** — the relevant backend module section(s) for the API contracts you consume (your per-session prompt names which)
5. **docs/CORE_PHILOSOPHY.md** — M1, M3, M7, M9, F1, F5 (the rules your code MUST honour)
6. **docs/status/STATUS_FRONTEND.md** — the master's STATUS file for cross-track context
7. **docs/status/STATUS_DESIGN_SYSTEM.md** — to know if design tokens are PARTIAL (placeholders) or FULL (ratified values)
8. **Your own agent memory** — `.claude/agent-memory/meesell-angular-component-builder/MEMORY.md` (the specialist you dispatch — read for prior session learnings)

---

## Universal communication protocol (inherited by every session)

**Reading from master:**
- Master's STATUS file (`docs/status/STATUS_FRONTEND.md`) is read once at bootstrap; thereafter on master-notify only
- FRONTEND_ARCHITECTURE.md is the binding contract; if anything seems ambiguous, surface to master via Q&A section in your STATUS file — do NOT improvise

**Reading sibling sub-sessions:**
- Sibling STATUS files (`docs/status/STATUS_FEATURE_*.md`) may be read for cross-session integration context
- Do NOT write to sibling STATUS files
- Do NOT modify code outside your scope (per FE-D12 + §17)

**Writing your own STATUS file:**
- Append an UPDATE block on every meaningful change (round start, dispatch, dispatch return, review, hand-off, completion)
- Format mirrors master's STATUS_FRONTEND format (Phase / Done / In progress / Blockers / Next / Hand-offs / Updates Log)

**Questions for master:**
- Surface in `## Questions for master` section at the bottom of your STATUS file
- Master polls on next master-session turn and answers below the question
- Do NOT block on the question — note the answer is pending and continue work in another area if possible

**Cross-session dependency questions:**
- Surface in your STATUS file's `## Questions for sibling sessions` section, named to the target session
- Sibling sessions read their own STATUS first; master may relay if needed

---

## Universal agent dispatch rights

| Agent | Tier | Sessions allowed to dispatch | Purpose |
|---|---|---|---|
| `meesell-angular-component-builder` | sonnet (default) | All 6 feature sub-sessions | Implement component bodies for THIS session's scope |
| `meesell-angular-ui-styler` | opus (per FE-D10) | Design system sub-session ONLY | Curation + compose phases |
| `meesell-angular-service-builder` | sonnet | None right now (service-builder dispatch is complete — scaffold landed 2026-06-05) | Service layer is done; if a new core/ service is needed, the cross-cutting session re-dispatches |
| All non-meesell agents | n/a | NEVER | Per CLAUDE.md ecosystem rule 1 |

**Dispatch prompt template** (every per-session dispatch includes):
```
PROJECT BOUNDARY: /Users/mugunthansrinivasan/Project/mesell. Stay inside frontend/src/app/features/<your-feature(s)>/. Do NOT write to other feature folders. Do NOT write to core/ or shared/ (cross-cutting session's scope). Do NOT write to design-system/ (design system sub-session's scope).

TASK: <specialist slice from your session>
CONTEXT: <your session's locked FRONTEND_ARCH section + relevant backend module specs>
OUTPUT: <files + acceptance criteria>
STOP CONDITIONS: <when to escalate to your session's coordinator>
```

---

## Universal hand-off protocol

**On significant completion:**
- Append a completion UPDATE block to your STATUS file
- Append a hand-off entry naming the target session/master + what they receive
- Surface to master via master's STATUS file (master reads on next turn)

**On full session completion** (your feature fully implemented + tested + integrated):
- Final completion UPDATE block in your STATUS file
- Notify master via STATUS_FRONTEND.md "From sub-sessions" section
- Hand off any cross-session-affecting changes (e.g., new shared component) to the appropriate session

---

## Universal scope guards (inherited by every session)

**NEVER:**
- Modify `docs/FRONTEND_ARCHITECTURE.md` (master's scope)
- Modify another session's STATUS file
- Dispatch non-meesell agents
- Modify code outside your session's scope
- Write to `.claude/agent-memory/` of another agent
- Improvise on ambiguous contract — surface via Q&A
- Ship code without npm test passing + ng build succeeding
- Hardcode color/typography values — use CSS custom properties from design-system

**ALWAYS:**
- Read your STATUS first to see prior state
- Read FRONTEND_ARCHITECTURE.md before any code change
- Append STATUS UPDATE blocks
- Honour §17 communication rules (no cross-feature imports)
- Honour CORE_PHILOSOPHY (M9 i18n, M3 validation messages, etc.)
- Use @core/* + @shared/* + @design-system/* aliases (never relative cross-folder imports)
- Write tests per §19 (Vitest + Testing Library + Playwright)
- Stay within the §19 performance budget (≤80 KB per-route gzip, except catalog-form ≤120 KB)

---

## Universal MF (Phase 2) preparation reminder

Per FE-D13, your sub-session corresponds to a future Module Federation remote in Phase 2. Code now to make extraction trivial later:
- Keep cross-feature imports limited to `@core/*` + `@shared/*` + `@design-system/*` (the three things that become the shell host's exposed API)
- No direct imports from sibling feature folders (you'd be importing across MF remote boundaries — would break)
- Feature state stays inside the feature (state services not promoted to @core/ unless 2+ features need them)
- Service contracts (model interfaces) consumed only via @core/models/

When V1 ships and MF extraction begins, your feature folder becomes a remote without code restructure — just build config changes.

---

## End of base prompt

Pair this with a per-session prompt (`docs/SESSION_PROMPTS_FEATURE_<YOUR-NAME>.md`) to bootstrap.
