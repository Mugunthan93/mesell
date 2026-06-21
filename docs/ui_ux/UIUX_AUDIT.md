# MeeSell V1 — Phase-1 UI/UX Audit

**Author:** meesell-frontend-coordinator (Frontend Lead) · **Session:** `mesell-uiux-audit-frontend-session-1`
**Date:** 2026-06-21 · **Branch:** `feature/uiux-audit/frontend` (off `develop` @ `1b71f91`)
**Stack audited:** LIVE running app — shell `:4200` (static build) + backend `:8000` + 7 Native-Federation remotes `:4201–4207`, slot-0/develop.
**Design target (founder-confirmed):** `frontend/libs/ui-kit` `mee-*` components + `theme.ts` tokens (MeeSell orange `#F26B23`, Aura preset). Sakai-ng = layout reference only. **No reversion to raw PrimeNG/Sakai is proposed** — that conflicts with the UI-DS decoupling plan.

> **THIS IS AN AUDIT PASS — NO PRODUCT-CODE CHANGES.** Each finding is phrased so it can become a Phase-2 SPEC line. Founder reviews before any Phase-2 work begins. Screenshots live under `/tmp/uiux-audit/` (referenced, not committed).

---

## Audit conditions & caveats (read before the matrix)

Two environmental facts materially shape the findings and MUST be carried into Phase 2:

