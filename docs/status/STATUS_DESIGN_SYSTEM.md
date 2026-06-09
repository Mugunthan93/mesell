═══════════════════════════════════════════════════════
UPDATE 2026-06-09 — TAILWIND SAFELIST DEBT ELIMINATED
═══════════════════════════════════════════════════════
Strategy: PREFERRED FIX (bare import + postcss.config.json). Safelist block DELETED.
Root cause discovered: @angular/build:application does NOT load postcss.config.mjs.
  It only reads postcss.config.json or .postcssrc.json (verified by reading Angular source).
  When no JSON PostCSS config exists, Angular tries its own Tailwind integration path:
  require('tailwindcss').default({ config }) — but Tailwind v4 has no .default export,
  so it silently fails. Result: zero utility classes generated; only static preflight CSS
  from esbuild resolving @import "tailwindcss" → tailwindcss/index.css.
Fix: created frontend/postcss.config.json with { "@tailwindcss/postcss": { "base": "/Users/mugunthansrinivasan/Project/mesell/frontend/" } }
  Angular detects postcss.config.json → sets postcssConfiguration → skips broken tailwind path
  → calls @tailwindcss/postcss({ base }) → full source scanning enabled on all .ts/.html files.
Layer order fix retained: styles.css @layer theme, base, primeng, components, utilities (declared before @import).
app.config.ts cssLayer.order updated to 'theme, base, primeng, components, utilities' (matches Tailwind v4 native layers).
Manual safelist block (@layer tailwind-utilities { .w-full {} .flex {} ... }) DELETED.
Auto-detection proof: mt-10 test class on h1 → h1_marginTop computed as 40px (PASS, on-demand generation confirmed).
Test class removed after proof. Final styles.css has no safelist and no @source directive.
Build: ZERO errors, 1.649 seconds.
Tests: 17/17 PASS, 0 regressions.
Screenshots: 3 pages (login/signup/otp-verify) at 1280x800 — all styled correctly.
Files modified: frontend/src/styles.css, frontend/src/app/app.config.ts, frontend/postcss.config.json (CREATED), frontend/postcss.config.mjs (comment-only update).
═══════════════════════════════════════
UPDATE 2026-06-09 — WAVE 2C HOTFIX: Tailwind v4 + PrimeNG layer wiring
═══════════════════════════════════════
Bug: auth controls unstyled (bare-text buttons, no-border inputs, left-bunched) — Preflight outranked PrimeNG because styles.css used bare @import "tailwindcss" while app.config.ts cssLayer.order referenced tailwind-base/tailwind-utilities (v3 names → empty phantom layers).
Fix: styles.css split-import into tailwind-base/primeng/tailwind-utilities layers matching the PrimeNG config; added w-full fluid classes to inputs + p-button hosts + centered OTP.
Tailwind @source note: @source glob scanning does NOT work with @angular/build:application esbuild pipeline (scanner gets no files because the builder virtualizes file paths). Workaround: explicit @layer tailwind-utilities { .w-full { ... } .flex { ... } ... } block added directly in styles.css to ensure critical utility classes are in the correct named layer.
Verified: computed-style probe — button bg rgb(242,107,35) (orange PASS), padding 10px 14px (non-zero PASS), borderRadius 999px (pill PASS), width 376px (full card PASS); input width 376px (full PASS), border 1px solid (non-zero PASS).
Screenshots: 6 captured at /tmp/mesell-shots-fixed/ (login/signup/otp-verify at 1280x800 + 390x844) — all pages render correctly.
Tests: 17/17 passing, 0 regressions.
Build: ZERO errors, 2.0s.
═══════════════════════════════════════
UPDATE 2026-06-09 — WAVE 2C AUTH PAGES
═══════════════════════════════════════
Components built: LoginComponent / SignupComponent / OtpVerifyComponent
Route added: /otp-verify
Tests added: 9 | Tests passing: 17/17 (all spec files)
Gate 1 BUILD:       ✅ ZERO errors, 2.497s
Gate 2 ROUTES:      ✅ /login, /signup, /otp-verify all registered as top-level routes in app.routes.ts
Gate 3 FORM VALID:  ✅ form.invalid prevents submit — confirmed via reactive form logic (required + pattern validators)
Gate 4 FUNCTIONAL:  ✅ 17/17 vitest tests pass
Gate 5 VISUAL:      pending founder
Open questions: none

