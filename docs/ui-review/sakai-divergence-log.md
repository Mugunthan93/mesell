# Sakai ↔ MeeSell — Intentional Divergence Log

**Deliverable:** 6.3 of `docs/plans/ui-sakai-comparison-plan.md`
**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-19

**Purpose:** record every **intentional** divergence from the Sakai/PrimeNG-Aura default so that a future "align to Sakai" pass does not erode deliberate brand identity or architecture decisions. Every entry below is marked **KEEP** — do not align away. Accidental divergences (none found in the static pass) would be logged separately and routed to `sakai-upgrade-path.md`.

## Decision-owner key

- **FRONTEND_ARCHITECTURE.md** — LOCKED 2026-06-05 (token wall, layer model).
- **SWAP_GUIDE.md** — library-swap-proof seam (`frontend/libs/ui-kit/SWAP_GUIDE.md`).
- **CLAUDE.md Decision #9–13** — Angular/Material/Tailwind/MF/Ionic locks.
- **Brand** — MeeSell brand identity (founder-owned).
- **V1 scope** — V1_FEATURE_SPEC scope boundary.

---

## Color / brand divergences

| # | Token / component | MeeSell value | Sakai (Aura default) | Rationale | Owner | Decision |
|---|---|---|---|---|---|---|
| D1 | Primary 500 / `--mee-color-primary` | `#F26B23` (orange) | `#10b981` (emerald) | MeeSell brand colour. The single most identity-defining token. | Founder | Brand | **KEEP** |
| D2 | Primary ramp 50–950 | Custom orange ramp (`#fff3ec … #4a1d03`) | Emerald ramp | Brand ramp derived from D1; powers hover/active/tint everywhere. | Founder | Brand | **KEEP** |
| D3 | Primary light / highlight | `rgba(242,107,35,0.12)` (+0.20 focus) | Emerald highlight tint | Brand-orange selection/highlight surfaces. | Founder | Brand | **KEEP** |
| D4 | Surface ground `--mee-color-bg` | `#f0f5f9` (cool grey) | Aura/Sakai neutral-slate ground | Cool-grey page canvas; calmer behind orange accents, avoids orange-on-warm clash. | ui-styler | Brand surface | **KEEP** |
| D5 | Surface ramp 0–950 | 12-step custom cool-grey ramp | Aura surface ramp | Cohesive cool-grey system; ramp doubles as text scale (900 = body text). | ui-styler | Brand surface | **KEEP** |
| D6 | Surface variant `#f2f6fa` | Cool grey | `--p-surface-100` | Secondary surface in the cool family. | ui-styler | Brand surface | **KEEP** |
| D7 | Text default `#2a3547` / muted `#5a6a85` | Cool slate | Aura neutral text | Cool-slate text pairs with cool-grey surfaces; not pure black. | ui-styler | Brand surface | **KEEP** |
| D8 | Border `#e5eaef` + variant `#dfe5ef` | Cool grey, 2 steps | Aura single content border | Cool border family + a second step for layered surfaces. | ui-styler | Brand surface | **KEEP** |
| D9 | Semantic error/success/warning/info | `#DC2626 / #16A34A / #D97706 / #2563EB` | Aura red/green/yellow/blue | Hand-tuned semantics; warning deliberately darker amber to not collide with brand orange. | ui-styler | Brand | **KEEP** |

## Sidebar / navigation divergences

| # | Token / component | MeeSell value | Sakai (default) | Rationale | Owner | Decision |
|---|---|---|---|---|---|---|
| D10 | Sidebar background `--mee-color-sidebar` | `#111c2d` (dark navy) | Light sidebar | **Dark-sidebar-on-light-page** pattern — premium SaaS look, strong nav/content separation. | ui-styler / shell | Design decision | **KEEP** |
| D11 | Sidebar text `#9fafca` | Muted blue-grey | `--p-navigation-item-color` | Readable low-contrast text on dark navy. | ui-styler | Design decision | **KEEP** |
| D12 | Sidebar active `#F26B23` | Brand orange | Aura active highlight | Brand-orange active indicator on dark sidebar — high-pop wayfinding. | ui-styler | Brand | **KEEP** |
| D13 | Shell sidebar structure | Custom 4-group (Home / Catalogs / Categories / Account) host-owned chrome | Sakai AppMenu config | Domain-specific IA; FE-3 shell-only sealed. | component-builder / shell | Architecture | **KEEP** |

## Radius / shape divergences

