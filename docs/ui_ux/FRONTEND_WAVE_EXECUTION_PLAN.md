# MeeSell Frontend — Wave Execution Plan (Parallel)

| Field | Value |
|---|---|
| **Document type** | Orchestration blueprint (step 3 of 3) |
| **Date** | 2026-06-09 |
| **Author** | meesell-frontend-coordinator (master) |
| **Architecture decision** | **Option A-full** — full 4-layer, auth refactored (founder ratified 2026-06-09) |
| **Companion docs** | `FRONTEND_MODULE_INVENTORY.md` (modules), per-module `WAVE_*_DISPATCH.md` (specs) |
| **Governs** | Waves 3–5 of the MeeSell frontend build |

---

## Prime Directive (Option A-full)

> Every feature imports ONLY from `../../ui` (mee-* UI Kit), `../../shared` (composites),
> `../../layouts`, and its own services. **ZERO `primeng/...` imports in any feature file.**
> PrimeNG lives behind the UI Kit wall (`src/app/ui/`) exclusively.

The 3 existing auth pages currently violate this. They are refactored in Wave 5 (F2–F4).

---

## The Dependency DAG

```
                    ┌─────────────────────────────┐
   Layer 1 ✅       │  Design System (tokens)      │  DONE
                    └──────────────┬──────────────┘
                                   ▼
   ┌───────────────────────────────────────────────────────────┐
   │  WAVE 3 — UI KIT (17 mee-* primitives)                     │  ← gates everything
   │  K1..K17 — internally independent → PARALLEL batch         │
   └──────────────┬────────────────────────────────────────────┘
                  ▼
   ┌───────────────────────────────────────────────────────────┐
   │  WAVE 4 — COMPOSITES (5 mee-* )                            │
   │  C1..C5 — independent of each other → PARALLEL             │
   └──────────────┬────────────────────────────────────────────┘
                  ▼
   ┌───────────────────────────────────────────────────────────┐
   │  WAVE 5 — FEATURES (11 pages)                              │
   │  independent of each other → PARALLEL fan-out             │
   │  (1 sub-session per feature, per locked arch §Wave 2E)     │
   └───────────────────────────────────────────────────────────┘

   ADJACENT TRACK (can start any time, no UI dependency):
   ┌───────────────────────────────────────────────────────────┐
   │  SERVICE LAYER — catalog/product/auth services + API       │
   │  client (meesell-angular-service-builder). Features        │
   │  SIMULATE until this lands, then wire (Wave 6 API).        │
   └───────────────────────────────────────────────────────────┘
```

**Hard ordering:** Wave 3 → Wave 4 → Wave 5. **Within each wave:** fully parallel.

---

## WAVE 3 — UI Kit (17 primitives)

| Property | Value |
|---|---|
| Dispatch doc | `WAVE_3_UI_KIT_DISPATCH.md` |
| Agent | `meesell-angular-component-builder` |
| Parallelism | Build as ONE coordinated batch (shared barrel `ui/index.ts`) |
| Gate to exit | All 17 build, each has a smoke test, barrel exports verified |
| Reference | `docs/primeng/*.md` (each mee-* wraps a documented p-component) |

The ONLY layer permitted to import `primeng/...`. Priority order:
`button → input → otp-input → badge → card → table → dialog → file-upload → steps → select → tree-select → skeleton → progress-bar → toast → confirm-dialog → password-input → textarea`

**Suggested split if parallelized across sessions:** 3 batches of ~6 (form primitives / data primitives / overlay+feedback primitives). Single-session sequential is also fine — they're small wrappers.

---

## WAVE 4 — Composites (5)

| Property | Value |
|---|---|
| Dispatch doc | `WAVE_4_COMPOSITES_DISPATCH.md` |
| Agent | `meesell-angular-component-builder` |
| Depends on | Wave 3 (each composite composes a UI Kit primitive) |
| Parallelism | All 5 independent → parallel, but small enough for one session |
| Gate to exit | All 5 build + smoke tests; consume mee-* internally (no direct PrimeNG) |

`mee-stat-card` · `mee-status-badge` · `mee-page-header` · `mee-empty-state` · `mee-loading-skeleton`

---

## WAVE 5 — Features (11 pages, parallel fan-out)

