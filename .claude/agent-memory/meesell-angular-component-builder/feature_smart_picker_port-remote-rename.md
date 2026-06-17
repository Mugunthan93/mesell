# feature_smart_picker_port-remote-rename.md

## Session header
Session: mesell-smart-picker-port-frontend-session-1
Date: 2026-06-11
Branch: feature/smart-picker-wiring/frontend
Worktree: /private/tmp/mesell-wt/smart-picker-wiring

## Files touched
- RENAME (git mv, R100): apps/mfe-catalog/src/app/catalog-new/ -> apps/mfe-catalog/src/app/smart-picker/
- RENAME (git mv, R100): catalog-new.component.ts -> smart-picker.component.ts
- RENAME (git mv, R100): catalog-new.component.spec.ts -> smart-picker.component.spec.ts
- RENAME (git mv, R100): services/smart-picker-api.service.ts -> services/category.service.ts
- RENAME (git mv, R100): smart-picker.model.ts -> smart-picker.model.ts (no-op, already correct)
- MODIFY: apps/mfe-catalog/src/app/smart-picker/smart-picker.model.ts — replaced invented model with §9.E-locked interfaces
- MODIFY: apps/mfe-catalog/src/app/smart-picker/smart-picker.component.ts — full contract fix (class+selector rename, MeeTreeSelect/SIMULATED_TREE removed, D1/§9.E port from e97c4f5)
- MODIFY: apps/mfe-catalog/src/app/smart-picker/smart-picker.component.spec.ts — ported from e97c4f5, adjusted import paths
- MODIFY: apps/mfe-catalog/src/app/smart-picker/services/category.service.ts — class SmartPickerApiService -> CategoryService; §9.E-shaped simulated stub
- NEW: apps/mfe-catalog/src/app/smart-picker/category-card.component.ts
- NEW: apps/mfe-catalog/src/app/smart-picker/category-card.component.spec.ts
- MODIFY: apps/mfe-catalog/src/app/catalog.routes.ts — import path updated (catalog-new -> smart-picker)

## What was done

### Commit #1 (7866499) — D4 git mv
- Executed D4 git mv per FEATURE_PLAN §D4 as first commit on the branch.
- 4 renames applied inside apps/mfe-catalog/src/app/:
  catalog-new/ -> smart-picker/
  catalog-new.component.ts -> smart-picker.component.ts
  catalog-new.component.spec.ts -> smart-picker.component.spec.ts
  services/smart-picker-api.service.ts -> services/category.service.ts
  smart-picker.model.ts was already correctly named — git mv of folder captured it.
- All R100 (100% similarity, blob-hash-identical). git log --follow traces to SP05 commit f11d0bf.
- NOTE: the smart-picker.model.ts rename from catalog-new/ -> smart-picker/ was captured as part of the folder mv (the file already had the correct name within the folder).

### Commit #2 (09af9db) — SmartPickerComponent §9.E/D1 contract fix
- smart-picker.model.ts: completely replaced invented model (CategorySuggestionModel with commission_pct, 0-100 confidence, SIMULATED_SUGGESTIONS constant) with §9.E-locked interfaces:
  - CategorySuggestion: category_id, super_id, super_name, path, leaf_name, confidence (0-1), reasons[]
  - SuggestResponse: suggestions[], fallback_offered boolean
  - Pure helpers retyped: sortByConfidence/topN/buildEditRoute/derivePickerState/validateDescription
  - confidence stays 0-1 in the model. Scale *100 ONLY at display layer.

- SmartPickerComponent:
  - class CatalogNewComponent -> SmartPickerComponent; selector app-catalog-new -> app-smart-picker
  - MeeTreeSelect import removed; SIMULATED_TREE constant removed; Router import removed
  - MeeSkeletonComponent replaces LoadingSkeletonComponent (the composites component renamed in SP03)
  - EmptyStateComponent from @mesell/composites used for fallback+empty path
  - CategoryCardComponent (new) used for each suggestion card
  - Reactive form: description field minLength(10)+maxLength(500). descCtrl.valueChanges -> debounceTime(400)+distinctUntilChanged+filter(valid)+switchMap(categoryService.suggest)
  - signals: loading, suggestions (CategorySuggestion[]), fallbackOffered
  - suggestions().slice(0,3) in @for — top-3 only per D1
  - fallbackOffered+empty -> EmptyStateComponent with cta_label="Browse all categories" (cta_click)->onBrowse()
  - fallbackOffered+non-empty -> secondary button "Browse if none match" -> onBrowse()
  - onBrowse() delegates to categoryService.browseRedirect()