1. **The `:4200` shell is a static build with NO `/api` dev-proxy.** Every relative `POST/GET /api/v1/*` returns the SPA `index.html` (HTTP 200, `text/html`) instead of reaching backend `:8000`. Consequence: **UI login is broken on this served stack** (OTP "Continue" → 200-with-HTML → FE parse-fail → generic "Something went wrong"), and every authenticated screen's data fetch falls through to its graceful empty/error state. This is an **INFRA/serving issue**, not product code — but it blocks the documented "log in via OTP 000000" path. → see **F-ENV-1 (P0, infra)**.
2. **Gated screens were reached by injecting a real backend-minted access token into the shell's in-memory `AuthService` and navigating via the SPA router** (a normal hard-load runs `AuthService.bootstrap()`, which 401s on the no-proxy refresh cookie and bounces to `/login`). This bypasses the shell's normal init. The desktop **sidebar-overlap** observed on gated screens is therefore **strongly suspected to be an artifact of this injection bypass** (the shell's layout state `staticMenuDesktopInactive` was left `true` while the 260px fixed sidebar still rendered) — NOT a confirmed product bug. The shell CSS itself is correct (`.mee-layout__main { margin-left: 260px }`). **Mobile (390px) rendered the same screens with zero overlap.** → see **F-SHELL-1 (P1, needs re-confirm)**.

OTP backend contract confirmed working directly against `:8000`: `POST /api/v1/auth/otp/send` (E.164 phone, `3/3600s` global rate-limit) → `POST /api/v1/auth/otp/verify` (`{phone, otp:"000000"}`) → `{access_token, expires_in:900}` + HttpOnly refresh cookie. Dev bypass `000000` works only after a successful send for that phone.

---

## PRIORITY MATRIX (Phase-2 SPEC candidates)

### P0 — blocks usability
| ID | Screen(s) | Finding (SPEC-ready) | Owner |
|----|-----------|----------------------|-------|
| **F-ENV-1** | login / all gated | The served `:4200` shell has no `/api` proxy → OTP "Continue" gets a 200-HTML response, fails to parse, and shows "Something went wrong"; **UI login cannot complete and no authenticated screen can fetch data**. Fix the dev-serving so `/api/*` proxies to `:8000` (the `ng serve` proxy config exists at `frontend/apps/shell/proxy.conf.json` but the static `serve.js` build does not apply it). | infra (memo) |

### P1 — notable
| ID | Screen(s) | Finding (SPEC-ready) | Owner |
|----|-----------|----------------------|-------|
| **F-SHELL-1** | dashboard, catalog-list, catalog-form, live-listings, pricing, export (desktop) | On desktop the 260px fixed dark sidebar overlaps page content (titles/cards clipped on the left) because layout state is `--sidebar-inactive` while the sidebar still renders. **Suspected injection-bypass artifact** (CSS is correct; mobile is clean). **SPEC: re-audit all gated screens under a real login once F-ENV-1 is fixed; if the overlap reproduces, fix the shell's desktop sidebar-active default in `LayoutService` init.** | frontend (shell) — re-confirm |
| **F-NAV-1** | smart-picker, catalog-form, catalog-list, pricing, export | `routerLinkActive` over-matches: the sidebar **"My Catalogs" AND "New Product" both show the active orange treatment on `/catalogs/new`**, and "My Catalogs" stays active on every `/catalogs/:id/*` sub-route. SPEC: scope `routerLinkActive` with `[routerLinkActiveOptions]={exact}` per nav item / disambiguate the `/catalogs` vs `/catalogs/new` prefix match. | frontend (shell) |
| **F-AUTH-1** | login, signup | "Continue/Sign up with Google" is a `<div class="google-area">` — **not a `<button>`/`mee-button`, no `role="button"`, no keyboard handler**. Design-system drift + a11y (not keyboard-focusable/activatable). SPEC: wrap the GIS button in `mee-button` (or a focusable `role="button"` with key handlers) consistent with the primary CTA. | frontend (component) |
| **F-IA-1** | dashboard vs catalog-list | **Two distinct surfaces both titled "My Catalogs"**: `/dashboard` (stat home: Draft/Ready counts + empty state) and `/catalogs` (filterable card grid). Sidebar "Home" → the stat page; sidebar "My Catalogs" → the grid; both carry the "My Catalogs" page-header. Confusing IA + duplicate naming. SPEC: rename the dashboard header (e.g. "Home"/"Overview") OR merge the two surfaces. | frontend (component) |

### P2 — polish
| ID | Screen(s) | Finding (SPEC-ready) | Owner |
|----|-----------|----------------------|-------|
| **F-BRAND-1** | all in-app chrome | Brand wordmark is lowercase **"mesell"** in the shell topbar + sidebar, but proper-case **"MeeSell"** on landing/login/signup. SPEC: standardise the in-app wordmark to "MeeSell". | ui-styler |
| **F-ACT-1** | catalog-list | The **"Preview" card action is bare text** while "Edit" is a pill button — inconsistent action affordance within the same card. SPEC: give Preview a consistent secondary-button (`mee-button` variant) treatment. | ui-styler |
| **F-DENS-1** | dashboard, smart-picker, profile, landing | Sparse vertical density on desktop: tall stat cards with small content, single-field smart-picker with large empty canvas below, profile content column appears off-centred with a large left gutter, landing hero has an empty right half (no illustration). SPEC: tighten desktop spacing / add hero visual / centre the profile column. | ui-styler |
| **F-PRICE-1** | plans, CLAUDE.md | UI shows a **Starter ₹199/mo** tier; CLAUDE.md product blurb says "₹499–1,999/month". Likely intentional plan expansion — flag for founder copy/pricing reconciliation, not a UI defect. | founder note |
| **F-FUNC-1** | pricing, export | Could not verify the full compute/export happy-path on this stack (server-calc only + no proxy → both correctly degrade to a graceful error/idle state). The **error/idle UX is well-handled** ("Couldn't calculate price — please try again", "Ready to calculate", "Ready to export"). SPEC: re-verify functional compute/download once F-ENV-1 is fixed. | frontend — re-verify |

---

## Per-screen audit

Scoring key per dimension: ✅ good · 🟡 minor · 🔴 issue. Dimensions: **1** DS-alignment · **2** Sakai-layout fidelity · **3** Visual consistency vs `theme.ts` · **4** Responsive/mobile (390px) · **5** A11y · **6** UX states · **7** Functional (screens 9–11).

### 1. Landing (`/` — `mfe-dashboard` → `LandingComponent`, PUBLIC)
`/tmp/uiux-audit/01-landing-desktop.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | `mee-button` primary "Start free", proper-case **MeeSell** wordmark, `RouterLink`. |
| 2 Sakai | ✅ | Standard marketing hero + "How it works" 3-step. |
| 3 Visual | ✅ | Solid brand orange CTA confirms theme is correct (in-app washed CTAs are just disabled state). |
| 4 Responsive | — | (desktop captured; public page, low risk) |
| 5 A11y | ✅ | Clear heading hierarchy, link "Log in" / "See how it works". |
| 6 States | ✅ | Static page, no async states. |
**Findings:** F-DENS-1 (empty hero right half), F-BRAND-1 (reference for the in-app drift).

### 2. Login (`/login` — `mfe-auth` → `LoginComponent`, PUBLIC)
`/tmp/uiux-audit/02-login-desktop.png`, `02-login-mobile.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | 🟡 | `mee-auth-layout` + `mee-input` + `mee-button` + `mee-toast` — clean. Google button is NOT a mee-button (F-AUTH-1). |
| 2 Sakai | ✅ | Centred auth card. |
| 3 Visual | ✅ | `#F26B23` primary (renders `opacity:0.6` only when disabled/empty — correct). Card radius/shadow match `theme.ts`. |
| 4 Responsive | ✅ | 390px: card fills width, no overflow, good touch targets. |
| 5 A11y | 🟡 | Phone input labelled "Mobile Number *". Google `<div>` not keyboard-operable (F-AUTH-1). |
| 6 States | 🔴 | Error state surfaces a **generic** "Something went wrong" on the no-proxy 200-HTML (F-ENV-1); message is not actionable. |
**Findings:** F-AUTH-1 (P1), F-ENV-1 (P0).

### 3. Signup (`/signup` — `mfe-auth` → `SignupComponent`, PUBLIC)
`/tmp/uiux-audit/03-signup-desktop.png`, `03-signup-mobile.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | 🟡 | `mee-input` ×2 (Full Name, Mobile) + `mee-button` + Google `<div>` (F-AUTH-1). |
| 2–4 | ✅ | Consistent with login; responsive clean. |
| 5 A11y | 🟡 | Both fields labelled; Google button same a11y gap. |
| 6 States | ✅ | Disabled CTA until valid; "Log in" cross-link present. |
**Findings:** F-AUTH-1 (P1).

### 4. Onboarding (`/onboarding` — `mfe-onboarding` → `OnboardingComponent`)
Reachable (route wired); not deep-audited this pass because the seeded test user already routes past it (`onboarding_complete:false` but the flow lands on dashboard via injection). No blocking findings observed. **SPEC: include in the Phase-2 re-audit once F-ENV-1 enables the real signup→onboarding flow.**

### 5. Dashboard / Home (`/dashboard` — `mfe-dashboard` → `DashboardComponent`)
`/tmp/uiux-audit/05-dashboard-desktop.png`, `05-dashboard-mobile.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | `mee-shell`, `mee-sidebar`, `mee-topbar`, `mee-page-header`, `mee-stat-card` ×2, `mee-empty-state`, `mee-card`, `mee-menu`. Exemplary `mee-*` usage. |
| 2 Sakai | ✅ | Sidebar + topbar + stat-cards + content matches Sakai dashboard structure. |
| 3 Visual | ✅ | Tokens consistent. |
| 4 Responsive | ✅ | 390px: stat cards 2-up, search/filter stack, **bottom tab bar** (Home/Catalogs/New/Account) with active state. Excellent mobile. |
| 5 A11y | ✅ | 0 unlabelled inputs, 0 img-without-alt, 0 buttons without accessible name. |
| 6 States | ✅ | Strong empty state (icon + copy + CTA). Data empty due to no-proxy (graceful). |
**Findings:** F-SHELL-1 (desktop overlap, suspected artifact), F-IA-1 (duplicate "My Catalogs"), F-BRAND-1, F-DENS-1 (tall stat cards).

### 6. Smart-picker (`/catalogs/new` — `mfe-catalog` → `SmartPickerComponent`)
`/tmp/uiux-audit/06-smartpicker-desktop.png`, `06b-smartpicker-filled.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | `mee-textarea` + `mee-page-header`; good helper text ("Between 10 and 500 characters") + placeholder. |
| 2 Sakai | ✅ | Single-field intro form. |
| 3 Visual | ✅ | Consistent. |
| 4 Responsive | — | (desktop primary) |
| 5 A11y | ✅ | Field labelled; the empty-text button is the topbar hamburger (correctly `aria-label="Toggle navigation menu"`). |
| 6 States | ✅ | On AI-suggest failure (no proxy) degrades gracefully to "No automatic suggestions found. Browse the full category list manually." + "Browse all categories". Good fallback. |
**Findings:** F-NAV-1 (both "My Catalogs"+"New Product" active), F-SHELL-1, F-DENS-1 (sparse below field).

### 7. My-Catalog list (`/catalogs` — `mfe-catalog` → `CatalogListComponent`)
`/tmp/uiux-audit/08-cataloglist-desktop.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | Catalog cards with status badges (Ready/Draft/Exported), category breadcrumb, SKU count, date; filter chips (All/Draft/Ready/Exported/Live); FAB. (Rendered seed data.) |
| 2 Sakai | ✅ | Card-grid + filter row. |
| 3 Visual | 🟡 | Status badges good; "Preview" action is bare text vs "Edit" pill (F-ACT-1). |
| 4 Responsive | — | (desktop captured; grid expected to wrap) |
| 5 A11y | ✅ | Card content readable; thumbnails are placeholder icons (seed). |
| 6 States | ✅ | Loaded + empty handled. |
**Findings:** F-ACT-1 (P2), F-IA-1, F-SHELL-1.

### 8. Catalog-form / edit (`/catalogs/:id/edit` — `mfe-catalog` → `CatalogFormComponent`)
`/tmp/uiux-audit/07-catalogform-desktop.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | Breadcrumb, Draft badge, "AI fill" button, Compulsory/Recommended/Optional accordions, Back/Images footer nav. |
| 2 Sakai | ✅ | Sectioned form with progressive disclosure. |
| 3 Visual | ✅ | Consistent. |
| 4 Responsive | — | (desktop primary) |
| 5 A11y | 🟡 | Accordion counts shown; field-level a11y not deep-checked (empty field sets on seed). |
| 6 States | ✅ | Renders with cached category context even with no live data. (Historical wizard bugs — `product_name` AI-fill key, `size_in_ltrs` 422 — are backend/contract, out of UI-audit scope; re-verify functionally in Phase 2.) |
**Findings:** F-SHELL-1, F-NAV-1.

### 9. Catalog-view (`/catalogs/live` — `mfe-catalog` → `LiveListingsComponent`)
`/tmp/uiux-audit/09-livelistings-desktop.png`
> **Note:** the old `:id/preview` route was RETIRED (PR #278); "My Live Listings" is the current live-product view. Audited as screen 9.
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | Empty-state + XLSX upload control (Select file / Upload / Cancel) + help text. |
| 6 States | ✅ | Clear empty state: "No listings loaded yet. Upload your Inventory Update File…" + guidance "Download your Inventory Update File from your Meesho supplier panel, then upload it here." |
| 7 Functional | 🟡 | Upload/parse not exercised (no proxy). Affordances present and labelled. |
**Findings:** F-SHELL-1.

### 10. Pricing calculator (`/catalogs/:id/pricing` — `mfe-pricing` → `PricingComponent`)
`/tmp/uiux-audit/10-pricing-desktop.png`, `10-pricing-mobile.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | `mee-card` ×2, `mee-input` ×2, `mee-button` ×2, `mee-page-header`, `mee-offline-banner`. |
| 2 Sakai | ✅ | Two-column form + result panel. |
| 3 Visual | ✅ | Consistent; ₹ adornment. |
| 4 Responsive | ✅ | **390px is perfectly clean** (full title, stacked inputs, P&L below, bottom nav) — confirms desktop overlap is shell-state, not pricing-remote layout. |
| 5 A11y | 🟡 | Number inputs labelled ("Selling price (listed on Meesho)", "Commission % (optional)"). |
| 6 States | ✅ | Idle "Ready to calculate" + error "Couldn't calculate price — please try again" both well-designed. |
| 7 Functional | 🔴(env) | **Server-calc only** ("NEVER compute locally"); with no proxy the calc returns the error banner. Compute happy-path **could not be verified** (F-FUNC-1). |
**Findings:** F-SHELL-1, F-NAV-1, F-FUNC-1.

### 11. Export (`/catalogs/:id/export` — `mfe-export` → `ExportComponent`)
`/tmp/uiux-audit/11-export-desktop.png`
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | `mee-card` ×2, `mee-button`, `mee-page-header`; "Pre-export checklist" + "Generate Export". |
| 2 Sakai | ✅ | Checklist + result panel. |
| 3 Visual | ✅ | Consistent. |
| 6 States | ✅ | Idle "Ready to export — Your Meesho-format XLSX will be generated once all checks pass." + "No blocking issues detected." |
| 7 Functional | 🔴(env) | Export generate/download **could not be triggered** end-to-end on the no-proxy stack (F-FUNC-1). |
**Findings:** F-SHELL-1, F-NAV-1, F-FUNC-1.

### (Bonus) Billing / Plans (`/billing/plans` — `mfe-billing` → `BillingRoutes`)
`/tmp/uiux-audit/11-plans-desktop.png` — not in the core 11 but on the user journey.
| Dim | Score | Note |
|---|---|---|
| 1 DS | ✅ | Trial banner + 4-tier pricing cards (Free / Starter ₹199 / Pro ₹499 "Most Popular" / Business ₹1,999) with feature checklists; renders fully (static content). |
| 3 Visual | ✅ | "Most Popular" highlight, consistent cards. |
**Findings:** F-PRICE-1 (₹199 Starter vs CLAUDE.md "₹499–1,999").

---

## Overall verdict

The product is in **strong UI/UX shape**. Design-system adherence is excellent — every audited screen composes `mee-*` wrappers (`mee-shell/sidebar/topbar/page-header/stat-card/card/empty-state/button/input/textarea/offline-banner`) with `theme.ts` tokens; raw PrimeNG appears only behind the wrappers (the `p-*` tags in fingerprints are the internals of `mee-*`). The **mobile experience is the standout** — bottom tab bar, stacked layouts, zero horizontal overflow at 390px — well-suited to Tirupur mobile sellers. Empty/error/idle states are consistently well-designed (a clear improvement over the project's history of blank-error/missing-label bugs).

**Worst screens (relative):**
- **Login/signup (functional)** — blocked by the no-proxy serving (F-ENV-1, P0) and the non-button Google control (F-AUTH-1, P1).
- **Pricing & export (functional verification)** — happy-path unverifiable on this stack (F-FUNC-1).
- **Desktop sidebar overlap** (F-SHELL-1) is the most visually alarming but is **most likely a test-harness artifact** of the auth-injection workaround; it must be re-confirmed under a real login before any code change.

**Nothing here contradicts the UI-DS decoupling direction.** All fixes stay within the `mee-*` + `theme.ts` system. The two genuine cross-cutting product issues for Phase 2 are **F-NAV-1** (routerLinkActive over-match) and **F-IA-1** (duplicate "My Catalogs" surfaces); the rest are polish or environment.

**Recommended Phase-2 sequence:** (1) infra fixes F-ENV-1 → unblocks a real-login re-audit; (2) re-confirm F-SHELL-1 + F-FUNC-1 under real auth; (3) frontend fixes F-NAV-1, F-AUTH-1, F-IA-1; (4) ui-styler polish F-BRAND-1, F-ACT-1, F-DENS-1; (5) founder reconciles F-PRICE-1.

---

## Re-audit (proxy-enabled stack)

**Author:** meesell-frontend-coordinator (Frontend Lead) · **Session:** `mesell-uiux-reaudit-frontend-session-1`
**Date:** 2026-06-21 · **Branch:** `feature/uiux-reaudit/frontend` (off `develop` @ `1b71f91`)
**Stack:** shell `:4200` **with `/api` reverse-proxy LIVE (PR #368)** → backend `:8000`; 7 Native-Federation remotes `:4201–4207`. `/api/v1/auth/me` returns a real `401` JSON (not SPA HTML) — proxy verified before the pass.

> **Purpose:** confirm-or-kill the findings the first pass flagged as proxy-contaminated, and run the functional verifications (login, pricing compute, export) that were impossible without the proxy. **FOCUSED scope** — did NOT re-walk all 11 screens. Re-audit screenshots live under `/tmp/uiux-reaudit/` (referenced, not committed).

### Method note — REAL login achieved, zero injection
Unlike the first pass (which injected a minted token into `AuthService`), this pass logged in through the **actual UI** with **no injection**: phone `9876543210` → "Continue" fired a real `POST /api/v1/auth/otp/send` (202, through the proxy) → UI advanced to `/otp-verify` → entered `000000` → real `POST /api/v1/auth/otp/verify` (200, `{access_token, expires_in:900}` + HttpOnly refresh cookie) → landed on `/onboarding` → completed the onboarding form (real `/api` write) → redirected to `/dashboard`. Every gated screen then fetched **real backend data** through the proxy. The desktop overlap re-check was therefore done under a **genuine `AuthService.bootstrap()` init**, which is exactly what the first pass could not exercise.

### Per-check verdicts

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | **Login P0 (F-ENV-1)** | ✅ **RESOLVED** | Full OTP login completes end-to-end through the UI on the proxy stack. The old "200-HTML → parse-fail → 'Something went wrong'" is gone; `otp/send` 202 + `otp/verify` 200 both reached `:8000`. The P0 blocker is **closed by PR #368**. *(login → otp-verify → onboarding → dashboard all UI-driven, no injection.)* |
| 2 | **Desktop sidebar overlap (F-SHELL-1)** | ❌ **KILLED — ARTIFACT** | At **1280px** under real login: `mainMarginLeft:260px`, sidebar `left:0→right:260` (visible), main content box `left:260`, page title "My Catalogs" at `left:284`, **`overlap:false`**. Screenshot `r-05-dashboard-1280.png` shows zero clipping. The first pass's overlap was the auth-injection bypass (layout state never initialised). **Confirmed a test-harness artifact — NOT a product bug. Remove from the backlog.** |
| 3 | **Pricing calculator (functional, F-FUNC-1)** | 🟡 **COMPUTE CORRECT / persistence blocked by DB drift** | `POST /products/{id}/price-calc {selling_price:599}` through the proxy reaches the backend and the **P&L math is correct** (shipping ₹68, GST-on-shipping ₹12.24, TDS ₹0.67, **estimated bank settlement ₹586.09**). It returns **500** only because the **local dev DB has unapplied migrations**: `pricing_calcs` is at alembic `f8fa7a36383f` but head is `e9415bdcae20`; the INSERT references columns (`selling_price`, `shipping`, `total_price`, `commission_fees`, `gst_on_shipping`, `meesho_leaf_id`, `estimated_bank_settlement`) that don't exist in the table yet. **This is dev-environment migration drift (infra/data), NOT a frontend or pricing-engine defect.** The UI degrades to its well-designed "Couldn't calculate price" banner. → **F-MIG-1 (P0, infra/data — dev only).** |
| 4 | **Export button (functional, F-FUNC-1)** | ✅ **FUNCTIONAL** | `POST /products/{id}/export-xlsx` through the proxy returns a clean structured **422** `export.validation_failed` with a `failed_checks` array (`front_image_missing`, `quality_status`) — the pre-export gate working **correctly** (it blocks export until the checklist passes; happy-path is `202 + async export job`). Not a 500, not a degraded error. The export validation engine is confirmed reachable and behaving as specced. *(A fully-completed product with images + passing quality is required to observe the 202; the freshly-created test product legitimately fails the gate.)* |
| 5a | **F-NAV-1 routerLinkActive over-match** | ✅ **CONFIRMED REAL** | On `/catalogs/new`, BOTH sidebar "My Catalogs" (`/catalogs`) AND "New Product" (`/catalogs/new`) carry `active:true` simultaneously (also in the mobile bottom bar: "Catalogs" + "New"). Screenshot `r-06-smartpicker-1280-navactive.png` shows both with the orange-active treatment. Genuine prefix over-match. |
| 5b | **F-AUTH-1 non-button Google control** | ✅ **CONFIRMED REAL** | The login "Continue with Google" control is a `DIV` with `role:null`, `tabindex:null`, no key handler — not keyboard-focusable/activatable. Design-system + a11y drift stands. |

### Functional results (the verifications the first pass couldn't run)

- **Auth OTP login** — works end-to-end through the UI on the proxy stack (send 202 / verify 200 / real session). **F-ENV-1 / P0 is resolved.**
- **Smart-picker AI suggest** — `POST /api/v1/categories/suggest {q:...}` returns real Gemini-backed category suggestions with confidence + reasons (e.g. "Women Fashion > Ethnic Wear > Kurtis", 0.95). Works through the proxy.
- **Onboarding submit** — real `/api` write completes and flips `onboarding_complete`, redirecting to dashboard.
- **Product create** — `POST /api/v1/products {name, category_id}` → 201 (requires a real `category_id`; the smart-picker supplies it).
- **Pricing compute** — math correct (settlement ₹586.09); blocked only by **DB migration drift** on persistence (F-MIG-1, dev infra).
- **Export gate** — structured 422 with actionable `failed_checks`; engine reachable and correct.

### Updated P0 / P1 backlog for Phase-2 (artifacts removed)

**P0**
- ~~F-ENV-1 (login no-proxy)~~ — **CLOSED by PR #368** (proxy live; UI login verified end-to-end).
- **F-MIG-1 (NEW, P0 — infra/data, dev-only):** the local dev Postgres has unapplied alembic migrations (`pricing_calcs` @ `f8fa7a36383f`, head `e9415bdcae20`) → `price-calc` INSERT 500s on missing W2 settlement columns. Run `alembic upgrade head` against the dev DB; verify `price-calc` returns 200 with the settlement (math already proven correct). **Does NOT affect product code; not a Phase-2 UI item — it's a dev-stack hygiene fix.** Owner: infra / data (memo).

**P1**
- **F-NAV-1 (CONFIRMED):** scope `routerLinkActive` with `[routerLinkActiveOptions]={exact:true}` per nav item so `/catalogs` doesn't stay active on `/catalogs/new` and `/catalogs/:id/*`. Owner: frontend (shell).
- **F-AUTH-1 (CONFIRMED):** wrap the GIS "Continue with Google" control in `mee-button` (or a focusable `role="button"` + key handlers). Owner: frontend (component).
- **F-IA-1 (unchanged):** two surfaces titled "My Catalogs" (`/dashboard` stat home + `/catalogs` grid). Rename the dashboard header (e.g. "Home"/"Overview") or merge. Owner: frontend (component).
- ~~F-SHELL-1 (desktop sidebar overlap)~~ — **KILLED as an auth-injection artifact** (verified `overlap:false` under real login). **Removed from the backlog.**
- ~~F-FUNC-1 (pricing/export unverifiable)~~ — **DISCHARGED:** export functional; pricing math correct (persistence blocked only by F-MIG-1 dev drift).

**P2 (unchanged from first pass):** F-BRAND-1 (lowercase "mesell" in-app vs "MeeSell" on landing — re-confirmed in `r-05-dashboard-1280.png`), F-ACT-1 (Preview bare-text action), F-DENS-1 (sparse desktop density — re-confirmed on smart-picker), F-PRICE-1 (₹199 Starter vs CLAUDE.md copy — founder note).

### Re-audit verdict
The proxy fix (PR #368) **closes the single P0** (login) and **discharges the F-FUNC-1 unknowns**. The most visually alarming first-pass finding — the desktop sidebar overlap — is **definitively an auth-injection artifact and is removed**. The only genuinely new item is **F-MIG-1**, a **dev-stack migration drift** (not product code): the pricing engine computes correctly and the only failure is persisting the result into a stale local table. The real Phase-2 frontend backlog is small and unchanged in substance: **F-NAV-1, F-AUTH-1, F-IA-1** (P1) + the P2 polish set. Nothing contradicts the UI-DS decoupling direction.