| Property | Value |
|---|---|
| Agent | `meesell-angular-component-builder` (+ `meesell-angular-service-builder` for data) |
| Depends on | Waves 3 + 4 complete |
| Parallelism | **Up to 11 concurrent sub-sessions** — features share no code |
| Rule | Import only mee-* / composites / layouts / own services. No PrimeNG. |

| Wave-5 ID | Module | Dispatch doc | Complexity | Parallel group |
|---|---|---|---|---|
| F2–F4 | **Auth refactor** (login/signup/otp) | `WAVE_5_AUTH_REFACTOR_DISPATCH.md` | S | A |
| F1 | **Landing** | `WAVE_5_LANDING_DISPATCH.md` | S | A |
| F5 | **Onboarding** | `WAVE_5_ONBOARDING_DISPATCH.md` | M | A |
| F13 | **Profile** | `WAVE_5_PROFILE_DISPATCH.md` | S | A |
| F6 | **Dashboard** | `WAVE_5_DASHBOARD_DISPATCH.md` | M | B |
| F7 | **Smart Picker** | `WAVE_5_SMART_PICKER_DISPATCH.md` | L | B |
| F8 | **Catalog Form** | `WAVE_5_CATALOG_FORM_DISPATCH.md` | L | B |
| F9 | **Images** | `WAVE_5_IMAGES_DISPATCH.md` | M | C |
| F10 | **Preview** | `WAVE_5_PREVIEW_DISPATCH.md` | L | C |
| F11 | **Pricing** | `WAVE_5_PRICING_DISPATCH.md` | M | C |
| F12 | **Export** | `WAVE_5_EXPORT_DISPATCH.md` | M | C |

**Parallel groups** are a suggested batching for a solo founder running ~4 sessions at once — not a hard ordering. Any feature can run as soon as Waves 3+4 are done. The catalog flow (F7→F8→F9→F10→F11→F12) shares the *product* data model but the components are independent and build in parallel; only end-to-end testing needs them sequential.

---

## Critical Path & Sequencing

```
Wave 3 UI Kit  ──►  Wave 4 Composites  ──►  Wave 5 Features  ──►  Wave 6 API wiring
   (gates all)        (gates features)         (parallel ×11)        (real HttpClient)
```

- **Fastest path to a clickable full app:** Wave 3 → Wave 4 → Wave 5 (simulated data).
- **API track** runs adjacent; features built against simulated services, then wired in Wave 6.
- **Do not start Wave 5** until the UI Kit barrel (`ui/index.ts`) is stable — feature imports depend on it.

---

## Gating Checklist Between Waves

| Transition | Must be true before proceeding |
|---|---|
| W3 → W4 | All 17 mee-* build; `ui/index.ts` exports all; smoke tests green |
| W4 → W5 | All 5 composites build; consume mee-* (no PrimeNG); smoke tests green |
| W5 → W6 | Features render with simulated data; routes resolve; visual founder pass |

---

## Dispatch Doc Index (step 2 deliverables)

| # | Doc | Module(s) | Wave |
|---|---|---|---|
| 1 | `WAVE_3_UI_KIT_DISPATCH.md` | 17 primitives | 3 |
| 2 | `WAVE_4_COMPOSITES_DISPATCH.md` | 5 composites | 4 |
| 3 | `WAVE_5_AUTH_REFACTOR_DISPATCH.md` | login/signup/otp | 5 |
| 4 | `WAVE_5_LANDING_DISPATCH.md` | landing | 5 |
| 5 | `WAVE_5_ONBOARDING_DISPATCH.md` | onboarding | 5 |
| 6 | `WAVE_5_PROFILE_DISPATCH.md` | profile | 5 |
| 7 | `WAVE_5_DASHBOARD_DISPATCH.md` | dashboard | 5 |
| 8 | `WAVE_5_SMART_PICKER_DISPATCH.md` | smart-picker | 5 |
| 9 | `WAVE_5_CATALOG_FORM_DISPATCH.md` | catalog-form | 5 |
| 10 | `WAVE_5_IMAGES_DISPATCH.md` | images | 5 |
| 11 | `WAVE_5_PREVIEW_DISPATCH.md` | preview | 5 |
| 12 | `WAVE_5_PRICING_DISPATCH.md` | pricing | 5 |
| 13 | `WAVE_5_EXPORT_DISPATCH.md` | export | 5 |

---

## Revision History

| Date | Change |
|---|---|
| 2026-06-09 | Initial — Option A-full ratified; 3-wave parallel structure defined |
