# WAVE 1B — TEMPLATE RESEARCH + LOCAL DEPLOYMENT — DESIGN SYSTEM DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 1B — UI/UX Reference Template Acquisition |
| **Phase** | Research → Deploy → Founder visual confirmation → Handoff |
| **Date authored** | 2026-06-08 |
| **Status** | 📤 READY TO DISPATCH (awaiting founder paste into design-system session) |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | mesell-design-system-2 (design system sub-session) |
| **Downstream recipient (post-ratification)** | mesell-ui-base-2 (cross-cutting session) |
| **Predecessor** | `WAVE_1A_AREA_1_LAYOUTS_DISPATCH.md` §14 Closing Addendum |
| **Trigger** | Founder decision 2026-06-08 — Spike paywall blocks visual comparison methodology |

---

## 1. Purpose

The Wave 1A methodology assumed Spike Angular playground would serve as the UI/UX visual reference. Discovery 2026-06-08: Spike's local copy is free-tier only; pro layouts are paywalled. Visual comparison was structurally impossible.

**Founder decision (Option B from the four-option methodology pivot):** find a different free Angular admin template — one with **full version, no pro-gate, full code access** — to serve as the new UI/UX reference.

This document dispatches that research + local deployment task to `mesell-design-system-2`. The output is a single ratified template, fully deployed in the local playground, that `mesell-ui-base-2` will then use as the implementation reference.

---

## 2. New Methodology — Sequenced Flow

| Phase | Owner | Action | Output |
|---|---|---|---|
| 1. **Research** | `mesell-design-system-2` | Shortlist 3 candidate templates meeting all selection criteria; document each | `WAVE_1B_TEMPLATE_SHORTLIST.md` |
| 2. **Recommend** | `mesell-design-system-2` | Pick top-1 with explicit rationale | Recommendation section in shortlist doc |
| 3. **Deploy** | `mesell-design-system-2` | Clone top-1 to `themes/<template-name>/`; install; run dev server | Live local URL |
| 4. **Visual confirm** | Founder | Review live in browser; ratify or reject | Founder verdict |
| 5. **If rejected** | `mesell-design-system-2` | Deploy next candidate; loop until ratified | Ratified template |
| 6. **Handoff** | `mesell-design-system-2` → master | Compose ratified-template spec for downstream ui-base-2 dispatch | Handoff packet |
| 7. **Implement** (NEXT WAVE) | `mesell-ui-base-2` (NOT this dispatch) | Implement MeeSell UI to match ratified template | Wave 1C — separate dispatch |

**Scope of THIS dispatch**: phases 1-6. Implementation (phase 7) is a separate dispatch authored AFTER ratification.

---

## 3. Selection Criteria (8 — all mandatory unless marked preferred)

| # | Criterion | Rationale | Mandatory? |
|---|---|---|---|
| 1 | **Angular 18+** | Matches MeeSell stack — zero migration burden | ✅ Mandatory |
| 2 | **Standalone components (no NgModules)** | FE-D7 / FE-D11 architecture mandate | ✅ Mandatory |
| 3 | **Full code access — no pro-gate, no paywall** | The Spike failure mode must not recur | ✅ Mandatory |
| 4 | **Permissive license (MIT, Apache 2.0, BSD, ISC)** | Allows downstream code reuse + redistribution | ✅ Mandatory |
| 5 | **Has all needed pieces** — shell (header + sidebar), auth pages (login + register), dashboard, forms, tables, chips/badges, dialogs | Otherwise areas 2/3/4 have no reference | ✅ Mandatory |
| 6 | **Active maintenance** — commits in the last 6 months | Avoids abandoned templates with security debt | ✅ Mandatory |
| 7 | **Material + Tailwind preferred** | Matches MeeSell design system tokens + Plus Jakarta Sans | ⭐ Strongly preferred |
| 8 | **Material Symbols Outlined (NOT Tabler)** | Founder explicitly rejected Tabler icons in Wave 1A | ⭐ Strongly preferred |

