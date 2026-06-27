## Session 2026-06-09 — Wave 5 F5 Onboarding — VERIFIED + SPEC FIX {#wave5-f5-onboarding}

### Route touched
`/onboarding` — features/account/onboarding/

### Services consumed
`Router` only. No API calls (simulate only per dispatch spec).

### Finding: Component already complete from prior session
`onboarding.component.ts` was already correctly authored in a prior session (matching all Wave 5 F5 spec requirements exactly):
- Standalone + OnPush
- ReactiveFormsModule via `inject(FormBuilder)`
- Three fields: businessName (required), city (required, default 'Tirupur'), gstNumber (optional)
- `optionalGstValidator()` custom validator exported from the file
- `loading` + `submitted` signals; three `computed()` error helpers
- `<mee-auth-layout>` wrapper with `<mee-steps>` + `<mee-input>` x3 + `<mee-button>`
- ZERO PrimeNG imports; ZERO Angular Material imports
- Route already in app.routes.ts inside shell canActivate:[authGuard] children

### Bug fixed: MeeInputStub missing CVA registration in spec
The spec file had `MeeInputStub` WITHOUT `NG_VALUE_ACCESSOR` + `ControlValueAccessor`.
This caused `NG01203: No value accessor for form control name: 'businessName'` at TestBed runtime.
All 8 `OnboardingComponent` tests failed.

FIX: Added CVA to stub:
```typescript
@Component({
  selector: 'mee-input',
  standalone: true,
  template: '<input class="mee-input-stub" />',
  providers: [{ provide: NG_VALUE_ACCESSOR, useExisting: forwardRef(() => MeeInputStub), multi: true }],
})
class MeeInputStub implements ControlValueAccessor {
  @Input() label: string | undefined = undefined;
  @Input() required = false;
  @Input() error: string | undefined = undefined;
  writeValue(_v: unknown): void {}
  registerOnChange(_fn: (_: unknown) => void): void {}
  registerOnTouched(_fn: () => void): void {}
  setDisabledState?(_isDisabled: boolean): void {}
}
```

Also removed unused `AuthLayoutComponent` import from the spec (it was imported but
not used since we override with stubs; Angular compilation did not reject it but it
was dead code that triggers confusion).

### Pattern: EVERY mee-input stub in specs MUST implement CVA
Any component that uses `formControlName="..."` binding on a child stub must register
`NG_VALUE_ACCESSOR`. Without it, NG01203 fires at TestBed runtime on detectChanges().
This applies to:
- mee-input (wraps CVA)
- mee-otp-input (wraps CVA)
- mee-select (wraps CVA)
- mee-password-input (wraps CVA)
- mee-textarea (wraps CVA)

Non-CVA stubs (mee-steps, mee-button, mee-badge, mee-card) do NOT need this.

### Build result (2026-06-09 Wave 5 F5 Onboarding)
- pnpm run build: ZERO errors, 3.112s
- onboarding-component chunk: 3.52 kB raw / 1.34 kB gzip (budget ≤80 kB — PASS)
- 12/12 onboarding tests pass in isolation (8 OnboardingComponent + 4 optionalGstValidator)
- Boundary: grep features/account/onboarding/ for primeng → EMPTY
- Route: /onboarding registered in app.routes.ts inside shell guard children (pre-existing)

---
