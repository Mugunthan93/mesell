## Session 2026-06-07 — Onboarding Dispatch 3 — ComplianceStepComponent {#onboarding-dispatch-3}

### Route touched
`/onboarding` — features/account/components/compliance-step/

### Services consumed
None. Pure UI component — no API calls.

### Pattern: FieldSpec inline interface (compliance required-fields vs catalog FieldSchema)
- `@core/models/field-schema.model.ts#FieldSchema` is the catalog wizard field shape
  (canonicalName, PrimitiveKind, StepId, LocaleMap displayLabel, etc.) — completely different
  from the compliance required-fields FieldSpec below.
- Backend's `RequiredFieldsResponse.extension_fields` uses a per-field FieldSpec with:
  `field_name`, `display_name`, `display_help` (plain string NOT LocaleMap),
  `field_type: 'text' | 'date' | 'select'`, `required: boolean`, `options: string[] | null`
- Solution: define inline `FieldSpec` interface in the component file with
  `// TODO(cross-cutting)` comment. Export it (the spec file imports it directly).
- Exporting the inline interface is required when the spec file uses the same type
  (avoids duplication and keeps the single source of truth in the component file itself).

### Pattern: Dynamic reactive form built in ngOnChanges from FieldSpec[]
- `form!: FormGroup` — not initialized in constructor, built on first ngOnChanges call.
- Guard: `if (!this.fields?.length) return;` — do not build an empty FormGroup.
- `for (const field of this.fields)` iterates fields, builds `Record<string, AbstractControl>`.
- `initial = this.completed[field.field_name] ? '' : null` — empty string for already-saved
  fields (allows clearing), null for fresh fields (marks required controls invalid).
- `new FormControl(initial, field.required ? [Validators.required] : [])` — inline FormControl,
  not via FormBuilder.control() — both work, inline version avoids overload ambiguity.
- `this.form = this.fb.group(controls)` — rebuild the entire group on each ngOnChanges.
- Rebuilding on each ngOnChanges is correct here: fields can change when superCategoryId changes.
- @if (form) guard in template prevents access to undefined form during the pre-change tick.

### Pattern: @if field_type dispatch in mat-form-field with Philosophy F5 enforcement
- Three cases: `field_type === 'select' && field.options?.length` → mat-select;
  `field_type === 'date'` → native date input; else → text input.
- CRITICAL defensive case: when `field_type === 'select'` but `options` is null → falls
  back to text input. Prevents blank mat-select with no options.
- Philosophy F5: `<mat-hint>{{ field.display_help }}</mat-hint>` is ALWAYS rendered
  regardless of field_type. The mat-hint block is outside all @if/@else branches — it
  is unconditional. This is the correct enforcement position.
- appearance="outline" on all mat-form-field per Spike form-field-overrides SECTION 10.
- `[formControlName]="field.field_name"` — square bracket binding required (dynamic key).

### Pattern: CATEGORY_NAMES as component-level constant (NOT a signal)
- `private readonly CATEGORY_NAMES: Record<string, string>` at CLASS level (after the class
  keyword) — NOT as a top-level module constant and NOT a signal.
- Wait — actually correct location is OUTSIDE the class as a module-level const OR
  inside as a private readonly class member. Either is valid. This dispatch used a
  module-level `const CATEGORY_NAMES` outside the class for clarity.
- `get categoryName(): string` getter reads `CATEGORY_NAMES[this.superCategoryId] ?? this.superCategoryId`
  — returns the raw ID as fallback for unknown super-categories.

### Pattern: setInput() for plain @Input() in zoneless TestBed (CRITICAL correction)
- Direct property assignment: `component.superCategoryId = '26'` does NOT trigger `ngOnChanges`
  in zoneless TestBed (provideExperimentalZonelessChangeDetection()).
- CORRECT: `fixture.componentRef.setInput('superCategoryId', '26')` triggers the Angular
  change detection pipeline including ngOnChanges.
- This is DIFFERENT from the signal input NG0950 issue (signal `input.required()` throws
  when setInput triggers template evaluation before the signal has a value).
- For PLAIN @Input() decorators: setInput() is safe and correctly fires ngOnChanges.
- Memory update: the earlier NG0950 pattern applies only to `input.required()` SIGNAL inputs.
  For plain `@Input({ required: true })` decorator metadata, setInput() works correctly.
- Call order: `setInput()` BEFORE `detectChanges()` — this ensures ngOnChanges fires with
  the correct values during the first change detection pass.

### Pattern: en.json flat key format for compliance namespace
- en.json uses flat dot-notation keys — NOT nested JSON objects.
- The spec said to add `"compliance": { "title": ... }` (nested) but en.json is FLAT.
- Correct keys added: `"onboarding.compliance.title"`, `"onboarding.compliance.fieldRequired"`,
  `"onboarding.compliance.save"`.
- Key `"onboarding.actions.back"` already existed — no duplicate.
- Template uses: `{{ 'onboarding.compliance.title' | transloco : { category: categoryName } }}`
  Transloco's `{{category}}` interpolation syntax (double curly inside single-quoted key string).

### Build result (2026-06-07 Onboarding Dispatch 3)
- ng build --configuration=production: ZERO errors, 4 pre-existing warnings (unchanged)
- onboarding-component lazy chunk: 1.53 kB gzip (ComplianceStepComponent not yet imported
  by OnboardingComponent — it will be wired in Dispatch 4; chunk grows then)
- 4/4 new tests passing (Vitest)

---
