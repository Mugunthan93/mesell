## Session 2026-06-10 — Wave 5 F9 Images EXECUTED {#wave5-f9-images}

### Route touched
`/catalogs/:id/images` — features/images/image-uploader/

### Services consumed
`ActivatedRoute` (route param), `Router` (navigate to /preview), `DestroyRef` (not used directly — ngOnDestroy used instead)

### Finding: Component already substantially complete from prior session
`image-uploader.component.ts`, `image-uploader.model.ts`, and the spec were already authored from
Wave 3 (2026-06-07 images session). However:
1. The route `/catalogs/:id/images` was MISSING from `app.routes.ts` (same issue as F8).
2. The spec had 16 TestBed-based tests that all failed with "Need to call TestBed.initTestEnvironment() first"
   when run via `pnpm exec vitest run` (the direct vitest runner, not `ng test`).
3. The 8 pure-function tests in the same spec were already passing.

### Pattern: WAVE_5_IMAGES_DISPATCH.md mandated TestBed-free workaround
The dispatch document explicitly stated the "Proven workaround" for the Angular 21 + Vitest crash:
  - Extract business logic into `image-uploader.model.ts` (pure TypeScript, no Angular decorators)
  - Write Vitest tests against pure functions
  - Minimum: cover the 5 pre-check gates
This pattern was already established in dashboard.model.ts, smart-picker.model.ts, catalog-form.model.ts.

### Model expansion — new pure functions added
Original model had: `buildPrecheckItems`, `slotProgress`
New functions added to image-uploader.model.ts:
- `computeCanContinue(images[])` — gate for "Continue to Preview" button
- `computeActiveExpandedImage(images[], expandedSlot)` — precheck report panel
- `toggleExpandedSlot(current, index)` — expand/collapse toggle semantics
- `addSlots(currentImages, fileNames, maxSlots)` — max-6 enforcement (abstracted from File[] for pure testability)
- `resetSlot(images[], slotIndex)` — immutable re-upload reset
- `applySimulationResult(images[], slotIndex, precheck)` — immutable simulation result application
- `statusForMeeStatusBadge(imageStatus)` — maps pass/fail/pending to ready/failed/pending (ProductStatus union)

### Pattern: addSlots uses string[] not File[] for pure testability
- `addSlots(currentImages, fileNames: string[], maxSlots)` — file names (strings) instead of File objects.
- The component's `onFilesSelected` creates the actual ProductImage slots with URL.createObjectURL.
- Separating the slot-counting logic (pure, testable) from the DOM-bound File API is the correct split.
- In tests: `addSlots(existing, ['a.jpg', 'b.jpg'])` — no File constructor needed.

### Pattern: component delegates to model, does not duplicate logic
After adding model functions, the component methods become 1-3 line delegates:
- `canContinue = computed(() => computeCanContinue(this.images()))`
- `activeExpandedImage = computed(() => computeActiveExpandedImage(this.images(), this.expandedSlot()))`
- `expandSlot(index) { this.expandedSlot.update(c => toggleExpandedSlot(c, index)); }`
- `onReupload(i) { this.images.update(prev => resetSlot(prev, i)); ... }`
- Private `simulateSlot(i)` calls `applySimulationResult` inside the `setTimeout` callback.

### Spec result
- 34 tests, 8 describe() blocks, ZERO TestBed, ZERO Angular imports
- All 5 pre-check gates + canContinue gate + expand/collapse + addSlots + resetSlot + applySimulation + statusMap
- 8 original pure-function tests preserved (buildPrecheckItems × 7 + slotProgress × 3)
- 26 new pure-function tests added (computeCanContinue × 5, computeActiveExpandedImage × 3,
  toggleExpandedSlot × 3, addSlots × 4, resetSlot × 3, applySimulationResult × 3, statusForMeeStatusBadge × 3)

### Build result (2026-06-10 Wave 5 F9)
- pnpm run build: ZERO errors, 2.862s
- image-uploader-component lazy chunk: 9.78 kB / 3.20 kB gzip (budget ≤80 kB — 96% headroom)
- 34/34 images spec tests pass (8 describe blocks)
- Full suite: 113/163 passed; 50 failures all pre-existing (TestBed ngModule null)
- Boundary: CLEAN — grep -r "from 'primeng/" features/images/ → EMPTY
- Route: /catalogs/:id/images added to app.routes.ts inside shell canActivate:[authGuard]

---