═════════════════════════════════════════════════
UPDATE 2026-06-08 — WAVE 2A FRAMEWORK RESEARCH
═════════════════════════════════════════════════
Trigger: Full frontend reset — archive + rebuild
Old frontend: archive/frontend_angular_material/ (archived)
Old themes: archive/themes/ (archived)
Task: Research Angular UI library candidates
Candidates evaluated: 8 (3 shortlisted, 5 rejected)
Shortlist: PrimeNG+Sakai-ng, NG-ZORRO+ng-alain, Taiga UI (conditional)
Recommendation: PrimeNG + Sakai-ng Free (MIT, standalone, Tailwind, 8 pre-built page types)
Gate A: ✅ Complete
Awaiting: founder pick for Wave 2B (scaffold)
═════════════════════════════════════════════════

# STATUS — DESIGN SYSTEM

**Owner:** Design System Coordinator sub-session (session-as-role; no separate `.claude/agents/` spec)
**Master:** `meesell-frontend-coordinator` session (master reads this file; sub updates it)
**Created:** 2026-06-05 by frontend coordinator on founder ruling to split design-system work
**Last update:** 2026-06-06 — sub-session LIVE; Phase 1 presented to founder; awaiting picks

**Status:** 🟢 SUB-SESSION LIVE (bootstrapped 2026-06-06) — Phase 1 Foundation refs presented to founder in chat; awaiting per-category responses (pick / more / narrower / broader)

## Construction Contract

`docs/DESIGN_SYSTEM_ARCHITECTURE.md` LOCKED 2026-06-05. Multi-turn iterative curate→pick→compose→confirm methodology with Reference Dictionary. 4 phases × 15 categories total.

## Current Phase

**Phase 1 — Foundation** (5 categories: primary color, secondary color, surface/neutral, typeface, iconography)
**Round:** Phase 1 Round 1 curation COMPLETE — references presented to founder; waiting for picks

Progress:
- [x] Phase 1 Round 1 curation dispatched by master (2026-06-05)
- [x] REFERENCE_DICTIONARY.md populated (38 strong refs from 75 evaluated)
- [x] Sub-session bootstrapped (2026-06-06)
- [x] Phase 1 presented to founder in compact per-category format
- [ ] Founder picks per category (or requests more/narrower/broader)
- [ ] Composition check (do all Phase 1 picks work together?)
- [ ] Phase 1 LOCKED

## Done

- Phase 1 Round 1 curation (meesell-angular-ui-styler, Opus tier) — 38 refs across 5 categories ✓
- Sub-session bootstrapped and all 9 mandatory files read (2026-06-06) ✓

## In Progress

- **Phase 1 picks** — Phase 1 references presented to founder in chat; awaiting responses per all 5 categories

## Blockers

_(none — waiting on founder picks, which is expected flow)_

## Next

1. **CURRENT:** Founder responds per category (pick / more / narrower / broader)
2. Sub-session processes picks:
   - All 5 picked → composition check → Phase 1 LOCK
   - Any category needs refinement → dispatch Round 2 for that category with constraint
3. Phase 1 locked → sub-session dispatches Phase 2 (Components: button language, form treatment, card language, empty state, loading state)
4. Phases 2/3/4 iterate the same way
5. All 4 phases locked → final compose-phase dispatch (13 design system files)
6. Compose complete → sub-session notifies master; master integrates into FRONTEND_ARCH §5A

## Hand-offs

- **From master (frontend coordinator) → design system sub-session:** When Phase 1 Round 1 dispatch completes, REFERENCE_DICTIONARY.md will be populated with Phase 1 sections. Master writes the handoff entry below.
- **From design system sub-session → master (frontend coordinator):** When all 4 phases complete and final compose-phase dispatch produces the 13 design system files, sub-session writes a completion entry; master integrates values into FRONTEND_ARCH §5A and flips §5A from PARTIAL LOCK → FULL LOCK.