### 3.1 Deal-breakers (auto-reject)

| Deal-breaker | Why |
|---|---|
| Pro-tier paywall on any page or component | Spike repeat — methodology dies on Day 1 |
| AdminMart / WrapPixel / Spike author lineage | Same paywall pattern as Spike (very high risk) — auto-reject unless explicitly proven different |
| NgModule-only (no standalone components) | Violates FE-D7 / FE-D11 |
| Bootstrap-only (no Material option) | Forces dual styling system |
| Tabler-icons-only with no swap path | Founder explicitly rejected Tabler in Wave 1A |
| License: proprietary / "free with attribution" loopholes / commercial-use restrictions | Blocks our V1 commercial launch |
| Last commit > 12 months ago | Stale, security debt, no upstream support |

---

## 4. Candidate Shortlist Starter (research only — design-system-2 verifies + expands)

The following templates are starter candidates known to the master session — `mesell-design-system-2` MUST independently verify each (paywall check, license check, Angular version check, component completeness check) before adding to the shortlist. **Do not trust this list — verify everything.**

| Candidate | Stack | Known concerns | Verify before shortlisting |
|---|---|---|---|
| **Berry Angular Free** (CodedThemes) | Angular Material | Has free + pro split — verify free version has all needed pages, no placeholders | Repo: `codedthemes/berry-angular-free` (verify URL) — paywall check, Angular 18 standalone check |
| **Material Dashboard Angular** (Creative Tim) | Angular Material custom | MIT but older Angular versions — verify Angular 18 support | Check latest release Angular version |
| **Argon Dashboard Angular** (Creative Tim) | Bootstrap-based | Bootstrap, not Material — likely auto-rejects on criterion 7 | Verify Material variant exists, or reject |
| **MatX Angular** (UI Lib) | Angular Material | Free + paid split — verify free completeness | Paywall check |
| **Modular Admin Template** | Various | Check Angular version + license | Verify everything |
| **Tabler Angular** | Tabler icons | Tabler-icons (deal-breaker) — auto-reject unless icon swap is trivial | Likely reject |
| **AdminMart / Modernize Free** | Author of Spike | ⛔ AUTO-REJECT same-author paywall risk | Skip |
| **Vuexy / Vex / Apex** | Various | Pro-only — auto-reject | Skip |

**Encouraged**: discover candidates outside this list. GitHub search queries to try:
- `angular admin template stars:>500 license:mit`
- `angular 18 material dashboard`
- `angular tailwind admin standalone`
- `awesome-angular-admin` curated lists

---

## 5. Deliverable 1 — `WAVE_1B_TEMPLATE_SHORTLIST.md`

Authored by `mesell-design-system-2`. Saved to `docs/ui_ux/WAVE_1B_TEMPLATE_SHORTLIST.md`. Must contain:

### 5.1 Required sections

1. **Methodology** — how candidates were sourced (GitHub search queries, awesome-lists scanned, etc.)
2. **Candidates considered + rejected** — every template touched, with one-line rejection reason
3. **Shortlist of 3** — finalists. Each entry contains:
   - Name + repo URL + GitHub stars + last commit date
   - License (verbatim from LICENSE file — not from README)
   - Stack (Angular version, Material/Bootstrap/Tailwind, icons library, state management)
   - **Paywall verification evidence** — clone, count pages, list any "pro" placeholders found
   - Page inventory — which of the required pieces (shell / auth / dashboard / forms / tables / chips / dialogs) are present, which are missing
   - Pros (3-5 bullets)
   - Cons (3-5 bullets)
4. **Recommendation** — top-1 pick with explicit "why this over the other 2"
5. **Risk factors** — anything that might surface post-deployment

### 5.2 Pass criteria for shortlist

