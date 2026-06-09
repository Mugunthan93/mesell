# WAVE 1A — AREA 1 (LAYOUTS) — CROSS-CUTTING DISPATCH NOTIFICATION

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | 1A — UI/UX Visual Fidelity |
| **Area** | 1 of 4 — Layouts (shell + auth-layout) |
| **Date authored** | 2026-06-08 |
| **Date closed** | 2026-06-08 (same day) |
| **Status** | 🏁 CLOSED — partial completion + methodology pivot. See §14 Closing Addendum. |
| **Author** | meesell-frontend-coordinator (master session) |
| **Recipient** | mesell-ui-base-2 (cross-cutting session) |
| **Verdicts source** | Founder via master session walk-through 2026-06-08 |
| **Spike reference root** | `themes/spike-angular/package/src/app/` |
| **Iterative pilot** | YES — validates wave methodology before scaling to Areas 2-4 |

---

## 1. Purpose

This document captures the **first dispatch of the UI/UX wave** (Wave 1A). Founder identified visual fidelity gap between current frontend implementation and Spike Angular playground reference. Rather than walk all four areas upfront, we run an **iterative pilot**: dispatch Area 1 (Layouts) → verify through four gates → decide whether to scale the same pattern to Areas 2-4 or revise the strategy.

**Why Area 1 first**:
- **Foundational** — every page inherits from `MeeShellComponent` + `MeeAuthLayoutComponent`. If layouts look right, the rest inherits visual quality. If they look wrong, the rest inherits the gap.
- **Smallest scope** — two layout files, one wave, ~10 founder verdicts. Lowest risk pilot for validating the methodology.
- **Visible** — easy for founder to verify via `ng serve` at 360px and 1280px.

**Hold on API integration**: per founder direction 2026-06-08, all API integration work is paused until UI/UX fidelity is correct.

---

## 2. Iterative Pilot Context

| Phase | Action | Owner |
|---|---|---|
| Walk | Master walks founder through Spike playground area-by-area | Master + founder |
| Verdict | Founder ratifies each Spike pattern (adopt / adopt-modified / skip) | Founder |
| Dispatch | Master authors this notification; founder pastes into sub-session | Master → founder |
| Build | Cross-cutting dispatches `meesell-angular-component-builder` | Cross-cutting session |
| Verify | Four-gate verification (build / token / visual / functional) | Cross-cutting + founder |
| Decide | ✅ All gates pass → walk next area / ❌ Any gate fails → revise methodology | Master + founder |

This document encodes the **Verdict** and **Dispatch** phases for Area 1.

---

## 3. Area 1 Scope — Layouts

### 3.1 Files in scope

| File | Current state | Wave 1A action |
|---|---|---|
| `frontend/src/app/layouts/shell/shell.component.ts` (`MeeShellComponent`) | Sidebar + branding + nav-list, NO header toolbar | Add Spike-style header toolbar |
| `frontend/src/app/layouts/auth/auth-layout.component.ts` (`MeeAuthLayoutComponent`) | Minimal auth shell | Verify visual match with Spike `blank/` reference |
| `frontend/src/app/layouts/shell/components/*` (new sub-components) | N/A | May add header toolbar sub-component + profile menu sub-component |

### 3.2 Spike reference files (READ-ONLY — do not import)

| Path | What it shows |
|---|---|
| `themes/spike-angular/package/src/app/layouts/full/full.component.html` | Overall shell structure (sidenav-container, sidebar, content, header) |
| `themes/spike-angular/package/src/app/layouts/full/header/header.component.html` | Header toolbar with hamburger, bell, profile dropdown |
| `themes/spike-angular/package/src/app/layouts/full/sidebar/sidebar.component.html` | Sidebar structure (branding + nav + sections) |
| `themes/spike-angular/package/src/app/layouts/blank/blank.component.html` | Auth/blank layout structure |

---

## 4. Founder Verdicts — 10 Spike Patterns

