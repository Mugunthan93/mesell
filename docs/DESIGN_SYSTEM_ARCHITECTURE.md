# MeeSell — Design System Architecture (AI-Assisted Production Pipeline)

**Status:** LOCKED 2026-06-05 — methodology + Reference Dictionary approach ratified by founder; individual category picks remain OPEN through iterative multi-turn confirmation (per §5)
**Owner (post-split 2026-06-05):** Design System Coordinator sub-session (see `docs/SESSION_PROMPTS_DESIGN_SYSTEM.md`)
**Master (post-split 2026-06-05):** `meesell-frontend-coordinator` session — receives final compose output, integrates values into FRONTEND_ARCH §5A
**Dispatched specialist:** `meesell-angular-ui-styler` (model upgrade: sonnet → opus per founder ruling FE-D10) — for curation rounds AND compose phase
**Authored by:** `meesell-frontend-coordinator`, 2026-06-05; ownership transferred to design system sub-session same day
**Peer documents:** `docs/FRONTEND_ARCHITECTURE.md §5A` (the contract for design tokens), `docs/03-wireframes/DESIGNER_BRIEF.md` (the human-designer brief — superseded for V1 by this doc but preserved for V1.5 reference)
**Sub-session STATUS file:** `docs/status/STATUS_DESIGN_SYSTEM.md`

> This document is the **construction contract** for AI-assisted production of MeeSell's visual identity + design tokens. Per founder ruling FE-D10 (2026-06-05), we skip external designer engagement and produce the V1 visual identity via AI tooling executed by an Opus-tier agent. This document peers with `FRONTEND_ARCHITECTURE.md §5A` (which locks the token *framework*) — this document specifies how the token *values* are produced.

---

## Table of Contents