| # | Token / component | MeeSell value | Sakai (Aura default) | Rationale | Owner | Decision |
|---|---|---|---|---|---|---|
| D14 | Button radius `--mee-radius-full` | `999px` (pill) | ~`6px` | Pill buttons — MeeSell's primary CTA language. | ui-styler | Design decision | **KEEP** |
| D15 | Button paddingX `1.25rem` | Wider | ~`1rem` | Roomier tap targets to match pill shape (mobile-first). | ui-styler | Design decision | **KEEP** |
| D16 | Card / dialog / panel radius `--mee-radius-md` | `16px` | ~`6–12px` | "Soft card" design language; larger, friendlier corners. | ui-styler | Design decision | **KEEP** |
| D17 | Input / select radius `--mee-radius-sm` | `7px` | ~`6px` | Smaller than card to establish shape hierarchy (controls < containers); near-match but deliberate. | ui-styler | Design decision | **KEEP** |
| D18 | Radius lg `18px` | Extra step | (none in Aura) | Spare large-radius step for hero/illustration surfaces. | ui-styler | Design decision | **KEEP** |

## Motion / elevation / spacing divergences

| # | Token / component | MeeSell value | Sakai (Aura default) | Rationale | Owner | Decision |
|---|---|---|---|---|---|---|
| D19 | Transition scale | 3-step `fast 150 / base 250 / slow 400 ms ease` | Single `--p-transition-duration` | Deliberate motion vocabulary (micro-feedback vs panel/overlay), not one global value. | ui-styler | Design decision | **KEEP** |
| D20 | Shadow scale | 3-step `sm / md / lg` global tokens | Per-component overlay shadows only | Global elevation system independent of component, swap-proof. | ui-styler | Architecture | **KEEP** |
| D21 | Spacing scale `--mee-space-1..10` | 4px-base global scale (8 steps) | No global spacing tokens (PrimeFlex utilities) | First-class spacing tokens consumed by layout primitives and Tailwind at use-site. | ui-styler / component-builder | Architecture | **KEEP** |

## Architecture divergences

| # | Token / component | MeeSell value | Sakai model | Rationale | Owner | Decision |
|---|---|---|---|---|---|---|
| D22 | Token wall `--mee-*` → preset → `--p-*` | MeeSell owns `--mee-*` as source of truth; `--p-*` is a derived projection via `MeeSellPreset` | Sakai consumes `--p-*` directly | Library-swap-proof: a future move off PrimeNG touches only the preset, not 100s of components. The headline architecture divergence. | Frontend Lead | FRONTEND_ARCHITECTURE.md §1 / SWAP_GUIDE.md | **KEEP** |
| D23 | PrimeNG seal (no PrimeNG imports outside ui-kit) | Enforced (FE-1) | Sakai imports PrimeNG everywhere | Abstraction wall; only `libs/ui-kit/**` touches PrimeNG. | Frontend Lead | FRONTEND_ARCHITECTURE.md / CI FE-1 | **KEEP** |
| D24 | Named layout primitives vs PrimeFlex | `mee-page/section/stack/grid/toolbar/form-layout` | PrimeFlex utility classes | Typed, discoverable, swap-proof layout API. | component-builder | Architecture | **KEEP** |
| D25 | Phase 7 swap seam shipped | `MeeSellAltPreset`, `MEE_ICONS_ALT`, `ActiveIcons` | n/a | Proves the swap-proof claim with an alternate preset + icon registry. | Frontend Lead | SWAP_GUIDE.md | **KEEP** |

## Scope divergences (V1 boundary)

| # | Token / component | MeeSell state | Sakai | Rationale | Owner | Decision |
|---|---|---|---|---|---|---|
| D26 | Color scheme | **Light only** (`MeeSellPreset` defines `colorScheme.light` only) | Sakai ships light + dark | V1 ships light-only to reduce surface area; dark is a deliberate deferral, not an oversight. | Founder / Frontend Lead | V1 scope | **KEEP for V1** (revisit P3 — see upgrade path) |

---

## Notes / watch-items (not divergences, but log them)

- **Internal inconsistency (not a Sakai divergence):** `--mee-shadow-md` uses alpha `0.10` while `MeeSellPreset.components.card.root.shadow` uses alpha `0.08`. Both are MeeSell-authored; this is an internal drift, not a Sakai gap. Routed to `sakai-upgrade-path.md` as a low-priority cleanup (align card shadow to `--mee-shadow-md`).
- **`panel.root.borderRadius` is themed but unused** (no `mee-panel` component). This is a component gap (see component-gaps doc), not a divergence — the radius value itself (16px) is a consistent KEEP per D16.

## Summary

**26 intentional divergences logged — all KEEP.** Breakdown: 9 color/brand, 4 sidebar, 5 radius, 3 motion/elevation/spacing, 4 architecture, 1 scope. **Zero accidental divergences** were found in the static pass; if the live visual capture (plan §5.1) surfaces any, append them here with a recorded rationale or route them to the upgrade path as alignment candidates.