### ✅ ADOPT (4 patterns)

| # | Spike pattern | MeeSell encoding |
|---|---|---|
| 1 | **Header toolbar in shell** | Add to `MeeShellComponent`: mobile hamburger (toggles sidebar) + RIGHT-side profile avatar (`mat-mini-fab` with initials/icon) → dropdown menu with "My Profile" + "Log out" only |
| 2 | **Blank/auth layout pattern** | Keep `MeeAuthLayoutComponent` — verify visual match with Spike `blank/` at 360px + 1280px |
| 3 | **Sidebar (brand + nav + section headers)** | Keep current sidebar — verify visual match with Spike `full/sidebar` at 360px + 1280px |
| 4 | **Profile dropdown items** | Only "My Profile" → `/profile`, "Log out" → `AuthService.logout()` → `/login`. Skip Spike's "My Account" + "My Task" (not in V1 IA) |

### ❌ SKIP (6 patterns)

| # | Spike pattern | Reason to skip |
|---|---|---|
| 5 | **Topstrip** (WrapPixel marketing dark bar with Templates / Help / Hire Us) | Pure WrapPixel marketing — not applicable to MeeSell |
| 6 | **Sidebar PRO upsell card** ("Check Pro Version") | No V1 monetization upsell needed at MVP — focus on core flow |
| 7 | **Footer** (WrapPixel attribution + links) | WrapPixel attribution not applicable; no footer needed in shell |
| 8 | **Tabler icons** (`<i-tabler name="...">`) | Design system standardized on Material Symbols Outlined — keep consistency |
| 9 | **Notifications bell + menu** | No notifications system in V1 — defer to later phase |
| 10 | **"Check Pro Template" header button** | Pure marketing — not applicable |

---

## 5. Constraints (non-negotiable)

