---
name: session-split-design-system
description: FE-D11 founder ruling 2026-06-05 — design system architecture work split into dedicated sub-session; this frontend coordinator session acts as MASTER for the new design system sub-session; session-as-role pattern matches existing FRONTEND/BACKEND/etc multi-session pattern
metadata:
  type: project
---

# FE-D11 — Session split for design system architecture (2026-06-05)

## The ruling

Founder noticed that running frontend architecture work + design system architecture work + reference dictionary curation iteration in the SAME session was overcomplicating coordination. Both concerns deserve their own STATUS surface, their own memory, their own focused agent dispatching cadence.

**Split applied 2026-06-05 same turn:**
- Frontend coordinator session (this one) → continues to own FRONTEND_ARCHITECTURE.md + non-design specialist dispatches
- New Design System Coordinator sub-session → owns DESIGN_SYSTEM_ARCHITECTURE.md + REFERENCE_DICTIONARY.md + design system iteration + ui-styler dispatches

## Master-sub coordination

I am the MASTER for the design system sub-session. The pattern matches the MeeSell project-level multi-session model:
- Master session = founder + master Claude
- Sub-sessions = FRONTEND, BACKEND, AI, DATA, INFRA, LEGAL (coordinator-led)
- Now also: sub-sub-session of FRONTEND = Design System Coordinator

### How coordination works

| Concern | Master action | Sub action |
|---|---|---|
| Architecture docs | Reads DESIGN_SYSTEM_ARCH for context only (do NOT edit) | Owns + edits DESIGN_SYSTEM_ARCH on amendments |
| Reference Dictionary | Doesn't touch | Owns + grows via ui-styler dispatches |
| STATUS reading | Reads STATUS_DESIGN_SYSTEM.md before any §5A action | Updates STATUS_DESIGN_SYSTEM.md on every round + phase lock |
| §5A integration | Integrates final compose output into FRONTEND_ARCH §5A on full completion | Does NOT touch FRONTEND_ARCH directly |
| Specialist dispatch | Dispatches angular-component-builder + service-builder for code | Dispatches angular-ui-styler (Opus override) for design |
| Cross-session questions | Polls sub STATUS "Questions for master" section + answers | Surfaces in STATUS "Questions for master" section |

## Why no separate agent spec

The MeeSell ecosystem has 18 agents. The design system coordinator role:
- Spans both coordinator and specialist responsibilities (curate + dispatch + integrate)
- Is V1-scoped (may not need long-term distinct identity)
- Can be honored via session-as-role pattern (matches existing FRONTEND/BACKEND/etc sub-sessions which also don't have explicit "*-coordinator" agent specs at the project layer)

If the pattern proves valuable beyond V1, a `meesell-design-system-coordinator` agent spec can be authored in V1.5. For now, the session is bootstrapped via the prompt in `docs/SESSION_PROMPTS_DESIGN_SYSTEM.md`.

## Files I (master) created during the split

1. `docs/SESSION_PROMPTS_DESIGN_SYSTEM.md` — bootstrap prompt + ownership maps
2. `docs/status/STATUS_DESIGN_SYSTEM.md` — skeleton STATUS file
3. Edits to `DESIGN_SYSTEM_ARCHITECTURE.md` header — ownership declaration
4. Edits to `FRONTEND_ARCHITECTURE.md §0.F` — FE-D11 ruling added
5. Append to `STATUS_FRONTEND.md` — split notice

## Phase 1 dispatch handoff protocol

The Phase 1 Round 1 dispatch was initiated in this (master) session BEFORE the split. The dispatched agent will complete here and notify this session. Handoff protocol:

1. Background agent completes → notification arrives in THIS session
2. I (master) read the completion result
3. I append a handoff entry to STATUS_DESIGN_SYSTEM.md noting:
   - REFERENCE_DICTIONARY.md is populated with Phase 1 sections
   - Phase 1 Round 1 dispatch summary (sources used, count per category, any sourcing difficulties)
   - "Design system sub-session takes over from here"
4. Founder opens new Claude window + pastes bootstrap prompt from SESSION_PROMPTS_DESIGN_SYSTEM.md
5. New sub-session reads STATUS_DESIGN_SYSTEM.md + REFERENCE_DICTIONARY.md
6. New sub-session presents Phase 1 references to founder in THAT session (not this one)
7. All subsequent design system iteration happens in sub-session

## What I (master) do AFTER the handoff

- Do NOT participate in per-category picks or composition checks (sub-session owns)
- Read STATUS_DESIGN_SYSTEM.md periodically to stay informed of progress
- Answer "Questions for master" entries when they appear
- On FULL completion (all 4 phases composed + final design system files produced):
  - Read sub-session's completion summary
  - Integrate token values into FRONTEND_ARCH §5A (replacing FE-D9/D10 placeholders)
  - Flip §5A STATUS from PARTIAL LOCK → FULL LOCK
  - Append integration entry to STATUS_FRONTEND.md
  - Authorise (or remind founder to authorise) meesell-angular-ui-styler COMPOSE dispatch
    if it didn't happen via sub-session (which would be unusual — sub-session normally
    handles compose)

## Edge case: what if user comes back to THIS session with design system questions?

Politely redirect: "Design system architecture is now owned by the Design System Coordinator sub-session per FE-D11. That session is at [open or not open]. The architecture doc is `docs/DESIGN_SYSTEM_ARCHITECTURE.md` and the STATUS is `docs/status/STATUS_DESIGN_SYSTEM.md`. Want me to surface what I see in the STATUS file, or shall we discuss frontend coordination concerns?"

Don't accidentally re-absorb the design system work back into this session — that defeats the split.