## Updates Log

=== UPDATE: 2026-06-05 SKELETON ===
STATUS file created by master (frontend coordinator) per founder ruling
2026-06-05 to split design system architecture work from frontend
coordination. Bootstrap prompt authored at
docs/SESSION_PROMPTS_DESIGN_SYSTEM.md. Design system sub-session not
yet bootstrapped — awaiting founder action.

Phase 1 Round 1 dispatch (meesell-angular-ui-styler at Opus tier)
running in master session; will hand off to this sub-session on
completion via REFERENCE_DICTIONARY.md + appended handoff entry here.
=========

=== UPDATE: 2026-06-05 HANDOFF FROM MASTER ===
Written by: meesell-frontend-coordinator (master session)
Trigger: Phase 1 Round 1 dispatch completion

DISPATCH COMPLETE — meesell-angular-ui-styler (Opus tier) finished curation.

Agent summary (from master's notification):
  - 38 strong references curated across 5 Phase 1 categories:
    • 1.1 Primary brand color — 9 strong refs (Razorpay navy, Khatabook
      orange, Vyapar amber, Zoho rust, Freshworks teal, Lightspeed
      terracotta, BharatPe deep-blue, OkCredit muted gold, Notion
      no-chromatic outlier)
    • 1.2 Secondary color — 8 strong refs (Carbon Blue 70, Material 3
      deep blue, Atlassian deep-teal, Tailwind slate, Polaris green,
      Primer blue, Tailwind emerald, Carbon cool-gray)
    • 1.3 Surface/neutral palette — 7 strong refs (Carbon 10-stop,
      Atlassian Neutral, Polaris warm-tinted, Primer 10-stop,
      Material 3 tonal, Tailwind Stone+Neutral, Notion warm cream)
    • 1.4 Primary typeface — 8 strong refs (Inter, Plus Jakarta Sans,
      DM Sans, Manrope, Be Vietnam Pro, Noto Sans, Hanken Grotesk,
      Public Sans) with Indic-script plan per typeface
    • 1.5 Iconography variant — 6 strong refs (Material Symbols
      Outlined/Rounded/Sharp, Phosphor, Lucide, Tabler)
  - All references in DESIGN_SYSTEM_ARCH §1.E format
  - 75 candidates evaluated; 38 culled as strong

Sourcing caveat (IMPORTANT):
  - The agent's WebFetch + WebSearch tools were NOT available during
    this dispatch. References were curated from the agent's
    training-corpus knowledge of public design system docs, Indian
    SaaS dashboards, Google Fonts catalog, and Material Symbols /
    open-source icon libraries — all stable public reference knowledge
    with verifiable hex codes, typeface metrics, and icon names.
  - If the founder wants screenshot artefacts for any specific
    reference, the design system sub-session can dispatch a Playwright
    capture in a follow-up round.

Four open questions surfaced by agent for founder direction (Round 2
priority list if refinement requested):
  1. Warm-primary intensity — saturated (Khatabook orange) vs muted
     (OkCredit gold) vs earthy (Lightspeed terracotta)?
  2. Native-Indic-glyph typography (Noto Sans, less brand-distinct,
     zero font-family seams) vs pair-with-Noto-fallback (Inter et al.,
     distinct Latin but faint Tamil-seam when scripts mix)?
  3. Iconography family — mechanical Material fit (no dep, looks
     "default") vs Phosphor/Lucide (small dep, more brand-distinct)?
  4. Outlier inclusion check — keep Notion no-chromatic-primary
     (Ref 9 in 1.1) and Freshworks teal (Ref 5 in 1.1) in scope, or
     exclude in Round 2 as drifting from brief's "warm Indian seller
     tool" hard-constraint?

Files written by the dispatch:
  - docs/design-system/REFERENCE_DICTIONARY.md (480 lines, all
    5 Phase 1 categories populated; Phases 2/3/4 placeholders awaiting
    future rounds)
  - docs/status/STATUS_FRONTEND.md (append-only — agent's session
    update blocks recorded there because agent memory write was
    blocked by boundary hook)

Agent memory write blocked:
  - .claude/agent-memory/meesell-angular-ui-styler/ was write-protected
    in agent's environment
  - 6 learnings were recorded as sidebar block in STATUS_FRONTEND.md
    instead
  - Design system sub-session can transcribe to agent memory in a
    follow-up turn if desired

=== END OF MASTER'S HANDOFF ENTRY ===

HANDOFF EFFECTIVE NOW. Design system sub-session takes over from this
point per FE-D11 (founder ruling 2026-06-05).

Master (frontend coordinator) reverts to lower-frequency master mode:
  - Will read this STATUS file periodically
  - Will answer "Questions for master" entries when they appear
  - Will integrate final compose output into FRONTEND_ARCH §5A only
    on full completion (all 4 phases composed + 13 design system
    files produced)
  - Will NOT participate in per-category picks or composition checks

Founder next action:
  1. Open new Claude Code window
  2. Paste bootstrap prompt from docs/SESSION_PROMPTS_DESIGN_SYSTEM.md
     into the new window
  3. The new sub-session reads this STATUS + REFERENCE_DICTIONARY.md
     and presents Phase 1 to founder for picks
  4. All subsequent design system iteration happens in the
     sub-session, not in the master

If founder prefers to defer the sub-session bootstrap (e.g., end the
working day here), no harm — REFERENCE_DICTIONARY.md is durable and
will be there whenever the sub-session is opened.
=========

## Questions for master

_(sub-session uses this section to surface cross-session questions; master polls on next session and answers below the question)_

_(none yet)_

## Updates Log (sub-session)

=== UPDATE: 2026-06-06 SUB-SESSION BOOTSTRAPPED ===
Design System Coordinator sub-session opened by founder per FE-D11 +
SESSION_PROMPTS_DESIGN_SYSTEM.md bootstrap prompt.

Mandatory reads complete (9 files):
  1. docs/DESIGN_SYSTEM_ARCHITECTURE.md (LOCKED 2026-06-05)
  2. docs/FRONTEND_ARCHITECTURE.md §0.F (FE-D1 through FE-D13)
  3. docs/FRONTEND_ARCHITECTURE.md §5A (framework LOCKED; values pending)
  4. docs/03-wireframes/DESIGNER_BRIEF.md (§3 positioning + §4 anti-refs)
  5. docs/VALIDATED_PAIN_POINTS.md (Tirupur seller persona)
  6. docs/CORE_PHILOSOPHY.md (M9 i18n; structural localization)
  7. docs/status/STATUS_DESIGN_SYSTEM.md (prior state + handoff entry)
  8. docs/design-system/REFERENCE_DICTIONARY.md (Phase 1 Round 1
     curated; 38 refs across 5 categories; awaiting founder picks)
  9. .claude/agent-memory/meesell-angular-ui-styler/MEMORY.md (empty
     baseline; 6 round-1 learnings still pending transcription from
     STATUS_FRONTEND.md sidebar block)

State assessment:
  - Phase 1 Round 1 dispatch CONFIRMED complete via master's handoff
    entry (2026-06-05)
  - REFERENCE_DICTIONARY.md populated with 5 categories × ~6-9 strong
    refs each = 38 total after culling from ~75 evaluated
  - Sourcing caveat acknowledged: training-corpus knowledge (WebFetch
    unavailable in dispatch) — hex codes, typeface metrics, icon names
    are stable public reference knowledge; Playwright capture available
    on per-ref request

Current phase: Phase 1 Foundation — presenting refs to founder for picks
Current round: Phase 1 Round 1 PRESENTATION (no new dispatch yet)

Action this turn:
  - Phase 1 (5 categories, 38 refs) presented to founder in chat in
    compact per-category format
  - 4 strategic tensions flagged BEFORE category presentation so picks
    are informed:
      (1) Warm-primary intensity preference
      (2) Native-Indic (Noto Sans) vs pair-with-Noto-fallback
      (3) Material-Symbols vs Phosphor/Lucide (icon dep tradeoff)
      (4) Outlier inclusion check (Notion no-chromatic / Freshworks teal)
  - Awaiting founder response per category — pick / more / narrower /
    broader
=========