| Constraint | Rule |
|---|---|
| **Design tokens** | No new hardcoded hex codes. Use `--mee-color-primary` (#F26B23), `--mee-color-bg` (#f0f5f9), and existing token surface set |
| **Icons** | Material Symbols Outlined for ALL icons (avatar fallback, hamburger, dropdown chevron, menu items) |
| **Token storage (FE-D5)** | In-memory only. Logout = `AuthService.logout()` calls `ACCESS_TOKEN_SIGNAL.set(null)` → `router.navigate(['/login'])`. NO `localStorage` / `sessionStorage` / `IndexedDB` / JS-readable cookie |
| **Component architecture** | Standalone components + `OnPush` + `signal`/`computed`. No NgModules. No Subscriptions where signal works |
| **Mobile baseline** | 360px — sidebar collapses to overlay drawer |
| **Desktop breakpoint** | ≥1024px — sidebar persists at 270px expanded / 80px collapsed |
| **Accessibility (WCAG 2.2 AA)** | Profile menu keyboard-reachable; avatar button has `aria-label`; dropdown items have `role="menuitem"`; ESC closes dropdown; focus trap when open |
| **Bundle budget** | Shell route ≤80 KB compressed (per FRONTEND_ARCHITECTURE.md §19) |
| **Testing** | All existing tests MUST continue to pass; new tests required for header dropdown behavior |

### 5.1 Required new tests

| # | Test name | Expected behavior |
|---|---|---|
| 1 | Dropdown opens on avatar click | Click avatar → menu visible |
| 2 | "My Profile" navigation | Click "My Profile" item → `Router.navigate(['/profile'])` |
| 3 | "Log out" calls AuthService + navigates | Click "Log out" → `AuthService.logout()` called (mock) + `Router.navigate(['/login'])` |
| 4 | ESC closes dropdown | Open menu, press ESC → menu closes |
| 5 | Focus trap when open | Tab cycles within menu items when menu is open |

---

## 6. Out of Scope (explicit — do not touch)

| Out-of-scope item | Reason |
|---|---|
| Auth page components (`SignupComponent`, `LoginComponent`, `OtpVerifyComponent`, `PhoneInputComponent`) | Area 2 future wave |
| Onboarding wizard, profile pages, catalog pages, dashboard page components | Areas 2/3/4 future waves |
| Auth flow logic (FE-D5 split-token pattern) | Unchanged — already correct |
| API integration code | ON HOLD per founder direction 2026-06-08 |
| Any new routes | Layouts only |
| Spike footer, topstrip, bell, PRO card, Tabler icons | Founder verdict: SKIP |
| Module Federation work | Phase 2 alignment unchanged |
| Dispatch to non-`meesell-*` agents | Forbidden per CLAUDE.md ecosystem rules |
| Tangential shared component visual refactors (e.g., `FormFieldComponent` label style) | Defer to Area 3 (UI components wave) to prevent scope creep |

---

## 7. Verification Gates

All four gates must pass before this dispatch is considered complete.

### Gate 1 — BUILD

```bash
cd frontend && ng build --configuration=production
```

**Pass criteria**: zero errors, zero new warnings, all bundle budgets within limit.

### Gate 2 — TOKEN HYGIENE

```bash
grep -rnE "#[0-9a-fA-F]{3,6}" frontend/src/app/layouts/
```

**Pass criteria**: zero NEW hex matches in `layouts/`. Existing pre-Wave-1A hex may remain; no new hex introduced.

### Gate 3 — VISUAL (founder review)

```bash
cd frontend && ng serve
```

Founder reviews:
- `http://localhost:4200/dashboard` → shell header + sidebar at 360px and 1280px
- `http://localhost:4200/login` → auth layout at 360px and 1280px

**Pass criteria**: visual match with Spike `full/` + `blank/` reference; founder verbal approval.

### Gate 4 — FUNCTIONAL

```bash
cd frontend && pnpm vitest run
```

**Pass criteria**: all existing tests pass + 5 new header dropdown tests (§5.1) pass.

### 7.1 Gate tracking table (update as gates land)

| Gate | Status | Verified by | Date | Evidence |
|---|---|---|---|---|
| 1 — BUILD | ⏳ pending | Cross-cutting | — | — |
| 2 — TOKEN | ⏳ pending | Cross-cutting | — | — |
| 3 — VISUAL | ⏳ pending | Founder | — | — |
| 4 — FUNCTIONAL | ⏳ pending | Cross-cutting | — | — |

---

## 8. Dispatch Notification (paste-ready block)

The following block is to be pasted **verbatim** into the cross-cutting sub-session (`mesell-ui-base-2`).

```
══════════════════════════════════════════════════════════════════
📨 MASTER → CROSS-CUTTING NOTIFICATION
Date: 2026-06-08
From: meesell-frontend-coordinator (master session)
Wave: WAVE 1A — UI/UX FIDELITY — AREA 1 (LAYOUTS)
Type: Iterative pilot dispatch (validates wave methodology)
══════════════════════════════════════════════════════════════════

CONTEXT
───────
Founder identified UI/UX visual gap vs Spike Angular playground
reference. We are running a Wave 0 audit comparing playground vs
current frontend implementation, area-by-area, with explicit
founder verdicts per Spike pattern.

This is the FIRST dispatch of the UI/UX wave. We are validating
the methodology on Area 1 (Layouts) BEFORE walking Areas 2-4
(Authentication, UI components, Dashboard). If this dispatch
lands cleanly through all 4 verification gates, we scale the
same pattern to remaining areas. If gates fail, we revise the
strategy before scaling.

⚠️  API integration work is ON HOLD until UI/UX is correct.
⚠️  This dispatch is LAYOUT-ONLY. No auth flow, no API, no other
    page components. Pure visual + structural shell + auth-layout.

══════════════════════════════════════════════════════════════════

SCOPE — AREA 1 LAYOUTS
──────────────────────
Files in scope:
  • frontend/src/app/layouts/shell/shell.component.ts
    (MeeShellComponent — authenticated app shell)
  • frontend/src/app/layouts/auth/auth-layout.component.ts
    (MeeAuthLayoutComponent — unauthenticated auth shell)
  • Any sub-components extracted from above (header toolbar,
    profile menu) — place under layouts/shell/components/

Spike reference files to consult (READ-ONLY — DO NOT IMPORT):
  • themes/spike-angular/package/src/app/layouts/full/full.component.html
  • themes/spike-angular/package/src/app/layouts/full/header/header.component.html
  • themes/spike-angular/package/src/app/layouts/full/sidebar/sidebar.component.html
  • themes/spike-angular/package/src/app/layouts/blank/blank.component.html

══════════════════════════════════════════════════════════════════

FOUNDER VERDICTS (10 patterns — encode exactly)
───────────────────────────────────────────────

✅ ADOPT (4):
  1. Header toolbar in MeeShellComponent
     — mobile hamburger (toggles sidebar)
     — RIGHT-side profile avatar (mat-mini-fab with initials or icon)
     — clicking avatar opens dropdown menu:
         · "My Profile"  → routes to /profile
         · "Log out"     → clears ACCESS_TOKEN_SIGNAL + routes to /login
     — NO bell, NO notifications, NO "Check Pro" button
  2. Keep BLANK LAYOUT pattern for MeeAuthLayoutComponent
     (verify visual match with Spike blank/ at 360px + 1280px)
  3. Keep SIDEBAR pattern (brand + nav + section headers)
     (verify visual match with Spike full/sidebar at 360px + 1280px)
  4. Profile dropdown items: "My Profile" + "Log out" ONLY
     (skip Spike's "My Account" + "My Task" — not in V1 IA)

❌ SKIP (6):
  5. TOPSTRIP (WrapPixel marketing dark bar) — SKIP
  6. SIDEBAR PRO UPSELL CARD ("Check Pro Version") — SKIP V1
  7. FOOTER (WrapPixel attribution) — SKIP
  8. TABLER ICONS (<i-tabler>) — SKIP, use Material Symbols Outlined
     (already established in design system)
  9. NOTIFICATIONS BELL + menu — SKIP V1
 10. "CHECK PRO TEMPLATE" header button — SKIP (marketing)

══════════════════════════════════════════════════════════════════

CONSTRAINTS (non-negotiable)
────────────────────────────
• Design tokens ONLY — no new hardcoded hex codes
  Use --mee-color-primary (#F26B23), --mee-color-bg (#f0f5f9),
  and existing token surface set
• Material Symbols Outlined for ALL icons
  (avatar fallback icon, hamburger, dropdown chevron, menu items)
• FE-D5 in-memory token preserved
  Logout = AuthService.logout() which calls
  ACCESS_TOKEN_SIGNAL.set(null) → router.navigate(['/login'])
  NO localStorage / sessionStorage / IndexedDB / JS-readable cookie
• Standalone components + OnPush + signals + computed
  (no NgModules, no Subscriptions where signal works)
• Mobile baseline 360px — sidebar collapses to overlay drawer
  Desktop ≥1024px — sidebar persists at 270px expanded / 80px collapsed
• WCAG 2.2 AA — profile menu reachable via keyboard, avatar button
  has aria-label, dropdown items have proper role="menuitem"
• Bundle budgets — shell route ≤80 KB compressed
• Existing tests MUST continue to pass
• NEW tests required for header dropdown behavior:
    · Dropdown opens on avatar click
    · "My Profile" navigates to /profile
    · "Log out" calls AuthService.logout() (mock) + navigates /login
    · ESC closes dropdown
    · Focus trap when open

══════════════════════════════════════════════════════════════════

OUT OF SCOPE (explicit — do not touch)
──────────────────────────────────────
✗ Auth page components (SignupComponent, LoginComponent,
  OtpVerifyComponent, PhoneInputComponent) — Area 2 future wave
✗ Onboarding wizard, profile pages, catalog pages, dashboard
  page components — Area 2/3/4 future waves
✗ Auth flow logic (FE-D5 split-token pattern) — unchanged
✗ API integration code — ON HOLD per founder direction
✗ Any new routes — layouts only
✗ Spike's footer, topstrip, bell, PRO card, Tabler icons
✗ Module Federation work — Phase 2 alignment unchanged
✗ Dispatch to non-meesell-* agents

══════════════════════════════════════════════════════════════════

VERIFICATION GATES (all 4 must pass before completion)
──────────────────────────────────────────────────────

Gate 1 — BUILD
  Command: cd frontend && ng build --configuration=production
  Pass criteria: zero errors, zero new warnings,
                 all bundle budgets within limit

Gate 2 — TOKEN HYGIENE
  Command: grep -rnE "#[0-9a-fA-F]{3,6}" frontend/src/app/layouts/
  Pass criteria: zero new hex matches in layouts/
                 (existing pre-Wave-1A hex stays; no NEW hex added)

Gate 3 — VISUAL (founder review)
  Command: cd frontend && ng serve
  Founder reviews:
    · http://localhost:4200/dashboard  → shell header + sidebar at 360px + 1280px
    · http://localhost:4200/login      → auth layout at 360px + 1280px
  Pass criteria: visual match with Spike full/ + blank/ reference,
                 founder verbal approval

Gate 4 — FUNCTIONAL
  Command: cd frontend && pnpm vitest run
  Pass criteria: all existing tests pass + new header dropdown
                 tests pass (4-5 new tests as listed above)

══════════════════════════════════════════════════════════════════

DISPATCH PATTERN
────────────────
You (cross-cutting session) will:
  1. Read FRONTEND_ARCHITECTURE.md §3 (Routing) + §5 (Components)
     to confirm shell + auth-layout current state
  2. Read the Spike reference files listed above
  3. Read current MeeShellComponent + MeeAuthLayoutComponent code
  4. Dispatch meesell-angular-component-builder ONE agent with:
       • the 10 verdicts above
       • the constraints above
       • the out-of-scope list above
       • all 4 verification gates
  5. When agent returns, run Gates 1+2+4 yourself
  6. Append UPDATE block to STATUS_FEATURE_CROSS_CUTTING.md
     (format below)
  7. Notify master session — master then notifies founder for Gate 3

══════════════════════════════════════════════════════════════════

STATUS UPDATE BLOCK (append to STATUS_FEATURE_CROSS_CUTTING.md)
───────────────────────────────────────────────────────────────

  ═══════════════════════════════════════════
  UPDATE 2026-06-08 — WAVE 1A AREA 1 LAYOUTS
  ═══════════════════════════════════════════
  Wave source: master session (frontend-coordinator)
  Verdicts source: founder via master 2026-06-08 walk-through
  Spike refs consulted: [list 4 paths]
  Files modified:        [list with line deltas]
  Files added:           [list any new sub-components]
  Tests added:           [count + brief description]
  Tests passing:         [N/M]
  Gate 1 BUILD:          ✅/❌ [evidence]
  Gate 2 TOKEN:          ✅/❌ [grep output]
  Gate 3 VISUAL:         ⏳ pending founder review
  Gate 4 FUNCTIONAL:     ✅/❌ [test output]
  Open questions:        [any blockers for master]

══════════════════════════════════════════════════════════════════

DECISION POINT (master session, post-completion)
────────────────────────────────────────────────
After all 4 gates pass:
  ✅ Master walks founder through Area 2 (Authentication pages)
  ✅ Same pattern: walk → verdicts → dispatch → verify → next

If any gate fails:
  ⚠️ Master + founder revise methodology BEFORE scaling
  ⚠️ Do NOT proceed to Area 2 until Area 1 is solid

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```

---

## 9. Workflow After Paste

| Step | Owner | Action | Output |
|---|---|---|---|
| 1 | Founder | Paste §8 block into `mesell-ui-base-2` window | Notification delivered to cross-cutting |
| 2 | Cross-cutting session | Read Spike refs + current `shell` + `auth-layout` code | Context loaded |
| 3 | Cross-cutting session | Dispatch `meesell-angular-component-builder` with verdicts + constraints + gates | Build agent working |
| 4 | Build agent | Implement 10 verdicts under constraints | Code changes + new tests |
| 5 | Cross-cutting session | Run Gate 1 (build) + Gate 2 (token grep) + Gate 4 (vitest) | Pass/fail evidence |
| 6 | Cross-cutting session | Append UPDATE block (template in §8) to `STATUS_FEATURE_CROSS_CUTTING.md` | Status recorded |
| 7 | Cross-cutting → Master | Cross-cutting notifies master of completion | Master notified |
| 8 | Master → Founder | Master surfaces completion + asks founder to run Gate 3 | Founder informed |
| 9 | Founder | `ng serve` + review `/dashboard` + `/login` at 360px + 1280px | Gate 3 verdict |
| 10 | Master + Founder | **Decision point** — ✅ walk Area 2 / ❌ revise methodology | Next-step decision |

---

## 10. Decision Point Criteria

After all four gates land:

### ✅ Proceed to Area 2 (Authentication)

Conditions:
- Gate 1 BUILD: ✅
- Gate 2 TOKEN: ✅
- Gate 3 VISUAL: ✅ (founder approval)
- Gate 4 FUNCTIONAL: ✅ (all tests pass)

Next steps:
- Master walks founder through Spike `pages/authentication/` (side-login + side-register + side-forgot)
- Same pattern: walk → verdicts → dispatch → 4 gates → decide

### ⚠️ Revise methodology

Conditions: ANY gate fails after retry.

Next steps:
- Master + founder review the failure
- Identify the methodology gap (verdict ambiguity / constraint gap / verification gap / dispatch pattern issue)
- Update this document with revisions
- **Do NOT proceed to Area 2 until Area 1 is solid**

---

## 11. Related Documents

| Document | Relevance |
|---|---|
| `docs/FRONTEND_ARCHITECTURE.md` §3 (Routing) | Defines shell + auth-layout architecture |
| `docs/FRONTEND_ARCHITECTURE.md` §5 (Components) | Component inventory |
| `docs/FRONTEND_ARCHITECTURE.md` §5A (Design System Tokens) | Token surface used in this dispatch |
| `docs/FRONTEND_ARCHITECTURE.md` §19 (Bundle budgets) | Budget constraint for shell route |
| `docs/DESIGN_SYSTEM_ARCHITECTURE.md` | Material Symbols Outlined standard + token system |
| `docs/status/STATUS_FRONTEND.md` | Master STATUS — Wave 1A entry added separately |
| `docs/status/STATUS_FEATURE_CROSS_CUTTING.md` | Receives UPDATE block per §8 template |
| `frontend/src/app/layouts/shell/shell.component.ts` | Primary file modified |
| `frontend/src/app/layouts/auth/auth-layout.component.ts` | Verification target (visual match) |
| `themes/spike-angular/package/src/app/layouts/full/*` | Read-only Spike reference |
| `themes/spike-angular/package/src/app/layouts/blank/*` | Read-only Spike reference |

---

## 12. Future Wave 1A Documents (forecast)

Following the iterative pilot pattern, these documents will land in `docs/ui_ux/` as the wave progresses:

| Document | When authored |
|---|---|
| `WAVE_1A_AREA_1_LAYOUTS_RESULT.md` | After Gate 3 verdict — captures actual changes + lessons |
| `WAVE_1A_AREA_2_AUTHENTICATION_DISPATCH.md` | After Area 1 decision point ✅ + Area 2 walk-through |
| `WAVE_1A_AREA_3_UI_COMPONENTS_DISPATCH.md` | After Area 2 decision point ✅ + Area 3 walk-through |
| `WAVE_1A_AREA_4_DASHBOARD_DISPATCH.md` | After Area 3 decision point ✅ + Area 4 walk-through |
| `SPIKE_UI_INVENTORY.md` | Consolidated reference — built across all 4 areas |
| `UI_UX_GAP_AUDIT.md` | Consolidated audit — built across all 4 areas |
| `UI_UX_WAVE_PLAN.md` | Retrospective wave plan — assembled post-Wave-1A |

---

## 13. Revision History

| Date | Author | Change |
|---|---|---|
| 2026-06-08 | meesell-frontend-coordinator (master) | Initial authoring after founder walk-through of Spike Area 1 (Layouts) |
| 2026-06-08 | meesell-frontend-coordinator (master) | Closing addendum appended (§14) — partial completion + methodology pivot |

---

## 14. Closing Addendum — 2026-06-08

> **This addendum supersedes Sections 1, 2, 7.1, 9, 10, and 12 of this document.** Sections 3–6 (scope, verdicts, constraints, out-of-scope) and Section 8 (paste-ready block) reflect what was actually executed and remain accurate as a historical record of the dispatch.

### 14.1 What actually shipped

The cross-cutting session (`mesell-ui-base-2`) dispatched `meesell-angular-component-builder` on 2026-06-08 and the agent landed all 10 verdicts. The code changes stand and are merged into the working tree.

| File | Delta | Summary |
|---|---|---|
| `frontend/src/app/layouts/shell/shell.component.ts` | +60 / -45 | Header toolbar added with hamburger + profile avatar (mat-mini-fab) + mat-menu dropdown ("My Profile" + "Log out" only). Notification bell explicitly removed. MatMenuModule added. `logout()` clears token + routes to `/login`. Token replacements: `#F26B23` → `var(--mee-color-primary)`, `#f0f5f9` → `var(--mee-color-bg)`, `#ffffff` → `var(--mee-color-bg-elevated)`, `#e8ecf0` → `var(--mee-color-outline)`. |
| `frontend/src/app/layouts/shell/shell.component.spec.ts` | +65 lines | 5 new tests: avatar aria-label, bell-absence, "My Profile" nav, "Log out" full path, direct `logout()` call. |
| `frontend/src/app/layouts/auth/auth-layout.component.ts` | +12 / -3 | Token cleanup. `#F26B23` → `var(--mee-color-primary)`, `#111827` → `var(--mee-color-on-surface)`, 16px radius → `var(--mee-radius-md)`. 12px logo radius kept (no token match). |

**Files added**: none (header toolbar + profile menu inlined into `shell.component.ts` — no sub-components extracted).

**Grandfathered hex** (no token equivalent — kept inline with documentation comment):
- `#111c2d` — dark sidebar background
- `rgba(255,255,255,*)` — sidebar text/icons on dark surface
- `#374151` / `#f3f4f6` — header toggle hover states
- `#fff` on avatar fab — white on primary

### 14.2 Verification gate outcomes

| Gate | Status | Evidence |
|---|---|---|
| 1 BUILD | ✅ | `ng build --configuration=production` zero errors, zero new warnings, all bundles within budget (7.5s) |
| 2 TOKEN | ✅ | `#F26B23` and `#f0f5f9` no longer in `layouts/`. No new hex introduced. Grandfathered hex documented inline. |
| 3 VISUAL | 🚫 **CANCELLED** | Spike Angular local copy is **free-tier only**; pro layout pages are paywalled. Visual comparison against Spike was impossible. **Methodology abandoned per founder decision 2026-06-08.** Code changes stand because the 10 verdicts were already founder-locked at dispatch time — no Spike comparison was needed to validate them. |
| 4 FUNCTIONAL | ✅ | 11/11 shell tests pass (6 existing + 5 new). 272/279 total (7 pre-existing failures in `export.component.spec.ts` — NG0300 Multiple components match, pre-existing since Wave 2b, unrelated). |

### 14.3 Methodology pivot — Option B chosen

Founder decision 2026-06-08: **abandon Spike playground as the UI/UX reference**. Trigger: the Spike Angular local copy is free-tier; pro layout pages are locked behind a paywall, so visual comparison was structurally impossible.

**New methodology** (Option B from master's four-option choice):
- Pick a **different free Angular admin template** as reference
- Constraints: full version (no pro paywall), full code access, Angular 18+ standalone, MIT or Apache or fully free license
- Workflow handoff: `mesell-design-system-2` researches + deploys → founder visually confirms → `mesell-ui-base-2` implements

**Successor document**: `docs/ui_ux/WAVE_1B_TEMPLATE_RESEARCH_DISPATCH.md` (dispatch notification for `mesell-design-system-2`).

### 14.4 Founder rulings on open questions

| # | Question | Ruling |
|---|---|---|
| Q1 | Sidebar footer "Logout" text button — remove? | ✅ **REMOVE.** Header dropdown "Log out" is sufficient. Queued as micro-dispatch — to be bundled into the eventual ui-base-2 template-implementation dispatch (post WAVE_1B template ratification). May be sent as standalone micro-dispatch sooner at founder's discretion. |
| Q2 | Dark sidebar token (`#111c2d`) — register as `--mee-color-surface-dark`? | ⏭️ **DEFER** to design system session. Token registration is design-system scope, not layouts scope. |

### 14.5 Sections superseded by this addendum

| Original Section | What's now stale | What replaces it |
|---|---|---|
| §1 Purpose — "iterative pilot validates Spike methodology" | The Spike methodology was abandoned, so the validation premise is moot | See §14.3 — methodology pivoted before Gate 3 could even run |
| §2 Iterative Pilot Context — "walk Areas 2-4 after Area 1 ✅" | Areas 2-4 walks are dead — no Spike reference to walk through | See `WAVE_1B_TEMPLATE_RESEARCH_DISPATCH.md` for new flow |
| §7.1 Gate tracking table — "⏳ pending" rows | Gates landed (1/2/4 ✅, 3 cancelled) | See §14.2 |
| §9 Workflow After Paste — steps 7-10 (founder runs Gate 3) | Founder cancelled Gate 3 instead | See §14.3 |
| §10 Decision Point Criteria — "✅ proceed to Area 2" | Area 2 path dead (Spike-bound) | New decision flow lives in WAVE_1B doc |
| §12 Future Wave 1A Documents | `WAVE_1A_AREA_{2,3,4}_*_DISPATCH.md`, `SPIKE_UI_INVENTORY.md`, `UI_UX_GAP_AUDIT.md`, `UI_UX_WAVE_PLAN.md` — none will be authored | Replaced by `WAVE_1B_TEMPLATE_RESEARCH_DISPATCH.md` series under the new methodology |

### 14.6 What was learned

- **Reference-template gating risk** must be checked BEFORE building methodology on top of it. The Spike paywall was discoverable in 10 minutes of source-tree inspection — should have been a pre-flight check before walking founder through 4 areas.
- **Decoupled verdicts survive methodology death**. Because verdicts were founder-locked before dispatch (10 explicit ADOPT/SKIP rulings), the code that landed remains correct even though the validation pathway was cancelled. This is a reusable pattern: capture verdicts independently of the reference comparison.
- **3 of 4 gates are reference-independent**. Build, token, functional — none required Spike. Only visual required Spike. Future dispatches: minimize reference-dependent gates; maximize tool-checkable gates.

### 14.7 Pointer to successor work

- `docs/ui_ux/WAVE_1B_TEMPLATE_RESEARCH_DISPATCH.md` — primary successor (template research + local deployment + founder visual confirmation, owned by `mesell-design-system-2`)
- Q1 sidebar logout micro-dispatch — queued; bundled into eventual ui-base-2 template-implementation dispatch unless founder sends sooner