- All 3 shortlisted templates pass all 6 mandatory criteria (§3)
- All 3 have paywall verification evidence (not "I think it's free" — clone + count)
- The recommendation has a defensible rationale (not "this one looks nice")

---

## 6. Deliverable 2 — Local Playground Deployment

Once the shortlist + recommendation is authored, deploy the top-1 candidate:

| Step | Command pattern | Pass criteria |
|---|---|---|
| 1. Clone | `git clone <repo-url> themes/<template-name>` | Directory exists at expected path |
| 2. Verify license | `cat themes/<template-name>/LICENSE` | License matches §3 criterion 4 |
| 3. Install | `cd themes/<template-name> && pnpm install` (or `npm` / `yarn` per template) | Zero install errors |
| 4. Verify Angular version | `cd themes/<template-name> && cat package.json \| grep "@angular/core"` | Version ≥18 |
| 5. Run dev server | `cd themes/<template-name> && pnpm start` (or `ng serve`) | Server starts cleanly; record port |
| 6. Visit all required pages | Open browser at recorded port; click through shell / login / register / dashboard / forms / tables | No "pro" gating, no broken pages |
| 7. Screenshot evidence | Capture screenshots of each page at 360px + 1280px | Saved to `docs/ui_ux/wave_1b_screenshots/<template-name>/` |

### 6.1 Deployment readiness checklist

Append to `WAVE_1B_TEMPLATE_SHORTLIST.md` under "Deployment outcome":

- [ ] Cloned to `themes/<name>/`
- [ ] License confirmed = MIT / Apache 2.0 / BSD / ISC
- [ ] Install successful (zero errors)
- [ ] Angular version ≥18
- [ ] Standalone components confirmed (grep for `standalone: true`)
- [ ] Dev server starts cleanly
- [ ] Local URL captured: `http://localhost:<port>/`
- [ ] All 8 required page types reachable (shell + auth-login + auth-register + dashboard + forms + tables + chips/badges + dialogs)
- [ ] Zero "pro" / "upgrade" / "premium" / "locked" placeholders found
- [ ] Screenshots saved per §6 step 7

---

## 7. Deliverable 3 — Founder Visual Confirmation

After deployment, `mesell-design-system-2` notifies master:

> Master notification format:
> ```
> WAVE_1B — TEMPLATE DEPLOYED + READY FOR FOUNDER REVIEW
> Template: <name>
> Local URL: http://localhost:<port>/
> Screenshots: docs/ui_ux/wave_1b_screenshots/<template-name>/
> Pages to review:
>   - /                      (shell + dashboard)
>   - /auth/login            (auth - login)
>   - /auth/register         (auth - register)
>   - /forms                 (form components)
>   - /tables                (table components)
>   - /ui/chips              (chip + badge components)
> Founder verdict requested.
> ```

Master then surfaces to founder for visual review.

### 7.1 Founder verdict format

- ✅ **RATIFY** — this template becomes the Wave 1C implementation reference
- ❌ **REJECT** — design-system-2 deploys next candidate from shortlist; loop
- 🔄 **MIXED** — ratify with explicit deviations (e.g., "use this shell but auth pages from candidate 2")

---

## 8. Deliverable 4 — Handoff Packet to ui-base-2

Once founder ratifies, `mesell-design-system-2` authors `WAVE_1B_RATIFIED_TEMPLATE_SPEC.md` at `docs/ui_ux/WAVE_1B_RATIFIED_TEMPLATE_SPEC.md` containing:

| Section | Contents |
|---|---|
| Ratified template identity | Name + repo URL + license + local path |
| Pages-to-mirror inventory | List of pages MeeSell will mirror, with template source paths |
| Token mapping | How template colors/spacing/radii map to existing MeeSell design tokens; new tokens needed flagged |
| Component inventory | Components MeeSell will adopt vs skip; reasons |
| Icon strategy | Material Symbols Outlined (mandatory) — how to swap if template uses different icons |
| Out-of-scope from template | Marketing pages, demos, locale switchers, theme toggles — anything MeeSell doesn't need |
| Founder verdicts captured during ratification | Any "mixed" rulings or per-page deviations |
| Risk register | Risks discovered during deployment (visual regressions, bundle bloat, etc.) |

