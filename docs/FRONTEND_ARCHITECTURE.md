# MeeSell — Frontend Architecture (Construction Contract)

**Status:** SKELETON — Section 0 LOCKED, Section 1 DRAFT, Sections 2-23 SKELETON
**Date:** 2026-06-05
**Drives:** the 3 frontend specialists (`meesell-angular-component-builder`, `meesell-angular-service-builder`, `meesell-angular-ui-styler`)
**Supersedes:** any prior implicit frontend layout in session-0 and session-1 drafts; the existing React 18 scaffold under `frontend/src/` is to be REPLACED with the Angular 18 stack per founder ratification 2026-06-05

> This document is the **construction contract** for the three MeeSell frontend specialists. It defines a **Features-first standalone Angular 18 application** with a data-driven dynamic form renderer at its core, organised into ten feature folders plus `core/`, `shared/`, and `design-system/`. Each section carries an explicit `STATUS: SKELETON | DRAFT | LOCKED` line directly under its heading. Specialists may NOT begin code on a section until that section's status is `LOCKED`. A section in `DRAFT` is in founder review and is NOT authoritative for dispatch. The coordinator does not flip a section from `DRAFT` to `LOCKED` — only the founder does, on a turn dedicated to that sign-off.
>
> This document peers with `docs/BACKEND_ARCHITECTURE.md` (the backend construction contract) and `docs/MVP_ARCHITECTURE.md` §4 + §5.6 (the data-driven wizard contract) — it translates them into a frontend-construction plan without contradiction.

---

## Table of Contents