- CategoryCardComponent (new):
  - input.required<CategorySuggestion>() for suggestion
  - confidencePct = computed(() => Math.round(suggestion().confidence * 100)) — 0-1 -> 0-100 at display
  - mee-progress-bar [value]="confidencePct()" — display layer scaling confirmed
  - reasons().slice(0,3) in @for
  - NO commission_pct rendered
  - @Output() readonly picked = new EventEmitter<string>() — emits category_id on "Use this category"
  - role="listitem" + aria-label from cardAriaLabel computed signal
  - min-height:44px on mee-button for touch target

- CategoryService (category.service.ts):
  - class SmartPickerApiService -> CategoryService
  - suggest() return type: Observable<SuggestResponse> (not Observable<CategorySuggestion[]>)
  - SIMULATED_RESPONSE uses §9.E-shaped objects (confidence 0-1 floats, super_id, super_name, leaf_name, reasons)
  - selectCategory() returns Observable<{id: string}> (service-builder Phase B replaces body)
  - browseRedirect() is a no-op stub (service-builder Phase B adds Router.navigate)

- catalog.routes.ts:
  - 'new' route: import('./catalog-new/catalog-new.component').then(m => m.CatalogNewComponent)
    -> import('./smart-picker/smart-picker.component').then(m => m.SmartPickerComponent)
  - All 5 CATALOG_ROUTES preserved (R-SP3-1)

## Test results
- smart-picker.component.spec.ts: 29 tests PASS (ported from e97c4f5, adjusted import paths)
- category-card.component.spec.ts: 15 tests PASS (new, ported from e97c4f5)
- mfe-catalog suite: 5 spec files / 142 tests PASS
- Total suite: 44 spec files (43 baseline + 1 new category-card spec)
- 229 tests PASS (36 spec files FAIL in src/ — all pre-existing @mesell/composites resolution errors, unchanged from develop baseline)
- mfe-catalog remote build: GREEN 2.742s
- shell build: GREEN 2.807s (both < 90s D12)
- tsc --noEmit (app + spec tsconfigs): CLEAN

## Open items
- Phase B (service-builder): rewrite CategoryService.suggest/selectCategory/browseRedirect with real HttpClient
  - suggest: HttpClient.get<SuggestResponse>('/api/v1/categories/suggest', { params: { q: description } })
  - selectCategory: POST /api/v1/catalogs + Router.navigate(['/catalogs', id, 'edit'])
  - browseRedirect: Router.navigate(['/categories/browse'])
- The §9.E model is field-for-field locked — service-builder must not change it

## Cross-feature gotchas
- mfe-catalog smart-picker now uses MeeSkeletonComponent (selector mee-skeleton) — NOT LoadingSkeletonComponent
  - This is because @mesell/composites renamed LoadingSkeletonComponent -> MeeSkeletonComponent in SP03
  - The old catalog-new.component.ts had LoadingSkeletonComponent — this was one of the contract-wrong items
- EmptyStateComponent from @mesell/composites: props are icon (string), message (string), cta_label (optional string), (cta_click) output void
- MeeProgressBarComponent from @mesell/ui-kit: [value] accepts 0-100 number, label string, [show_value] boolean
- confidence in §9.E is ALWAYS 0.0-1.0 float — never store 0-100. Scale at display layer only.
- pnpm-workspace.yaml gets auto-modified by ng build adding @parcel/watcher and msgpackr-extract entries — always git checkout -- it after a build run, do NOT commit it

## Next-session brief
SmartPickerComponent is ready for service-builder Phase B. CategoryService.ts is at
apps/mfe-catalog/src/app/smart-picker/services/category.service.ts with correct method
signatures and §9.E-shaped simulated stubs. Service-builder should replace the of(SIMULATED_RESPONSE)
bodies with real HttpClient calls. The §9.E model at smart-picker.model.ts must not be changed —
it is field-for-field verified. After Phase B the integration branch can be updated and the
founder-gate PR opened.