This packet drives the eventual Wave 1C dispatch to `mesell-ui-base-2`.

---

## 9. Constraints (non-negotiable)

| Constraint | Rule |
|---|---|
| **Read-only on Spike** | Existing Spike copy at `themes/spike-angular/` stays. May be referenced for what NOT to do (paywall pattern). Do not delete. |
| **Workspace boundary** | All work stays within `/Users/mugunthansrinivasan/Project/mesell/` |
| **No npm install outside `themes/<chosen>/`** | Template's dependencies stay scoped to its own directory; do not pollute root package.json |
| **No master-repo changes** | This dispatch produces docs + a cloned theme directory — no changes to `frontend/src/` (that's Wave 1C, separate dispatch) |
| **Dispatch only meesell-* agents** | Per CLAUDE.md ecosystem rules. No nexus / general-purpose / other agents |
| **Token additions are deferred** | If the ratified template needs new tokens (e.g., `--mee-color-surface-dark`), surface in §8 handoff but do NOT add to `_tokens.scss` here. Token additions are design-system scope, separate task. |
| **Memory hygiene** | `mesell-design-system-2` writes learnings to its own memory at `.claude/agent-memory/mesell-design-system/MEMORY.md`. Does not write to any other agent's memory. |

---

## 10. Out of Scope (do not touch)

| Out-of-scope item | Reason |
|---|---|
| Implementing MeeSell UI changes | Wave 1C — separate dispatch after ratification |
| Modifying `frontend/src/` | Implementation phase only |
| Adding new tokens to `_tokens.scss` | Defer to dedicated design-system task |
| Authentication flow logic | Wave 1A code stands; not in scope here |
| API integration | Held until UI/UX direction is locked |
| Mobile / Ionic considerations | Phase 2 — not now |
| Module Federation | Phase 2 — not now |
| Updating any STATUS files other than `STATUS_FEATURE_CROSS_CUTTING.md` or a new STATUS file owned by design-system | Per session ownership rules |
| Cross-project work | Workspace boundary — MeeSell only |

---

## 11. Verification Gates

All gates owned by `mesell-design-system-2` before founder visual confirmation:

### Gate A — RESEARCH SOUNDNESS

- [ ] At least 8 candidates evaluated (3 shortlisted + 5 rejected with reasons)
- [ ] Each shortlisted candidate has paywall evidence (clone + page count)
- [ ] Each shortlisted candidate has verified license file (not just README claim)
- [ ] Recommendation has comparative rationale across all 3 shortlist entries

### Gate B — DEPLOYMENT SUCCESS

- [ ] Cloned + installed + builds cleanly
- [ ] All §6.1 checklist items ✅
- [ ] Screenshots saved per §6 step 7
- [ ] Master notification sent per §7

### Gate C — HANDOFF READINESS (post-ratification only)

- [ ] `WAVE_1B_RATIFIED_TEMPLATE_SPEC.md` authored per §8
- [ ] Pages-to-mirror inventory complete
- [ ] Token mapping documented
- [ ] Risk register populated

---

## 12. Dispatch Notification (paste-ready block)

The following block is to be pasted **verbatim** into the design system sub-session (`mesell-design-system-2`).

```
══════════════════════════════════════════════════════════════════
📨 MASTER → DESIGN-SYSTEM NOTIFICATION
Date: 2026-06-08
From: meesell-frontend-coordinator (master session)
Wave: WAVE 1B — UI/UX TEMPLATE RESEARCH + LOCAL DEPLOYMENT
Type: Research dispatch + local deployment (NOT implementation)
══════════════════════════════════════════════════════════════════

CONTEXT — METHODOLOGY PIVOT
───────────────────────────
Wave 1A used Spike Angular playground as the UI/UX reference.
Discovery 2026-06-08: Spike pro layouts are PAYWALLED. Visual
comparison was structurally impossible.

Founder decision 2026-06-08: abandon Spike. Pick a different
free Angular admin template — FULL VERSION, NO PRO-GATE,
FULL CODE ACCESS — as the new UI/UX reference.

YOUR JOB: research + shortlist + deploy + visual confirmation.
NOT implementation — that's a separate dispatch to ui-base-2
AFTER founder ratifies the template.

══════════════════════════════════════════════════════════════════

DELIVERABLES (4)
────────────────
1. docs/ui_ux/WAVE_1B_TEMPLATE_SHORTLIST.md
   - 3 candidates passing all 6 mandatory criteria
   - Paywall verification evidence per candidate (clone + count)
   - Verified license file per candidate (NOT README claims)
   - Top-1 recommendation with comparative rationale

2. Local playground deployment of top-1
   - Clone to themes/<template-name>/
   - Install + dev server running
   - All 8 required page types reachable
   - Zero "pro/upgrade/premium/locked" placeholders
   - Screenshots at 360px + 1280px in docs/ui_ux/wave_1b_screenshots/<name>/

3. Founder visual confirmation notification
   - Master notification with local URL + screenshots
   - If founder rejects: deploy next shortlist candidate; loop

4. docs/ui_ux/WAVE_1B_RATIFIED_TEMPLATE_SPEC.md (post-ratification)
   - Pages-to-mirror inventory
   - Token mapping (current MeeSell tokens vs template tokens)
   - Component inventory (adopt / skip)
   - Icon strategy (Material Symbols Outlined mandatory)
   - Risk register

══════════════════════════════════════════════════════════════════

SELECTION CRITERIA — 8 (6 mandatory + 2 preferred)
─────────────────────────────────────────────────
Mandatory:
  1. Angular 18+ (zero migration burden)
  2. Standalone components — no NgModules (FE-D7/D11)
  3. Full code access — no pro-gate, no paywall
  4. Permissive license — MIT / Apache 2.0 / BSD / ISC
  5. Has ALL needed pieces — shell + auth + dashboard + forms
     + tables + chips/badges + dialogs
  6. Active maintenance — commits in last 6 months

Preferred:
  7. Material + Tailwind stack
  8. Material Symbols Outlined (NOT Tabler — founder rejected
     Tabler in Wave 1A)

DEAL-BREAKERS — auto-reject:
  ✗ Any pro-tier paywall on any page
  ✗ AdminMart / WrapPixel / Spike author lineage (same paywall pattern)
  ✗ NgModule-only (no standalone components)
  ✗ Bootstrap-only with no Material option
  ✗ Tabler-icons-only with no swap path
  ✗ Proprietary / "free with attribution" / commercial restrictions
  ✗ Last commit > 12 months ago

══════════════════════════════════════════════════════════════════

CANDIDATE STARTER LIST (verify everything — do not trust)
─────────────────────────────────────────────────────────
  • Berry Angular Free (CodedThemes) — verify Angular 18 + paywall
  • Material Dashboard Angular (Creative Tim) — verify Angular version
  • Argon Dashboard Angular (Creative Tim) — Bootstrap (likely reject)
  • MatX Angular (UI Lib) — verify paywall
  • Modular Admin Template — verify Angular version
  • Tabler Angular — Tabler icons (likely reject)
  • AdminMart / Modernize Free — ⛔ AUTO-REJECT (same author as Spike)
  • Vuexy / Vex / Apex — ⛔ AUTO-REJECT (pro-only)

Discover beyond this list:
  - GitHub search: angular admin template stars:>500 license:mit
  - GitHub search: angular 18 material dashboard
  - awesome-angular-admin curated lists

══════════════════════════════════════════════════════════════════

CONSTRAINTS (non-negotiable)
────────────────────────────
• Read-only on existing themes/spike-angular/ (do not delete)
• Workspace boundary — stay within /Users/mugunthansrinivasan/Project/mesell/
• No npm install at workspace root — keep template deps scoped to
  themes/<chosen>/
• No changes to frontend/src/ — that's Wave 1C (separate dispatch)
• Dispatch only meesell-* agents
• Token additions deferred — flag needed new tokens in handoff but
  do NOT modify _tokens.scss in this wave
• Memory hygiene — write learnings to
  .claude/agent-memory/mesell-design-system/MEMORY.md only

══════════════════════════════════════════════════════════════════

OUT OF SCOPE (do not touch)
───────────────────────────
✗ Implementing MeeSell UI changes — Wave 1C, separate dispatch
✗ Modifying frontend/src/
✗ Adding new tokens to _tokens.scss
✗ Authentication flow logic
✗ API integration
✗ Mobile / Ionic / Module Federation
✗ STATUS files outside your session ownership
✗ Cross-project work — MeeSell only

══════════════════════════════════════════════════════════════════

VERIFICATION GATES (all must pass before founder confirmation)
──────────────────────────────────────────────────────────────

Gate A — RESEARCH SOUNDNESS
  ✓ At least 8 candidates evaluated (3 shortlisted + 5+ rejected)
  ✓ Each shortlisted has paywall evidence (clone + page count)
  ✓ Each shortlisted has verified license FILE (not README)
  ✓ Recommendation has comparative rationale

Gate B — DEPLOYMENT SUCCESS
  ✓ Cloned + installed + builds cleanly
  ✓ All §6.1 checklist items ✅
  ✓ Screenshots saved at 360px + 1280px
  ✓ Master notification sent

Gate C — HANDOFF READINESS (post-ratification only)
  ✓ WAVE_1B_RATIFIED_TEMPLATE_SPEC.md authored
  ✓ Pages-to-mirror inventory complete
  ✓ Token mapping documented
  ✓ Risk register populated

══════════════════════════════════════════════════════════════════

WORKFLOW
────────
1. Read this notification + WAVE_1A_AREA_1_LAYOUTS_DISPATCH.md §14
2. Read existing MeeSell design system at
   frontend/src/app/design-system/_tokens.scss + DESIGN_SYSTEM_ARCHITECTURE.md
3. Research: source 8+ candidates; reject ineligible ones
4. Shortlist 3; clone each briefly to verify paywall + license
5. Recommend top-1 with rationale
6. Author WAVE_1B_TEMPLATE_SHORTLIST.md
7. Deploy top-1 to themes/<name>/; capture local URL + screenshots
8. Notify master per §7 format
9. WAIT for founder verdict (ratify / reject / mixed)
10. If rejected: deploy next; loop
11. If ratified: author WAVE_1B_RATIFIED_TEMPLATE_SPEC.md
12. Notify master — Wave 1B complete, Wave 1C dispatch can begin

══════════════════════════════════════════════════════════════════

STATUS UPDATE BLOCK (append to your session's STATUS file)
──────────────────────────────────────────────────────────

  ═══════════════════════════════════════════
  UPDATE 2026-06-08 — WAVE 1B TEMPLATE RESEARCH
  ═══════════════════════════════════════════
  Wave source: master session (frontend-coordinator)
  Trigger: Spike paywall — methodology pivot (Option B)
  Candidates evaluated: [N]
  Candidates rejected:  [N — list w/ one-line reasons]
  Shortlist (3):        [names + repo URLs]
  Recommendation:       [name + rationale]
  Deployment outcome:
    Cloned:             ✅/❌
    Builds:             ✅/❌
    All pages reachable: ✅/❌
    Local URL:          http://localhost:<port>/
    Screenshots:        ✅/❌
  Founder verdict:      ⏳ pending review
  Open questions:       [any blockers for master]

══════════════════════════════════════════════════════════════════

DECISION POINTS
───────────────
After Gate B + founder review:
  ✅ Ratify → author handoff spec (§8) → notify master for Wave 1C dispatch
  ❌ Reject → deploy next shortlist candidate → re-review
  🔄 Mixed → document deviations → author handoff spec with explicit
              per-page rulings

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## 13. Workflow After Paste

| Step | Owner | Action |
|---|---|---|
| 1 | Founder | Paste §12 block into `mesell-design-system-2` window |
| 2 | Design-system session | Read this dispatch + Wave 1A §14 addendum + existing design system docs |
| 3 | Design-system session | Research 8+ candidates; reject ineligible |
| 4 | Design-system session | Author `WAVE_1B_TEMPLATE_SHORTLIST.md` |
| 5 | Design-system session | Deploy top-1 to `themes/<name>/` |
| 6 | Design-system session | Capture screenshots + local URL |
| 7 | Design-system session | Notify master via §7 format |
| 8 | Master → Founder | Surface notification + screenshots + URL |
| 9 | Founder | Visual review → ratify / reject / mixed |
| 10 | Loop | If rejected: deploy next; re-review |
| 11 | Design-system session | Post-ratification: author `WAVE_1B_RATIFIED_TEMPLATE_SPEC.md` |
| 12 | Design-system session → Master | Notify Wave 1B complete |
| 13 | Master | Author Wave 1C dispatch for `mesell-ui-base-2` (separate document) |

---

## 14. Decision Point Criteria

After founder visual review:

### ✅ Ratify

Proceed to handoff packet authoring (§8) and Wave 1C dispatch authoring.

### ❌ Reject

Design-system-2 deploys next candidate from shortlist. Loop until ratified or shortlist exhausted.

### Shortlist exhausted (worst case)

Master + founder regroup. Options:
- Expand search criteria
- Loosen non-mandatory criteria (e.g., accept Tailwind-only without Material)
- Switch to Option A (founder-driven design) or Option C (MeeSell-native from scratch)

---

## 15. Related Documents

| Document | Relevance |
|---|---|
| `docs/ui_ux/WAVE_1A_AREA_1_LAYOUTS_DISPATCH.md` §14 | Predecessor — explains why this wave exists |
| `docs/FRONTEND_ARCHITECTURE.md` §5A (Design System Tokens) | Current token surface |
| `docs/DESIGN_SYSTEM_ARCHITECTURE.md` | Design system contract for what template must support |
| `frontend/src/app/design-system/_tokens.scss` | Token implementation reference |
| `themes/spike-angular/` | Read-only — kept as historical record of why Option B exists |
| (To be created) `docs/ui_ux/WAVE_1B_TEMPLATE_SHORTLIST.md` | Deliverable 1 |
| (To be created) `docs/ui_ux/wave_1b_screenshots/<name>/` | Deliverable 2 evidence |
| (To be created) `docs/ui_ux/WAVE_1B_RATIFIED_TEMPLATE_SPEC.md` | Deliverable 4 — drives Wave 1C |

---

## 16. Successor Documents (Wave 1C and beyond)

After this wave completes:

| Document | Purpose | Authored when |
|---|---|---|
| `docs/ui_ux/WAVE_1C_TEMPLATE_IMPLEMENTATION_DISPATCH.md` | Dispatch to `mesell-ui-base-2` to implement MeeSell UI matching ratified template | After §8 handoff packet exists |
| `docs/ui_ux/WAVE_1A_AREA_1_LAYOUTS_RESULT.md` | (Optional, deferred) Result artifact for the original Area 1 work | If needed for audit trail |

Q1 (sidebar footer logout removal) will be bundled into Wave 1C unless founder sends as standalone micro-dispatch sooner.

---

## 17. Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-08 | meesell-frontend-coordinator (master) | Initial authoring after Wave 1A methodology pivot to Option B |
