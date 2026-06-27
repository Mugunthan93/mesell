## Session 2026-06-07 — Onboarding Dispatch 4 — OnboardingWizardComponent Phase 2+3 wiring {#onboarding-dispatch-4}

### Route touched
`/onboarding` — features/account/onboarding/onboarding.component.ts (update)

### Services consumed
None (structural wiring only — API service stub; real data from onboarding-api.service.ts lands in next dispatch).

### Pattern: Intra-feature imports (same feature folder — allowed per §17)
- §17 cross-feature import rules prohibit importing between DIFFERENT features.
- Imports WITHIN the same feature folder (features/account/onboarding/ importing from
  features/account/components/) are explicitly allowed — they are intra-feature.
- Import path: `'../components/super-category-chips/super-category-chips.component'`
  (relative path within features/account/ — correct per §3 relative-within-feature rule)
- Same for ComplianceStepComponent: `'../components/compliance-step/compliance-step.component'`
- Also import the `FieldSpec` interface from the compliance step file directly:
  `import { ComplianceStepComponent, FieldSpec } from '../components/compliance-step/...'`
  The type is exported from the component file itself (single source of truth).

### Pattern: Passing signal VALUE (not signal ref) to @Input()
- `[saving]="saving()"` — call the signal with `()` to pass the current value to a plain `@Input()`.
- The child component receives a boolean, not a WritableSignal<boolean>.
- `[saving]="saving"` (without parentheses) would pass the signal object itself — TypeScript
  strict mode catches this as a type mismatch when the input is typed `boolean`.
- This is distinct from signal INPUTS (`input<boolean>(false)`) on children — those accept
  direct bindings differently. For PLAIN `@Input() saving = false`, always call the signal.

### Pattern: overrideComponent stub pattern for @Input({ required: true }) decorator metadata
- `@Input({ required: true })` uses Angular's DECORATOR metadata, NOT the signal `input.required()` API.
- For plain required @Input decorators: TestBed.overrideComponent() + stub class with matching
  `@Input()` declarations is the correct isolation approach.
- This is DIFFERENT from signal `input.required()` (which throws NG0950 if not set before template evaluation).
- For `@Input({ required: true })` decorator metadata: NG0950 risk is lower but Angular still validates
  at component initialization — using stubs avoids any validation entirely.
- Stub pattern:
  ```typescript
  @Component({ selector: 'mee-compliance-step', standalone: true, template: '' })
  class ComplianceStepStub {
    @Input() superCategoryId = '';
    @Input() fields: unknown[] = [];
    @Input() saving = false;
    @Output() formSubmit = new EventEmitter<Record<string, string | null>>();
    @Output() formBack = new EventEmitter<void>();
  }
  ```
  Note: stub uses plain `@Input()` WITHOUT `required: true` — no validation on the stub itself.
- Override:
  ```typescript
  TestBed.overrideComponent(OnboardingWizardComponent, {
    remove: { imports: [SuperCategoryChipsComponent, ComplianceStepComponent] },
    add:    { imports: [SuperCategoryChipsStub, ComplianceStepStub] },
  })
  ```
  Both must be listed in `remove[]` explicitly — empty `remove: { imports: [] }` does nothing.

### Pattern: [attr.aria-label] for native HTML attributes on Material components
- `[aria-label]="expr"` causes NG8002 error in production builds when used on Angular Material
  components (e.g., `mat-chip-listbox`) — Angular treats it as an attempted component @Input binding.
- `aria-label="{{ expr }}"` interpolation ALSO causes NG8002 for the same reason — the compiler
  still sees it as a native attribute binding attempt on a Material component.
- CORRECT: `[attr.aria-label]="expr"` — Angular's canonical way to set a native HTML attribute
  on any element regardless of whether the host is a Material component.
- This was a pre-existing bug in super-category-chips.component.ts from Dispatch 3 (not caught
  until this dispatch ran the production build with the component actually imported into the wizard).

### Pattern: stepper.previous() in child formBack handler
- `(formBack)="stepper.previous()"` — binds the compliance step's Back button to the parent
  wizard's MatStepper directly in the template.
- `stepper` is a `@ViewChild('stepper') stepper!: MatStepper` on the wizard component.
- Template reference bindings to @ViewChild refs work correctly in event handler expressions
  because the event fires only after the view is initialized (stepper is guaranteed non-null).

### Build result (2026-06-07 Onboarding Dispatch 4)
- ng build --configuration=production: ZERO errors; 4 pre-existing NG8102 warnings unchanged
- onboarding-component lazy chunk: 11.58 kB raw / 3.37 kB gzip (budget <=80 kB — PASS)
- 7/7 tests passing (4 existing + 3 new)

---
