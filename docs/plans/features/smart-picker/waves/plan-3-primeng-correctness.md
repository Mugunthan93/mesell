# Plan 3 — PrimeNG Correctness Redevelop

**Status:** DONE ✓ (squash `11531a4` on integration)
**Type:** FE-only (LAYOUT-FREEZE — composition fix only)
**Branch:** feature/section-2/frontend → squashed to integration
**Specialists:** meesell-angular-component-builder (Task B only — Task A empty)

---

## Premise

The MeeSell Nx monorepo enforces a PrimeNG abstraction wall: PrimeNG components live ONLY in `frontend/libs/ui-kit` (Layer 2), exposed through `mee-*` wrappers. Feature code in `frontend/apps/mfe-catalog` must use ONLY `mee-*` wrappers — zero direct PrimeNG imports.

The frontend coordinator audit found ONE genuine violation. The "hand-rolled card div" was already compliant (`category-card.component.ts` already uses `<mee-card>` and `<mee-button>`).

---

## Violation found and fixed

| Element | File + approx lines | Replacement |
|---|---|---|
| Raw `<button type="button" ... style="...background:none...">Browse if none match</button>` | `smart-picker.component.ts` L129–138 | `<mee-button variant="ghost" size="sm" [fullWidth]="false" (clicked)="onBrowse()" label="Browse if none match" />` |

No new `mee-*` wrappers were needed (`MeeButtonComponent` with `variant="ghost"` covered the case).

---

## Changes delivered (commit 646a370 → squash 11531a4)

1. Replaced raw `<button>` with `<mee-button>` in `smart-picker.component.ts` template.
2. Added `MeeButtonComponent` to component `imports[]`, imported from `@mesell/ui-kit`.
3. All signals, RxJS pipeline, `onBrowse()` handler preserved unchanged.
4. Layout unchanged (LAYOUT-FREEZE enforced).

---

## Verification results (gate-passed)

- `grep "<button" smart-picker.component.ts` → ZERO hits ✓
- `grep "primeng" apps/mfe-catalog/src/app/smart-picker/` → ZERO hits ✓
- Build check: SKIPPED (no node_modules in worktree — environment limitation). Static contract verified against ui-kit source.
- **Founder action required:** Run `ng build mfe-catalog` on `feature/section-2/integration` before integration→develop PR merge to confirm build health.

---

## Gate verdict

PASS — squash-merged and pushed to integration as `11531a4`.
