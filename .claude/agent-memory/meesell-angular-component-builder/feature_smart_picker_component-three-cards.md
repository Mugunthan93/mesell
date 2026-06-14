# feature_smart_picker_component-three-cards.md

## Session header
Session: mesell-smart-picker-frontend-session-1
Date: 2026-06-11
Branch: feature/smart-picker/frontend
Worktree: /private/tmp/mesell-wt/smart-picker-frontend

## Files touched
- RENAME: frontend/src/app/features/catalog-new/ -> features/smart-picker/ (git mv, history-preserving)
- RENAME: catalog-new.component.ts -> smart-picker.component.ts (CatalogNewComponent -> SmartPickerComponent; selector app-catalog-new -> app-smart-picker)
- RENAME: catalog-new.component.spec.ts -> smart-picker.component.spec.ts (content fully replaced)
- RENAME: services/smart-picker-api.service.ts -> services/category.service.ts (SmartPickerApiService -> CategoryService; simulated body preserved)
- MODIFY: frontend/src/app/features/smart-picker/smart-picker.model.ts — replaced invented model with §9.E-locked interfaces
- NEW: frontend/src/app/features/smart-picker/category-card.component.ts
- NEW: frontend/src/app/features/smart-picker/category-card.component.spec.ts
- MODIFY: frontend/src/app/app.routes.ts — /catalogs/new import path updated (path unchanged)
- MODIFY: docs/status/STATUS_FRONTEND.md

## What was done
- Executed D4 git mv rename (catalog-new -> smart-picker) as first commit on the branch. git log --follow correctly traces spec file back through the rename (7001b44 pre-rename commit visible).
- Replaced smart-picker.model.ts entirely: removed CategorySuggestionModel/commission_pct/0-100 confidence. New: CategorySuggestion + SuggestResponse matching §9.E field-for-field. Pure helpers retyped to new shapes.
- Built SmartPickerComponent: standalone, OnPush, signals (loading/suggestions/fallbackOffered). Reactive form description with minLength(10)+maxLength(500). valueChanges -> debounce(400)+distinctUntilChanged+filter(valid) -> switchMap -> CategoryService.suggest(). suggestions().slice(0,3) in @for. EmptyStateComponent for fallback+empty. Secondary "Browse if none match" button for fallback+non-empty.
- Built CategoryCardComponent: standalone, OnPush, input.required() suggestion, @Output() picked EventEmitter<string>. Renders path + mee-progress-bar([value]=confidence*100) + reasons.slice(0,3) + "Use this category" mee-button -> picked.emit(category_id). NO commission_pct.
- Renamed category.service.ts class SmartPickerApiService -> CategoryService; updated method signatures to match what component calls (suggest returns Observable<SuggestResponse>, selectCategory returns Observable<{id}>, browseRedirect returns void); simulated bodies preserved for service-builder.
- Updated app.routes.ts: /catalogs/new now loads SmartPickerComponent from features/smart-picker/smart-picker.component. Route PATH unchanged.
- Wrote 44 pure-function Vitest tests (2 spec files, 0 failures).

## Test results
- smart-picker.component.spec.ts: 29 tests PASS — covers: validateDescription (6), derivePickerState (8), topN/top-3 (5), sortByConfidence (3), buildEditRoute (2), §9.E conformance (5)
- category-card.component.spec.ts: 15 tests PASS — covers: confidence scaling 0-1 -> *100 (6), reasons max-3 (3), picked emission (3), commission_pct absent (1), path/leaf_name (2)
- Total: 44/44 PASS
- Build: PASS — smart-picker-component chunk 23.45 kB dev

## Open items
- CategoryService HTTP wiring: service-builder must rewrite suggest/selectCategory/browseRedirect to use real ApiClient (HttpClient) in the next session
- The simulated body uses the new §9.E interface shapes — service-builder only needs to replace `of(SIMULATED_RESPONSE)` with actual HTTP calls
- model interfaces MUST end identical in service-builder's verified slice — no drift from §9.E allowed

## Cross-feature gotchas
- The EmptyStateComponent from @mesell/composites takes: icon (required string), message (required string), cta_label (optional string), cta_click (output void). Does NOT accept content projection or title/subtitle inputs. Template must use these exact props.
- MeeSkeletonComponent selector is mee-skeleton (not mee-loading-skeleton). variant='card' is valid.
- PageHeaderComponent: title (required), subtitle (optional), cta_label (optional), cta_icon (optional).
- MeeProgressBarComponent: value (required number 0-100), label (optional string), show_value (optional boolean). For confidence (0-1 float): multiply by 100 in the component computed signal, NOT in the model.
- worktree path is /private/tmp/mesell-wt/smart-picker-frontend (symlink /tmp/mesell-wt -> /private/tmp/mesell-wt). node_modules symlinked from main tree for build.
- git worktree was prunable after its directory was deleted mid-session. Re-added with `git worktree add`. All file writes must use absolute /private/tmp/... path.

## Next-session brief
The SmartPickerComponent is PR-ready. CategoryService has correct method signatures and simulated bodies. meesell-angular-service-builder should:
1. Read category.service.ts — it now has CategoryService class with suggest()/selectCategory()/browseRedirect() with correct return types matching §9.E
2. Replace the `of(SIMULATED_RESPONSE)` body with real HttpClient.get<SuggestResponse>('/api/v1/categories/suggest', { params: { q: description } })
3. Replace selectCategory with real POST /api/v1/catalogs + Router.navigate to /catalogs/:id/edit
4. Verify model interfaces match §9.E (they already do — field-for-field verified this session)
5. Do NOT touch component files, spec files, or the model file body