0. [Architectural Premises](#section-0--architectural-premises)
1. [System Topology](#section-1--system-topology)
2. [Feature Catalog](#section-2--feature-catalog)
3. [File Structure](#section-3--file-structure)
4. [`core/` — Cross-Cutting Foundation](#section-4--core--cross-cutting-foundation)
5. [`shared/` — UI Primitives + Pipes + Directives](#section-5--shared--ui-primitives--pipes--directives)
5A. [`design-system/` — Tokens, Theming, Typography, Spacing](#section-5a--design-system--tokens-theming-typography-spacing)
5B. [Wireframe & Mockup Methodology](#section-5b--wireframe--mockup-methodology)
6. [Third-Party Tool Selection](#section-6--third-party-tool-selection)
7. [Feature: `account` (V1 Feature 1 + seller profile)](#section-7--feature-account-v1-feature-1--seller-profile-post-2026-06-05b-merger)
8. (Reserved — content merged into §7 per 2026-06-05B)
9. [Feature: `dashboard` (Feature 8)](#section-9--feature-dashboard-feature-8)
10. [Feature: `smart-picker` (Feature 2)](#section-10--feature-smart-picker-feature-2)
11. [Feature: `catalog-form` (Features 3 + 4)](#section-11--feature-catalog-form-features-3--4)
12. [Feature: `images` (Feature 5)](#section-12--feature-images-feature-5)
13. [Feature: `preview` (Feature 6)](#section-13--feature-preview-feature-6)
14. [Feature: `pricing` (Feature 7)](#section-14--feature-pricing-feature-7)
15. [Feature: `export` (Feature 9)](#section-15--feature-export-feature-9)
16. [Cross-Cutting Walkthroughs](#section-16--cross-cutting-walkthroughs)
17. [Service-Component Communication Rules](#section-17--service-component-communication-rules)
18. [The 11 Primitives + Form Renderer](#section-18--the-11-primitives--form-renderer)
19. [Test Strategy & Performance Budget](#section-19--test-strategy--performance-budget)
20. [Build & Deployment Topology](#section-20--build--deployment-topology)
21. [SOLID, DRY, and Modern Techniques](#section-21--solid-dry-and-modern-techniques)
22. [Acceptance & Sign-Off](#section-22--acceptance--sign-off)
22A. [Risk Register & Mitigations](#section-22a--risk-register--mitigations)
23. [Route Inventory](#section-23--route-inventory)

---

## Section 0 — Architectural Premises

STATUS: LOCKED (2026-06-05, founder ratification of Angular 18 framework)

### A. What this document is

This document is the **construction contract** for the three frontend specialists (`meesell-angular-component-builder`, `meesell-angular-service-builder`, `meesell-angular-ui-styler`). Builders execute against this contract; they do NOT improvise, do NOT infer requirements from CLAUDE.md, and do NOT write code outside what a LOCKED section explicitly authorises. Where this document differs from any prior frontend assumption (session-0 React scaffold, session-1 route drafts, ad-hoc CLAUDE.md interpretation), this document supersedes. `docs/MVP_ARCHITECTURE.md §4 + §5.6` remains the authoritative source for the data-driven wizard contract and the 11 input primitives; this document peers with it and translates it into a frontend-construction plan without contradiction.

Sections in this document carry an explicit `STATUS: SKELETON | DRAFT | LOCKED` line directly under their heading. Specialists may NOT begin code on a section until the section's status is `LOCKED`. A section in `DRAFT` is in founder review and is not authoritative for dispatch.

### B. Framework — Angular 18 standalone (founder-locked 2026-06-05)

**Decision:** The frontend is built in **Angular 18 with standalone components, RxJS + signals, Tailwind + Angular Material, Reactive Forms, HttpClient with global JWT interceptor, and lazy `loadComponent` routing**.

This honours `CLAUDE.md` locked Decisions 9–13:
- D9: Angular 18, not React
- D10: Services + RxJS + signals, not NgRx/Zustand
- D11: Tailwind + Angular Material, not Material alone
- D12: Module Federation deferred to Phase 2
- D13: Ionic + Capacitor deferred to Phase 2

The existing React 18 scaffold under `frontend/src/` (8 pages + 5 components + Vitest tests) is **to be deleted** during the first specialist dispatch under this contract. The React scaffold was a session-1 deviation; founder ratification on 2026-06-05 restored Decision 9 as authoritative.

### C. Architecture style — Features-first standalone

**Decision:** the V1 frontend is built as a single Angular 18 standalone application organised by **feature** (not by type), with each feature owning its own components, services, and routes. Feature-to-feature communication is strictly through `core/` services and typed contracts; cross-feature component imports and cross-feature service imports are forbidden (the rule is concretised in §17).

**Why features-first, not type-first.** Three reasons:
1. **Lazy code-splitting alignment.** Each feature is `loadComponent`-lazy-loaded. A type-first layout (`components/`, `services/`, `pages/`) bundles every page's deps into a shared graph, defeating lazy loading. Features-first means `pricing` ships only when the seller navigates to `/catalogs/:id/pricing`.
2. **Tirupur device floor.** Initial bundle target is ≤180 KB gzip per route (see §19). With ten routes and the heaviest dependencies concentrated in `catalog-form` (form renderer + 11 primitives) and `pricing` (chart library), only features-first + `@defer` can hit that target.
3. **Module-Federation upgrade path.** Per Decision 12 (Phase 2 micro-frontends), each feature folder maps 1:1 to a future remote. Features-first today is the lowest-friction path to MF later.

**Why this is not a fragmented monolith.** The discipline that distinguishes a features-first app from a fragmented one is the inter-feature communication contract (§17). A traditional Angular app imports services and components freely across the app — features-first forbids exactly that — `catalog-form` may NOT import `pricing.PricingComponent`, may NOT inject `pricing.PricingService` directly, may only navigate to the pricing route. Shared concerns live in `core/` (services, models, interceptors, guards) or `shared/` (stateless UI primitives, pipes, directives).

### D. Data-driven form renderer is the spine

**Decision:** the catalog wizard (`/catalogs/:id/edit`) is a **single renderer component** that consumes the schema returned by `GET /api/v1/categories/{id}/schema` and dispatches each field to one of **11 primitive components** based on `schema.fields[i].primitive`. There is NO category-specific component code anywhere in the frontend. There is NO per-category template. The renderer + 11 primitives + step composer cover all 3,772 leaf categories.

This is non-negotiable. It is enshrined in `MVP_ARCHITECTURE.md §4.1, §4.2, §5.6.1` and `BACKEND_ARCHITECTURE.md §0.G.D2`. Any specialist proposing a category-specific component should be redirected to add a new primitive (with founder approval) instead.

The 11 primitives:

| Primitive | Selection rule | Selector | V1 dep |
|---|---|---|---|
| `text_short` | `data_type=text`, no name-pattern match | `<mee-text-short>` | `MatFormField` + `MatInput` |
| `text_long` | name matches `*description\|notes\|ingredients\|address` | `<mee-text-long>` | `MatFormField` + `MatInput` (textarea) |
| `number` | `data_type=number`, no unit suffix | `<mee-number>` | `MatFormField` + `MatInput type="number"` |
| `number_with_unit` | numeric field with companion `*_unit` field, OR name matches `*weight\|voltage\|wattage\|frequency\|capacity` | `<mee-number-unit>` | `MatFormField` + suffix slot |
| `currency` | name matches `*price\|mrp` (renders `₹` prefix) | `<mee-currency>` | `MatFormField` + prefix slot |
| `dropdown_small` | enum count 1–20 (radio or simple select) | `<mee-dropdown-small>` | `MatRadioGroup` or `MatSelect` |
| `dropdown_medium` | enum count 21–100 (in-memory autocomplete) | `<mee-dropdown-medium>` | `MatAutocomplete` |
| `dropdown_large` | enum count 101–500 (virtualised autocomplete) | `<mee-dropdown-large>` | `MatAutocomplete` + `cdk-virtual-scroll-viewport` |
| `dropdown_api_search` | enum count >500 (debounced API call) | `<mee-dropdown-api>` | `MatAutocomplete` + RxJS `debounceTime + switchMap` |
| `image_upload` | `data_type=image_url` (matches `^Image\s+\d+`) | `<mee-image-upload>` | CDK drag-drop + `ngx-image-compress` |
| `address_group` | composite — collapsed-compliance flag set | `<mee-address-group>` | composes `text_long` + `text_short` |

**Total: 11 primitive components covering 1,831 unique field names corpus-wide.**

### E. CORE_PHILOSOPHY compliance commitments

`docs/CORE_PHILOSOPHY.md` is the rulebook. The frontend commits to honouring these rules as construction invariants — feature sections cite each rule rather than re-stating it.

- **M1 (Every field has two names).** Frontend renders `display_label` only. `meesho_column_header` is never present in API responses (per backend §6.4 stripping rule) — therefore the frontend cannot accidentally leak it.
- **M2 (Help text is ours).** All inline help comes from `field.display_help` resolved against active locale. Meesho's original help text is never available to the frontend.
- **M3 (Validation messages are ours).** Error messages come from `field.validation_message` per locale; fallback to library defaults (matching backend `app/i18n/validation_messages.py`). Backend's `validation_message_id` returns in 422 responses; frontend resolves to display string locally.
- **M4 (Dropdowns are bilingual at the seam).** Frontend renders `enum_entries[i].labels[locale]`. The `meesho` field is never sent back to the frontend (stripped).
- **M5 (Wizard layout follows seller intuition).** Steps are composed by `step_id` grouping (13 step IDs from `MVP §5.6.3`), titles are plain-language constants, never Meesho column-group names.
- **M7 (AI works in canonical space).** Frontend's autofill UI shows the AI-suggested value rendered through the same primitive that handles direct seller input. The yellow-highlight diff overlay is a presentation concern only — the underlying value is canonical.
- **M9 (Localisation is structural).** No hardcoded English strings outside the i18n bundle (V1 ships English, V1.5 adds Tamil + Hindi). Display strings come from either (a) the schema's `display_*` maps (per-field), (b) Transloco translation files (app-shell UI), or (c) backend `validation_message_id` responses.
- **F1 (Never show Meesho's raw column header to the seller).** Naturally enforced — backend strips them before the frontend sees the schema.
- **F5 (Never show a field without an explanation).** The renderer asserts `display_help` exists on every rendered field; if missing, it falls back to `display_placeholder`, then to a generic "Optional details" string. Advanced fields (`is_advanced: true`) are the documented exception per Pattern 5.

### F. Founder-locked rulings this session (FE-D1 — FE-D13)

These rulings are normative for every later section in this document.

- **FE-D1. The existing React scaffold under `frontend/src/` is to be deleted in full.** Implication: the first dispatch under this contract is a clean-slate scaffold of the Angular 18 app. No incremental React→Angular port. No dual stack. The Vitest test files for React components are deleted with their pages.
- **FE-D2. Frontend reads only the display + canonical layers from the API.** Implication: any specialist seeing `meesho_column_header` or `meesho_column_index` in an API response should treat it as a backend bug and surface it to the coordinator — not consume it.
- **FE-D3. Code is written ONLY by the respective specialist sessions; master orchestrates and the frontend coordinator coordinates — neither writes code.** Implication: every code-writing task under `frontend/src/` is executed by the relevant `meesell-angular-*-builder` specialist. The master session dispatches specialists and reviews their work — it does NOT directly write production code. The coordinator (this agent) dispatches specialists when permitted, authors and updates `FRONTEND_ARCHITECTURE.md`, updates `STATUS_FRONTEND.md`, updates its own memory, and produces integration glue documentation — but does NOT write production code under `frontend/src/`. Production code authorship is the specialists' role, period.
- **FE-D4. The form renderer + 11 primitives is the only code path through which seller-entered values flow.** Implication: ad-hoc inline form HTML is forbidden in the catalog-form feature. If a screen needs a one-off field that doesn't fit the schema (e.g. the `/catalogs/new` description input for Smart Picker), it uses Reactive Forms directly with a standard Material input — but it does NOT bypass the renderer for any field that is in `templates.schema_jsonb`.
- **FE-D5. The frontend NEVER persists tokens to client-side storage. Authentication state ownership lives backend-side.** Implication: `localStorage`, `sessionStorage`, `IndexedDB`, and document.cookie writes are forbidden for any auth-related value. The access JWT is held in an in-memory signal (`AuthService.accessToken`) and is lost on page reload by design. The refresh token is owned by the backend and delivered as `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Domain=.mesell.xyz` cookie that JS cannot read. The backend maintains a refresh allowlist in Valkey DB 0 keyed by `cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` (HMAC-with-pepper per backend ratification 2026-06-05 — a Valkey-only breach yields nothing without the Secret Manager-stored pepper). Rotation on every refresh is atomic via a Lua `EVAL` (single round-trip CAS, no `WATCH` race). **Server-side revocation on logout** — `DEL` on the same hashed keyspace. On page reload, the app calls `POST /api/v1/auth/refresh` from the `AuthGuard` bootstrap — the browser sends the refresh cookie automatically, the backend validates the allowlist, and a new access token is returned. This decision was applied as append-only `AMENDMENT 2026-06-05` blocks to `V1_FEATURE_SPEC.md §F1`, `MVP_ARCHITECTURE.md §11.7`, and `CLAUDE.md` Decision 14 by the backend coordinator on ratification (per `STATUS_BACKEND.md` 2026-06-05 entry).
- **FE-D6. Token lifetimes are backend-controlled via env vars; the frontend reads `expires_in` from the response.** Implication: production defaults are 15-min access (`ACCESS_TOKEN_TTL_SECONDS=900`) and 7-day refresh (`REFRESH_TOKEN_TTL_SECONDS=604800`); dev and staging override these to test the silent-refresh path (e.g. `ACCESS_TOKEN_TTL_SECONDS=30` makes refresh fire every 30 seconds — useful for verifying the interceptor's refresh-on-401 loop without waiting 15 minutes). The frontend has **NO env coupling for token lifetimes** — `AuthService.scheduleRefresh()` reads `expires_in` from each `/auth/otp/verify` or `/auth/refresh` response and schedules the next refresh at `expires_in - 30s` (30-second safety margin to avoid racing the 401). Backend env-var definition lives in the backend session; this section just records the frontend contract: **trust the response**.

- **FE-D9. Visual identity values come from an external designer, not the coordinator.** Implication: §5A token framework (semantic naming, type scale rungs, spacing grid, breakpoints, elevation tiers, motion tiers, theming flow, dark-mode structure, WCAG 2.2 AA contract) is LOCKED. §5A values (hex codes, font family, exact px values, button/card/form visual language, iconography style, empty-state illustrations, microcopy tone) are PLACEHOLDERS pending external designer ratification. The `meesell-angular-ui-styler` dispatch is BLOCKED until designer artefacts exist and §5A values are founder-ratified against them. The `meesell-angular-component-builder` dispatch is NOT blocked — component bodies/templates/logic do not require finalised visual identity; they consume CSS custom properties whose values land later. Coordinator records this gap explicitly so future PRs that touch design tokens or visual surfaces cite FE-D9 rather than treating the placeholders as authoritative.

- **FE-D10. SUPERSEDES FE-D9 for V1 — visual identity produced via AI-assisted pipeline, NOT external human designer.** Implication: external designer engagement is deferred (potentially to V1.5 for brand refinement post-launch). V1 visual identity production happens via `meesell-angular-ui-styler` upgraded to Opus model tier, executing the contract in `docs/DESIGN_SYSTEM_ARCHITECTURE.md`. The agent produces token values (color, typography, iconography, microcopy) through internal color-theory + accessibility reasoning rather than via SaaS GUI tools. Founder reviews live `ng serve` output (the working app IS the mockup), not Figma artefacts. `DESIGNER_BRIEF.md` is preserved unchanged for potential V1.5 human-designer engagement. The `meesell-angular-ui-styler` dispatch is AUTHORISABLE once `docs/DESIGN_SYSTEM_ARCHITECTURE.md` is founder-LOCKED. The `meesell-angular-component-builder` dispatch remains parallel-authorisable (unchanged from FE-D9). **Amended 2026-06-05 by founder ruling — the internal-reasoning approach is superseded by the Reference Dictionary + iterative pick methodology in DESIGN_SYSTEM_ARCH §1 + §5; the agent CURATES from public web examples and founder PICKS rather than the agent reasoning internally.**

- **FE-D11. Design system architecture work runs in a dedicated sub-session of the frontend coordinator, not in the same session as frontend architecture coordination.** Implication: `docs/DESIGN_SYSTEM_ARCHITECTURE.md`, `docs/design-system/REFERENCE_DICTIONARY.md`, `docs/design-system/RATIONALE.md`, `docs/design-system/MICROCOPY_TONE.md`, `docs/design-system/ICONOGRAPHY.md`, and `docs/status/STATUS_DESIGN_SYSTEM.md` are owned by a Design System Coordinator sub-session (session-as-role per `docs/SESSION_PROMPTS_DESIGN_SYSTEM.md`). The frontend coordinator (this session) acts as MASTER for the sub-session — reads STATUS_DESIGN_SYSTEM.md for progress, integrates final compose output into §5A on completion, and does NOT participate in the iterative curate-pick-compose-confirm rounds. This split matches the existing MeeSell project-level multi-session pattern (FRONTEND/BACKEND/AI/DATA/INFRA/LEGAL sub-sessions of master). Rationale: cognitive load and STATUS surface in the frontend coordinator session was bloating; the split keeps each session focused. No new agent spec required (session-as-role pattern); a `meesell-design-system-coordinator` agent spec MAY be authored in V1.5 if the pattern proves valuable beyond V1.

- **FE-D12 (AMENDED 2026-06-06). Frontend feature development happens in dedicated sub-sessions grouped by founder-ratified frontend-native cohesion, NOT 1:1 per feature folder NOR 1:1 per backend module.** Founder ratified the grouping 2026-06-06: **6 sub-sessions** — `auth` (`/`, `/signup`, `/login`) · `onboarding` (`/onboarding`) · `profile` (`/profile`) · `dashboard` (`/dashboard`) · `catalog` (`/catalogs/new` + `:id/edit` + `:id/images` + `:id/preview` + `:id/pricing` + `:id/export`) · `cross-cutting` (core/ + shared/ — with the special discipline rule that any change must check all routes). Each sub-session owns:
  - Its slice of FRONTEND_ARCHITECTURE.md (e.g., §7 for `account`, §9 for `dashboard`, §11 for `catalog-form`, etc.)
  - Its own STATUS file (e.g., `docs/status/STATUS_FEATURE_ACCOUNT.md`)
  - Its own bootstrap prompt (e.g., `docs/SESSION_PROMPTS_FEATURE_ACCOUNT.md`)
  - `meesell-angular-component-builder` dispatches scoped to ITS feature only
  
  The frontend coordinator (this session) remains the MASTER — reads sub STATUS files for progress, integrates code-side contract amendments back into FRONTEND_ARCH when feature sub-sessions surface them, and does NOT participate in per-feature component implementation.
  
  **Recommended dispatch sequence** (depends on inter-feature dependencies per §17):
  1. Foundation features (parallel-safe): `landing`, `account`, `dashboard`
  2. `smart-picker` (creates products consumed by catalog-form)
  3. **`catalog-form` — THE SPINE** (the 11 primitives + wizard renderer per §18; consumed by `images`, `preview`, `pricing`, `export`)
  4. Dependent features (parallel-safe once catalog-form is locked): `images`, `preview`, `pricing`, `export`
  
  Rationale: a single combined component-builder dispatch held context for 10 routes + 11 form primitives + 6 shared components simultaneously, which risked agent confusion (mixing primitive contracts across features, mixing navigation logic, mixing test patterns). Per-feature dispatch keeps each agent's context focused; the agent reads only the §3.D 7-file pattern + the relevant per-feature spec + the locked §4 + §5 + §5A + §17 + §18 contracts. Mirrors the FE-D11 split pattern at the feature granularity.
  
  Infrastructure for the per-feature sub-sessions (bootstrap prompts, STATUS file skeletons, ownership map) is authored by the frontend coordinator WHEN design system completes — premature setup before design system tokens land would be dead documentation. For now, Task #12 (component-builder dispatch) is DEFERRED and the per-feature dispatch model is the binding contract.

  **AMENDMENT 2026-06-06 (founder ratification of 6-session grouping):** The pre-design-system "wait" was over-cautious for bootstrap prompts specifically (governance, not styling). Founder ratified 6 sub-sessions grouped by frontend-native cohesion (auth/onboarding/profile/dashboard/catalog/cross-cutting). Bootstrap prompts + STATUS skeletons authored 2026-06-06 in `docs/SESSION_PROMPTS_FEATURE_*.md` and `docs/status/STATUS_FEATURE_*.md`. The 9-feature mirror of backend modules (original FE-D12) is RETIRED. The base prompt + 6 per-session prompts capture: ownership scope, mandatory reads, master-sub communication protocol, dispatch authority, MF-remote alignment (per FE-D13), and the cross-cutting discipline rule (any change in cross-cutting session requires verification against all routes).

- **FE-D13. Sub-session boundaries align with Phase 2 Module Federation remote boundaries.** Implication: each of the 6 sub-sessions ratified in FE-D12 (auth, onboarding, profile, dashboard, catalog, cross-cutting) corresponds 1:1 to a planned Phase 2 micro-frontend remote (auth-mfe, onboarding-mfe, profile-mfe, dashboard-mfe, catalog-mfe; cross-cutting = the shell host). Per CLAUDE.md Decision 12 (MF deferred to Phase 2), the features-first folder structure under `features/` is the MF-ready substrate. Founder ruling 2026-06-06 makes the alignment explicit: when V1 ships and team size or build-time pressure forces MF in Phase 2, each sub-session's code root extracts cleanly as a remote without restructuring. The dashboard's side menu reflects the same module structure (each menu item = one sub-module = one future remote), reinforcing the cohesion between code organization, session organization, and future deployment organization.

### G. Inherited locked decisions from CLAUDE.md and MVP_ARCHITECTURE

`CLAUDE.md` records 15 locked decisions. The 5 frontend-impacting decisions and their FRONTEND implications:

- **D9 (Angular 18, not React).** This contract.
- **D10 (Services + RxJS + signals, no NgRx).** State management is co-located in feature services; signals for component-local reactive state, BehaviorSubject for shared long-lived state (see §16 for the rules).
- **D11 (Tailwind + Material, not Material alone).** Tailwind utility classes handle layout, spacing, breakpoints, one-off styling. Material handles accessible interactive primitives (forms, dialogs, snackbars, autocomplete, menus, steppers). Design tokens flow from a single SCSS source through both — see §5A.
- **D12 (Module Federation deferred to Phase 2).** V1 ships single bundle. Features-first folder structure (§3) is the MF-ready substrate; no MF dependencies are added in V1.
- **D13 (Ionic + Capacitor deferred to Phase 2).** V1 is a web-only PWA. The PWA install prompt is wired (Section 16); the codebase remains Angular Material throughout — no Ionic components.

From `MVP_ARCHITECTURE.md`:

- **§4.1 — 11 input primitives.** Frontend implements all 11; the dispatcher in §18 selects at compile time based on `schema.primitive`.
- **§4.2 — Wizard renderer.** Single `<mee-wizard>` component consumes the schema; never any category-specific code.
- **§4.3 — Onboarding wizard.** Separate from catalog wizard; covers the 9-field seller profile + super-category declaration + conditional compliance extensions.
- **§4.4 — State management.** Reactive Forms; `signal() + computed()` for component-local state; `BehaviorSubject` in services for shared (Auth, current catalog).
- **§4.5 — Route layout.** Adds `/onboarding` (separate from catalog wizard) and `/profile` to the V1 §6 route list.
- **§5.6.2 — Locale handling.** Every seller-facing string is a locale map `{en, ta?, hi?}`. V1 ships English; V1.5 fills Tamil + Hindi without schema or code migration.
- **§5.6.3 — Wizard step composition.** 13 step IDs grouped at runtime; step titles from a code constant `STEP_TITLES` rendered in the seller's locale.
- **§6.3 — HTTP caching.** Browser honours `Cache-Control` + `ETag` directives sent by backend. The HTTP interceptor (§4) does NOT implement an in-memory cache layer in V1 — the browser HTTP cache plus the backend's Valkey DB 3 cache are sufficient.

### H. Corpus-grounded premises imported from backend §0.I

These are facts from full-corpus parse, not hypotheses. Frontend implications:

- 3,772 categories × 11 primitives = single renderer covers the corpus. **No per-category UI code.**
- **No Recommended tier** — binary compulsory/optional. The frontend marks compulsory with a red asterisk and a blocking validator; optional gets no marker.
- Image rules are **100% uniform corpus-wide** (4 slots, slot 1 required). The image-uploader component has zero category branches.
- **1,831 unique field names** → handled by the 10-primitive classifier + the `address_group` composite. New field names from quarterly Meesho refresh fall into existing primitives by classifier rule.
- **291 Brand-pattern fields** (same name, different enum source per category) → `<mee-dropdown-api>` calls `GET /api/v1/categories/{id}/enum/{field_name}?q=` debounced; the call site is identical for every category.
- Median compulsory-field count **19–33 by super-category** → wizard progress bar is data-driven (denominator = compulsory count from schema).
- **Eye-Serum represents an alternate compliance shape** (1 of 3,772) — frontend uses the `address_group` composite primitive when the schema marks fields with the collapsed-compliance flag. Same data flow path; just a different primitive selected.

### I. The 10 routes + 25-endpoint contract

The route table is locked at `V1_FEATURE_SPEC.md §6` (10 routes) plus the two MVP additions (§4.5: `/onboarding`, `/profile`). The endpoint contract is locked at `BACKEND_ARCHITECTURE.md §0.C` (25 endpoints). Frontend consumes 24 of the 25 — the 25th (`GET /api/v1/products/{id}/draft`) is consumed by the catalog-form feature's draft-recovery flow on browser reload.

Section 23 is the canonical route inventory mapped to feature owners. Section 11 (`catalog-form`) wires the `/draft` recovery endpoint.

### J. Frontend baseline — clean-state required

Per FE-D1, the existing React scaffold is to be deleted. Current React state (verified 2026-06-05):
- `frontend/package.json` — React 18.3.1, Vite 5, Zustand 4, React Router 6, Vitest 2
- `frontend/src/pages/` — 8 React pages (Landing, Onboarding, Dashboard, CatalogCreate, CatalogPreview, QualityCheck, PriceCalculator, ExportPage)
- `frontend/src/components/` — 5 React components with `.test.jsx`
- `frontend/src/api/client.js` — axios + JWT interceptor (logic salvageable as Angular reference)
- `frontend/src/stores/` — Zustand authStore + catalogStore (replaced by Angular services)
- `frontend/vite.config.js`, `frontend/vitest.config.js` — replaced by Angular CLI

Construction builds FORWARD from a clean Angular 18 scaffold. The first dispatch under this contract authors `frontend/` from scratch via `ng new frontend --standalone --routing --style=scss --ssr=false --skip-tests=false`, then applies the §3 file structure, then wires Tailwind + Material per §5A.

### K. What Section 0 does NOT cover

Section 0 is decision-record only. The runtime topology (where the frontend pod runs, how it talks to the API, how the build is served) lives in §1. The folder tree lives in §3. The cross-cutting layer (interceptors, guards, models, error handlers) lives in §4. Design tokens, theming, typography live in §5A. Per-feature wireframes and component lists live in §7–15. Section 0 establishes the WHY; later sections specify the WHAT and WHERE.

A reviewer evaluating Section 0 is asking only: "are the premises sound, are the rulings correct, are the inherited decisions all here?" — not "is the folder structure right" (§3), not "are the features correctly carved" (§2), not "is the design system complete" (§5A). Those evaluations belong to their own founder-review turns.

---

## Section 1 — System Topology

STATUS: LOCKED (2026-06-05, post backend coordinator ratification of FE-D5 + FE-D6 with 3 founder-ratified strengthenings: Lua `EVAL` rotation atomicity, HMAC-SHA256-with-`REFRESH_TOKEN_PEPPER` for Valkey allowlist keyspace, cookie `Path=/api/v1/auth` corrected from initial `Path=/auth` proposal which would not have matched the backend's actual endpoint mount)

### A. What Section 1 establishes

Section 1 is the **runtime topology map** of the V1 frontend — what runs in the browser, what runs at build time, and what flows across the wire. It is NOT a K3s manifest spec (that belongs to §20), NOT a feature catalog (§2), and NOT a directory tree (§3). The single question Section 1 answers is: "if a Tirupur seller types `studio.mesell.xyz` into Chrome on their Android phone, what loads, what runs, and what gets cached?" Every later section refines a slice of this map.

### B. ASCII topology diagram

```
                                  Tirupur seller on Android Chrome
                                              │ HTTPS
                                              ▼
                            ┌──────────────────────────────────┐
                            │  Traefik ingress                 │
                            │  dev.mesell.xyz / www.mesell.xyz │
                            │  TLS via cert-manager (LE)       │
                            └────────────┬─────────────────────┘
                                         │ HTTP in-cluster
                                         ▼
                            ┌──────────────────────────────────┐
                            │  K8s Service: frontend           │
                            │  (ClusterIP, :80)                │
                            └────────────┬─────────────────────┘
                                         │
                                         ▼
                            ┌──────────────────────────────────┐
                            │  Frontend pod (nginx + static)   │
                            │  serves /index.html + /assets    │
                            │  pre-built by Angular CLI        │
                            │  asia-south1-docker.pkg.dev/.../ │
                            │  meesell-prod-images/frontend    │
                            └────────────┬─────────────────────┘
                                         │ initial bundle (HTML+JS+CSS)
                                         ▼
                            ┌──────────────────────────────────┐
                            │  Browser — Angular 18 app boots  │
                            │                                  │
                            │  ┌───── core/ (singleton) ─────┐ │
                            │  │  AuthService                │ │
                            │  │   • accessToken (signal)    │ │
                            │  │   • bootstrap() → /refresh  │ │
                            │  │   • scheduleRefresh()       │ │
                            │  │   • logout() → /logout      │ │
                            │  │  JwtInterceptor             │ │
                            │  │  LocaleInterceptor          │ │
                            │  │  RefreshInterceptor (401→   │ │
                            │  │   /refresh → replay)        │ │
                            │  │  ErrorInterceptor           │ │
                            │  │  ApiClient                  │ │
                            │  │  AuthGuard (bootstrap on    │ │
                            │  │   first auth-route hit)     │ │
                            │  │  PlanGuard                  │ │
                            │  │  TranslocoService           │ │
                            │  │  ServiceWorker (ngsw)       │ │
                            │  └────────────┬────────────────┘ │
                            │               │                  │
                            │  ┌────── feature lazy chunks ──┐ │
                            │  │  auth (chunk on /login)     │ │
                            │  │  dashboard (chunk)          │ │
                            │  │  catalog-form (chunk +      │ │
                            │  │   11 primitives sub-chunks) │ │
                            │  │  pricing (chunk + chart lib)│ │
                            │  │  …                          │ │
                            │  └─────────────────────────────┘ │
                            └────────────┬─────────────────────┘
                                         │ HTTPS (Authorization: Bearer JWT)
                                         ▼
                            ┌──────────────────────────────────┐
                            │  FastAPI backend (api.mesell.xyz)│
                            │  25 endpoints per §17 backend    │
                            └──────────────────────────────────┘

  Cached at browser:
    - index.html (no-cache, always fresh — service worker safety net)
    - /assets/*  (immutable, 1-year max-age, hashed filenames)
    - /api/v1/categories/{id}/schema  (ETag + stale-while-revalidate=3600)
    - /api/v1/categories/{id}/enum/{field_name}  (ETag + stale-while-revalidate)
    - /api/v1/categories/browse  (max-age=86400)

  Not cached:
    - /api/v1/auth/*  (no-store; refresh cookie travels per request)
    - /api/v1/seller-profile/*  (no-store, user-specific)
    - /api/v1/products/*  (no-store, user-owned mutable)
    - /api/v1/exports/*  (no-store, polled)

  Cookie flow (per FE-D5, post backend ratification 2026-06-05):
    Set-Cookie: refresh_token=<opaque secrets.token_urlsafe(48)>; HttpOnly; Secure;
                SameSite=Strict; Path=/api/v1/auth; Domain=.mesell.xyz;
                Max-Age=604800
    — set by POST /api/v1/auth/otp/verify + rotated on every POST /api/v1/auth/refresh
      via Lua EVAL (atomic CAS — no WATCH race)
    — cleared by POST /api/v1/auth/logout (Max-Age=0 + server-side Valkey DEL
      on cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)})
    — sent automatically by browser on /api/v1/auth/* only (Path scope)
```

### C. Request flow walkthrough (representative — dashboard load with reload)

Representative call: seller closes their browser, reopens it the next day, and lands directly on `/dashboard` via a bookmark. The access JWT is gone (in-memory only per FE-D5), but the refresh cookie is still in the browser jar (within its 7-day TTL).

1. Browser sends HTTPS request → Traefik ingress → frontend pod → nginx returns `/index.html` (small, ~5 KB).
2. Browser parses index, requests root JS chunk (Angular bootstrap + core services + AppComponent + router). Service worker (ngsw) intercepts — if cached, serves immediately and revalidates in background.
3. Angular bootstraps, evaluates `app.routes.ts`, matches `/dashboard` → triggers `loadComponent: () => import('./features/dashboard/dashboard.routes')`.
4. `AuthGuard.canActivate` runs first. It checks `AuthService.accessToken()` — null (memory was wiped on close). It calls `AuthService.bootstrap()` which fires `POST /api/v1/auth/refresh` (no body — the browser automatically attaches the `refresh_token` HttpOnly cookie). Three branches:
   - **Refresh valid → backend returns `{access_token, expires_in: 900}` + rotated refresh cookie.** `AuthService.accessToken.set(...)` + `AuthService.scheduleRefresh(900 - 30)`. Guard returns `true`. Proceed to step 5.
   - **Refresh invalid (expired / revoked at logout / not present) → backend returns `401`.** Guard returns `UrlTree('/login')`. Seller sees the login page.
   - **Network failure → `ErrorInterceptor` surfaces "You appear to be offline" snackbar.** Guard holds with a spinner until reconnect (or seller dismisses).
5. The dashboard chunk downloads (target: ≤80 KB gzip per route). `DashboardComponent` constructor injects `DashboardService` (feature-scoped, `providedIn: 'root'` because it composes data from multiple sources).
6. Component calls `dashboardService.listProducts({page: 1})` → returns RxJS `Observable<ProductListResponse>`.
7. `ApiClient.get<ProductListResponse>('/api/v1/products', {params})` runs through the interceptor chain: `JwtInterceptor` adds `Authorization: Bearer ${AuthService.accessToken()}`, `RefreshInterceptor` watches for `401` and (if encountered) triggers a refresh + replay of the original request, `ErrorInterceptor` wraps other 4xx/5xx, browser HTTP cache check (no cache for products — always fresh).
8. FastAPI responds with `{data: [...], total: N, page: 1}`.
9. Component sets `products.set(response.data)`, `loading.set(false)`. Template reacts via signal binding.
10. If response is empty, the empty-state UI shows with CTA "Create your first catalog" → routes to `/catalogs/new`.

### D. Cached request walkthrough (representative — schema fetch)

Representative call: seller picks "Kurti" on Smart Picker, lands on `/catalogs/:id/edit`.

1. `CatalogFormComponent` constructor injects `CatalogFormService` and `CategorySchemaService`.
2. Component calls `categorySchemaService.getSchema(categoryId)`.
3. `ApiClient.get('/api/v1/categories/{id}/schema')` is dispatched. The browser HTTP cache checks for a fresh entry:
   - If found and within `max-age=86400` → returned instantly, no network call.
   - If found but stale (within `stale-while-revalidate=3600`) → returned instantly AND revalidation request fires in background. If backend returns `304 Not Modified` (ETag match), the cached entry is refreshed. If backend returns `200` with new body, the cache is updated.
   - If absent → full `200 OK` request, body cached with `ETag` and `Cache-Control` headers.
4. Component receives the schema, derives wizard steps via `WizardStepComposerService` (groups by `step_id`, drops empty steps, sorts by canonical order).
5. Wizard renders. The 11-primitive dispatcher selects components per field's `primitive`.

This means the second time the seller opens any "Kurti" catalog, the schema fetch is **instant** (no network) — critical for the 2G/3G Tirupur experience.

### E. Service worker flow

The PWA service worker (`@angular/pwa` ngsw) manages app-shell caching:
- **Pre-caching** at install: `index.html`, root JS chunk, root CSS, app icon, manifest.
- **Lazy caching** on first visit: feature chunks (cached after first use; served instantly thereafter).
- **API caching**: configured per-URL in `ngsw-config.json` to honour the same TTLs the backend declares — `categories/{id}/schema` cached 24h with `freshness` strategy, `auth/*` and `products/*` never cached.
- **Update notification**: when a new index.html lands (deploy), service worker downloads in background and notifies the running app via `SwUpdate.versionUpdates$`; app shows a "New version available" snackbar with reload action.

### F. Network boundaries and token storage (per FE-D5 + FE-D6)

Inside the browser: Angular app + core services + feature chunks + service worker + HTTP cache. Inside the K3s cluster but separate pods: the nginx pod serving static assets, the FastAPI pod (the API backend). Outside the cluster (from the browser's perspective): Google Cloud Storage signed-URL GETs for downloaded XLSX exports.

**Token model — split storage, backend-owned session:**

| Token | Lifetime (prod default; env-overridable) | Storage | How attached | Owner |
|---|---|---|---|---|
| Access JWT | 15 min (`ACCESS_TOKEN_TTL_SECONDS=900`) | In-memory `AuthService.accessToken` signal — lost on reload by design | `Authorization: Bearer <access>` header on every API call | Frontend holds the bearer; backend validates per request |
| Refresh token | 7 days (`REFRESH_TOKEN_TTL_SECONDS=604800`); rotated on every use via Lua `EVAL` | `HttpOnly; Secure; SameSite=Strict; Path=/api/v1/auth; Domain=.mesell.xyz` cookie — JS cannot read it | Browser sends automatically on `/api/v1/auth/*` calls | Backend allowlist in Valkey DB 0 (`cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}`); server-side revocation on logout |

The security boundary that matters most is **server-side revocation**: an attacker who exfiltrates the access token has at most a 15-minute window (the access token's TTL — verified via env-driven short-TTL tests in dev); after that, all further requests need a refresh, and the refresh allowlist can be revoked on logout, password change, or anomaly detection. The HttpOnly refresh cookie is not exfiltrable via XSS. The Bearer access token has no CSRF surface. The refresh cookie has SameSite=Strict, eliminating CSRF on the refresh endpoint.

Tokens never appear in URL query strings. Tokens never appear in `localStorage`, `sessionStorage`, or `IndexedDB`. Per FE-D5, any code attempting such writes is a contract violation and the specialist building it is to be redirected.

### G. What Section 1 does NOT cover

K3s manifests — pod resource requests/limits, replica counts, liveness/readiness probes — live in §20. Build pipeline (Angular CLI + Dockerfile + nginx config) lives in §20. The exact set of interceptors and their order lives in §4. Service worker config (precache list, runtime strategies) lives in §16. Section 1 is the topology map; later sections specify each component's spec.

---

## Section 2 — Feature Catalog

STATUS: LOCKED (2026-06-05, founder ratification with one revision: original 10-feature catalog merged `auth` + `onboarding` into a single `account` feature owning 4 routes — /signup, /login, /onboarding, /profile — with peer backend modules `iam` + `customer`. Rationale: the seller journey is structurally one identity-flow with the same actor and the same dependency on `core/auth/AuthService`. Final count: 9 feature folders, 12 routes, 26 of 27 contract endpoints consumed. Merger propagated as AMENDMENT 2026-06-05B to §3 + §6 + §7 + §8 (now Reserved) + §23 + TOC.)

### A. What §2 establishes

§2 is the **feature ownership ledger**. It enumerates the ten feature folders (the only allowed sub-folders under `app/features/` per §3.C.4), names what each one owns (routes + endpoints), states what each is explicitly **NOT** responsible for (so cross-feature scope creep is preventable), names its peer backend module (per `BACKEND_ARCHITECTURE.md §2`), and records the V1 → V1.5 → V2 expansion plan. It also catalogs the three non-feature layers (`core/`, `shared/`, `design-system/`) for completeness.

§2 is the **first place a specialist looks** when given a task. "Add an image cropping flow" → §2 says `images` owns it. "Add a category-rename action on the dashboard" → §2 says `dashboard` owns the listing but the rename action belongs in `catalog-form` because it owns the category-bound product state. The catalog disambiguates.

§2 is NOT the deep contract for each feature (§7-§15 carry those). It is the at-a-glance map.

### B. The 10 features (V1 ownership ledger)

| # | Feature folder | Owns routes | Owns endpoints | Backend module peer(s) | V1 status | Lazy |
|---|---|---|---|---|---|---|
| 1 | `landing` | `/` | none | none | shipping V1 | ✓ |
| 2 | `auth` | `/signup`, `/login` | `POST /auth/otp/send`, `POST /auth/otp/verify`, `POST /auth/refresh` (cross-cutting), `POST /auth/logout` (cross-cutting) | `iam` | shipping V1 | ✓ |
| 3 | `onboarding` | `/onboarding` | `GET /seller-profile/required-fields`, `PUT /seller-profile` | `customer` | shipping V1 | ✓ |
| 4 | `profile` | `/profile` | `GET /seller-profile`, `PUT /seller-profile` | `customer` | shipping V1 | ✓ |
| 5 | `dashboard` | `/dashboard` | `GET /products` (paginated list), `DELETE /products/:id` | `dashboard` | shipping V1 | ✓ |
| 6 | `smart-picker` | `/catalogs/new` | `GET /categories/suggest?q=`, `GET /categories/browse?q=&super_id=`, `POST /products` (creates draft + routes to `/edit`) | `category` | shipping V1 | ✓ |
| 7 | `catalog-form` | `/catalogs/:id/edit` | `GET /categories/:id/schema`, `GET /products/:id`, `GET /products/:id/draft`, `PATCH /products/:id`, `POST /products/:id/autofill`, `GET /categories/:id/enum/:field_name?q=` | `catalog`, `category` | shipping V1 — **the spine** | ✓ |
| 8 | `images` | `/catalogs/:id/images` | `POST /products/:id/images` (multipart), `GET /products/:id/images` (poll for precheck) | `image` | shipping V1 | ✓ |
| 9 | `preview` | `/catalogs/:id/preview` | `GET /products/:id/preview` | `catalog` | shipping V1 | ✓ |
| 10 | `pricing` | `/catalogs/:id/pricing` | `POST /products/:id/price-calc` | `pricing` | shipping V1 | ✓ |
| 11 | `export` | `/catalogs/:id/export` | `POST /products/:id/export-xlsx`, `GET /exports/:id` (poll) | `export` | shipping V1 | ✓ |

**Total: 11 feature folders (post FE-D12 amendment 2026-06-06A un-merger), 12 routes, 26 of 27 contract endpoints consumed** (per §23). All features are lazy-loaded via `loadComponent` / `loadChildren`.

**Sub-session ownership map** (per FE-D12 amended 2026-06-06):
- **auth session** owns features: `landing`, `auth` (the auth-flow folder including signup/login + otp-verify components)
- **onboarding session** owns feature: `onboarding`
- **profile session** owns feature: `profile`
- **dashboard session** owns feature: `dashboard`
- **catalog session** owns features: `smart-picker`, `catalog-form`, `images`, `preview`, `pricing`, `export` (six features in one mega-session due to shared productId state context)
- **cross-cutting session** owns: `core/`, `shared/` (and consumes `design-system/` tokens from the design system sub-session)

**Merger note (2026-06-05):** `auth` and `onboarding` were originally proposed as separate features. Per founder ruling 2026-06-05, they merged into a single `account` feature because the seller journey (phone → OTP → seller profile compliance → dashboard) is structurally one flow with the same actor and the same dependency on `core/auth/AuthService`. The `account` feature owns both the first-time onboarding wizard AND the return-user login AND the `/profile` edit-existing-profile view. Internal sub-folders (`signup/`, `login/`, `otp-verify/`, `onboarding/`, `profile/`) preserve the per-screen separation §3.D requires.

**Un-merger note (2026-06-06 — AMENDMENT 2026-06-06A per FE-D12 + FE-D13):** The 2026-06-05 merger of auth+onboarding+profile into `account` is REVERSED for sub-session and Module Federation alignment. Founder ratified 6-session grouping where auth/onboarding/profile are SEPARATE sub-sessions (signup+login share an OTP component but are otherwise distinct concerns from the 3-phase compliance wizard and from the edit-existing-profile view). Code structure now: `features/auth/` (signup+login+otp-verify) · `features/onboarding/` (3-phase wizard + super-category-chips) · `features/profile/` (edit existing). The `compliance-step/` component (used by both onboarding and profile) moves to `shared/components/compliance-step/` per §3.G shared-by-2+-features rule. Aligns sessions to MF remote boundaries per FE-D13.

### C. Per-feature responsibility + non-responsibility

#### C.1 — `landing`
- **Responsibility:** Render the public landing page at `/`. Hero, value props, signup/login CTAs routing to `/signup` and `/login`.
- **NOT responsible for:** Authentication state, navbar (the navbar in `shared/` reacts to auth state independently). Marketing email capture (deferred to V1.5).
- **Backend peer:** none — fully static after first paint.

#### C.2 — `account` (V1 Feature 1 + seller profile)
- **Responsibility:** The complete seller-identity surface end-to-end:
  - **`/signup` + `/login`** — phone number entry, OTP entry (wraps `ng-otp-input` for paste-aware SMS auto-fill), surfaces 429 rate-limit responses as friendly "Try again in X minutes", redirects on verify success (to `/onboarding` if profile incomplete, else `/dashboard`)
  - **`/onboarding`** — the 3-phase seller-profile wizard: Base (9 compliance fields + Country of Origin) + Super-category multi-select chips + Conditional compliance extension forms per declared super-category. Reads `GET /seller-profile/required-fields` to drive which conditional steps render
  - **`/profile`** — edit-existing-profile view (same form as onboarding but populated from `GET /seller-profile`)
  - Logout call site (UI lives in shared navbar; logic lives here)
- **NOT responsible for:** Token storage (per FE-D5, `core/auth/AuthService` owns the in-memory access token). Refresh interceptor (per §4, `core/interceptors/refresh.interceptor.ts` owns the 401-handling). Plan gating (per §4, `core/auth/plan.guard.ts`). The catalog wizard (that's `catalog-form` — a separate, data-driven renderer). Profile-incomplete redirect from auth-guarded routes (that's `core/auth/AuthGuard` after bootstrap returns the profile state).
- **Backend peers:** `iam` (otp + refresh + logout) **and** `customer` (seller-profile CRUD). Cross-module dependency is acceptable here because the frontend surface is one feature — the seller journey doesn't separate "I logged in" from "I declared my legal-metrology compliance" in the seller's mind.
- **Internal sub-folders:** `signup/`, `login/`, `otp-verify/` (shared by signup + login), `onboarding/`, `profile/`, plus optional feature-private `components/` for shared sub-pieces.

#### C.3 — `dashboard` (V1 Feature 8)
- **Responsibility:** Paginated product table (MatTable + MatPaginator), status filter chips (draft / exported / live), debounced name search (300ms), row navigation to `/catalogs/:id/edit`, soft-delete confirm dialog. Empty state with "Create your first catalog" CTA.
- **NOT responsible for:** Bulk operations (V1.5). Analytics / CTR / conversion per product (V1.5). Status mutation other than soft-delete (status flips happen in the relevant feature — `export` sets `exported`, seller manually marks `live`).
- **Backend peer:** `dashboard`.

#### C.4 — `smart-picker` (V1 Feature 2)
- **Responsibility:** Description input (min-10-char Reactive Form validator), AI suggest call to `GET /categories/suggest`, render top-3 `CategoryCardComponent` cards with path + confidence + sample attributes, manual browse fallback via `BrowseFallbackComponent` (uses `/categories/browse` with pg_trgm indexes). On card click: `POST /products` to create draft + navigate to `/catalogs/:id/edit`.
- **NOT responsible for:** The form rendering after category is picked (that's `catalog-form`). The Gemini prompt or backend ranking logic (that's `ai_ops` + `category` backend modules). Caching (backend caches by description SHA-256 for 24h — frontend reaps the benefit transparently).
- **Backend peer:** `category`.

#### C.5 — `catalog-form` (V1 Features 3 + 4) — **the spine**
- **Responsibility:** The wizard renderer, the 11 primitives (per §18), the autofill overlay (yellow-highlight accept/reject UI per V1 Feature 4), the autosave directive integration (10s + blur per V1 §F3), and the draft recovery (`GET /products/:id/draft` on init). Fetches the per-category schema (`GET /categories/:id/schema`) and dispatches each field to the right primitive based on `schema.primitive`.
- **NOT responsible for:** Category selection (that's `smart-picker`). Image upload (that's `images` — even though the schema may include `image_upload` primitives, those are placeholders that link to `/catalogs/:id/images`). Pricing math (that's `pricing`). Live preview (that's `preview`). Export trigger (that's `export`).
- **Backend peer:** `catalog`, with cross-module dependency on `category` (for schema) and `customer` (for compliance-block readback at export-validation time).

#### C.6 — `images` (V1 Feature 5)
- **Responsibility:** 4-slot drag-drop uploader (slot 1 marked compulsory per `DATABASE_ARCHITECTURE.md §2.9`), client-side compression via `ngx-image-compress` (10 MB raw → ~1 MB), `POST /products/:id/images` multipart upload, polling `GET /products/:id/images` every 2s until each image's status is `ready`, render `PrecheckReportComponent` per image with the 5 checks (JPEG / RGB / resolution / white-BG / no-watermark) + one-line fix hint sourced from `validation_message` library.
- **NOT responsible for:** Image cropping (deferred to V1.5). EXIF stripping (backend handles this at upload). Watermark application (out of V1 scope entirely — we DETECT watermarks per `image_has_watermark` check, we don't apply them).
- **Backend peer:** `image`.

#### C.7 — `preview` (V1 Feature 6)
- **Responsibility:** Three preview surfaces — feed thumbnail (~30-char truncation indicator), product detail page (Meesho-style hero + variant), mobile card (Meesho mobile app simulation). Reads `GET /products/:id/preview` for the normalised JSON. Stateless presentation only — no editing.
- **NOT responsible for:** Editing values (seller goes back to `/catalogs/:id/edit`). Multi-variant matrix preview (deferred to V1.5 — V1 shows first variant only).
- **Backend peer:** `catalog`.

#### C.8 — `pricing` (V1 Feature 7)
- **Responsibility:** MRP + target-margin Reactive Form, `POST /products/:id/price-calc` (≤200ms response), `PnlBreakdownComponent` with red/green margin indication, `MarginSliderComponent` (Material slider with live debounced 100ms recompute), `PricingChartComponent` (chart.js horizontal bar visualisation).
- **NOT responsible for:** RTO/return cost simulation (V1.5 — V1 shows a "Shipping not included" caveat). Multi-product price-rollup (V1.5). GST registration helper (V1.5 — V1 just reads `categories.commission_pct` snapshot at calc time).
- **Backend peer:** `pricing`.

#### C.9 — `export` (V1 Feature 9)
- **Responsibility:** Pre-export validation summary (lists missing compulsory fields and non-`pass` images with deep links back), "Generate XLSX" CTA firing `POST /products/:id/export-xlsx`, polling `GET /exports/:id` until `ready` or `failed`. On `ready`: two download buttons (XLSX + image ZIP) using signed URLs (1h TTL, countdown indicator). On `failed`: render seller-facing error messages (`TemplateNotFoundError`, `MissingComplianceError`, `GCSUploadError`) + retry CTA.
- **NOT responsible for:** XLSX generation itself (backend `export` module owns the 9-step pipeline + Strategy classes). Round-trip validation (backend). Image ZIP packaging (backend).
- **Backend peer:** `export`.

### D. Non-feature layers (catalogued for completeness)

These are NOT feature folders — they live as peer top-level folders under `app/` per §3.B. They have no routes, no API endpoints of their own; they are the substrate every feature consumes.

| Layer | Path | Stateful? | Used by |
|---|---|---|---|
| `core/` | `app/core/` | Yes (singleton services) | Every feature (via `@core/*` alias imports) |
| `shared/` | `app/shared/` | No (stateless components / pipes / directives / enums) | Every feature (via `@shared/*` alias imports) |
| `design-system/` | `app/design-system/` | No (SCSS tokens + TS mirrors for runtime style access) | Every feature implicitly via Material theme + Tailwind config; explicitly via `@use '@design-system/_tokens'` |

The deep contract for each layer lives in §4 (`core/`), §5 (`shared/`), and §5A (`design-system/`). §2 only enumerates their existence.

### E. Cross-feature dependency rule (forward-ref to §17)

**Features MAY NOT import from one another.** Cross-feature data flows happen through one of three sanctioned channels:

1. **Router params** — `catalog-form` navigates to `/catalogs/:id/images` and `images` reads `productId` from `ActivatedRoute`
2. **`core/` services** — both `catalog-form` and `export` inject `core/auth/AuthService` to read `accessToken`; both `dashboard` and `catalog-form` inject `core/services/ErrorService` to surface snackbar messages
3. **`shared/` primitives** — both `dashboard` and `export` consume `<mee-status-badge>` from `shared/components/`

A specialist who finds themselves writing `import { PricingService } from '@features/pricing/...'` from inside `@features/catalog-form/` is in violation. Surface to coordinator; restructure via channel (1), (2), or (3). The 6-rule formal contract lives in §17.

### F. V1 → V1.5 → V2 feature roadmap

| Phase | New features (planned) | Folder treatment |
|---|---|---|
| V1 (this contract) | The 10 above | `app/features/<10 folders>/` |
| V1.5 (30-60 days post-V1) | `bulk-ops` (multi-SKU upload), `analytics` (CTR/conversion per product), `brand-validator` (validate vs Meesho's 3,730 approved brand list), `billing` (Razorpay Pro tier upgrade flow), `versioning` (catalog draft history + revert) | Each gets its own `app/features/<name>/` folder following §3.D pattern |
| V2 (longer horizon) | Multi-marketplace (`features/marketplaces/amazon`, `flipkart`), team accounts (`features/team/`), real-time chat support (`features/support-chat/`) | Same — each is a new feature folder |
| Phase 2 (Module Federation, per Decision 12) | Each feature folder becomes its own remote (`shell` host + `catalog-mfe`, `pricing-mfe`, `export-mfe` remotes). Folder layout stays the same; only the build pipeline changes | See §20 for MF extraction |

**No feature is removed in V1.5 or V2** — the V1 catalog is the floor.

### G. What §2 does NOT cover

The deep contract for each feature lives in §7-§15. The 11 primitive components owned by `catalog-form` are in §18 (their interface contract) and §3.C.4 (their file structure). The non-feature layer contracts are in §4 (`core/`), §5 (`shared/`), §5A (`design-system/`). The route table is in §23. The endpoint contract is in `BACKEND_ARCHITECTURE.md §17`. The communication rules are in §17 of this doc. Section 2 is the at-a-glance map; §7-§15 say what each feature actually does.

---

## Section 3 — File Structure

STATUS: LOCKED (2026-06-05, founder ratification with one correction recorded inline: `design-system/` is the **style architecture surface**, not a SCSS-only folder — it may carry SCSS (primary), TypeScript (runtime token mirrors for JS-driven layout, animations, canvas/chart rendering), and Tailwind plugin extensions. The boundary is style architecture, not file type. SCSS remains the source of truth; TS mirrors are derived. §3.C.3 + §3.G updated to reflect.)

**AMENDMENT 2026-06-05B — `features/auth/` + `features/onboarding/` merged into `features/account/`** per §2 LOCK with auth+onboarding merger. The 7-file feature pattern (§3.D) is unchanged; only the folder count drops 10 → 9. The `account/` folder carries internal sub-folders `signup/`, `login/`, `otp-verify/`, `onboarding/`, `profile/` per the §3.D nested-page convention. The §3.D example block below illustrates the post-merger structure. All other §3 lock content unchanged.

### A. What §3 establishes

Section 3 is the **canonical directory contract** for `frontend/`. It locks the top-level layout (root files + 4 non-feature top-level peers + `features/` with 10 sub-folders), the **uniform per-feature internal layout** (so every feature pattern-matches), the **naming conventions** (file kebab-case, class PascalCase, selector prefix `mee-`), the **tsconfig path aliases** (so imports stay short + intent-revealing), and the **decision rules** for "does this go in `core/`, `shared/`, `design-system/`, or `features/`?"

Specialists may NOT invent new top-level folders. Specialists may NOT restructure a feature's internal layout. Specialists may NOT bypass the path aliases. Any deviation requires a founder-reviewed amendment to this section.

Section 3 is NOT the cross-cutting layer's deep contract (that's §4), NOT the design-system contract (that's §5A), NOT the third-party tool selection (that's §6), and NOT the per-feature deep spec (that's §7-§15). Section 3 says **where things live**; later sections say **what those things do**.

### B. Top-level layout (root files + 4 non-feature peers)

The `frontend/` root carries the Angular CLI workspace files plus deploy artefacts:

```
frontend/
├── angular.json                         # Angular CLI workspace config
├── package.json                         # locked deps per §6
├── package-lock.json
├── tsconfig.json                        # strict mode + path aliases (per §3.E)
├── tsconfig.app.json
├── tsconfig.spec.json
├── tailwind.config.js                   # extends design-system tokens (per §5A)
├── postcss.config.js
├── ngsw-config.json                     # service-worker cache rules (per §16)
├── vitest.config.ts                     # unit/component test config (per §19)
├── playwright.config.ts                 # e2e test config (per §19)
├── .eslintrc.json
├── .prettierrc
├── Dockerfile                           # multi-stage Node 20 → nginx:alpine (per §20)
├── nginx.conf                           # static-asset cache + SPA fallback (per §20)
├── public/
│   ├── icons/                           # PWA app icons
│   └── favicon.ico
└── src/
    ├── main.ts                          # bootstrapApplication(AppComponent, appConfig)
    ├── index.html                       # single <app-root /> + viewport meta + manifest link
    ├── styles.scss                      # Tailwind directives + Material theme entry
    ├── manifest.webmanifest             # PWA manifest (per §16)
    ├── i18n/                            # Transloco translation files (per §6)
    │   ├── en.json
    │   ├── ta.json                      # V1.5 — empty stub in V1
    │   └── hi.json                      # V1.5 — empty stub in V1
    └── app/
        ├── app.component.ts             # Root standalone; navbar + <router-outlet>
        ├── app.component.html
        ├── app.component.scss
        ├── app.config.ts                # ApplicationConfig — providers + router + interceptors + transloco + service worker
        ├── app.routes.ts                # Top-level route table; every feature is loadComponent-lazy
        ├── core/                        # § C.1 — cross-cutting infrastructure
        ├── shared/                      # § C.2 — stateless reusable primitives
        ├── design-system/               # § C.3 — SCSS-only tokens, theme, typography
        └── features/                    # § C.4 — 10 feature folders, one per route family
```

**The 4 non-feature top-level peers under `app/`** (`core/`, `shared/`, `design-system/`, `features/`) are the ONLY top-level folders allowed. No `pages/`, no `components/`, no `services/`, no `utils/` at the top level — those are type-first patterns that this layout explicitly rejects (per §0.C).

### C. The canonical tree

#### C.1 — `core/` (cross-cutting infrastructure)

```
app/core/
├── api/
│   ├── api-client.service.ts            # Typed HttpClient wrapper (used by every feature service)
│   ├── api-client.service.spec.ts
│   ├── api-error.ts                     # ApiError class + normaliser
│   └── api-error.spec.ts
├── auth/
│   ├── auth.service.ts                  # accessToken signal, bootstrap(), scheduleRefresh(), logout() — per §4 + FE-D5
│   ├── auth.service.spec.ts
│   ├── auth.guard.ts                    # CanActivate — bootstraps + redirects to /login on 401
│   ├── auth.guard.spec.ts
│   ├── plan.guard.ts                    # CanActivate — reads plan claim, wired-but-inert in V1
│   ├── plan.guard.spec.ts
│   ├── jwt-payload.model.ts             # {sub: UUID, exp: number, plan: 'free'|'pro'}
│   └── auth-tokens.ts                   # InjectionToken<AccessTokenSignal> for cross-module DI
├── interceptors/
│   ├── jwt.interceptor.ts               # Authorization: Bearer <accessToken>
│   ├── jwt.interceptor.spec.ts
│   ├── locale.interceptor.ts            # Accept-Language: <active locale>
│   ├── locale.interceptor.spec.ts
│   ├── refresh.interceptor.ts           # 401 → POST /auth/refresh → replay (per §4)
│   ├── refresh.interceptor.spec.ts
│   ├── error.interceptor.ts             # 4xx/5xx → ApiError → ErrorService
│   └── error.interceptor.spec.ts
├── models/                              # Shared cross-feature types
│   ├── product.model.ts
│   ├── catalog.model.ts
│   ├── category.model.ts
│   ├── field-schema.model.ts            # Mirror of MVP §5.6.1 three-layer shape
│   ├── ai-suggestion.model.ts
│   ├── pricing-calc.model.ts
│   ├── export-record.model.ts
│   ├── seller-profile.model.ts
│   └── paginated-response.model.ts      # Generic {data, total, page}
├── services/
│   ├── error.service.ts                 # MatSnackBar surface for ApiError
│   ├── error.service.spec.ts
│   ├── network.service.ts               # navigator.onLine signal
│   ├── network.service.spec.ts
│   └── telemetry.service.ts             # V1.5 analytics hook — stub in V1
└── tokens/
    ├── api-base-url.token.ts            # InjectionToken<string>
    ├── env-config.token.ts              # InjectionToken<EnvConfig>
    └── env-config.model.ts              # {production: boolean, apiBaseUrl: string, ...}
```

**Rule for what lives in `core/`:** stateful, singleton-scoped (`providedIn: 'root'`), used by 2+ features. Interceptors live here even though they're not user-facing because they participate in every API call. Models live here because they're the typed contract every feature reads.

#### C.2 — `shared/` (stateless reusable primitives)

```
app/shared/
├── components/                          # Stateless presentation — pure input/output
│   ├── empty-state/
│   │   ├── empty-state.component.ts
│   │   ├── empty-state.component.html
│   │   ├── empty-state.component.scss
│   │   └── empty-state.component.spec.ts
│   ├── status-badge/
│   ├── loading-spinner/
│   ├── confirm-dialog/
│   ├── offline-banner/
│   └── navbar/                          # App-shell navbar (logout button calls AuthService)
├── pipes/
│   ├── inr-currency.pipe.ts             # ₹1,49,900 Indian numbering
│   ├── inr-currency.pipe.spec.ts
│   ├── locale-label.pipe.ts             # Resolves {en, ta, hi} maps to active locale
│   ├── locale-label.pipe.spec.ts
│   ├── relative-time.pipe.ts            # "2 hours ago"
│   └── relative-time.pipe.spec.ts
├── directives/
│   ├── autosave.directive.ts            # 10s + blur autosave per V1 §F3
│   ├── autosave.directive.spec.ts
│   └── click-outside.directive.ts
└── enums/
    ├── product-status.enum.ts           # 'draft' | 'ready' | 'exported' | 'deleted'
    ├── plan-tier.enum.ts                # 'free' | 'pro'
    ├── image-precheck-result.enum.ts    # 'pass' | 'fail' | 'pending'
    ├── primitive-kind.enum.ts           # The 11 primitive identifiers (text_short, etc.)
    └── step-id.enum.ts                  # The 13 wizard step IDs
```

**Rule for what lives in `shared/`:** stateless (no service state), reused by 2+ features, pure input/output. If a component owns state, it does NOT belong here — it belongs in `features/` (or, if cross-feature state, in `core/services/`).

#### C.3 — `design-system/` (the style architecture surface)

```
app/design-system/
├── _tokens.scss                         # Color, spacing, typography, elevation, motion, breakpoints
├── _theme.scss                          # Angular Material M3 theme using tokens
├── _tailwind-bridge.scss                # Maps tokens to CSS custom props consumed by Tailwind
├── _typography.scss                     # Type scale + font family selection
├── _elevation.scss                      # Shadow tokens (flat / sm / md / lg)
├── _motion.scss                         # Duration + easing tokens
├── breakpoints.ts                       # TS mirror of SCSS breakpoint tokens (for JS-driven layout decisions, lazy module triggers, virtual-scroll item heights)
├── tokens.ts                            # TS mirror of selected runtime-readable tokens (motion durations, semantic colors for canvas/chart rendering)
└── tailwind/                            # Tailwind plugin extensions, custom utility generators (if needed beyond config)
```

**What lives here: style architecture artefacts.** Primarily SCSS (tokens, theme, typography, elevation, motion) consumed via `@use` from `styles.scss` and from feature SCSS that needs token values. **May also include TypeScript** for runtime-readable token mirrors — breakpoints (for JS-driven layout decisions), motion durations (for Angular animations), semantic colors (for chart.js + canvas rendering where CSS custom props don't apply). **May include Tailwind plugin extensions** for custom utility generators when `tailwind.config.js` is insufficient.

The boundary is **style architecture**, not "files of a specific type." If a thing exists to shape how the app looks, feels, moves, or responds to breakpoints — it belongs here. If it has behavior or state, it belongs in `core/` (cross-cutting) or a feature.

**TS-mirror discipline:** the SCSS file is the source of truth for any token that has both an SCSS and a TS form. A build-time codegen step (added in §20 build pipeline) MAY auto-generate the TS file from the SCSS source — V1 ships both files hand-maintained with a smoke test asserting parity; V1.5 considers the codegen step. Either way, **never hand-edit only the TS file** — always update SCSS first.

#### C.4 — `features/` (post FE-D12 amendment 2026-06-06A — un-merged account into 3 separate folders for sub-session and MF-remote alignment)

```
app/features/
├── landing/                             # Route: /                                  [auth session]
├── auth/                                # Routes: /signup, /login                   [auth session]
├── onboarding/                          # Route: /onboarding                        [onboarding session]
├── profile/                             # Route: /profile                           [profile session]
├── dashboard/                           # Route: /dashboard                         [dashboard session]
├── smart-picker/                        # Route: /catalogs/new                      [catalog session]
├── catalog-form/                        # Route: /catalogs/:id/edit  (THE SPINE)    [catalog session]
├── images/                              # Route: /catalogs/:id/images               [catalog session]
├── preview/                             # Route: /catalogs/:id/preview              [catalog session]
├── pricing/                             # Route: /catalogs/:id/pricing              [catalog session]
└── export/                              # Route: /catalogs/:id/export               [catalog session]
```

**11 feature folders** (post un-merger). Each follows the **§3.D uniform internal layout**. The bracketed annotation per folder shows which sub-session OWNS it per FE-D12 amended grouping. Sub-sessions may own multiple folders (auth session owns 2, catalog session owns 6); but a folder is owned by exactly ONE sub-session — no cross-session writes to the same folder. Per FE-D13, each sub-session's folder set corresponds to a future MF remote in Phase 2.

**Previously-merged `account/` folder is RETIRED** in this amendment. Sub-folders that were inside `account/` (signup/, login/, onboarding/, profile/, components/otp-verify/, components/compliance-step/, components/super-category-chips/) redistribute as follows:
- `account/signup/`, `account/login/`, `account/components/otp-verify/` → `auth/signup/`, `auth/login/`, `auth/components/otp-verify/`
- `account/onboarding/`, `account/components/compliance-step/`, `account/components/super-category-chips/` → `onboarding/onboarding-wizard/`, **`shared/components/compliance-step/`** (moved to shared/ because profile session also reuses it), `onboarding/components/super-category-chips/`
- `account/profile/` → `profile/profile-edit/`

The `compliance-step` move to `shared/components/` is per §3.G rule — anything reused by 2+ features (here: onboarding + profile) belongs in shared/. This is the first §3 amendment that adds a shared component post-LOCK; the rule held throughout.

### D. Per-feature uniform internal layout (THE pattern)

Every feature folder under `features/` follows the same internal structure so specialists can pattern-match across features. This is what `account/` looks like (a representative multi-route example, post 2026-06-05B merger):

```
app/features/account/
├── account.routes.ts                    # Exports: default Routes[]  — 4 routes: /signup, /login, /onboarding, /profile
├── account-api.service.ts               # Feature-scoped service: HttpClient calls for /auth/otp/* + /auth/refresh + /auth/logout + /seller-profile/*
├── account-api.service.spec.ts
├── signup/                              # Sub-folder per route — page component
│   ├── signup.component.ts              # Standalone — page component for /signup route
│   ├── signup.component.html
│   ├── signup.component.scss            # Component-scoped styles (Tailwind classes in HTML are preferred)
│   └── signup.component.spec.ts
├── login/
│   └── ...                              # Same 4-file pattern
├── onboarding/
│   ├── onboarding.component.ts          # 3-phase wizard page for /onboarding route
│   ├── onboarding.component.html
│   ├── onboarding.component.scss
│   └── onboarding.component.spec.ts
├── profile/
│   └── ...                              # Same 4-file pattern (edit-existing-profile for /profile)
├── components/                          # Feature-private sub-components shared across the routes above
│   ├── otp-verify/                      # Used by signup + login
│   │   └── ...                          # Same 4-file pattern
│   ├── compliance-step/                 # Used by onboarding + profile
│   └── super-category-chips/            # Used by onboarding only
└── account.model.ts                     # Feature-private types (e.g., OnboardingPhase enum)
```

**The 7-file pattern** every feature follows:

| File / folder | Purpose | Always present? |
|---|---|---|
| `<feature>.routes.ts` | Routes[] array; consumed by `app.routes.ts` via `loadChildren` | Yes |
| `<feature>-api.service.ts` | Feature-scoped service for HTTP calls. NEVER `providedIn: 'root'` — provided by the feature route via `providers: [...]` so it can be lazy-tree-shaken | Yes (except `landing` which has no API) |
| `<page>/` folder per route | One sub-folder per route the feature owns; contains the page component (`*.component.ts/html/scss/spec.ts`) | Yes |
| `components/` folder | Feature-private sub-components (not reused across features) | Only if needed |
| `<feature>.model.ts` | Feature-private types (not promoted to `core/models/`) | Only if needed |
| `<feature>-state.service.ts` | Feature-scoped state (BehaviorSubject + signals). NEVER `providedIn: 'root'` | Only if needed |
| `<feature>.utils.ts` | Feature-private pure functions (formatters, mappers). Promote to `shared/` only if reused | Only if needed |

**Examples of features with extra structure:**

```
app/features/catalog-form/               # The spine — biggest feature
├── catalog-form.routes.ts
├── catalog-form.component.ts            # Page component
├── catalog-form-api.service.ts
├── catalog-form-state.service.ts        # Holds product + schema + draft state per route instance
├── draft-recovery.service.ts            # Wraps GET /products/:id/draft
├── wizard-renderer/                     # Feature-private sub-tree
│   ├── wizard-renderer.component.ts     # Iterates steps, dispatches fields
│   ├── step-composer.service.ts         # Groups schema.fields by step_id
│   └── field-dispatcher.component.ts    # Selects primitive based on schema.primitive
├── primitives/                          # The 11 primitives — feature-private sub-tree
│   ├── primitive.contract.ts            # PrimitiveInputs + ValueChange interfaces
│   ├── text-short/
│   ├── text-long/
│   ├── number/
│   ├── number-with-unit/
│   ├── currency/
│   ├── dropdown-small/
│   ├── dropdown-medium/
│   ├── dropdown-large/
│   ├── dropdown-api/
│   ├── image-upload/
│   └── address-group/
└── autofill-overlay/                    # Feature-private sub-component
    ├── autofill-overlay.component.ts
    └── ...
```

```
app/features/pricing/
├── pricing.routes.ts
├── pricing.component.ts
├── pricing-api.service.ts
├── pnl-breakdown/                       # Feature-private sub-component
├── margin-slider/                       # Feature-private sub-component
└── pricing-chart/                       # Feature-private sub-component (uses chart.js)
```

### E. Naming conventions (locked)

| Item | Convention | Example |
|---|---|---|
| File names | kebab-case | `auth.service.ts`, `catalog-form.component.ts`, `inr-currency.pipe.ts` |
| Class names | PascalCase + suffix | `AuthService`, `CatalogFormComponent`, `InrCurrencyPipe`, `JwtInterceptor` |
| Selector prefix | `mee-` (MeeSell) | `<mee-empty-state>`, `<mee-status-badge>`, `<mee-text-short>` |
| Component file suffix | `.component.ts` (template optional inline) | `dashboard.component.ts` |
| Service file suffix | `.service.ts` | `catalog-form-api.service.ts` |
| Interceptor file suffix | `.interceptor.ts` | `refresh.interceptor.ts` |
| Guard file suffix | `.guard.ts` | `auth.guard.ts` |
| Pipe file suffix | `.pipe.ts` | `inr-currency.pipe.ts` |
| Directive file suffix | `.directive.ts` | `autosave.directive.ts` |
| Routes file | `<feature>.routes.ts` | `catalog-form.routes.ts` |
| Model / type file | `.model.ts` | `product.model.ts` |
| Enum file | `.enum.ts` | `product-status.enum.ts` |
| InjectionToken file | `.token.ts` | `api-base-url.token.ts` |
| Test file | `.spec.ts` | `auth.service.spec.ts` (Vitest) |
| E2E file | `.e2e.spec.ts` | `dashboard-flow.e2e.spec.ts` (Playwright) |
| SCSS file | `kebab-case.scss`; partials prefix `_` | `_tokens.scss`, `dashboard.component.scss` |

**No exceptions.** Angular CLI generators (`ng g component`) produce these names by default; if a specialist hand-writes a file, it must match this table.

### F. tsconfig path aliases (locked)

`tsconfig.json` declares the following aliases. Imports use these — never relative paths that escape the current folder.

```jsonc
{
  "compilerOptions": {
    "paths": {
      "@core/*":          ["src/app/core/*"],
      "@shared/*":        ["src/app/shared/*"],
      "@features/*":      ["src/app/features/*"],
      "@design-system/*": ["src/app/design-system/*"],
      "@env":             ["src/environments/environment"]
    }
  }
}
```

**Rules:**
- Imports within a feature use **relative paths** (`./signup/signup.component`)
- Imports from another folder use the **alias** (`@core/auth/auth.service`, `@shared/pipes/inr-currency.pipe`)
- **NEVER** `import { AuthService } from '../../../core/auth/auth.service'` — that's a sign of either misuse or wrong layer placement
- **NEVER** `import { CatalogFormService } from '@features/catalog-form/...'` from another feature — that's a §17 violation

### G. Decision rules — where does X go?

```
Does X shape how the app looks, feels, moves, or responds to breakpoints?
    YES → design-system/ (SCSS first; TS mirror only if runtime access is needed)
    NO  → continue

Is X stateless presentation reused by 2+ features?
    YES → shared/components/
    NO  → continue

Is X a singleton service / interceptor / guard / cross-cutting infrastructure?
    YES → core/
    NO  → continue

Does X own state or render a route?
    YES → features/<feature>/
    NO  → it probably doesn't belong in the app — challenge the need
```

**Specific edge cases:**

| Case | Decision |
|---|---|
| A type used by 2 features (`Product`) | `core/models/` |
| A type used by 1 feature (`SmartPickerSuggestion`) | `features/smart-picker/smart-picker.model.ts` |
| A formatter used by 2 features (`formatInr`) | `shared/pipes/inr-currency.pipe.ts` |
| A formatter used by 1 feature (`formatPrecheckHint`) | `features/images/images.utils.ts` |
| Autosave directive (used by `catalog-form` only in V1) | `shared/directives/` — anticipating V1.5 onboarding-form autosave reuse |
| The 11 form primitives | `features/catalog-form/primitives/` — they exist ONLY for the wizard renderer; if V2 needs them elsewhere, promote to `shared/` THEN |
| Material custom theme override | `design-system/_theme.scss` |
| OTP input wrapper around `ng-otp-input` | `features/account/components/otp-verify/` (only the account feature uses it; post 2026-06-05B merger) |

### H. What is NOT in this tree (V1 explicit exclusions)

- `src/app/state/` — there is no global store. State lives in services (per Decision 10). If you find yourself reaching for one, surface it as a §17 question.
- `src/app/api/` (at top-level) — `core/api/` exists; there is no second one.
- `src/app/store/` — same reasoning as `state/`.
- `src/app/types/` — types live next to their owner (`core/models/` for shared, `<feature>/<feature>.model.ts` for feature-private).
- `src/app/constants/` — constants live in `<feature>/<feature>.constants.ts` or `shared/enums/`. No god-bag of constants.
- `src/app/mocks/` — MSW mock handlers live in `src/mocks/` (Vitest-managed), not under `app/`.
- Module Federation `mf-config.js` — deferred to Phase 2 (per Decision 12).
- Ionic / Capacitor folders — deferred to Phase 2 (per Decision 13).
- `assets/` folder — Angular CLI 17+ uses `public/` directly; no `src/assets/`.

### I. What §3 does NOT cover

The deep contract for each `core/` member lives in §4 (specifically the interceptor chain order, the `AuthService` signal API, the `ApiClient` method signatures). The design system token catalog and theming flow live in §5A. Each feature's deep spec — what its `*.component.ts` actually does, which sub-components it owns, what data it fetches — lives in §7-§15. The PWA service worker rules live in §16. The test file conventions live in §19. Section 3 says **where files live**; specialists writing actual code consult the per-section spec for **what those files contain**.

---

## Section 4 — `core/` — Cross-Cutting Foundation

STATUS: LOCKED (2026-06-05, founder ratification with 3 review outcomes recorded inline:
  Look 1 — APPLIED: opt-in `retryOn503: boolean` added to `ApiOptions` (§4.E.1) with 3-try exponential backoff (1s/2s/4s); default false; recommended use sites named (autofill, image upload, export trigger);
  Look 2 — DEFERRED to V1.5: `NetworkService` stays online-only signal in V1; `navigator.connection.effectiveType` added when a feature has adaptive behavior to drive;
  Look 3 — DEFERRED to V1.5: "Report this issue" button in error snackbar deferred until support infrastructure exists; traceId-in-Details-dialog is the V1 surface.)

### A. What §4 establishes

§4 is the **contract for the cross-cutting infrastructure** every feature depends on. It locks:
- The **4-interceptor chain** in canonical order (Jwt → Locale → Refresh → Error)
- The **`AuthService` API** — signals, methods, lifecycle (bootstrap on reload, schedule refresh, logout)
- The **`AuthGuard` + `PlanGuard`** behavior and integration with route declarations
- The **`ApiClient` typed wrapper** over Angular's native `HttpClient` — the only HTTP interface features import
- The **`ErrorService`** — snackbar surface for user-facing errors
- The **`NetworkService`** — `navigator.onLine` signal for offline UX
- The **`InjectionToken` set** — env config, API base URL, build-time constants
- The **cross-feature model registry** in `@core/models/` — typed contracts shared across features

This is the **shared toolkit each feature imports rather than re-implements**. The philosophy mandates (M9 locale, M3 validation messages) and the FE-D5/D6 security invariants (in-memory token, silent refresh, server-side revocation) all apply uniformly because every feature talks to the backend through this layer.

§4 is NOT the per-feature deep spec (§7-§15), NOT the design system (§5A), NOT the build/deploy spec (§20). §4 says **what every feature can rely on**.

### B. The interceptor chain (4 interceptors, canonical order)

Registered in `app.config.ts` via `provideHttpClient(withInterceptors([...]))`. Order is **load-bearing** — changing it changes semantics.

```
Outgoing request:
  ┌──────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
  │ feature call │ →  │ JwtInterceptor   │ →  │ LocaleInterceptor│ →  │ RefreshIntcptr  │
  └──────────────┘    └──────────────────┘    └──────────────────┘    └─────────────────┘
                                                                              ↓
                       ┌──────────────────┐    ┌──────────────────┐    ┌─────────────────┐
                       │  feature handler │ ←  │ ErrorInterceptor │ ←  │   HttpClient    │
                       └──────────────────┘    └──────────────────┘    └─────────────────┘
Incoming response:
```

**Registration order in code:**
```typescript
// app.config.ts
provideHttpClient(
  withInterceptors([
    jwtInterceptor,        // 1. Attach Authorization: Bearer
    localeInterceptor,     // 2. Attach Accept-Language
    refreshInterceptor,    // 3. Catch 401, refresh, replay
    errorInterceptor,      // 4. Normalize 4xx/5xx → ApiError, snackbar surface
  ])
)
```

#### B.1 — `JwtInterceptor`

- **Reads:** `AuthService.accessToken()` signal
- **Writes:** `Authorization: Bearer <token>` header
- **Skips:** any URL matching `/api/v1/auth/otp/*` or `/api/v1/auth/refresh` (no token needed; refresh cookie does the work)
- **Behavior:** if accessToken is `null` AND the URL is auth-guarded, do NOT add header — the `AuthGuard` should have caught this; if it reaches the interceptor, downstream will 401 and `RefreshInterceptor` recovers
- **File:** `core/interceptors/jwt.interceptor.ts`

#### B.2 — `LocaleInterceptor`

- **Reads:** `TranslocoService.getActiveLang()` (or the env-token default `en`)
- **Writes:** `Accept-Language: <locale>` header
- **Skips:** none — always attaches even on `/auth/*` because backend validation messages are locale-keyed (per Philosophy M3)
- **Behavior:** locale falls back to `en` if no active locale set. V1 ships English only; V1.5 Tamil/Hindi swap is the value of this interceptor — flips happen via `TranslocoService.setActiveLang('ta')` and every subsequent request switches locale without any feature code knowing
- **File:** `core/interceptors/locale.interceptor.ts`

#### B.3 — `RefreshInterceptor`

- **Catches:** `HttpErrorResponse` with `status === 401` on any URL NOT matching `/api/v1/auth/*` (auth endpoints handle their own 401 — they ARE the auth)
- **Behavior on 401:**
  1. Check a shared `refreshing$` `BehaviorSubject<Observable<string> | null>` — if a refresh is already in flight, wait for it (don't fire concurrent refreshes)
  2. If no in-flight refresh, fire `POST /api/v1/auth/refresh` (browser sends HttpOnly cookie automatically), store the resulting `Observable<string>` (access_token) in `refreshing$`
  3. On refresh success: `AuthService.setAccess(response)`, clear `refreshing$`, replay the ORIGINAL failed request with the new token (the next interceptor pass picks up the new accessToken from the signal)
  4. On refresh failure (401 from `/auth/refresh` itself): propagate to `ErrorInterceptor` (which routes to `/login`)
- **Deduplication:** if 5 in-flight requests get 401 simultaneously, only ONE `/auth/refresh` fires; the other 4 wait for the same Observable, then all 5 replay
- **File:** `core/interceptors/refresh.interceptor.ts`

#### B.4 — `ErrorInterceptor`

- **Catches:** any unhandled `HttpErrorResponse` (the `RefreshInterceptor` handles 401 + refresh; everything else lands here)
- **Behavior:**
  - **4xx (other than 401)** — wrap into `ApiError` (see §4.E.4), surface user-facing message via `ErrorService.showError(apiError)`, RE-THROW so feature code can also `catch` if it wants (e.g., 422 validation errors are usually feature-handled)
  - **5xx** — wrap into `ApiError`, surface generic "Something went wrong on our side" via `ErrorService`, RE-THROW
  - **401 reaching here** (refresh also failed) — clear `AuthService.accessToken`, route to `/login`, surface "Your session expired" snackbar
  - **Network error (no response)** — wrap into `ApiError(kind: 'network')`, surface "You appear to be offline" if `NetworkService.online()` is `false`; otherwise "Cannot reach the server"
- **File:** `core/interceptors/error.interceptor.ts`

### C. `AuthService` — the full API contract

`core/auth/auth.service.ts` — `providedIn: 'root'`, singleton.

```typescript
@Injectable({ providedIn: 'root' })
export class AuthService {
  // ── Signals (the public reactive surface) ──
  readonly accessToken    = signal<string | null>(null);
  readonly userId         = computed<UUID | null>(() => decodeJwt(this.accessToken())?.sub ?? null);
  readonly plan           = computed<PlanTier | null>(() => decodeJwt(this.accessToken())?.plan ?? null);
  readonly isAuthenticated = computed<boolean>(() => this.accessToken() !== null);

  // ── Lifecycle ──
  bootstrap(): Observable<boolean>;
    // Called by AuthGuard.canActivate on auth-guarded routes when accessToken is null.
    // Fires POST /api/v1/auth/refresh; emits true on success, false on 401.
    // Schedules the next refresh via scheduleRefresh().

  setAccess(response: { access_token: string; expires_in: number }): void;
    // Called by AccountApiService after successful /auth/otp/verify or by RefreshInterceptor
    // after successful /auth/refresh. Updates accessToken signal + schedules refresh.

  scheduleRefresh(expiresInSeconds: number): void;
    // Internal — schedules a setTimeout to fire POST /auth/refresh at (expiresIn - 30s).
    // Cancels any prior scheduled refresh. No env coupling — uses what backend sent.

  logout(): Observable<void>;
    // Called by navbar logout button. Fires POST /api/v1/auth/logout (backend revokes Valkey
    // allowlist + clears refresh cookie). Clears accessToken signal. Navigates to /.

  clear(): void;
    // Called by ErrorInterceptor on unrecoverable 401 (refresh failed). Wipes accessToken
    // signal + cancels scheduled refresh. Does NOT call /auth/logout — the refresh already
    // failed, so server-side state is gone.
}
```

**Key constraints (per FE-D5 + FE-D6):**
- `accessToken` is in-memory ONLY. No write to `localStorage`, `sessionStorage`, `IndexedDB`, or JS-readable cookies
- `bootstrap()` is the ONLY way the app recovers an access token across reloads
- `scheduleRefresh()` reads `expires_in` from response — no env-driven lifetime on the frontend (per FE-D6)
- `logout()` fires `POST /api/v1/auth/logout` which triggers server-side `DEL cache:refresh:{hmac_sha256(token, REFRESH_TOKEN_PEPPER)}` (per backend ratification §1)

### D. `AuthGuard` + `PlanGuard`

#### D.1 — `AuthGuard`

```typescript
// core/auth/auth.guard.ts
export const authGuard: CanActivateFn = (route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);

  // Fast path: token is in memory
  if (auth.isAuthenticated()) return true;

  // Slow path: bootstrap via /auth/refresh
  return auth.bootstrap().pipe(
    map(success => success ? true : router.createUrlTree(['/login']))
  );
};
```

Applied to every route in `app.routes.ts` EXCEPT `/` + `/signup` + `/login`. Per §23 route inventory.

#### D.2 — `PlanGuard`

```typescript
// core/auth/plan.guard.ts
export const planGuard = (requiredPlan: PlanTier): CanActivateFn =>
  (route, state) => {
    const auth = inject(AuthService);
    const router = inject(Router);
    const error = inject(ErrorService);

    if (!auth.plan()) return router.createUrlTree(['/login']);
    if (auth.plan() === 'pro' || requiredPlan === 'free') return true;

    error.showInfo('This feature is available on the Pro plan');
    return router.createUrlTree(['/dashboard']);
  };
```

**Wired-but-inert in V1.** No V1 route uses `planGuard('pro')` — every feature is on the free tier. V1.5 lights it up for: bulk operations, advanced exports, analytics. The guard is shipped to V1 so V1.5 only adds the `canActivate: [planGuard('pro')]` line, no architecture change.

### E. `ApiClient` — typed HttpClient wrapper

`core/api/api-client.service.ts` — the ONLY HTTP interface features import. Per §3 LOCK: `import { HttpClient } from '@angular/common/http'` in a feature service is a contract violation; injecting `ApiClient` is the only sanctioned form.

#### E.1 — Method signatures

```typescript
@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);  // env-driven InjectionToken

  get<T>(path: string, options?: ApiOptions): Observable<T>;
  post<T>(path: string, body: unknown, options?: ApiOptions): Observable<T>;
  patch<T>(path: string, body: unknown, options?: ApiOptions): Observable<T>;
  put<T>(path: string, body: unknown, options?: ApiOptions): Observable<T>;
  delete<T = void>(path: string, options?: ApiOptions): Observable<T>;

  // Specialized for multipart (image upload — used by features/images/)
  postMultipart<T>(path: string, formData: FormData, options?: ApiOptions): Observable<T>;
}

interface ApiOptions {
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
  withCredentials?: boolean;  // true for /auth/* per FE-D5 cookie attachment

  /**
   * Opt-in retry-with-backoff on 503 Service Unavailable.
   * Default: false (caller handles via RxJS retry() per call).
   * When true: ApiClient retries up to 3 times with exponential backoff
   *   (1s, 2s, 4s) before letting the error reach ErrorInterceptor.
   * Use for: autofill (Gemini cold start), image upload (GCS hiccup),
   *   export trigger (Celery queue backpressure).
   * Do NOT use for: catalog autosave PATCH (loud failures are correct —
   *   the seller needs to see the offline banner immediately).
   */
  retryOn503?: boolean;

  // Note: NOT a per-call cache option. Caching is server-side (ETag + browser HTTP cache);
  // ApiClient does NOT implement an in-memory cache layer.
}
```

#### E.2 — What it does NOT do

- **No in-memory caching.** The browser HTTP cache + backend Cache-Control headers handle that.
- **No automatic retry-on-error EXCEPT 503 when explicitly opted in.** The `RefreshInterceptor` handles 401 retry transparently. Other retries are feature-decided via RxJS `retry()` operators on a per-call basis. The single exception is the opt-in `retryOn503` flag in `ApiOptions` (added per §4 LOCK Look 1) — when `true`, `ApiClient` retries up to 3 times with exponential backoff (1s, 2s, 4s) before propagating to `ErrorInterceptor`. Default is `false`.
- **No request deduplication.** Same as caching — browser HTTP cache handles GET deduplication via ETags.
- **No automatic JSON parsing config.** Angular's HttpClient defaults to JSON. `ApiClient` doesn't override.

#### E.3 — Why the wrapper exists

Three reasons that aren't just style:
1. **Centralized `baseUrl` injection.** Features write `apiClient.get('/products')` not `httpClient.get('/api/v1/products')`. The `/api/v1` prefix and the host name live in `API_BASE_URL` token — swappable by env without feature code changes.
2. **`withCredentials: true` enforced for `/auth/*`.** Without this, the refresh cookie doesn't travel cross-origin. The wrapper applies it automatically for any URL starting with `/auth/`.
3. **V1.5/V2 swap path.** When V1.5 considers gRPC or tRPC, only `ApiClient` changes. Features keep the same `apiClient.get('/products')` calls.

#### E.4 — `ApiError` shape

```typescript
// core/api/api-error.ts
export class ApiError extends Error {
  readonly kind: 'http' | 'network' | 'parse';
  readonly status: number;          // 0 for network, else HTTP status
  readonly code: string | null;     // backend's machine-readable code (e.g., 'rate_limit_exceeded')
  readonly displayMessage: string;  // locale-resolved user-facing message
  readonly traceId: string | null;  // backend's request-id header (for support escalation)
  readonly raw: HttpErrorResponse | null;  // original response if available
}
```

Every interceptor wrapping wraps unhandled responses into `ApiError`. Features `catch` and handle, or let `ErrorService` surface to the snackbar. `displayMessage` is resolved against the i18n bundle by `ErrorInterceptor` BEFORE the error reaches the feature (so feature code never has to translate).

### F. `ErrorService` — snackbar surface

`core/services/error.service.ts` — `providedIn: 'root'`.

```typescript
@Injectable({ providedIn: 'root' })
export class ErrorService {
  showError(error: ApiError | Error | string): void;
    // Surfaces error.displayMessage (or .message) via MatSnackBar.
    // Duration: 6s for errors, swipe-to-dismiss on mobile.
    // Action button: "Details" if error.traceId exists → opens dialog with traceId
    //                  for support escalation.

  showWarning(message: string): void;
    // Yellow snackbar, 4s.

  showInfo(message: string): void;
    // Blue snackbar, 3s. Used by PlanGuard upsell + autosave indicators.

  showSuccess(message: string): void;
    // Green snackbar, 3s. Used by feature success confirmations (autofill applied,
    // image uploaded, export ready).
}
```

**Not in scope:** persistent error log, error grouping, retry-from-snackbar. V1.5 may add a `core/services/error-log.service.ts` if support demand justifies it.

### G. `NetworkService` — offline UX

`core/services/network.service.ts` — `providedIn: 'root'`.

```typescript
@Injectable({ providedIn: 'root' })
export class NetworkService {
  readonly online = signal<boolean>(navigator.onLine);
  // Updates on window 'online' + 'offline' events.

  // Effect: when offline → online, the AutosaveDirective (shared/) reads this
  // signal and flushes its queue of pending PATCHes.
}
```

The signal drives two visible behaviors:
1. **`<mee-offline-banner>`** (shared component) — appears in app shell when `online() === false`
2. **`AutosaveDirective`** (shared directive) — queues PATCH calls when offline, replays on reconnect

V1.5 may extend with `effectiveType` from `navigator.connection` for 2G/3G UX adaptations (low-data mode, defer non-critical images). V1 is binary online/offline.

### H. `InjectionToken` set — env config

`core/tokens/` holds the typed env contract:

```typescript
// core/tokens/api-base-url.token.ts
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL');
// e.g., 'https://api.mesell.xyz' (prod), 'https://api-dev.mesell.xyz' (dev)

// core/tokens/env-config.token.ts
export const ENV_CONFIG = new InjectionToken<EnvConfig>('ENV_CONFIG');

// core/tokens/env-config.model.ts
export interface EnvConfig {
  readonly production: boolean;
  readonly apiBaseUrl: string;
  readonly defaultLocale: 'en' | 'ta' | 'hi';
  readonly serviceWorkerEnabled: boolean;
  readonly bundleAnalyzerEnabled: boolean;  // dev-only flag
}

// core/auth/auth-tokens.ts (added 2026-06-05 post service-builder dispatch — was in §3.C.1 tree
// but not enumerated in this §4.H section originally)
// Allows cross-module DI of the access-token signal without circular imports through AuthService.
export const ACCESS_TOKEN_SIGNAL = new InjectionToken<Signal<string | null>>('ACCESS_TOKEN_SIGNAL');
// Used by RefreshInterceptor + JwtInterceptor when AuthService import would create a circular dep.
```

**Provision pattern in `app.config.ts`:**
```typescript
providers: [
  { provide: API_BASE_URL, useValue: environment.apiBaseUrl },
  { provide: ENV_CONFIG,   useValue: environment },
  // ... interceptors, router, transloco, service worker
]
```

`environment.ts` + `environment.prod.ts` per Angular CLI defaults. **Build-time replacement** via `fileReplacements` in `angular.json` — no runtime env swap in V1. V1.5 may add `/config.json` fetch at app boot if a single Docker image needs to serve multiple environments without rebuild.

### I. Cross-feature models in `@core/models/`

Typed contracts every feature reads. The shape mirrors the backend's response shape per `BACKEND_ARCHITECTURE.md` and `DATABASE_ARCHITECTURE.md §4` JSONB shapes:

```typescript
// core/models/product.model.ts
export interface Product {
  readonly id: UUID;
  readonly catalogId: UUID;
  readonly userId: UUID;
  readonly categoryId: UUID;
  readonly name: string | null;
  readonly description: string | null;
  readonly fields: Record<string, FieldValue>;        // products.fields_jsonb
  readonly aiSuggestions: Record<string, AiSuggestion>;  // products.ai_suggestions_jsonb
  readonly status: ProductStatus;
  readonly createdAt: string;
  readonly updatedAt: string;
}

// core/models/field-schema.model.ts (the three-layer field per MVP §5.6.1 — DISPLAY+CANONICAL only;
// meesho_* layer stripped by backend per Philosophy F1)
export interface FieldSchema {
  readonly canonicalName: string;
  readonly dataType: 'text' | 'number' | 'dropdown' | 'image_url' | 'date' | 'boolean';
  readonly primitive: PrimitiveKind;        // one of 11
  readonly marker: 'compulsory' | 'optional';
  readonly isAdvanced: boolean;
  readonly isHidden: boolean;
  readonly stepId: StepId;                  // one of 13
  readonly maxLength: number | null;
  readonly minLength: number | null;
  readonly regex: string | null;
  readonly minValue: number | null;
  readonly maxValue: number | null;
  readonly unitSuffix: string | null;
  readonly displayLabel: LocaleMap;         // {en, ta?, hi?}
  readonly displayHelp: LocaleMap | null;
  readonly displayPlaceholder: LocaleMap | null;
  readonly displayUnitLabel: LocaleMap | null;
  readonly validationMessage: LocaleMap | null;
  readonly helpUrl: string | null;
  // meesho_column_header, meesho_column_index, enum_codes_map — NEVER present per Philosophy M10
}

// core/models/ai-suggestion.model.ts (per DB §4.5 + MVP §4)
export interface AiSuggestion {
  readonly value: string | number | string[];
  readonly confidence: number;     // 0.0 - 1.0
  readonly source: string;         // e.g., 'gemini-2.5-flash'
  readonly accepted: boolean;
  readonly rejectedReason?: string;
}

// core/models/paginated-response.model.ts (generic)
export interface PaginatedResponse<T> {
  readonly data: readonly T[];
  readonly total: number;
  readonly page: number;
  readonly limit: number;
}
```

**Plus:** `Catalog`, `Category`, `PricingCalc`, `ExportRecord`, `SellerProfile`, `LocaleMap` (`{en: string, ta?: string, hi?: string}`). Full list in `@core/models/`.

**Rule:** if a feature defines a type the backend already returns, it's a duplication bug. Use the model. If the model doesn't exist, surface to coordinator + add it here.

### J. What §4 does NOT cover

- Per-feature service implementations (those live in `features/<feature>/<feature>-api.service.ts` per §3.D)
- The interceptor source code (specialists implement per this contract during dispatch)
- Service worker config (`ngsw-config.json` lives in §16)
- The 11 primitives + form renderer contract (that's §18)
- Test setup for `core/` services (that's §19)
- How `app.config.ts` wires everything (that's §20 build/deploy)

§4 says **what the cross-cutting layer exposes**; specialists writing code consult this for the contract.

---

## Section 5 — `shared/` — UI Primitives + Pipes + Directives

STATUS: LOCKED (2026-06-05, founder ratification as-is; coordinator depth call ratified — inventory section, not deep contract; 6 components + 3 pipes + 2 directives + 6 enums; `<mee-navbar>` exception to stateless rule documented; `[meeAutosave]` is the most complex item)

### A. What §5 establishes

§5 is the **stateless reusable UI inventory**. It enumerates every component, pipe, directive, and enum that lives in `shared/` with each item's contract (inputs, outputs, behavior), the features that consume it, and the rule for what qualifies for `shared/` versus staying in a feature.

§5 is intentionally an **inventory section, not a deep contract section** — each item is small. The contract IS the inventory. Specialists writing these components don't need a per-section deep spec; they need the list + the input/output contract per item.

### B. The qualifying rule (load-bearing)

Something lives in `shared/` if and only if:

1. **It is stateless** — no service state, no signals beyond inputs, no side effects beyond DOM rendering or event emission
2. **It is reused by 2+ features** — single-feature use stays in the feature folder (per §3.G)
3. **It is presentation, not behavior orchestration** — orchestration belongs in `core/`

If any of these fails, it does not belong in `shared/`. The `AutosaveDirective` is the edge case — it's used by `catalog-form` only in V1, but moved to `shared/` because V1.5 onboarding-form autosave reuse is on the roadmap (per `discipline_no_premature_dispatch.md`).

### C. Components inventory

All standalone components, `OnPush` change detection, selector prefix `mee-`.

#### C.1 — `<mee-empty-state>`

- **Purpose:** Empty-state placeholder with icon + headline + body + CTA
- **Inputs:** `icon: string` (Material Symbols name), `headline: string`, `body?: string`, `ctaLabel?: string`
- **Outputs:** `ctaClick: EventEmitter<void>`
- **Used by:** `dashboard` (empty product list), `images` (no images uploaded), `pricing` (no calc yet), `export` (validation gate not passed)
- **File:** `shared/components/empty-state/empty-state.component.ts`

#### C.2 — `<mee-status-badge>`

- **Purpose:** Color-coded status pill — gray/draft, blue/exported, green/live, red/failed
- **Inputs:** `status: ProductStatus | ExportStatus | ImagePrecheckResult`
- **Outputs:** none
- **Used by:** `dashboard` (per-row status), `export` (export status), `images` (per-image precheck status)
- **File:** `shared/components/status-badge/status-badge.component.ts`

#### C.3 — `<mee-loading-spinner>`

- **Purpose:** Centered Material spinner with optional caption
- **Inputs:** `diameter?: number` (default 32), `caption?: string` (e.g., "Generating XLSX…")
- **Outputs:** none
- **Used by:** `auth` (OTP send), `smart-picker` (Gemini call), `images` (upload progress), `pricing` (calc), `export` (poll), `catalog-form` (autofill)
- **File:** `shared/components/loading-spinner/loading-spinner.component.ts`

#### C.4 — `<mee-confirm-dialog>`

- **Purpose:** Modal confirmation dialog (Material MatDialog template ref)
- **Inputs:** `title: string`, `message: string`, `confirmLabel?: string` (default "Confirm"), `cancelLabel?: string` (default "Cancel"), `destructive?: boolean` (red confirm button if true)
- **Outputs:** dialog closes with `boolean` (true = confirm, false/undefined = cancel)
- **Used by:** `dashboard` (soft-delete), `catalog-form` (category change warning), `export` (re-export overwrite warning)
- **File:** `shared/components/confirm-dialog/confirm-dialog.component.ts`

#### C.5 — `<mee-offline-banner>`

- **Purpose:** Top-of-app banner shown when `NetworkService.online()` is `false`
- **Inputs:** none (reads `NetworkService` directly via `inject()`)
- **Outputs:** none
- **Used by:** `app.component.ts` (root) — visible across every route
- **File:** `shared/components/offline-banner/offline-banner.component.ts`

#### C.6 — `<mee-navbar>`

- **Purpose:** App-shell top navigation. Logo + brand + (when authenticated) seller phone + logout button
- **Inputs:** none (reads `AuthService` signals directly)
- **Outputs:** none — logout button calls `AuthService.logout()`
- **Used by:** `app.component.ts` (root) — visible on every auth-guarded route
- **File:** `shared/components/navbar/navbar.component.ts`

### D. Pipes inventory

All standalone, `pure: true`.

| Pipe | Purpose | Usage |
|---|---|---|
| `InrCurrencyPipe` (`inrCurrency`) | Indian numbering format with ₹ prefix — `1499` → `₹1,499`; `149900` → `₹1,49,900` | `{{ product.price \| inrCurrency }}` |
| `LocaleLabelPipe` (`localeLabel`) | Resolves `LocaleMap` (`{en, ta?, hi?}`) to active locale; falls back to `en` if requested locale missing | `{{ field.displayLabel \| localeLabel }}` |
| `RelativeTimePipe` (`relativeTime`) | "2 hours ago", "yesterday", "last week" using `Intl.RelativeTimeFormat` (locale-aware) | `{{ product.updatedAt \| relativeTime }}` |

All three live in `shared/pipes/`.

### E. Directives inventory

#### E.1 — `AutosaveDirective` (`[meeAutosave]`)

- **Purpose:** Form autosave dispatcher per V1 §F3 — fires 10s after last change + on blur
- **Inputs:**
  - `meeAutosave: (formValue: T) => Observable<void>` — the persistence callback (typically calls `apiClient.patch`)
  - `meeAutosaveDebounceMs?: number` — default `10000`
  - `meeAutosaveOnBlur?: boolean` — default `true`
- **Outputs:** `meeAutosaveStatus: EventEmitter<'idle' | 'saving' | 'saved' | 'error'>` — features bind to this to show "Saving…" / "Saved" indicators
- **Behavior:**
  - Subscribes to `FormGroup.valueChanges` with `debounceTime(meeAutosaveDebounceMs)`
  - Listens to `(blur)` events on the host
  - Queues the call if `NetworkService.online()` is `false`; replays on reconnect (subscribes to the online signal via `toObservable`)
  - On call success → emits `'saved'` (3s) then `'idle'`
  - On call error → emits `'error'` (stays until next change)
- **Used by:** `catalog-form` (the wizard form) — V1's only consumer. V1.5 will add `account/onboarding` (multi-step compliance form autosave).
- **File:** `shared/directives/autosave.directive.ts`

#### E.2 — `ClickOutsideDirective` (`[meeClickOutside]`)

- **Purpose:** Emits when click occurs outside the host element. Used for dismissing dropdowns, popovers, drawers
- **Inputs:** none (binds host element ref)
- **Outputs:** `meeClickOutside: EventEmitter<MouseEvent>`
- **Used by:** `smart-picker` (close suggestions overlay), `catalog-form` (close autofill diff popover), `dashboard` (close action menu)
- **File:** `shared/directives/click-outside.directive.ts`

### F. Enums inventory

Typed constants used across features. The enum file is the **single source of truth for the value set**; feature code imports and uses these names — never string literals.

```typescript
// shared/enums/product-status.enum.ts
export type ProductStatus = 'draft' | 'ready' | 'exported' | 'live' | 'deleted';
export const PRODUCT_STATUS = {
  DRAFT: 'draft', READY: 'ready', EXPORTED: 'exported',
  LIVE: 'live', DELETED: 'deleted',
} as const satisfies Record<string, ProductStatus>;
```

| Enum | Values | Used by |
|---|---|---|
| `ProductStatus` | draft / ready / exported / live / deleted | dashboard, catalog-form, export |
| `PlanTier` | free / pro | core/auth, V1.5 features |
| `ImagePrecheckResult` | pending / processing / ready / failed | images |
| `ExportStatus` | processing / ready / failed | export |
| `PrimitiveKind` | text_short / text_long / number / number_with_unit / currency / dropdown_small / dropdown_medium / dropdown_large / dropdown_api_search / image_upload / address_group | catalog-form (the 11 primitives — per §18) |
| `StepId` | basics / pricing / inventory / sizing / materials / food / tech_specs / safety / warranty / compliance / photos / description / advanced | catalog-form (the 13 wizard steps — per MVP §5.6.3) |

All in `shared/enums/`.

### G. Models in `shared/` vs `core/`

Quick disambiguation rule (referenced from §3.G):
- **Behavior model + cross-feature** → `core/models/` (e.g., `Product`, `Category`, `FieldSchema`)
- **Value-only + cross-feature** → `shared/enums/` (e.g., `ProductStatus`, `StepId`)
- **Feature-private** → `features/<feature>/<feature>.model.ts`

If unsure: start in the feature folder. Promote to `shared/enums/` or `core/models/` when a second consumer appears.

### H. What §5 does NOT cover

- Per-component test files (Vitest, covered by §19)
- Component-scoped SCSS (Tailwind utility classes preferred; SCSS only for what Tailwind can't express — covered by §5A)
- Component visual mockups (each component will get a small mockup as part of §5B wireframe artefacts)
- The 11 form primitives (those are FEATURE-private to `catalog-form/primitives/` per §3.D — NOT in `shared/`)
- The wizard step composer (feature-private to `catalog-form/wizard-renderer/`)

§5 says **what's in the stateless reusable layer**; specialists writing these consult §4 for cross-cutting services, §5A for design tokens to style with, and §19 for test patterns.

---

## Section 5A — `design-system/` — Tokens, Theming, Typography, Spacing

STATUS: FULL LOCK (2026-06-06 — integration AMENDMENT 2026-06-06B per design system sub-session deliverables per FE-D10 + FE-D11)

**AMENDMENT 2026-06-06B — Design system values integrated 2026-06-06:**
Values landed in `frontend/src/app/design-system/` per `DESIGN_SYSTEM_ARCHITECTURE.md §2.A`. `ng build --configuration=production` succeeds with zero errors using the new tokens. Bundle stays within §19 budget. §5A framework remains LOCKED unchanged (no token taxonomy / scale rung / breakpoint shifts). The values portion of §5A is now AUTHORITATIVE per the design system sub-session output.

**Locked value highlights (consumed via CSS custom properties):**
- **Primary brand**: `#F26B23` saffron-leaning warm orange (preserved from placeholder)
- **Secondary**: `#1E40AF` deep blue (preserved from placeholder)
- **Background**: `#f0f5f9` soft cool-gray (changed from `#FFFFFF` placeholder — softer canvas per Spike Angular alignment)
- **Surface**: `#ffffff`; on-surface `#2a3547`
- **Typography**: **Plus Jakarta Sans** (Google Fonts; weights 300-800) — deviation from Inter placeholder; better x-height for 360px mobile; Indic-script fallbacks (Noto Sans Tamil + Noto Sans Devanagari) preserved for V1.5
- **Border radius**: 7/16/18/full (added beyond original §5A scope — soft rounded feel)
- **Reduced-motion**: respected via `prefers-reduced-motion` media query (durations zeroed)
- **Iconography (interim ratification)**: Material Symbols **Outlined** variant as V1 default until `docs/design-system/ICONOGRAPHY.md` authors final ratification

**Spike Angular alignment (NEW visual reference):**
The design system sub-session adopted Spike Angular's light-theme as the reference template. Substantial component-level visual language pre-baked via `_component-overrides.scss` (20 KB) covering 15 Material components: badge / button / card / chip / dialog / expansion / icon-button / menu / option / select / snackbar / stepper / tab / textfield / toolbar. Component-builder dispatches across feature sub-sessions inherit this language — they do NOT reinvent component visuals.

**Deferred deliverables (4 of 13 from DESIGN_SYSTEM_ARCH §2.A — non-blocking for module-wise UI work):**

| Deliverable | Why deferred | Workaround until landed | Owner |
|---|---|---|---|
| `_tokens.spec.ts` (WCAG contrast verification) | CI gate gap; not blocking dev | Manual verification per dispatch | design system sub-session |
| `docs/design-system/RATIONALE.md` | Documentation gap | Spike alignment + Plus Jakarta Sans rationale captured in this amendment | design system sub-session |
| `docs/design-system/MICROCOPY_TONE.md` | Tone-consistency gap | Each feature sub-session uses Tirupur-seller voice (5th-grade English, action verbs, no jargon) until landed | design system sub-session |
| `docs/design-system/ICONOGRAPHY.md` | Variant decision gap | Material Symbols Outlined as interim default per this amendment | design system sub-session |

**Implications for consumer sessions (feature sub-sessions):**
1. **CSS custom properties are LIVE** — components use `var(--mee-color-primary)`, `var(--mee-text-base)`, etc. Direct hex values forbidden.
2. **Tailwind utility classes work** — `bg-primary`, `text-on-surface`, `p-4`, `text-lg` consume the tokens correctly.
3. **Material directives work** — `color="primary"` resolves to `#F26B23`; M3 theme is wired.
4. **Component overrides apply automatically** — feature components rendering Material primitives inherit Spike Angular visual language with zero feature-side config.
5. **No re-styling pass needed** — components built against the locked tokens land in their final visual form (subject to per-feature mockup review).

---

**Historical context (pre-2026-06-06B amendment) — preserved for chain-of-custody:**

Per founder ruling FE-D9 (2026-06-05), values were PLACEHOLDER pending external designer engagement. Per founder ruling FE-D10 (2026-06-05), FE-D9 was superseded by AI-assisted production via `meesell-angular-ui-styler` (Opus tier). Per founder ruling FE-D11 (2026-06-05), design system work moved to a dedicated sub-session. Per 2026-06-06A grouping ratification, design system sub-session bootstrapped + Phase 1 Round 1 curation completed + multi-turn iteration ratified per `DESIGN_SYSTEM_ARCHITECTURE.md §5`. This AMENDMENT 2026-06-06B records the integration outcome.

### A. What §5A establishes

§5A is the **single source of visual truth**. It locks:
- The **6 semantic color tokens** (primary, secondary, surface, error, success, warning — each with on-* foreground variants)
- The **typography scale** — Inter (Latin) primary + Noto Sans Tamil/Devanagari fallbacks for V1.5
- The **spacing scale** — 8-point grid, mobile-first
- The **breakpoints** — 4 standard Tailwind breakpoints, all design starts at 360px
- The **elevation system** — 4 levels mapped to Material's M3 elevation tokens
- The **motion system** — 3 duration tokens, Material default easings
- The **theming flow** — SCSS tokens → Material M3 theme + Tailwind `theme.extend` → both produce visually identical output
- The **dark mode plan** — V1.5 deferred; structure already supports it via `prefers-color-scheme`
- The **accessibility commitments** — WCAG 2.2 AA contrast ratios on every semantic pair

§5A does NOT lock: component-specific SCSS overrides (those live with the component per §3), wireframe/mockup deliverables (those are §5B), or the i18n font loading strategy (that's §16).

### B. Color tokens (semantic, not literal)

All tokens are CSS custom properties, defined in `design-system/_tokens.scss` and re-exported as Tailwind theme values via `_tailwind-bridge.scss`. Hex values are V1; V1.5 may refine per seller feedback without renaming tokens.

| Token | V1 hex | Foreground pair | Purpose |
|---|---|---|---|
| `--mee-color-primary` | `#F26B23` | `--mee-color-on-primary: #FFFFFF` | Warm orange — saffron-leaning, sells Indian-marketplace feel. Primary CTAs, brand accents, active states |
| `--mee-color-secondary` | `#1E40AF` | `--mee-color-on-secondary: #FFFFFF` | Deep blue — trust + clarity. Used for pricing breakdowns, legal copy, secondary CTAs |
| `--mee-color-surface` | `#FFFFFF` | `--mee-color-on-surface: #1F2937` | Card / dialog / menu background; near-black text |
| `--mee-color-surface-variant` | `#F9FAFB` | `--mee-color-on-surface-variant: #4B5563` | Subtle background variation (alternating rows, disabled states) |
| `--mee-color-bg` | `#FFFFFF` | (uses `--mee-color-on-surface`) | App-shell background |
| `--mee-color-bg-elevated` | `#FFFFFF` | (uses `--mee-color-on-surface`) | Elevated surfaces (cards on the bg) — shadow conveys depth, not color in V1 |
| `--mee-color-error` | `#DC2626` | `--mee-color-on-error: #FFFFFF` | Validation errors, destructive confirms, negative margin |
| `--mee-color-success` | `#16A34A` | `--mee-color-on-success: #FFFFFF` | Positive margin, image-precheck pass, "Saved" indicator |
| `--mee-color-warning` | `#D97706` | `--mee-color-on-warning: #FFFFFF` | Rate-limit notifications, autofill confidence flags |
| `--mee-color-info` | `#2563EB` | `--mee-color-on-info: #FFFFFF` | Tips, V1.5 upsell banners |
| `--mee-color-outline` | `#D1D5DB` | — | Border tone for inputs, cards, dividers |

**Contrast ratios (WCAG 2.2 AA — every semantic pair tested):**
- on-primary on primary: 4.8:1 (passes AA Large; AAA Large)
- on-secondary on secondary: 8.6:1 (AAA)
- on-surface on surface: 12.6:1 (AAA)
- on-error on error: 4.7:1 (AA Large)
- on-success on success: 4.9:1 (AA Large)

A `vitest` test in `design-system/_tokens.spec.ts` asserts every pair meets ≥4.5:1 (AA normal text). CI fails if a future change drops a pair below.

### C. Typography scale

```scss
// design-system/_typography.scss
$mee-font-family-base: 'Inter', system-ui, -apple-system, sans-serif;
$mee-font-family-tamil: 'Noto Sans Tamil', $mee-font-family-base;        // V1.5
$mee-font-family-hindi: 'Noto Sans Devanagari', $mee-font-family-base;  // V1.5
```

| Token | px | line-height | weight | Use |
|---|---|---|---|---|
| `--mee-text-xs` | 12 | 1.4 | 400 | Form helper text, secondary metadata |
| `--mee-text-sm` | 14 | 1.4 | 400 | Body small, table cells, captions |
| `--mee-text-base` | 16 | 1.5 | 400 | Body text default — minimum mobile-readable size |
| `--mee-text-lg` | 18 | 1.4 | 500 | Subheadings, emphasis |
| `--mee-text-xl` | 20 | 1.3 | 600 | Section titles |
| `--mee-text-2xl` | 24 | 1.3 | 600 | Page titles |
| `--mee-text-3xl` | 30 | 1.2 | 700 | Hero headings (landing) |
| `--mee-text-4xl` | 36 | 1.2 | 700 | Largest — reserved for marketing hero |

V1 uses Inter for English. V1.5 swap loads the appropriate Noto font lazily based on `TranslocoService.getActiveLang()` — the font load is deferred (via `font-display: swap`) so first paint never blocks on font.

### D. Spacing scale (8-point grid)

```scss
$mee-space-0: 0;
$mee-space-1: 4px;
$mee-space-2: 8px;
$mee-space-3: 12px;
$mee-space-4: 16px;
$mee-space-5: 24px;
$mee-space-6: 32px;
$mee-space-7: 48px;
$mee-space-8: 64px;
```

Maps 1:1 to Tailwind's `spacing` scale (`p-1` = 4px, `p-4` = 16px, etc.). Component spec patterns:
- Touch target minimum: 44 × 44px (per WCAG 2.5.5 + Material guideline)
- Card padding: `--mee-space-4` (16px) mobile, `--mee-space-5` (24px) tablet+
- Section gap: `--mee-space-6` (32px) mobile, `--mee-space-7` (48px) desktop
- Inline gap between tags/chips: `--mee-space-2` (8px)

### E. Breakpoints (mobile-first)

| Token | Width | Tailwind | Use |
|---|---|---|---|
| (base) | 0+ | (default) | **360px baseline** — every component designed here first |
| `sm` | 640+ | `sm:` | Larger phones, small tablets |
| `md` | 768+ | `md:` | Tablets portrait |
| `lg` | 1024+ | `lg:` | Tablets landscape, small laptops |
| `xl` | 1280+ | `xl:` | Desktops |

**Mobile-first discipline:** every component spec lists its 360px layout first, then progressive enhancement for larger breakpoints. Tirupur sellers on low-end Android are the primary target (per `VALIDATED_PAIN_POINTS.md §5`).

### F. Elevation system

4 levels mapped to Material M3 elevation tokens:

| Token | Material level | Shadow CSS | Use |
|---|---|---|---|
| `--mee-elevation-0` | M3 0 | `none` | Flat (default) |
| `--mee-elevation-1` | M3 1 | `0 1px 2px 0 rgb(0 0 0 / 0.05)` | Cards, list items |
| `--mee-elevation-2` | M3 2 | `0 4px 6px -1px rgb(0 0 0 / 0.1)` | Floating menus, popovers, dropdowns |
| `--mee-elevation-3` | M3 3 | `0 10px 15px -3px rgb(0 0 0 / 0.1)` | Modals, dialogs |

### G. Motion system

3 duration tokens + Material's standard easings:

| Token | Duration | Easing | Use |
|---|---|---|---|
| `--mee-motion-micro` | 100ms | `cubic-bezier(0.4, 0, 0.2, 1)` | Hover/focus transitions, ripples |
| `--mee-motion-standard` | 200ms | `cubic-bezier(0.4, 0, 0.2, 1)` | Default for all UI transitions |
| `--mee-motion-large` | 300ms | `cubic-bezier(0.4, 0, 0.2, 1)` | Modal enter/exit, large state changes |

Specified once here so components don't invent per-component durations. Drives Angular's `BrowserAnimationsModule` defaults.

### H. Theming flow (SCSS → Material + Tailwind)

```
design-system/_tokens.scss
        │  (the SCSS variables — single source of truth)
        ▼
design-system/_theme.scss
        │  @use '@angular/material' as mat;
        │  $theme: mat.define-theme((color: (...), typography: (...), density: (...)));
        │  Material M3 emits CSS custom properties from this theme.
        ▼
design-system/_tailwind-bridge.scss
        │  :root { --mee-color-primary: $primary-hex; ... }  ←  re-publishes tokens as CSS props
        ▼
src/styles.scss
        │  @use 'design-system/theme';   // Material M3 theme
        │  @use 'design-system/tailwind-bridge';
        │  @tailwind base; @tailwind components; @tailwind utilities;
        ▼
tailwind.config.js
        │  theme: { extend: { colors: { primary: 'var(--mee-color-primary)', ... } } }
        ▼
Browser
        │  Material components read CSS custom props (M3 native)
        │  Tailwind classes read the same CSS custom props (via theme.extend)
        ▼
Visual output is byte-identical across Material primitives and Tailwind utility classes.
```

**Discipline rule:** if a component needs a color, spacing, or typography value:
1. Tailwind class first (`bg-primary text-on-primary p-4 text-lg`)
2. Material directive next (`color="primary"`, `appearance="outline"`)
3. Component SCSS with `@use 'design-system/tokens' as tokens` last — only for what Tailwind/Material can't express
4. Inline `style="..."` NEVER

### I. Dark mode (V1.5 deferred, structure-ready)

V1 ships light-mode only. The structure already supports dark mode:

```scss
// design-system/_tokens.scss
:root {
  --mee-color-surface: #FFFFFF;
  --mee-color-on-surface: #1F2937;
  // ... all tokens
}

@media (prefers-color-scheme: dark) {
  :root {
    --mee-color-surface: #1F2937;
    --mee-color-on-surface: #F9FAFB;
    // ... inverted tokens
  }
}
```

V1.5 adds the `@media` block + the inverted token values. **Zero component code changes** — every component already reads via custom property. A user-toggle (override `prefers-color-scheme`) is V2.

### J. Accessibility commitments

§5A is the design-system anchor for §19's WCAG 2.2 AA target:
- All semantic color pairs ≥4.5:1 contrast (B above)
- Focus indicator: 2px solid `--mee-color-primary` outline + 2px offset (Material's `cdk-focus-visible` selector)
- Touch targets ≥44 × 44px on every interactive element
- Reduced-motion respect: `@media (prefers-reduced-motion: reduce)` block in `_motion.scss` disables transitions (Material respects this natively)
- Font scaling: all `rem`-based; user can zoom to 200% without horizontal scroll on 360px baseline

### K. What §5A does NOT cover

- Per-component visual mockups (those are §5B wireframe artefacts)
- Icon library selection (Material Symbols inline — no separate icon dep per §6)
- Loading skeleton screens (component-specific; per-feature §7-§15)
- Animation choreography for the wizard flow (that's §11 catalog-form spec)
- The TS-mirror codegen for V1.5 (mentioned in §3.C.3; implementation is V1.5 work)

§5A says **the visual identity**; component-builder + ui-styler specialists consult this for every styling decision.

---

## Section 5B — Wireframe & Mockup Methodology

STATUS: LOCKED (2026-06-05, founder ratification as-is; coordinator depth call: process-artifact section, already substantial — 3-stage methodology + storage convention + per-route deliverable list. Drill into per-route specifics later if needed.)

This section locks how wireframes and mockups are authored, reviewed, and converted to code. The methodology has three stages — **low-fidelity wireframes** (decision artifacts), **high-fidelity mockups** (handoff artifacts), **clickable prototype** (validation artifact).

### Stage 1 — Low-fidelity wireframes (Excalidraw or pen-and-paper)

For each of the 10 V1 routes:
- 360-width mobile frame (primary canvas)
- Component blocks labelled (header, body, CTA, list)
- State variations: empty, loading, populated, error
- Annotations: which Material primitive, which Tailwind utility, which validator
- Stored at: `docs/03-wireframes/<route-name>/wireframe.png` (or .excalidraw)

Lo-fi wireframes are decision artifacts — they exist to settle layout and information hierarchy questions BEFORE any pixel-pushing. The founder reviews and locks the wireframe before mockup work starts.

### Stage 2 — High-fidelity mockups (Figma or Penpot)

For each route — at three breakpoints (360 mobile, 768 tablet, 1280 desktop):
- Material components rendered with the locked design tokens (§5A)
- Tailwind utility classes annotated in component labels
- States: empty, loading, populated, error, offline
- Accessibility annotations: focus order, ARIA roles, color contrast ratios
- Stored at: `docs/03-wireframes/<route-name>/mockup-{breakpoint}.png` (export from Figma)

Hi-fi mockups are the handoff artifact — the component builder specialist consumes them, the styler specialist matches them. The founder reviews and locks each mockup before code lands.

### Stage 3 — Clickable prototype (Figma prototype or Storybook)

For the end-to-end seller journey (V1 §3):
- Click-through from `/` → `/signup` → OTP → `/dashboard` → `/catalogs/new` → ... → `/catalogs/:id/export`
- Used for: founder seller-time-trial test (V1 §8 acceptance: "<10 min for first-time user")
- Stored at: Figma project link recorded in `docs/03-wireframes/README.md`

The prototype is a validation artifact — it lets us measure the time-to-export pain reduction before any code ships. A first-time seller in Tirupur should complete the prototype in under 10 minutes; if not, the wireframe goes back to Stage 1.

### Where wireframes/mockups live in source control

`docs/03-wireframes/` exists in the repo. Each route gets a subfolder. The Figma project is the authoritative source; PNG exports + a `notes.md` per route live in the repo so future Claude sessions can read them without Figma access.

### Designer brief (post FE-D9, 2026-06-05)

`docs/03-wireframes/DESIGNER_BRIEF.md` is the **founder-handoff brief** for engaging an external visual designer. It is self-contained — a designer can produce the full deliverable set without reading the engineering architecture. The brief contains: product context, target user, brand positioning, anti-references (what we don't want to look like), deliverables list (color/typography/iconography/component-visual-language/3 hero mockups/microcopy tone), technical constraints, reference inspirations, engagement format options, timeline, integration protocol, and Q&A routing.

When the designer's deliverables land, the coordinator updates §5A values from those artefacts (replacing the FE-D9 placeholders), flips §5A status from PARTIAL LOCK → FULL LOCK, and dispatches `meesell-angular-ui-styler` with the ratified tokens + Figma references.

---

## Section 6 — Third-Party Tool Selection

STATUS: LOCKED (2026-06-05, founder ratification with no revisions — 14 runtime + 4 dev-only packages, all MIT/Apache-2.0, ~165 KB initial bundle vs 180 KB budget. Founder discipline ratified: NO specialist dispatch until the full FRONTEND_ARCHITECTURE.md is locked end-to-end.)

### A. What §6 establishes

§6 is the **dependency contract**. It locks the V1 third-party library set with rationale, bundle cost (gzipped, post-tree-shake estimate), license, and the alternative considered. It also locks the **introduction policy** — what process a specialist follows if they need a dep that isn't here. Builders cannot introduce a new dependency without amending this section via founder-reviewed turn.

The picks honour the budget targets in §19 (≤180 KB initial bundle, ≤80 KB per route, ≤120 KB exception for catalog-form). Every locked dep below has a bundle column so we can sum it against the budget at any time.

### B. Locked picks (14 packages)

| # | Concern | Pick | Bundle (gzip) | License | Why |
|---|---|---|---|---|---|
| 1 | UI primitives + a11y | `@angular/material` + `@angular/cdk` | ~95 KB tree-shaken | MIT | Material 3 design-token-native; CDK virtual scroll + drag-drop + a11y; only library where MeeSell needs all four families (forms, dialogs, snackbars, autocomplete). Used by 8 of 10 features |
| 2 | Styling utilities | `tailwindcss` | 0 KB runtime (PostCSS purges unused) | MIT | Per Decision 11; layout + spacing + breakpoints; aligns with design-system tokens (§5A). JIT mode + content scan keeps prod CSS small (~10-15 KB after purge) |
| 3 | Internationalisation | `@jsverse/transloco` | ~12 KB | MIT | Runtime locale swap (V1.5 Tamil/Hindi), lazy translation file loading per feature scope. Built-in `@angular/i18n` rejected: requires per-locale rebuild — would force separate prod build artifacts for en, ta, hi which breaks K3s single-image deploy |
| 4 | HTTP client | `@angular/common/http` (native) | included in Angular | MIT | Native `HttpClient` + `provideHttpClient(withInterceptors(...))` per CLAUDE.md Decision 14; no axios. Wrapped by `core/api/ApiClient` (per §3.C.1) |
| 5 | Form library | `@angular/forms` (Reactive) | included in Angular | MIT | Native Reactive Forms. Signal Forms (Angular 20+) is candidate for V2 |
| 6 | OTP input | `ng-otp-input` | ~6 KB | MIT | Reactive Forms-compatible (FormControl + FormControlName), paste-aware for SMS auto-fill (`autocomplete="one-time-code"`), Angular 18+ tested. Used only in `features/account/components/otp-verify/` (post 2026-06-05B merger) |
| 7 | Image compression | `ngx-image-compress` | ~10 KB | MIT | Client-side compress before upload — **critical** for 2G/3G Tirupur (10 MB raw → ~1 MB pre-upload, ~85% smaller). Reduces backend image pre-check queue depth too. Used only in `features/images/` |
| 8 | Charts | `chart.js` + `ng2-charts` | ~30 KB tree-shaken | MIT | P&L breakdown rendering. Only 2 chart variants needed (horizontal bar + waterfall). ApexCharts (611 KB) + Highcharts (commercial license) explicitly rejected. Used only in `features/pricing/pricing-chart/` |
| 9 | Service worker / PWA | `@angular/service-worker` (native ngsw) | included | MIT | Aligns with backend cache TTLs via `ngsw-config.json` (per §16). Configured via `@angular/pwa` schematic at scaffold time |
| 10 | State (shared) | `rxjs` (`BehaviorSubject`) | included | Apache-2.0 | Per Decision 10; no NgRx, no Zustand, no NGXS. Used in `core/auth/AuthService` + `core/services/NetworkService` + feature state services |
| 11 | State (local reactive) | Angular signals (native) | included | MIT | Per Decision 10; `signal()` + `computed()` for component-local state. Default. RxJS only when bridging async sources |
| 12 | Testing — unit/component | `vitest` + `@analogjs/vitest-angular` + `@testing-library/angular` + `jsdom` | dev-only | MIT | Angular CLI's new default (replaces Karma + Jasmine). Faster cold start, better mocking, ESM-native. Aligns with §19 test pyramid |
| 13 | Testing — e2e | `@playwright/test` | dev-only | Apache-2.0 | Mobile emulation built-in (Pixel 5 + Moto G Power profiles for Tirupur devices). Network throttling for 3G. Visual snapshots for V1.5 regression |
| 14 | Linter / formatter | `@angular-eslint/*` + `eslint` + `prettier` + `husky` (pre-commit) | dev-only | MIT | Standard. Husky pre-commit runs eslint + prettier + vitest --changed |

**Total estimated runtime bundle (gzipped):** ~165 KB before app code. Initial bundle budget is 180 KB — leaves ~15 KB for the app shell + AppComponent + router config. Per-route lazy chunks share the deps, so feature chunks only carry their own component code. Healthy.

**Locked dep count: 14 runtime + 4 dev-only.** This is intentionally small. Every dep added later widens the bundle, the security audit surface, and the upgrade-treadmill cost.

### C. Considered and rejected (8 alternatives)

| Concern | Rejected | Why rejected |
|---|---|---|
| Form library | React Hook Form + Zod | Not Angular; locked out by Decision 9 |
| State | NgRx | Per Decision 10 — boilerplate cost not justified for V1 |
| State | NGXS | Same as NgRx |
| Icons | Heroicons standalone bundle | Material already ships an icon font + we'll use Material Symbols inline. Adding Heroicons doubles icon surface |
| Charts | ApexCharts | 611 KB core bundle vs Chart.js 30 KB; MeeSell uses only 2 chart variants |
| Charts | Highcharts | Commercial license (would block GitLab CI build); bundle larger than Chart.js |
| HTTP | axios | Native HttpClient + interceptors handle everything; axios is a second framework |
| i18n | `@angular/i18n` built-in | No runtime locale swap; V1.5 Tamil/Hindi swap would force a rebuild + new build artifact per locale — breaks single-K3s-image deploy |
| File upload | `ngx-awesome-uploader` | Too broad — cropping, image lightbox, multi-language file picker etc. are not in V1 scope; build narrow drag-drop component on CDK instead |
| Date library | `date-fns` / `dayjs` / `luxon` | V1 has no complex date math. Native `Intl.DateTimeFormat` + the `RelativeTimePipe` (custom, 30 lines) suffice. If V1.5 adds analytics with timezone math, revisit |

### D. Introduction policy (how to add a new dep)

When a specialist proposes a new dependency mid-construction:

1. **Open a discussion in STATUS_FRONTEND.md** — name the dep, the concern it solves, the alternative considered, the bundle cost, the license
2. **Coordinator reviews** — is there a native solution? Is the dep on the rejected list? Does it duplicate an existing pick?
3. **If sane:** coordinator drafts a proposed amendment to §6.B (add a row) and surfaces to founder
4. **Founder ratifies or rejects** in their next review turn
5. **On ratify:** §6.B updated, lock note records the date + rationale; specialist proceeds
6. **On reject:** specialist proceeds without the dep (custom-builds or descopes)

**NEVER auto-install a dep.** Even a "tiny utility" widens the security audit surface and the upgrade-treadmill cost. The 14-package floor is defended on purpose.

### E. Bundle budget tie-in

Every dep in §6.B carries a bundle column. Specialists must NOT exceed the §19 budgets:
- **Initial bundle** (root chunk): ≤180 KB gzip. Currently committed: ~165 KB from deps + ~15 KB app shell. **At-capacity.**
- **Per-route lazy chunk**: ≤80 KB gzip. Catalog-form exception: ≤120 KB (because of the 11 primitives + autofill overlay + draft-recovery service).
- **Per-feature CSS**: ≤10 KB gzip (Tailwind purge after build).

Build-time verification: a `vitest` test runs `webpack-bundle-analyzer` JSON output against the budget JSON; CI fails if any chunk exceeds. This test is added during the §20 build-pipeline LOCK.

### F. License + security review

All 14 runtime deps are **MIT or Apache-2.0** — both permissive, both compatible with the closed-source MeeSell product. No GPL/LGPL/AGPL deps. No commercial-use restrictions.

**Quarterly review** (added to §22A risk register implicitly): coordinator runs `npm audit` + `npm outdated` + checks each dep for license change. Any dep that:
- Switches license to GPL-family → must be replaced within 30 days
- Goes unmaintained (>12 months since last release) → flagged for replacement evaluation
- Has a high-severity CVE → patched within 7 days

The V1 list above is the founder-locked baseline. The quarterly review can promote replacements without re-founder-review IF the replacement is license-compatible AND bundle-cost-similar; otherwise back to founder.

### G. What §6 does NOT cover

The exact integration spec for each library (which directive to use, which options to pass) lives in the relevant feature section (§7-§15). The wireframe library or design tooling (Figma, Penpot, Excalidraw) lives in §5B (it's a process artifact, not a runtime dep). The build pipeline (vite, esbuild, ngsw config) lives in §20. The CI lint/test runner configuration lives in §19. Section 6 says **which packages**; the rest say **how they're wired**.

---

## Section 7 — Feature: `account` (V1 Feature 1 + seller profile, post 2026-06-05B merger)

STATUS: LOCKED (2026-06-05, founder ratification as-is; coordinator depth call: spec is already substantial from merger; 4 routes + 7 endpoints + key UX details + defer-to-core list + sub-folder structure all specified inline; per-page deep specs deferred until specialist dispatch when needed.)

This section specifies the account feature — the complete seller-identity surface end-to-end, post merger of the originally separate `auth` and `onboarding` features (per §2 LOCK 2026-06-05).

**Owns 4 routes:**
- `/signup` + `/login` — phone-entry component (`/signup` + `/login` share the same UX with different copy), OTP-verify component
- `/onboarding` — 3-phase seller-profile wizard (Base 9 compliance fields + Country of Origin; Super-category multi-select chips; Conditional compliance extensions per declared super-category)
- `/profile` — edit-existing-profile view (same form layout as onboarding, populated from `GET /seller-profile`)

**Owns 7 endpoints** (via `AccountApiService`):
- `POST /api/v1/auth/otp/send` + `POST /api/v1/auth/otp/verify` — OTP flow
- `POST /api/v1/auth/refresh` + `POST /api/v1/auth/logout` — cross-cutting (called from `core/auth/AuthService`, NOT directly from this feature — the feature exposes UI for logout, the service does the work)
- `GET /api/v1/seller-profile/required-fields` — drives which conditional onboarding steps render
- `GET /api/v1/seller-profile` — read-existing for `/profile` route
- `PUT /api/v1/seller-profile` — write for both onboarding submit and profile edit

**Key UX details:**
- 30-second resend timer on the OTP screen
- 3-OTP-per-hour rate-limit surface (read from 429 response, shown as friendly "Try again in X minutes")
- Post-verify redirect logic: if profile incomplete → `/onboarding`; if complete → `/dashboard`
- Wraps `ng-otp-input` (per §6 pick #6) in `components/otp-verify/` for paste-aware SMS auto-fill
- 3-phase wizard is **fixed-shape** (not data-driven) — distinguishes it from the catalog wizard (§10, formerly §11) which IS data-driven from `templates.schema_jsonb`. The two wizards do NOT share renderer code

**Defers to `core/`:**
- Access-token signal storage + refresh scheduling + bootstrap-on-reload → `core/auth/AuthService` (§4)
- 401 → refresh → replay loop → `core/interceptors/refresh.interceptor.ts` (§4)
- Plan claim reading → `core/auth/plan.guard.ts` (§4)
- Refresh cookie handling → browser + backend (HttpOnly, invisible to JS per FE-D5)

**Cross-feature dependencies:** none in (no feature imports `account/`); out to `shared/` (navbar logout button), `core/` (AuthService).

**Backend peers:** `iam` (otp + refresh + logout endpoints) **and** `customer` (seller-profile CRUD endpoints).

---

## Section 8 — (Reserved — content merged into §7 per 2026-06-05B)

STATUS: MERGED — see §7

Originally this section specified the `onboarding` feature as a separate surface. Per founder ruling 2026-06-05 (recorded in §2 LOCK), the originally-separate `auth` and `onboarding` features were merged into a single `account` feature because the seller journey (phone → OTP → seller profile compliance → dashboard) is structurally one flow with the same actor. Full content for the merged feature lives in §7. This section is preserved as a numbered placeholder so cross-references like "§7-§15 deep specs" in other sections (§17, §22) continue to resolve correctly; future renumbering may close this gap on a separate founder-review turn.

---

## Section 9 — Feature: `dashboard` (V1 Feature 8)

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator additions per FE-D8)

### A. Responsibility

Paginated product list view (`/dashboard`) — the seller's home base after login. Reads `GET /api/v1/products?page=&limit=&status=&q=` (server-paginated, 20 per page default). Status filter chips (draft / exported / live). Debounced name search (300ms). Row click → navigate to `/catalogs/:id/edit`. Per-row soft-delete via `MatMenu` action → `<mee-confirm-dialog>` → `DELETE /api/v1/products/:id`.

### B. Components

- `DashboardComponent` (page) — at `/dashboard`
- `ProductRowComponent` (feature-private, in `components/`) — single row with name + category badge + `<mee-status-badge>` + relative updated time + action menu
- `<mee-empty-state>` from `shared/` — when zero products exist, with CTA "Create your first catalog" → `/catalogs/new`

### C. Service

`DashboardService` — wraps `apiClient.get<PaginatedResponse<Product>>('/products', {...})` and `apiClient.delete('/products/:id')`. Returns `Observable` and a local signal cache for the current page (no global state — paginated reads are always fresh from server per §6.3 backend cache headers).

### D. Performance

- Empty state target: first paint ≤500ms (cache-warm tab, ≤2s cold)
- Populated dashboard with 100 products: ≤500ms TTI per V1 spec §F8
- Debounce: 300ms on search, 0ms on filter chip click

### E. Coordinator depth call

Dashboard is a CRUD list — the spec is the inventory. The deep work happens in the catalog-form spine (§11), not here. Locking with the inventory.

---

## Section 10 — Feature: `smart-picker` (V1 Feature 2)

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator additions per FE-D8)

### A. Responsibility

Description-to-category AI flow. Seller types product description (min 10 chars), submits → backend Gemini suggest returns top-3 candidates. Seller picks a card → creates draft product → routes to `/catalogs/:id/edit`. Fallback: manual browse fallback via `<mee-browse-fallback>` using pg_trgm-backed `GET /categories/browse`.

### B. Components

- `SmartPickerComponent` (page) — at `/catalogs/new`
- `<mee-description-input>` — Reactive Form with min-10-char validator + `<mat-form-field>` outline
- `<mee-category-card>` — single suggestion card showing full path + confidence (percent badge) + sample attribute names, click emits `categorySelected`
- `<mee-browse-fallback>` — manual search by super-category + leaf name (collapsed accordion shown after first failed AI suggest or via "Browse manually" link)

### C. Service

`SmartPickerService`:
- `suggest(description: string): Observable<CategoryCandidate[]>` — calls `GET /categories/suggest?q=<description>`, debounced 500ms
- `browse(query: string, superId?: string): Observable<Category[]>` — calls `GET /categories/browse?q=&super_id=`
- `selectCategory(category: Category, description: string): Observable<Product>` — calls `POST /products` with `{category_id, description}`, returns created draft

### D. Cache leverage

Backend caches Gemini suggest responses by `SHA-256(description)` for 24h (per `MVP_ARCHITECTURE.md §6.3`). Re-typing the same description returns instantly — frontend never knows it was cached. Feature does NOT implement its own cache.

### E. Performance

- Suggest P95 ≤3s per V1 spec §F2
- Description debounce: 500ms (avoid double-fire while typing)
- Cards animate in via Angular `@if` transition with `--mee-motion-standard` (200ms)

### F. Coordinator depth call

Smart picker is the narrowest feature — one form input, three result cards, one fallback widget. Locking the inventory + service contract. Per-card visual mockup deferred to §5B artefacts.

---

## Section 11 — Feature: `catalog-form` (V1 Features 3 + 4) — THE SPINE

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator deep authoring per FE-D8)

### A. Responsibility — the spine

`catalog-form` owns the per-product data-driven wizard at `/catalogs/:id/edit`. It is the **largest, most consequential feature** in V1 — it consumes 6 of the 27 contract endpoints, renders the most component code, owns the 11 primitives, and integrates the autofill overlay, autosave, and draft recovery.

### A.1 — Backend §10 cross-check amendment (2026-06-05, post backend §10 LOCK)

Backend §10 catalog module LOCKED specifies the autosave PATCH contract with an **`X-Autosave: true` header** signal — when present, backend additionally upserts the `product_drafts` row (per `MVP_ARCH §11.6` for crash recovery); when absent, only `products.fields_jsonb` is mutated. The `AutosaveDirective` (shared/, per §5.E.1) MUST set this header on every autosave-triggered PATCH so draft recovery works on browser reload. Manual "Save & Continue" button clicks (per V1 §F3) do NOT set the header — those are explicit submits, not autosaves. The `CatalogFormApiService` PATCH wrapper passes the header through `ApiOptions.headers` per §4.E.

Backend §10 also locks the rate-limit posture: **PATCH is per-IP only (600/h)**, not per-user — so autosave can fire frequently without 429-ing real sellers. Plan guard does NOT participate in PATCH. POST creates have plan guard (100 active products cap) + per-user rate limit (20/h) per §4.E + §4.D.

Error-code mapping for the catalog-form feature (consumed by §4.F ErrorService):
- `catalog.product_not_found` (404) → "This product is no longer available" + route to /dashboard
- `validation.fields.unknown_key` (400) → engineering bug; surface as generic error + traceId
- `validation.<canonical_name>.<constraint>` (422) → resolve via `validation_message_id` from response; render inline on the field per §18 primitive contract
- `customer.profile_incomplete_for_category` (422) on POST → "Complete your seller profile to create this product" + deep link to /onboarding
- `plan.limit_exceeded` (402) on POST → V1 friendly "You've hit the 100-product limit; delete drafts to free space" + deep link to /dashboard
- `rate_limit.exceeded` (429) → "Pausing for a moment, please try again in X seconds" with backend's Retry-After header value

The contract for the wizard renderer + 11 primitives lives in §18 (the renderer is the spine within the spine). §11 lives one layer above — the page-level wiring.

### B. Components

- `CatalogFormComponent` (page) at `/catalogs/:id/edit` — orchestrator
- `WizardRendererComponent` (feature-private, in `wizard-renderer/`) — composes steps + dispatches fields to primitives per §18
- `StepComposerService` (feature-private, in `wizard-renderer/`) — groups schema fields by `step_id`, drops empty steps, sorts per the canonical 13-step order from `MVP §5.6.3`
- `FieldDispatcherComponent` (feature-private, in `wizard-renderer/`) — selects which of 11 primitives to render per field (see §18 for the contract)
- The **11 primitive components** (feature-private, in `primitives/`) — `text-short`, `text-long`, `number`, `number-with-unit`, `currency`, `dropdown-small`, `dropdown-medium`, `dropdown-large`, `dropdown-api`, `image-upload`, `address-group`. Full contract in §18
- `AutofillOverlayComponent` (feature-private, in `autofill-overlay/`) — yellow-highlight accept/reject UI per V1 Feature 4
- `<mee-loading-spinner>` from shared/ during schema fetch + autofill

### C. Services

- `CatalogFormApiService` — wraps `GET /products/:id`, `GET /products/:id/draft`, `PATCH /products/:id`, `POST /products/:id/autofill`
- `CategorySchemaService` (in `core/` per §4 if cross-feature, or feature-private — coordinator decision: feature-private since only catalog-form fetches schemas during the wizard) — wraps `GET /categories/:id/schema`
- `EnumLookupService` (feature-private) — wraps `GET /categories/:id/enum/:field_name?q=` for the `dropdown_api` primitive
- `CatalogFormStateService` (feature-private) — holds product + schema + draft state per route instance via signals
- `DraftRecoveryService` (feature-private) — wraps `GET /products/:id/draft` on component init

### D. Lifecycle (init → autosave → submit)

1. **Init** — `CatalogFormComponent` resolves route param `:id`, calls `CatalogFormApiService.getProduct(id)` + `CategorySchemaService.getSchema(categoryId)` in parallel
2. **Draft recovery** — if browser was reloaded mid-edit, `DraftRecoveryService.getDraft(id)` returns the last autosaved state (per `DATABASE_ARCHITECTURE.md §4.9`); merges into the form
3. **Render** — `WizardRendererComponent` composes steps, dispatches fields. Field values populate from `product.fields`
4. **Autosave** — `[meeAutosave]` directive from shared/ fires `apiClient.patch('/products/:id', formValue)` 10s after last change + on blur
5. **Autofill** — seller clicks "AI fill" button → `apiClient.post('/products/:id/autofill', {})` → response writes to `product.aiSuggestions` → `AutofillOverlayComponent` renders yellow-highlight diff with per-field accept/reject
6. **Validation** — each field validates per its `validation_message` from schema on blur; compulsory fields marked with red asterisk; "Next step" blocked if any compulsory field empty
7. **Submit** — last "Next step" navigates to `/catalogs/:id/images`

### E. Performance constraints

- Schema fetch P95 ≤200ms cold / ≤50ms cache-hit (backend §6.6)
- Autofill P95 ≤5s per V1 §F4
- Autosave debounce: 10s + blur per V1 §F3
- Wizard first paint ≤500ms after schema received per V1 §F3
- Rate limit 50 autofills/h/user — friendly "Pause for X minutes" on 429
- The catalog-form chunk gets a §19 budget exception: ≤120 KB gzip (vs 80 KB other features) because of the 11 primitives + autofill overlay + draft-recovery overhead

### F. Cross-feature dependencies

- Reads `core/auth/AuthService` (token + plan)
- Reads `core/api/ApiClient` (via feature service)
- Reads `core/services/NetworkService` (autosave online check)
- Reads `core/services/ErrorService` (snackbar surfaces)
- Uses `shared/directives/AutosaveDirective`, `shared/components/loading-spinner`, `shared/pipes/inrCurrency`, `shared/pipes/localeLabel`
- Does NOT import any other feature

### G. What §11 defers to §18

The 11-primitive interface contract (`PrimitiveInputs`, `ValueChange`, dispatcher logic, per-primitive behavior) is intentionally NOT here. It lives in §18 because the renderer + primitives is a contract that future V1.5/V2 features might consume (e.g., a bulk-edit screen). §11 specifies the page wiring; §18 specifies the renderer.

### H. Coordinator depth call

This section gets the deepest treatment of any feature spec because:
- It's the spine
- It consumes the most endpoints
- It integrates the most cross-feature dependencies
- A misalignment here ripples into §18 + §5A + every primitive specialist dispatches
Locking with the full §A-§G contract.

---

## Section 12 — Feature: `images` (V1 Feature 5)

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator additions per FE-D8)

### A. Responsibility

4-slot drag-drop uploader at `/catalogs/:id/images`. Slot 1 (front) is compulsory per `DATABASE_ARCHITECTURE.md §2.9`. Client-side compression via `ngx-image-compress` (per §6 pick #7) reduces 10 MB raw → ~1 MB pre-upload. Polls precheck status every 2s. Surfaces 5 checks per image with pass/fail + fix hint.

### B. Components

- `ImageUploaderComponent` (page) at `/catalogs/:id/images`
- `ImageSlotComponent` (feature-private) — single slot with drag-drop zone, preview thumbnail, replace action, slot 1 marked compulsory
- `PrecheckReportComponent` (feature-private) — per-image 5-check list: `is_jpeg`, `color_space === 'RGB'`, `resolution_ok`, `white_bg_ok`, `watermark_pass` (per DB §4.6). Fix hints from i18n `validation_messages` (`image_wrong_color`, `image_too_small`, `image_has_watermark`, `image_not_white_bg`)
- `<mee-loading-spinner>` during processing

### C. Service

`ImagesApiService`:
- `upload(productId, slotIdx, file): Observable<HttpEvent>` — multipart `POST /products/:id/images`, emits progress events for `<mat-progress-bar>`
- `pollImages(productId): Observable<ProductImage[]>` — `GET /products/:id/images` with `interval(2000)` polling, completes when all 4 slots' statuses leave `pending`

### D. Client-side compression

```typescript
// Pseudo-flow inside ImageUploaderComponent.onFileDropped()
const compressed = await ngxImageCompress.compressFile(rawDataUrl, -2, 75, 75);
// 75% quality, 75% size scaling — reduces 10MB JPEG to ~1MB while preserving Meesho's 1500×1500 min
const blob = await fetch(compressed).then(r => r.blob());
return imagesApi.upload(productId, slotIdx, blob).pipe(retryOn503);
```

### E. Performance

- Compression: ~300-500ms per 10MB image on a 2-core Android phone
- Upload over 3G: ~2-5s per ~1MB compressed file
- Precheck pipeline (backend): ≤8s per image
- Total flow per image: ~10-15s on Tirupur 3G
- 4 images parallel via `forkJoin`: total ~20-30s

### F. Cross-feature dependencies

- `apiClient.postMultipart` from `core/api/` with `retryOn503: true` (Look 1 from §4 — GCS hiccups are 503-prone)
- `NetworkService` for offline detection (block upload, queue on reconnect)
- `<mee-confirm-dialog>` from shared/ for replace warning

### G. Block-export gate

Slot 1 must reach `status: 'ready'` AND `precheck_jsonb.watermark_pass === true` before "Next step" enables routing to `/catalogs/:id/preview`. Surfaces deep-link back to fix failed images.

### H. Coordinator depth call

Mid-depth — upload + poll + precheck is well-defined; the 4 components are simple; the only complexity is the compression + retry-on-503 combo, which §6 + §4 already cover.

---

## Section 13 — Feature: `preview` (V1 Feature 6)

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator additions per FE-D8)

### A. Responsibility

Three preview surfaces showing how the product will render on Meesho before publish:
- **Feed thumbnail** — Meesho-style square card with ~30-char title truncation indicator (Meesho mobile cuts ~30 chars)
- **Product detail page** — Meesho-style hero image + title + price + variant section + description
- **Mobile card** — Meesho mobile app card simulation

Tablet/desktop: side-by-side. Mobile: stacked vertically. Read-only — no editing here.

### B. Components

- `PreviewComponent` (page) at `/catalogs/:id/preview`
- `<mee-preview-feed>` (feature-private) — feed thumbnail with title-truncation marker
- `<mee-preview-detail>` (feature-private) — full detail page mock
- `<mee-preview-mobile>` (feature-private) — mobile card simulation
- `<mee-empty-state>` from shared/ when title or slot-1 image is missing, with deep link back to `/catalogs/:id/edit`

### C. Service

`PreviewApiService.getPreview(productId): Observable<PreviewData>` — wraps `GET /products/:id/preview`. Backend returns normalised JSON `{title, price, imageUrls[], firstVariant, fullDescription}`.

### D. Performance

- All three previews render ≤1s per V1 §F6
- Image carousel uses CSS-only swipe on mobile (no JS gesture lib)
- Title truncation: pure CSS `text-overflow: ellipsis` + `max-width` for the 30-char marker

### E. Coordinator depth call

Pure presentation — three layout components reading the same input. Simple. Locking the inventory.

---

## Section 14 — Feature: `pricing` (V1 Feature 7)

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator additions per FE-D8)

### A. Responsibility

P&L calculator at `/catalogs/:id/pricing`. Seller enters MRP + target margin → backend returns commission + GST + seller payout + net margin breakdown. Live slider for MRP adjustment with debounced 100ms local recompute; commit hits backend.

### B. Components

- `PricingComponent` (page) at `/catalogs/:id/pricing`
- `PnLBreakdownComponent` (feature-private) — line items table with `inrCurrency` pipe + red/green margin indication
- `MarginSliderComponent` (feature-private) — `<mat-slider>` for MRP, 100ms local recompute, 500ms commit
- `PricingChartComponent` (feature-private) — chart.js horizontal bar (per §6 pick #8)

### C. Service

`PricingApiService.calculate(productId, mrp, targetPayout): Observable<PricingCalc>` — wraps `POST /products/:id/price-calc`.

### D. Local recompute

First calc snapshots `commission_pct` + `gst_pct`. MarginSlider mirrors formula client-side for instant feedback (no extra API calls during slide); commit on slide-end.

### E. Performance

- Initial calc P95 ≤200ms per V1 §F7
- Slider live update <100ms (local recompute, no network)

### F. Coordinator depth call

Math is the contract; UI is 3 small components. Locking with inventory + local-recompute formula.

---

## Section 15 — Feature: `export` (V1 Feature 9)

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator additions per FE-D8)

### A. Responsibility

XLSX export trigger + download at `/catalogs/:id/export`. Pre-export validation gate. Async backend job triggered, polled to completion, signed URLs surfaced for download.

### B. Components

- `ExportComponent` (page) at `/catalogs/:id/export`
- `ValidationSummaryComponent` (feature-private) — lists missing compulsory fields + non-pass images with deep links back to `/catalogs/:id/edit` and `/catalogs/:id/images`
- `ExportProgressComponent` (feature-private) — polling state machine UI (processing spinner → ready download buttons → failed error + retry)
- `<mee-confirm-dialog>` from shared/ for re-export warning if previous export exists

### C. Service

`ExportApiService`:
- `trigger(productId): Observable<ExportRecord>` — `POST /products/:id/export-xlsx`, returns `{export_id, status: 'processing'}`
- `poll(exportId): Observable<ExportRecord>` — `GET /exports/:id` with `interval(2000)`, completes on `status: 'ready' | 'failed'`

### D. UX states

- **Pre-validation fail** — block "Generate XLSX" button; show ValidationSummary with deep links
- **Pre-validation pass** — show "Generate XLSX" CTA
- **Processing** — show ExportProgress with spinner + estimated time
- **Ready** — show two download buttons (XLSX + image ZIP) with countdown to signed-URL expiry (1h TTL)
- **Failed** — show seller-facing `error_message` (`TemplateNotFoundError`, `MissingComplianceError`, `GCSUploadError`) + retry button. Engineering bugs (round-trip-validation failed) show generic "Something went wrong" + traceId

### E. Performance

- Trigger response immediate (returns `processing`)
- Backend pipeline ≤15s for 1 product + 6 images per V1 §F9
- Frontend poll interval: 2s
- Download via signed URL — no auth header (the URL itself is the auth)

### F. Coordinator depth call

State machine is the main contract. 4 UI states, 1 service with 2 methods. Locking with inventory.

---

## Section 16 — Cross-Cutting Walkthroughs

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator deep authoring per FE-D8 — synthesises rules from §4 + §17 into operational flows)

### A. What §16 establishes

Operational walkthroughs of how cross-cutting concerns flow across features. NOT a new contract — synthesis of contracts from §4 (cross-cutting services), §17 (communication rules), §6.3 (cache TTLs from backend). Specialists consult §16 when implementing a flow that touches more than one feature.

### B. State management decision tree (recap from earlier preview)

```
Is state local to ONE component AND synchronous?
    YES → signal() + computed()
    NO  → continue

Is state derived from async (HTTP, polling, debounced input)?
    YES → RxJS Observable; subscribe via async pipe or toSignal()
    NO  → continue

Is state shared across 2+ features?
    YES → BehaviorSubject in core/services/ (providedIn: 'root')
    NO  → BehaviorSubject in features/<feature>/<feature>-state.service.ts
```

### C. i18n flow

```
Backend schema fetch                     App-shell UI string
       │                                       │
       ▼                                       ▼
{display_label: {en, ta?, hi?}}        Transloco translation file en.json
       │                                       │
       ▼                                       ▼
LocaleLabelPipe (shared/)              {{ 'dashboard.empty.cta' | transloco }}
       │                                       │
       ▼                                       ▼
       Renders active locale (TranslocoService.getActiveLang())
       │
       └─ LocaleInterceptor (core/) sets Accept-Language on every request
```

V1 ships `en.json` populated. `ta.json` + `hi.json` are empty stubs (V1.5 fills them without code change).

### D. HTTP caching flow

```
Feature → ApiClient.get('/categories/:id/schema')
       │
       ▼
Browser HTTP cache (no in-app layer per §4.E.2)
       │  honours Cache-Control: max-age=86400, stale-while-revalidate=3600
       │  honours ETag (sends If-None-Match on revalidation)
       ▼
If cache miss → backend → Valkey DB 3 → PostgreSQL (per backend §6.3)
```

Frontend never writes its own cache. Caching is HTTP-layer only — leverages the backend's `MVP §6.3` Cache-Control headers transparently.

### E. Offline UX

```
NetworkService.online() signal
       │
       ├──→ <mee-offline-banner> visible at app shell when false
       │
       └──→ AutosaveDirective queues PATCH calls when false
            replays queue when transition false → true (subscribed via toObservable)
```

V1 offline = no API calls work, autosave queues. V1.5 may add IndexedDB-backed offline catalog edit (deferred — adds complexity, not validated demand).

### F. Plan gating flow

```
Login OTP verify → backend issues JWT with {sub, exp, plan: 'free' | 'pro'}
       │
       ▼
AuthService.setAccess() extracts claims into signals
       │
       ▼
plan signal reactive across the app
       │
       ├──→ PlanGuard on plan-gated routes (V1: none; V1.5: bulk-ops, advanced exports)
       │
       └──→ UI banner / upsell CTA reads plan() signal (V1: none; V1.5: dashboard upsell)
```

V1 ships everything as `free` tier. Plan-gating infrastructure is in place per §4.D so V1.5 only adds the route guard line.

### G. Error surface flow

```
Backend 4xx/5xx
       │
       ▼
HTTP request through interceptor chain
       │
       ▼
ErrorInterceptor normalises HttpErrorResponse → ApiError
       │
       ├──→ displayMessage resolved from i18n bundle (locale-aware)
       │
       ├──→ ErrorService.showError(apiError) → MatSnackBar (6s, swipe-dismiss)
       │       │
       │       └──→ "Details" action button shows traceId dialog if present
       │
       └──→ ApiError re-thrown so feature can also catch (e.g., 422 validation handled per-feature)
```

### H. Service worker flow

```
@angular/service-worker (ngsw) loaded via app.config.ts provideServiceWorker()
       │
       ▼
ngsw-config.json (in frontend/ root) declares:
       │
       ├──→ assetGroups: 'prefetch' for index.html + root chunks
       │
       ├──→ assetGroups: 'lazy' for feature chunks (cached after first use)
       │
       └──→ dataGroups: 'freshness' for /api/v1/categories/:id/schema (24h, ETag respected)
            dataGroups: 'never' for /api/v1/auth/*, /api/v1/products/*, /api/v1/exports/*

SwUpdate.versionUpdates$ in app.component.ts
       │
       ▼
On new deploy detected: show "New version available" snackbar + reload action
```

### I. Coordinator depth call

These flows synthesise contracts already locked in §4 + §5A + §6 + §17. Locking the synthesis. Per-flow deep specs (e.g., the IndexedDB offline edit V1.5 plan) deferred.

This section is the **single source of truth for cross-cutting concerns** as they participate across all ten features: state management (signals vs RxJS rule per Decision 10), i18n (Transloco scope + locale-map resolution), HTTP caching (browser cache + ETag), service worker (PWA precache + runtime strategies), autosave (10s + blur per V1 §F3), offline UX (`NetworkService` + offline banner + queued autosave retry), plan gating (`PlanGuard` + V1.5 upsell banner), and error handling (snackbar surface + 401 redirect + 429 friendly retry). Each concern is described once here, then referenced from each feature section rather than repeated.

### State management decision tree (preview)

```
Is the state local to one component and synchronous?
    YES → signal() + computed()
    NO  → continue

Is it derived from an async source (HTTP, SSE, debounced input)?
    YES → RxJS Observable; subscribe via async pipe or toSignal()
    NO  → continue

Is it shared across two or more features?
    YES → BehaviorSubject in a service in core/ (providedIn: 'root')
    NO  → BehaviorSubject in a service in features/<feature>/
```

### i18n flow (preview)

```
Backend schema fetch       App-shell UI string
       │                          │
       ▼                          ▼
{display_label: {en, ta, hi}}    Transloco translation file
       │                          │
       ▼                          ▼
LocaleLabelPipe              {{ 'dashboard.empty.cta' | transloco }}
       │                          │
       ▼                          ▼
       Renders active locale (default: en)
```

---

## Section 17 — Service-Component Communication Rules

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator authoring per FE-D8)

This section defines the contract between features and within features: what `catalog-form` IS allowed to do (call `core/api/ApiClient`, call its own `CatalogFormService`, inject `core/auth/AuthService`), what it is NOT allowed to do (import `pricing/PricingService`, import `dashboard/DashboardComponent`). The symmetric rule applies to every feature pair. It also specifies how this discipline survives Phase 2 Module Federation — feature-scoped services become remote-scoped services without changing call sites. This is the rule that keeps the features-first layout extractable rather than tangled.

### The 6 communication rules (preview)

1. **A feature MUST NOT import another feature's component or service.** Period. Cross-feature data flows through `core/` services or through the router.
2. **A feature MUST NOT read another feature's state.** If two features need shared state, that state moves to a `core/` service.
3. **`core/` MAY be imported by any feature.** It is the lingua franca.
4. **`shared/` MAY be imported by any feature.** It is stateless presentation.
5. **`design-system/` IS NEVER imported by TypeScript** — it is consumed only at SCSS compile time via `@use`. The design system has no runtime presence.
6. **The router IS the cross-feature communication channel.** If feature A needs to hand data to feature B, A navigates to B with route params (e.g., `/catalogs/:id/edit?from=picker`); B reads route params and proceeds. No global state bus.

---

## Section 18 — The 11 Primitives + Form Renderer

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator deep authoring per FE-D8 — the contract for the spine-within-the-spine)

### A. What §18 establishes

The interface contract for the **11 form primitives** + the **wizard renderer** that consumes them. This is the single most consequential contract after §4 — it determines how every catalog form for all 3,772 Meesho categories renders. Per §0.D: there is NO category-specific component anywhere. The renderer + 11 primitives + step composer covers the entire corpus.

### B. The wizard renderer

```typescript
// features/catalog-form/wizard-renderer/wizard-renderer.component.ts
@Component({
  selector: 'mee-wizard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <mat-stepper #stepper linear>
      @for (step of steps(); track step.id) {
        <mat-step [label]="step.title | localeLabel">
          @for (field of step.fields; track field.canonicalName) {
            <mee-field-dispatcher
              [schema]="field"
              [value]="model()[field.canonicalName]"
              [aiSuggestion]="aiSuggestions()[field.canonicalName] ?? null"
              [disabled]="false"
              (valueChange)="patch($event)"
            />
          }
        </mat-step>
      }
    </mat-stepper>
  `
})
export class WizardRendererComponent {
  readonly steps = input.required<WizardStep[]>();
  readonly model = input.required<Record<string, unknown>>();
  readonly aiSuggestions = input<Record<string, AiSuggestion>>({});
  readonly valueChange = output<ValueChange>();

  patch(change: ValueChange): void { this.valueChange.emit(change); }
}
```

### C. The dispatcher

```typescript
// features/catalog-form/wizard-renderer/field-dispatcher.component.ts
@Component({
  selector: 'mee-field-dispatcher',
  standalone: true,
  imports: [TextShortPrimitive, TextLongPrimitive, /* ... all 11 */],
  template: `
    @switch (schema().primitive) {
      @case ('text_short')          { <mee-text-short  [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('text_long')           { <mee-text-long   [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('number')              { <mee-number      [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('number_with_unit')    { <mee-number-unit [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('currency')            { <mee-currency    [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('dropdown_small')      { <mee-dropdown-small  [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('dropdown_medium')     { <mee-dropdown-medium [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('dropdown_large')      { <mee-dropdown-large  [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('dropdown_api_search') { <mee-dropdown-api    [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('image_upload')        { <mee-image-upload    [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
      @case ('address_group')       { <mee-address-group   [schema]="schema()" [value]="value()" [aiSuggestion]="aiSuggestion()" (valueChange)="onChange($event)" /> }
    }
  `
})
export class FieldDispatcherComponent { /* ... */ }
```

### D. The primitive contract (shared by all 11)

```typescript
// features/catalog-form/primitives/primitive.contract.ts
export interface PrimitiveInputs {
  readonly schema: FieldSchema;            // per @core/models/field-schema.model.ts (§4.I)
  readonly value: unknown;                 // current value from products.fields_jsonb
  readonly aiSuggestion: AiSuggestion | null;  // from products.ai_suggestions_jsonb
  readonly disabled: boolean;
}

export interface ValueChange {
  readonly canonicalName: string;
  readonly value: unknown;                 // primitive-specific type at runtime
  readonly source: 'seller' | 'ai-accept';
}
```

Every primitive component:
1. Takes the 4 inputs (`schema`, `value`, `aiSuggestion`, `disabled`) via signal inputs
2. Implements `ControlValueAccessor` so it slots into Reactive Forms
3. Emits `ValueChange` on commit (typed `source` distinguishes seller edits from AI accepts)
4. Renders inside an autofill-overlay wrapper when `schema.marker === 'compulsory' && aiSuggestion !== null && !aiSuggestion.accepted`
5. Resolves `schema.displayLabel`, `schema.displayHelp`, `schema.displayPlaceholder`, `schema.validationMessage` via `localeLabel` pipe

### E. The 11 primitives — one-line spec each

| Primitive | Material backbone | Special behavior |
|---|---|---|
| `<mee-text-short>` | `<mat-form-field>` + `<input matInput>` | Standard text; `maxLength` from schema |
| `<mee-text-long>` | `<mat-form-field>` + `<textarea matInput>` | Auto-grow; `maxLength` counter |
| `<mee-number>` | `<mat-form-field>` + `<input type="number">` | `min`/`max` from schema |
| `<mee-number-unit>` | `<mat-form-field>` with suffix `<span>` | Shows `schema.displayUnitLabel` as suffix |
| `<mee-currency>` | `<mat-form-field>` with prefix `<span>₹</span>` | Renders `inrCurrency` on blur |
| `<mee-dropdown-small>` | `<mat-radio-group>` | ≤20 entries; all visible |
| `<mee-dropdown-medium>` | `<mat-autocomplete>` | 21-100 entries; in-memory filter |
| `<mee-dropdown-large>` | `<mat-autocomplete>` + `<cdk-virtual-scroll-viewport>` | 101-500 entries; virtual scroll per §6 pick #1 CDK |
| `<mee-dropdown-api>` | `<mat-autocomplete>` + RxJS `debounceTime + switchMap` | >500 entries; debounced 300ms server-side search via `EnumLookupService` |
| `<mee-image-upload>` | Placeholder link to `/catalogs/:id/images` | Schema-level reference only; actual upload is `features/images/` per §12 |
| `<mee-address-group>` | Composite — 1 textarea + 2 inputs + pincode validator | Used only for collapsed-compliance template (Eye-Serum, 1 of 3,772 categories) |

### F. Wizard step composition

`StepComposerService` (per §11 list):
```typescript
compose(schema: FieldSchema[]): WizardStep[] {
  const grouped = groupBy(schema, f => f.stepId);
  return STEP_ORDER
    .filter(stepId => grouped[stepId]?.length > 0)  // drop empty
    .map(stepId => ({
      id: stepId,
      title: STEP_TITLES[stepId],
      fields: grouped[stepId],
    }));
}

const STEP_ORDER: StepId[] = [
  'basics', 'pricing', 'inventory', 'sizing', 'materials', 'food',
  'tech_specs', 'safety', 'warranty', 'compliance', 'photos',
  'description', 'advanced',
];

const STEP_TITLES: Record<StepId, LocaleMap> = {
  basics:      { en: 'Tell us about your product' },
  pricing:     { en: 'Set your price' },
  inventory:   { en: 'Stock and weight' },
  sizing:      { en: 'Sizing' },
  materials:   { en: 'Materials and pattern' },
  food:        { en: 'Food details' },
  tech_specs:  { en: 'Specifications' },
  safety:      { en: 'Safety information' },
  warranty:    { en: 'Warranty' },
  compliance:  { en: 'Your seller details' },
  photos:      { en: 'Add photos' },
  description: { en: 'Description (optional)' },
  advanced:    { en: 'Advanced fields' },
};
```

### G. Autofill overlay

`AutofillOverlayComponent` wraps every **compulsory** field that has a pending AI suggestion:
- Yellow border around the field (`--mee-color-warning` 1px)
- Yellow background tint on the input
- Below the input: "AI suggests: <suggested value>" with Accept (✓) and Reject (✗) buttons
- Accept → field receives `valueChange` with `source: 'ai-accept'`, overlay clears
- Reject → backend `PATCH /products/:id` with `ai_suggestions_jsonb.{field}.rejected_reason: 'user_rejected'`, overlay clears
- Edit-in-place (typing in the field) → AI suggestion cleared, overlay disappears

### H. Coordinator depth call

This is the deepest section after §4 because it's the single contract that determines how every catalog form renders. Locking with full renderer + dispatcher + primitive contract + step composer + autofill overlay. Per-primitive deep specs deferred to specialist dispatch — the contract is enough to scaffold.

This section locks the exact interface contract for the 11 primitive components and the field dispatcher. Each primitive consumes the same input shape (a `FieldSchema` object), emits the same output shape (a `ValueChange` event), and implements `ControlValueAccessor` so it slots into Reactive Forms natively. The dispatcher selects which primitive to render based on `schema.primitive`. The wizard renderer composes steps via `WizardStepComposerService`. The autofill overlay is layered on top of every compulsory field via `AutofillOverlayComponent` wrapper. This is the **single backend-side contract** mirror in the frontend — the `templates.schema_jsonb.fields[]` shape locked at `MVP §5.6.1` and `BACKEND_ARCHITECTURE §5A` is the input here.

### Primitive interface (preview)

```typescript
// frontend/src/app/features/catalog-form/primitives/primitive.contract.ts
export interface PrimitiveInputs {
  readonly schema: FieldSchema;          // The locked MVP §5.6.1 shape
  readonly value: unknown;               // Current value from products.fields_jsonb
  readonly aiSuggestion: AiSuggestion | null;  // From products.ai_suggestions_jsonb
  readonly disabled: boolean;
}

export interface ValueChange {
  readonly canonicalName: string;
  readonly value: unknown;
  readonly source: 'seller' | 'ai-accept';
}
```

Every primitive component takes `PrimitiveInputs` as `@Input`s (signal inputs in Angular 18) and emits `ValueChange`. The dispatcher passes these through; the autosave directive listens to the renderer's aggregate output and PATCHes the backend.

---

## Section 19 — Test Strategy & Performance Budget

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator authoring per FE-D8 — tables already drafted in skeleton; expanded with CI gates and budget verification mechanism)

This section specifies the test pyramid and the performance budget — both as construction invariants.

### Vitest + Angular component spec note (post service-builder dispatch 2026-06-05)

The service-builder dispatch surfaced a config nuance: Vitest in zoneless Angular mode does NOT natively resolve `styleUrl` references in component decorators during test runs. This blocks component spec files (e.g., `app.component.spec.ts`) from loading. **The component-builder dispatch MUST install `@analogjs/vite-plugin-angular`** as a dev dependency and wire it into `vitest.config.ts` to enable `styleUrl` resolution. This is a one-time setup; once wired, all subsequent component spec files render correctly. The service-builder noted this hand-off; component-builder applies it.

### Test pyramid (preview)

| Layer | Tool | Coverage target | Run on |
|---|---|---|---|
| Unit (services, pipes, utilities) | Vitest + jsdom | ≥85% lines | every commit |
| Component (primitives, shared) | Vitest + `@testing-library/angular` | ≥80% lines | every commit |
| Integration (feature happy paths) | Vitest + MSW | smoke per feature | every PR |
| E2E (seller journey) | Playwright with mobile emulation (Pixel 5 + Moto G Power) | full §V1.3 journey | every PR |
| Visual regression (V1.5) | Playwright snapshots | TBD | nightly |

### Performance budget (preview, mobile 3G)

| Metric | V1 budget | Note |
|---|---|---|
| LCP (Largest Contentful Paint) | ≤2.5s | Per Core Web Vitals |
| INP (Interaction to Next Paint) | ≤200ms | Per Core Web Vitals |
| CLS (Cumulative Layout Shift) | ≤0.1 | Per Core Web Vitals |
| Initial JS bundle (root chunk) | ≤180 KB gzip | |
| Per-route lazy chunk | ≤80 KB gzip | Catalog-form chunk has a budget exception at 120 KB |
| Time to interactive (3G throttled) | ≤5s | Lighthouse mobile profile |
| Wizard schema fetch (cached) | <50ms | Per backend §6.6 |
| Wizard schema fetch (cold) | <200ms | Per backend §6.6 |
| Autofill response (P95) | <5s | Per V1 spec |
| Smart Picker (P95) | <3s | Per V1 spec |

---

## Section 20 — Build & Deployment Topology

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator deep authoring per FE-D8)

### A. What §20 establishes

The build pipeline (Angular CLI → static assets) + Docker packaging (nginx) + K3s deployment (per `INFRASTRUCTURE_ARCHITECTURE.md`) + CI/CD wiring (GitLab → Artifact Registry → K3s). Translates §1 topology into concrete deploy artefacts.

### B. Build pipeline

```bash
# Local + CI
ng build --configuration=production
# Output: frontend/dist/frontend/browser/
#   ├── index.html (no-cache; SW manages updates)
#   ├── main.[hash].js + chunks
#   ├── styles.[hash].css
#   ├── assets/ (PWA icons, fonts)
#   ├── ngsw.json (service-worker manifest)
#   ├── ngsw-worker.js
#   └── manifest.webmanifest
```

Production build flags:
- `aot: true` — AOT compile (required for standalone)
- `optimization: true` — minification + tree-shake
- `buildOptimizer: true` — Angular-specific dead code removal
- `outputHashing: 'all'` — fingerprint all assets for 1-year immutable cache
- `sourceMap: false` (V1) — V1.5 may enable for production debugging with restricted access

### C. Dockerfile (multi-stage)

```dockerfile
# frontend/Dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --no-audit --prefer-offline
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O- http://localhost/ || exit 1
```

**Important — Angular 18 standalone output path** (post service-builder dispatch correction 2026-06-05): the build output is `dist/frontend/browser/` (nested), NOT `dist/frontend/`. The `COPY --from=builder` line above MUST use the nested path or the runtime image will serve an empty document root. Verified against the locked Angular CLI standalone build configuration.

V1.5 may switch runtime to `distroless` for smaller attack surface.

### D. nginx config

```nginx
# frontend/nginx.conf
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  # SPA fallback — all unknown routes serve index.html (Angular router handles)
  location / {
    try_files $uri $uri/ /index.html;
  }

  # index.html — never cache (SW manages updates)
  location = /index.html {
    add_header Cache-Control "no-cache, no-store, must-revalidate";
  }

  # Hashed assets — immutable for 1 year
  location /assets/ {
    add_header Cache-Control "public, max-age=31536000, immutable";
  }

  location ~* \.(js|css|woff2)$ {
    add_header Cache-Control "public, max-age=31536000, immutable";
  }

  # Service worker — short cache (SW updates within 5 min)
  location = /ngsw.json {
    add_header Cache-Control "no-cache";
  }

  # Gzip on
  gzip on;
  gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
```

### E. K3s deployment

Per `INFRASTRUCTURE_ARCHITECTURE.md`:
- **Image**: `asia-south1-docker.pkg.dev/<project>/meesell-prod-images/frontend:<tag>`
- **Pod**: `Deployment` in `dev` namespace (and later `staging` + `prod`)
- **Replicas**: 1 in dev, 2 in staging+prod
- **Resources**: requests 50m CPU / 64Mi RAM, limits 200m CPU / 256Mi RAM (nginx static-serve is cheap)
- **Service**: ClusterIP exposed at `frontend.dev.svc.cluster.local:80`
- **Ingress**: Traefik routes `dev.mesell.xyz` + `www.mesell.xyz` (prod) → frontend service

### F. Env configuration

Build-time replacement via Angular CLI `fileReplacements`:

```typescript
// src/environments/environment.ts (dev)
export const environment: EnvConfig = {
  production: false,
  apiBaseUrl: 'https://api-dev.mesell.xyz',
  defaultLocale: 'en',
  serviceWorkerEnabled: true,
  bundleAnalyzerEnabled: true,
};

// src/environments/environment.prod.ts
export const environment: EnvConfig = {
  production: true,
  apiBaseUrl: 'https://api.mesell.xyz',
  defaultLocale: 'en',
  serviceWorkerEnabled: true,
  bundleAnalyzerEnabled: false,
};
```

V1.5 considers runtime `/config.json` fetch at app boot if a single image needs to serve multiple environments without rebuild.

### G. CI/CD wiring (per infra §10)

```yaml
# .gitlab-ci.yml stages
stages:
  - lint        # eslint + prettier --check
  - test        # vitest run (per §19)
  - build       # ng build --configuration=production
  - bundle-check # webpack-bundle-analyzer JSON vs §19 budgets
  - docker      # docker build + push to Artifact Registry via WIF (per infra §10)
  - deploy      # kubectl set image deployment/frontend frontend=<new-tag> -n dev
```

Manual gate for `dev → staging → prod` promotions.

### H. Service-worker update strategy

```typescript
// app.component.ts (root)
constructor() {
  if (this.swUpdate.isEnabled) {
    this.swUpdate.versionUpdates
      .pipe(filter(e => e.type === 'VERSION_READY'))
      .subscribe(() => {
        this.snackBar.open('A new version is available', 'Reload', { duration: 0 })
          .onAction().subscribe(() => location.reload());
      });
  }
}
```

### I. Coordinator depth call

Build + deploy is sufficiently locked when specialists have: Dockerfile, nginx.conf, env config, CI stages. Per-step CI flag tuning deferred to first deployment.

This section concretises §1 into the actual build + deployment pipeline: `ng build --configuration=production` outputs `dist/frontend/browser/`, the multi-stage Dockerfile copies that into an nginx image, image push to Artifact Registry, K3s Deployment manifest at `k8s/frontend.yaml` mounts it, Traefik ingress routes `dev.mesell.xyz` and `www.mesell.xyz` to the frontend service. The nginx config sets cache headers on `/assets/*` (1y immutable), `/index.html` (no-cache), and proxies nothing — all API calls go direct to `api.mesell.xyz`. Environment config is baked at build time via Angular's `fileReplacements` (no runtime env injection in V1; if V1.5 needs runtime swap, we move to a `/config.json` fetch at app boot). The Dockerfile is multi-stage: Node 20 builder → nginx:alpine runtime, distroless candidate for V1.5.

---

## Section 21 — SOLID, DRY, and Modern Techniques

STATUS: LOCKED (2026-06-05, founder ratification as-is; content already substantial from initial authoring; coordinator depth call: principles charter is now a citation surface for PR reviews)

This section is the **principles charter** — how SOLID, DRY, and modern Angular 18 techniques apply concretely in this codebase. Reviewers cite this section when a PR is refused for principle violation.

### SOLID — applied

**Single Responsibility (SRP)**
- One component = one UI role. `CatalogFormComponent` orchestrates the wizard; it does NOT also calculate pricing.
- One service = one business responsibility. `CatalogFormService` handles product CRUD; pricing math lives in `PricingService`.
- The 11 primitives demonstrate SRP at its purest: each renders one input shape, nothing else.

**Open/Closed (OCP)**
- The form renderer is closed for modification (its dispatcher logic doesn't change) but open for extension (adding a 12th primitive = adding a class + a dispatcher entry; no other code changes).
- New marketplaces in V2 = new feature folders consuming the same `core/api` — V1 code remains untouched.

**Liskov Substitution (LSP)**
- All 11 primitives implement the same `ControlValueAccessor` interface. The renderer treats them identically. Replacing one primitive with another (e.g. swapping the autocomplete library) does not break callers.

**Interface Segregation (ISP)**
- `PrimitiveInputs` carries only what every primitive needs. `dropdown_api_search` does NOT receive a static enum list (it fetches its own); `dropdown_small` does NOT receive a search-fn input (it doesn't search).
- `CatalogFormService` exposes only catalog-form operations. Plan-tier checks live on `AuthService`, not on every feature service.

**Dependency Inversion (DIP)**
- Features depend on `ApiClient` (an abstraction), not on `HttpClient` directly. V1.5 might swap to a typed-gRPC client; only `ApiClient` changes.
- The dispatcher depends on `PrimitiveInputs` (a contract), not on concrete primitive classes.

### DRY — applied

- The validation message library lives in `core/i18n` and is read by every form. No feature redeclares "required field" copy.
- The `InrCurrencyPipe` is the only place INR formatting lives. No feature inlines its own `₹` prefix.
- The `StatusBadgeComponent` renders product status everywhere. No feature inlines status pills.
- The `AuthGuard` + `PlanGuard` run on every route declaration. No feature inlines auth checks.
- The autosave directive runs on every Reactive Form that wants it. No feature reinvents debounced-PATCH.

### Modern Angular 18 techniques — applied

- **Standalone components everywhere.** No NgModules.
- **Signal inputs + signal outputs** for component IO (Angular 17+ `input.required<T>()` API).
- **`@if @for @switch`** template control flow (no `*ngIf`, no `*ngFor`).
- **`@defer` blocks** for non-critical UI (the chart in `pricing`, the preview surfaces in `preview`).
- **`OnPush` change detection** as the default on every component.
- **`inject()`** for DI in component class bodies and `runInInjectionContext` for guards.
- **Lazy `loadComponent`** routing for every feature.
- **`toSignal()`** to bridge RxJS into the template without async pipe.
- **`computed()`** for derived state with auto-tracked deps.
- **Service worker** via `@angular/pwa` aligned with backend Cache-Control headers.

### What this section explicitly forbids

- NgModules (use standalone)
- `*ngIf` / `*ngFor` (use `@if` / `@for`)
- `subscribe()` in templates (use `async` pipe or `toSignal`)
- Manual `Subscription.unsubscribe()` in feature code (use `takeUntilDestroyed()` or async pipe)
- Service Locator anti-pattern (always `inject()` or constructor DI)
- God services (each service has a single responsibility — split if it exceeds 200 lines)
- Inline magic strings for enum-like values (use the `shared/enums/` namespace)
- Hardcoded English strings in templates (use Transloco)

---

## Section 22 — Acceptance & Sign-Off

STATUS: LOCKED (2026-06-05, founder ratification as-is + coordinator authoring per FE-D8 — checklist mirrored from V1 §8)

### A. The V1-done checklist (frontend granularity)

- [ ] All 12 routes render and are auth-guard wired correctly per §23
- [ ] Account feature (§7): phone OTP send + verify works; refresh + logout works (FE-D5 split-token); onboarding wizard 3 phases work; /profile edits saved
- [ ] Dashboard (§9): paginated product list; status filter; debounced search; soft-delete confirm
- [ ] Smart picker (§10): description → 3 cards; manual browse fallback; card click creates draft + routes to edit
- [ ] Catalog form (§11): schema fetch ≤200ms cache-miss; wizard renders per §18; autofill yellow-highlight overlay; autosave 10s+blur; draft recovery on reload
- [ ] Images (§12): 4-slot drag-drop; client-side compress; precheck poll; per-image fix hints; slot-1 gate to preview
- [ ] Preview (§13): 3 surfaces render ≤1s; title truncation indicator on feed
- [ ] Pricing (§14): MRP+slider; local recompute <100ms; backend commit ≤200ms; red/green margin
- [ ] Export (§15): pre-validation gate; trigger + poll; signed-URL downloads with TTL countdown; seller-facing error mapping
- [ ] Cross-cutting: i18n English ships, ta/hi stubs present; offline banner appears on `online=false`; service worker cache works per §16
- [ ] Performance budget per §19 met (initial bundle ≤180 KB gzip, per-route ≤80 KB, catalog-form ≤120 KB)
- [ ] Core Web Vitals on Tirupur 3G profile: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1
- [ ] WCAG 2.2 AA verified via axe-core on every route
- [ ] End-to-end Playwright journey completes <10min for first-time user (V1 spec §8 acceptance)

### B. Founder sign-off ritual

1. Coordinator presents acceptance checklist with each item ✓ or ✗
2. ✗ items show: what failed, blocker class, mitigation plan
3. Founder signs `STATUS_FRONTEND.md` Updates Log with V1-DONE block
4. Coordinator hands off to deployment phase (per `STATUS_MASTER.md` cross-track sign-off)

### C. Coordinator depth call

Short — checklist mirrors V1 spec; ritual mirrors backend coordinator's pattern. Locking as-is.

This section is the V1-done checklist mirrored from `docs/V1_FEATURE_SPEC.md §8`, expressed at the frontend granularity: per-feature acceptance criteria, the 10-route navigability assertion, performance budget green-state assertion, accessibility audit (axe-core) pass, end-to-end Playwright journey passes, and the founder sign-off ritual. When every checkbox here is ticked, the frontend is V1-complete and the coordinator hands off to the deployment phase.

---

## Section 22A — Risk Register & Mitigations

STATUS: LOCKED (2026-06-05, founder ratification as-is; 11 risks already enumerated; coordinator depth call: register is now the defense-citation surface for future PRs that touch constrained areas)

This section enumerates the 10 frontend-specific architectural risks alongside the mitigation each design choice in this document carries:

1. **2G/3G first paint slow** → mitigated by features-first lazy chunks + service worker pre-cache + `@defer` for non-critical UI.
2. **3,772 categories × dynamic schema = unbounded form combinations** → mitigated by 11-primitive renderer; no per-category code path.
3. **Tirupur low-end Android RAM pressure** → mitigated by virtual scroll on every >100-item list, ≤180 KB initial bundle, no SSR (would double memory).
4. **Access JWT expiry mid-wizard** → mitigated by `RefreshInterceptor` catching 401 + silent `/auth/refresh` + retry of the original request (transparent to seller, per FE-D5 + §4). If the refresh ALSO fails (refresh expired / revoked / network drop), `ErrorInterceptor` clears `AuthService.accessToken` and routes to `/login` — the autosaved `product_drafts` row (backend §11.6) is re-hydrated on re-login via `GET /products/:id/draft` so no work is lost.
5. **Autosave network drop mid-flight** → mitigated by `AutosaveDirective` queueing + retry on `NetworkService.onLine = true`.
6. **Schema cache stale → seller sees old fields after Meesho refresh** → mitigated by ETag + 24h `stale-while-revalidate` — refresh propagates within 24h max.
7. **Tamil/Hindi font weight inflation** → mitigated by Transloco lazy translation files; Noto fonts loaded only when locale is active.
8. **Dropdown-api (Brand, up to 4,481 entries) inflates the wire** → mitigated by debounced (300ms) `switchMap` queries, server returns top 20.
9. **Service worker stale-app on deploy** → mitigated by `SwUpdate.versionUpdates$` notification + reload action; index.html is `no-cache` so new boot picks up new chunks.
10. **Module-Federation deferred but later difficult** → mitigated by features-first layout today; each feature folder ports 1:1 to a future MF remote in Phase 2.
11. **`REFRESH_TOKEN_PEPPER` infrastructure dependency** → the backend's HMAC-with-pepper Valkey keyspace (per backend ratification 2026-06-05) requires `REFRESH_TOKEN_PEPPER` to be populated in GCP Secret Manager before the iam module ships. If unpopulated, every `/api/v1/auth/refresh` returns 500. **Mitigated by:** infra-builder writes the secret during the `meesell-auth-builder` dispatch (per `STATUS_BACKEND.md` 2026-06-05 hand-off); frontend deploy is gated on the iam module being healthy (checked via `GET /health` from the smoke test). The frontend has no direct exposure to the pepper — it's an infra-side prerequisite the frontend coordinator watches but does not own. Frontend coordinator surfaces this in pre-deploy checklist.

This is the canonical defense citation: future PRs that touch a constrained area cite this register to justify the design choice rather than re-litigating it.

---

## Section 23 — Route Inventory

STATUS: LOCKED (2026-06-05, founder ratification as-is; 12 routes + 1 cross-cutting reference; all routes auth-guard wired per §4.D except `/`, `/signup`, `/login`; endpoint contract 27 backend / 26 frontend-consumed post FE-D5 ratification; post 2026-06-05B merger 4 routes now owned by `account` feature)

This section is the locked 10-route contract mapped to feature owners and endpoint consumers. The table has columns: route path, feature owner, auth required, plan required, endpoints consumed, component, lazy-loaded.

| Route | Feature | Auth? | Plan? | Endpoints consumed | Component | Lazy |
|---|---|---|---|---|---|---|
| `/` | `landing` | no | — | none | `LandingComponent` | yes |
| `/signup` | `auth` | no | — | `POST /auth/otp/send` | `SignupComponent` | yes |
| `/login` | `auth` | no | — | `POST /auth/otp/send`, `POST /auth/otp/verify` | `LoginComponent` | yes |
| (no route — cross-cutting) | `cross-cutting` (core/) | n/a | — | `POST /auth/refresh`, `POST /auth/logout` | (called from `AuthService` in `core/`; not user-navigable) | n/a |
| `/onboarding` | `onboarding` | yes | — | `GET /seller-profile/required-fields`, `PUT /seller-profile` | `OnboardingWizardComponent` | yes |
| `/profile` | `profile` | yes | — | `GET /seller-profile`, `PUT /seller-profile` | `ProfileEditComponent` | yes |
| `/dashboard` | `dashboard` | yes | — | `GET /products`, `DELETE /products/:id` | `DashboardComponent` | yes |
| `/catalogs/new` | `smart-picker` | yes | — | `GET /categories/suggest`, `GET /categories/browse`, `POST /products` | `SmartPickerComponent` | yes |
| `/catalogs/:id/edit` | `catalog-form` | yes | — | `GET /categories/:id/schema`, `GET /products/:id`, `GET /products/:id/draft`, `PATCH /products/:id`, `POST /products/:id/autofill`, `GET /categories/:id/enum/:field` | `CatalogFormComponent` | yes |
| `/catalogs/:id/images` | `images` | yes | — | `POST /products/:id/images`, `GET /products/:id/images` | `ImageUploaderComponent` | yes |
| `/catalogs/:id/preview` | `preview` | yes | — | `GET /products/:id/preview` | `PreviewComponent` | yes |
| `/catalogs/:id/pricing` | `pricing` | yes | — | `POST /products/:id/price-calc` | `PricingComponent` | yes |
| `/catalogs/:id/export` | `export` | yes | — | `POST /products/:id/export-xlsx`, `GET /exports/:id` | `ExportComponent` | yes |

**Total: 12 user-navigable routes** (10 from V1 §6 + `/onboarding` + `/profile` per MVP §4.5). All auth-guarded except `/`, `/signup`, `/login`. None plan-gated in V1 (`plan_gating` is V1.5 feature for advanced exports + bulk operations).

**Endpoints consumed: 26** — 24 of the 27 contract endpoints per `BACKEND_ARCHITECTURE.md §0.C` (post 2026-06-05 amendment block — every endpoint except `POST /api/v1/auth/login` which is reserved for V1.5 email/password) plus the **2 new auth endpoints from the FE-D5 ratification**: `POST /api/v1/auth/refresh` (cross-cutting; called by `AuthService.bootstrap()` and by `RefreshInterceptor` on 401) and `POST /api/v1/auth/logout` (called from navbar logout action via `AuthService.logout()`). Backend coordinator ratified all 7 deltas from `backend_handoff_jwt_session_pattern.md` on 2026-06-05 plus added 3 founder-ratified strengthenings (Lua `EVAL` rotation, HMAC-pepper allowlist keyspace, `Path=/api/v1/auth` cookie). Endpoint contract is now LOCKED at 27 on the backend side, 26 consumed on the frontend side.

---
