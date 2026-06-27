## Session 2026-06-09 — Wave 5 Dispatch Authoring F6/F7/F8 {#wave5-dispatch-authoring}

### Task
Authored THREE Wave 5 dispatch documents (spec documents only — no component code).

### Pattern: Dynamic form — Record signal not FormGroup
- CatalogFormComponent fields are runtime-defined from JSONB schema. Field count/names unknown at compile time.
- CORRECT: fieldValues = signal<Record<string, unknown>>({}) updated on each field event.
- Do NOT use FormBuilder.group() with dynamic keys — TypeScript strict rejects without casts.
- Per-field validation: getFieldError(canonicalName) — plain method checking fieldValues() for required presence.

### Pattern: AI autofill highlight via [class.mee-ai-suggested] binding
- Avoids inline style (prohibited) and separate [style] binding.
- CSS class (in component styles): background-color: var(--mee-color-warning-light); border-color: var(--mee-color-warning).
- Binding: [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)".
- isAiSuggested() is a plain method (name in this.aiSuggestions()), NOT a computed — parameterized lookups cannot be computed().
- Highlight clears when key removed from aiSuggestions() signal — no DOM manipulation needed.

### Pattern: MeeToastService NOT MatSnackBar in Wave 5 features
- Layer 4 features cannot import from @angular/material/* — architecture boundary violation.
- All toast surfaces in features use MeeToastService (from ../../ui).
- Older component dispatches (pre-architecture-lock) used MatSnackBar — those are legacy and will be refactored.

### Pattern: Simulation delay calibration (Wave 5)
- Product list: delay(800) — DB query 20 rows
- Gemini suggest: delay(1200) — V1 spec 3s P95 budget
- Category schema: delay(800) — lightweight JSONB fetch
- Autofill: delay(2000) — V1 spec 5s P95 budget
- Autosave PATCH: delay(300) — fast DB write

### Pattern: mee-tree-select for manual category fallback
- mee-tree-select wraps p-treeSelect (PrimeNG); accepts MeeTreeNode[] nodes.
- Smart Picker uses it as a fallback when no AI suggestions match or user prefers manual browse.
- For Wave 5 simulation: static 2-level tree stub after 600ms delay. Real tree (3,772 nodes) is Wave 6 work.
- showFallback = signal(false) — toggled by "Browse manually" link. mee-tree-select only rendered when showFallback().

### Dispatch docs authored
- docs/ui_ux/WAVE_5_DASHBOARD_DISPATCH.md — F6 /dashboard — DashboardComponent
- docs/ui_ux/WAVE_5_SMART_PICKER_DISPATCH.md — F7 /catalogs/new — SmartPickerComponent
- docs/ui_ux/WAVE_5_CATALOG_FORM_DISPATCH.md — F8 /catalogs/:id/edit — CatalogFormComponent

---
