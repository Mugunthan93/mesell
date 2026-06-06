---
name: locked-decisions-inherited
description: The CLAUDE.md + MVP_ARCHITECTURE + CORE_PHILOSOPHY decisions the frontend must honour — concise index for fast reference during specialist dispatch
metadata:
  type: reference
---

# Locked decisions the frontend inherits

## From CLAUDE.md (15 decisions, 5 frontend-relevant)

- **D9: Angular 18, not React** — drives every other choice
- **D10: Services + RxJS + signals, no NgRx/Zustand/Redux** — state management rule
- **D11: Tailwind + Material, not Material alone** — styling rule
- **D12: Module Federation deferred to Phase 2** — but features-first today is the MF substrate
- **D13: Ionic + Capacitor deferred to Phase 2** — V1 is web-only PWA, no Ionic components
- **D14: MSG91 OTP + JWT in localStorage** — auth storage rule (not sessionStorage, not cookies)

## From CORE_PHILOSOPHY.md (10 MANDATES + 8 FORBIDS, frontend-relevant subset)

**MANDATES the frontend honours:**
- **M1** — Display labels only; `meesho_*` never visible to seller
- **M2** — Inline help from `display_help`, never from Meesho's original
- **M3** — Validation messages from i18n library + per-field overrides
- **M4** — Dropdown labels from `enum_entries[i].labels[locale]`
- **M5** — Wizard layout follows seller intuition (13 step IDs grouped at runtime)
- **M7** — AI suggestions render through same primitives; canonical values only
- **M9** — Locale maps `{en, ta, hi}` resolved at render time

**FORBIDS the frontend respects:**
- **F1** — Never show Meesho's raw column header (naturally enforced — backend strips them)
- **F5** — Never show a field without explanation (renderer asserts display_help exists, falls back to placeholder)

## From MVP_ARCHITECTURE.md §4 + §5.6 (the wizard contract)

- **§4.1** — 11 input primitives (frontend implements all 11)
- **§4.2** — Single `<mee-wizard>` renderer, NO category-specific code anywhere
- **§4.3** — Onboarding wizard (3 phases) separate from catalog wizard
- **§4.4** — State per Decision 10
- **§4.5** — Adds /onboarding + /profile to V1 §6 route list
- **§5.6.1** — Three-layer field schema (display / canonical / export) is the input contract
- **§5.6.2** — Locale handling via `Accept-Language` header + `{en, ta, hi}` JSONB maps
- **§5.6.3** — 13 step IDs (basics, pricing, inventory, sizing, materials, food, tech_specs, safety, warranty, compliance, photos, description, advanced)
- **§6.3** — HTTP caching: schema 24h max-age + stale-while-revalidate=3600 + ETag; seller profile no-store

## From BACKEND_ARCHITECTURE.md §0

- **§0.G.D2** — `is_advanced` allowlist = `group_id` only for V1 (Pattern 5 advanced fields section)
- **§0.G.D3** — `GET /api/v1/products/{id}/draft` is the 25th endpoint (autosave recovery)
- **JWT claims** `{sub, exp, plan}` — frontend reads `plan` for plan-gating UI
- **Rate limits** — OTP 3/h, autofill 50/h, picker 100/h, create-product 20/h — frontend surfaces friendly 429 retry hints

## How to apply

When dispatching a specialist:
1. The dispatch prompt includes "Honour CORE_PHILOSOPHY M1/M9 and CLAUDE.md D9/D10" (or whichever subset applies)
2. The specialist reads FRONTEND_ARCHITECTURE.md §0.E + §0.G which cites these decisions
3. If a specialist proposes a violation, redirect them to the relevant decision; if they have a legitimate case, surface it to founder — do NOT amend the doc unilaterally