0. [Architectural Premises](#section-0--architectural-premises)
1. [The AI Tool Stack](#section-1--the-ai-tool-stack)
2. [Deliverables](#section-2--deliverables)
3. [Quality Gates](#section-3--quality-gates)
4. [Integration with FRONTEND_ARCHITECTURE.md §5A](#section-4--integration-with-frontend_architecturemd-5a)
5. [Iteration Loop](#section-5--iteration-loop)
6. [Acceptance Criteria](#section-6--acceptance-criteria)
7. [What This Is NOT](#section-7--what-this-is-not)

---

## Section 0 — Architectural Premises

STATUS: DRAFT

### A. Why AI-assisted (FE-D10 founder ruling)

Per founder ruling FE-D10 (2026-06-05), V1 visual identity is produced via AI tooling rather than external human designer engagement. Rationale:
- **Timeline pressure** — V1 needs to ship fast; designer engagement is 4-7 weeks
- **Cost** — designer engagement is ₹15k-120k; AI-assisted path is near-zero
- **Iterability** — AI-assisted values can be refined in hours, designer engagement in weeks
- **V1 scope** — MeeSell V1 has 10 routes + 6 shared components + 11 form primitives; AI tooling can credibly produce token-level decisions for this scope
- **Post-V1 path** — once V1 ships and we have real seller feedback, V1.5 may engage a designer for brand refinement based on usage data, not assumptions

### B. What we ARE producing

The agent produces:
1. **Color tokens** — semantic palette (primary, secondary, surface, error, success, warning, info, outline) with WCAG 2.2 AA contrast verified
2. **Typography tokens** — typeface family + 8-rung scale + weight set + line-heights, with Latin + Tamil + Devanagari script support
3. **Spacing tokens** — 8-point grid (4/8/12/16/24/32/48/64 px)
4. **Breakpoint tokens** — 360/640/768/1024/1280 (mobile-first)
5. **Elevation tokens** — 4 levels mapping to Material M3
6. **Motion tokens** — 3 duration tiers
7. **SCSS files** — `_tokens.scss`, `_theme.scss` (Material M3 theme), `_tailwind-bridge.scss`, `_typography.scss`, `_elevation.scss`, `_motion.scss`
8. **TS mirrors** — `breakpoints.ts`, `tokens.ts`
9. **Tailwind config** — `tailwind.config.js` with `theme.extend` consuming the tokens
10. **Iconography decision** — Material Symbols variant pick (outlined/filled/rounded/sharp)
11. **Microcopy tone guide** — `docs/design-system/MICROCOPY_TONE.md`
12. **Visual rationale** — `docs/design-system/RATIONALE.md` documenting WHY each choice
13. **Contrast verification proof** — `frontend/src/app/design-system/_tokens.spec.ts` (Vitest test asserting every pair ≥4.5:1)

### C. What we are NOT producing in this pass

- **Hi-fi screen mockups** — the working app IS the mockup. Founder reviews live `ng serve` instead of static PNGs
- **Component-level visual specs** — the rendered components in `ng serve` are the spec
- **Logo design** — placeholder type-set logo for V1; logo engagement is separate
- **Hindi + Tamil locale content** — V1.5 fills these (typography supports them; copy is later)
- **Animations / motion choreography** — token-level only (durations + easings); component-specific motion is per-component work

### D. Authority + scope

- The agent has authority to make all token-level visual decisions within the FRONTEND_ARCH §5A framework
- The agent does NOT have authority to:
  - Change the token framework (semantic naming, scale rung positions, theming flow) — that's §5A's lock
  - Introduce new dependencies — §6 of FRONTEND_ARCH is the locked dep list
  - Touch component bodies — that's `meesell-angular-component-builder` scope
- Founder retains final ratification — agent produces; founder reviews `ng serve` output; either ratify or send back for revision

### E. Model upgrade rationale

Per founder ruling FE-D10, the dispatched `meesell-angular-ui-styler` runs at **Opus** model tier (override from spec default of sonnet). Reasoning:
- Visual identity decisions require trade-off reasoning across brand positioning + accessibility + technical constraints simultaneously
- The "anti-Meesho-buyer-aesthetic" instruction requires judgment, not pattern-match
- Color palette generation requires perceptual reasoning + WCAG verification math
- Microcopy tone authoring requires cultural sensitivity (Indian seller voice)
- These are all Opus-strength tasks

---

## Section 1 — The Approach: Reference Dictionary + Iterative Pick

STATUS: LOCKED 2026-06-05 (founder amendment to original §1 — "agent-internal reasoning" superseded by curate-then-pick methodology)

### A. Why curate-then-pick beats agent-internal reasoning

The original §1 proposed agent-internal reasoning (color theory + typography selection done by the Opus agent in isolation). Founder amendment 2026-06-05 supersedes this approach because:

- **Visual identity is judgment, not computation.** Brand fit, anti-reference avoidance, and Indian-context-appropriateness require founder judgment grounded in real examples, not abstract reasoning
- **Concrete grounding beats abstract description.** Picking from 5 real button references is faster and more accurate than evaluating an agent's abstract button spec
- **Multi-turn iteration handles composition validation.** Individual picks made in isolation might not compose well together (color may clash with typography; iconography may not fit the button style). The system as a whole tells you if it works, not the parts
- **Reusable artefact.** The Reference Dictionary survives V1 — V1.5 brand refinement re-reads the picks and the rejected alternatives
- **Documents rationale clearly.** "Picked option C from Khatabook because of warm Indian-seller energy" beats "agent decided #FF6F00"

### B. The Reference Dictionary — `docs/design-system/REFERENCE_DICTIONARY.md`

The agent's primary deliverable is NOT the design system files directly — it's the **Reference Dictionary**: a curated collection of real-world design references from the public web, organised by category, that founder picks from. Once founder confirms the composition works, a separate compose-phase dispatch produces the design system files from confirmed picks.

### C. Category structure (4 phases × 15 categories total)

#### Phase 1 — Foundation (5 categories) — start here

| Category | What we pick | Why first |
|---|---|---|
| **Primary brand color** | Hue + value (saturation/lightness) of the main brand color | Drives every other color choice |
| **Secondary color** | Complementary hue + value | Drives semantic palette |
| **Surface/neutral palette** | Background, surface, surface-variant stops | Drives readability |
| **Primary typeface** | Typeface family (with Indic-script-compatible plan) | Drives type system + tone |
| **Iconography variant** | Material Symbols outlined/filled/rounded/sharp OR alternative set | Drives visual weight |

#### Phase 2 — Components (5 categories)

| Category | What we pick |
|---|---|
| Button visual language | Primary/secondary/destructive/ghost styles |
| Form input treatment | Material outline vs fill; density; error display |
| Card visual language | List-row + grid-tile variants |
| Empty state approach | Illustration vs icon-only; tone |
| Loading state approach | Skeleton vs spinner; placement |

#### Phase 3 — Layout (3 categories)

| Category | What we pick |
|---|---|
| Landing hero layout | Sets brand voice |
| Dashboard density | Compact vs comfortable spacing |
| Wizard form layout | Step indicator + field grouping |

#### Phase 4 — Voice (2 categories)

| Category | What we pick |
|---|---|
| Microcopy tone | Casual / formal / direct / encouraging |
| Error message tone | Helpful / terse / instructive |

### D. Curation sources (where the agent looks)

| Source | URL pattern | Strength |
|---|---|---|
| Mobbin (public pages) | mobbin.com/apps/* | Curated mobile app screenshots |
| Dribbble | dribbble.com/shots/* | Component-level visual exploration |
| Refero.design | refero.design | Curated design references |
| Behance | behance.net | Brand/typography case studies |
| Real Indian SaaS dashboards | razorpay.com, zoho.com, freshworks.com, khatabook.com, vyaparapp.in, paytmbusiness.com, gst.gov.in (anti-ref) | Indian-context credibility |
| Tirupur seller adjacent tools | khatabook.com, vyaparapp.in, tally.solutions | Direct persona match |
| Public design system docs | carbondesignsystem.com, atlassian.design, polaris.shopify.com, primer.style (GitHub), gitlab-design.com | Token framework references |
| Google Fonts | fonts.google.com | Typeface options + Indic script coverage |
| Material Symbols | fonts.google.com/icons | Iconography variant samples |

### E. Reference format (per entry in the dictionary)

```markdown
### Reference N — <name> (<source URL>)
- **Visual signal:** <hex code / typeface name / variant choice>
- **Source context:** <what kind of app — Indian SaaS / B2B tool / etc.>
- **Why included:** <relevance to MeeSell brand principles>
- **Why might FIT MeeSell:** <which positioning pillar it serves>
- **Why might NOT fit:** <honest anti-reference check>
- **Screenshot/exemplar:** <WebFetch'd image URL or descriptive text>
```

### F. Iteration mechanics — multi-turn until composition works

Per founder ruling 2026-06-05, this is explicitly **multi-turn**:
1. Agent curates initial set per category (no hard count — aim 5-10 strong candidates after evaluating ~15-20 per category)
2. Coordinator presents to founder in chat
3. Founder may: pick / request more options / ask for narrower (e.g., "warmer secondaries") / ask for broader
4. Coordinator re-dispatches agent with refinement instruction; agent appends to dictionary
5. After per-category picks ratified, founder also evaluates **composition** — does this color work with this typeface work with this iconography? If composition fails, re-open any category for re-pick
6. Phase concludes only when founder confirms the **system as a whole** works for the phase
7. Next phase begins, informed by prior phase locks
8. Final compose-phase dispatch produces SCSS/TS/Tailwind files from confirmed picks across all 4 phases

There is **no fixed iteration count**. The cap from original §5 (4 iterations → escalate) is REMOVED. We iterate until founder confirms composition.

### G. WCAG verification (preserved from original)

The compose-phase dispatch writes a Vitest test asserting every defined token pair meets the 4.5:1 contrast threshold. Runs in CI. Fails if a future change drops below.

```typescript
// frontend/src/app/design-system/_tokens.spec.ts (illustrative)
describe('Design system contrast (WCAG 2.2 AA)', () => {
  pairs.forEach(([bg, fg]) => {
    it(`${fg} on ${bg} ≥ 4.5:1`, () => {
      expect(contrastRatio(tokens[bg], tokens[fg])).toBeGreaterThanOrEqual(4.5);
    });
  });
});
```

If the founder-picked palette fails WCAG verification, the compose dispatch reports back and we re-open the affected color category for a tighter pick.

---

## Section 2 — Deliverables

STATUS: DRAFT

### A. File-by-file deliverables

| File | Purpose | Location |
|---|---|---|
| `_tokens.scss` | All CSS custom property declarations (color, typography, spacing, etc.) | `frontend/src/app/design-system/` |
| `_theme.scss` | Angular Material M3 theme using tokens | same |
| `_tailwind-bridge.scss` | Bridges tokens to Tailwind-consumable CSS props | same |
| `_typography.scss` | Type family + scale | same |
| `_elevation.scss` | Shadow tokens | same |
| `_motion.scss` | Duration + easing tokens | same |
| `breakpoints.ts` | TS mirror of breakpoints | same |
| `tokens.ts` | TS mirror of runtime-readable tokens | same |
| `_tokens.spec.ts` | WCAG contrast verification test | same |
| `tailwind.config.js` | `theme.extend` consuming tokens via CSS props | `frontend/` |
| `RATIONALE.md` | Why each choice — color theory, typography pick, iconography, microcopy tone | `docs/design-system/` |
| `MICROCOPY_TONE.md` | Tone guide with sample copy | `docs/design-system/` |
| `ICONOGRAPHY.md` | Material Symbols variant pick + 15 key icon names | `docs/design-system/` |

### B. Updates to existing files

| File | Update |
|---|---|
| `docs/FRONTEND_ARCHITECTURE.md §5A` | Values replaced from agent output; STATUS flips PARTIAL LOCK → FULL LOCK |
| `docs/status/STATUS_FRONTEND.md` | Append agent completion block with summary |

### C. NOT delivered in this pass

- Component-level CSS overrides (component-builder owns those)
- Per-feature mockups (founder reviews live `ng serve` instead)
- Logo asset (placeholder type-set logo from typography pick)
- Hindi + Tamil microcopy translations (V1.5)
- Marketing site beyond `/` landing page styling

---

## Section 3 — Quality Gates

STATUS: DRAFT

### A. Automated gates (CI-enforced)

| Gate | Test | Failure consequence |
|---|---|---|
| WCAG contrast | `_tokens.spec.ts` — every pair ≥ 4.5:1 | Build fails |
| Type compilation | `tsc` clean on token files | Build fails |
| SCSS compilation | `ng build` succeeds with no errors | Build fails |
| Bundle budget | Tailwind output ≤ 15 KB gzip after purge | Warning + coordinator review |
| Material theme validity | Material's M3 schematic accepts the theme | Build fails |

### B. Founder review gates (manual)

| Gate | Method | Failure consequence |
|---|---|---|
| Brand fit | Founder runs `ng serve` + opens `/` landing route | Founder rejects → agent revision turn |
| Anti-reference check | Founder verifies app doesn't feel like Meesho buyer / generic SaaS / fintech | Founder rejects → agent revision turn |
| Mobile readability | Founder views on 360px viewport (Chrome DevTools mobile) | Founder rejects → agent revision turn |
| Microcopy tone | Founder reads `MICROCOPY_TONE.md` sample copy | Founder rejects → agent revision turn |

### C. Agent self-checks before reporting completion

The agent runs these checks before reporting back:
1. `npm run lint` clean
2. `npm test` — `_tokens.spec.ts` passes (and any other affected tests)
3. `ng build --configuration=production` succeeds; capture bundle delta vs pre-styling baseline (should be < +10 KB gzip)
4. Take a screenshot via Playwright (`npx playwright screenshot http://localhost:4200/ landing-screenshot.png` after `ng serve`) — for founder review without running the dev server themselves
5. Generate a markdown summary of every decision with rationale → `RATIONALE.md`

---

## Section 4 — Integration with FRONTEND_ARCHITECTURE.md §5A

STATUS: DRAFT

### A. The framework that's already LOCKED in §5A

FRONTEND_ARCH §5A locks the **framework**:
- Token naming (semantic, not literal)
- 8-rung type scale rung positions (xs/sm/base/lg/xl/2xl/3xl/4xl)
- 8-point spacing grid arithmetic
- 5 breakpoints (360/640/768/1024/1280)
- 4 elevation levels mapping to Material M3
- 3 motion tiers
- M3 → Tailwind theming flow
- Dark mode media-query structure (V1.5)
- WCAG 2.2 AA contrast contract

The agent does NOT change any of these. The agent fills in VALUES within this framework.

### B. The values the agent fills in

Per FE-D9 (now superseded by FE-D10), §5A values were placeholders. The agent's output replaces:
- Hex codes (currently `#F26B23` saffron + others — agent may keep or revise)
- Type family (currently Inter — agent may keep or revise)
- Exact px per rung (currently 12/14/16/18/20/24/30/36 — agent may keep or revise)
- Iconography variant (currently "Material Symbols inline" — agent picks outlined/filled/rounded/sharp)

### C. Update protocol on agent completion

When the agent reports completion:
1. Coordinator reads `RATIONALE.md` for the decisions
2. Coordinator reads `MICROCOPY_TONE.md` for tone
3. Coordinator runs `ng serve` and opens `/` + `/dashboard` + `/catalogs/:id/edit` (the 3 hero routes) on 360px + 1280px viewports
4. Coordinator captures screenshots for founder review
5. Coordinator surfaces a comprehensive review to founder with: rationale, screenshots, contrast verification proof, bundle delta
6. Founder ratifies or sends back for revision
7. On ratification: coordinator updates FRONTEND_ARCH §5A values from agent output, flips STATUS to FULL LOCK, dispatches `meesell-angular-component-builder` if not already dispatched

---

## Section 5 — Iteration Loop (Multi-Turn, No Cap)

STATUS: LOCKED 2026-06-05 (founder amendment — multi-turn iteration until composition confirmed; original 4-iteration cap REMOVED)

### A. Round structure per phase

Each of the 4 phases (Foundation / Components / Layout / Voice) follows the same round structure:

```
Round N curation dispatch
    ↓
Agent appends/refines references in REFERENCE_DICTIONARY.md
    ↓
Coordinator presents per-category options to founder in chat
    ↓
Founder responses per category:
   (a) pick → ratified per category
   (b) "more options" → coordinator dispatches Round N+1 with refinement
   (c) "narrower" → coordinator dispatches Round N+1 with constraint
   (d) "broader" → coordinator dispatches Round N+1 with widened scope
    ↓
When all categories in the phase have a pick → composition check:
    Does Color + Typeface + Iconography (Phase 1) work TOGETHER?
        If yes → phase LOCKED, advance to next phase
        If no  → re-open any category, return to "pick" decision
```

### B. No iteration cap

Per founder ruling 2026-06-05, the original cap of 4 iterations is REMOVED. Reasoning: visual identity is brand judgment — premature termination produces a mediocre result. Iterate until founder confirms the system as a whole works.

If iteration takes longer than expected (>10 rounds per phase), the symptom is brand-brief ambiguity, not agent failure. Founder may clarify the anti-reference list, narrow the persona description, or pick a strong reference and constrain future curation around it.

### C. Composition check between phases

Each phase informs the next. Phase 1 picks (colors + typeface + iconography) constrain Phase 2 candidates (the agent searches for buttons that work with the Phase 1 picks, not generic buttons). If a Phase 2 composition check fails because Phase 1 picks are wrong, Phase 1 re-opens. This is by design — the system as a whole must work.

### D. Final compose-phase dispatch

After all 4 phases LOCKED with composition confirmed, a single final dispatch produces the 13 design system files from confirmed picks. The agent does NOT re-judge — it composes from picks. WCAG verification runs; if it fails, the affected color category re-opens for tighter pick.

---

## Section 6 — Acceptance Criteria

STATUS: DRAFT

The AI-assisted design system production is "done" when ALL of:
- [ ] All 13 deliverable files (§2.A) exist in correct locations with valid content
- [ ] `_tokens.spec.ts` passes (all WCAG contrast pairs ≥ 4.5:1)
- [ ] `ng build --configuration=production` succeeds
- [ ] Tailwind purged output ≤ 15 KB gzip
- [ ] Coordinator-captured screenshots of `/`, `/dashboard`, `/catalogs/:id/edit` at 360px + 1280px
- [ ] `RATIONALE.md` documents every choice with reasoning
- [ ] `MICROCOPY_TONE.md` includes 10+ sample sentences
- [ ] `ICONOGRAPHY.md` names the Material Symbols variant + 15 key icons
- [ ] Founder ratifies the visual identity via review of live app + screenshots + rationale
- [ ] FRONTEND_ARCH §5A values updated from agent output
- [ ] §5A STATUS flipped PARTIAL LOCK → FULL LOCK
- [ ] STATUS_FRONTEND.md updated with completion block

---

## Section 7 — What This Is NOT

STATUS: DRAFT

This document is NOT:
- A replacement for FRONTEND_ARCH §5A — §5A locks the framework; this doc specifies how values are produced
- A replacement for `DESIGNER_BRIEF.md` — that brief is preserved for potential V1.5 human-designer engagement
- A specification for component visual bodies — `meesell-angular-component-builder` produces those
- A specification for K3s deploy or build pipeline — that's FRONTEND_ARCH §20
- A specification for testing strategy — that's FRONTEND_ARCH §19
- A long-term governance doc — this is V1-scoped; V1.5 may switch to human designer

The AI-assisted path is V1's pragmatic visual identity production strategy, not a permanent commitment to AI-only design.

---

**End of DESIGN_SYSTEM_ARCHITECTURE.md (DRAFT)**

**Founder review required before specialist dispatch.**
