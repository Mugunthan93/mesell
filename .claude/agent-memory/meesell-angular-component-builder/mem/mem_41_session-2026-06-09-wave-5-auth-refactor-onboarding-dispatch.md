## Session 2026-06-09 — Wave 5 Auth Refactor + Onboarding Dispatch Docs {#wave5-auth-onboarding-dispatch}

### Task
Authored TWO Wave 5 dispatch documents (spec-only, no frontend code written):
- docs/ui_ux/WAVE_5_AUTH_REFACTOR_DISPATCH.md — F2/F3/F4 refactor
- docs/ui_ux/WAVE_5_ONBOARDING_DISPATCH.md — F5 new page

### Key pattern: Auth refactor import surgery (exact list)
Per-file removals and additions documented in the dispatch:
- login.component.ts: remove InputText/Button, add MeeInputComponent/MeeButtonComponent
- signup.component.ts: same as login
- otp-verify.component.ts: remove InputOtp/Button, add MeeOtpInputComponent/MeeButtonComponent
Boundary check: `grep -r "from 'primeng" features/auth/` must return ZERO after refactor.

### Key pattern: OtpVerify CVA strategy change
mee-otp-input does NOT participate in ReactiveFormsModule via formControlName.
It emits via (completed) output. Correct migration:
- Drop FormGroup otp control entirely
- Add `otpValue = signal<string>('');`
- `onOtpCompleted(v: string): void { this.otpValue.set(v); }`
- Disable button: `[disabled]="otpValue().length < 6"`
- Use `this.otpValue()` in onSubmit() instead of form.get('otp')?.value

### Key pattern: Onboarding field selection
V1_FEATURE_SPEC does NOT enumerate onboarding fields. Three fields chosen from
inferred seller-profile shape: businessName (required), city (required, default 'Tirupur'),
gstNumber (optional). Super-category, address, logo, bank deferred to V1.5.
Custom optionalGstValidator: same pattern as optionalPincodeValidator from Profile dispatch.

### Key pattern: mee-steps decorative usage
For simple single-form onboarding, mee-steps is decorative only:
  steps = [{ label: 'Account' }, { label: 'Business' }, { label: 'Done' }]
  [active_index]="1" — static, no navigation
No multi-step logic needed for MVP.

### Architecture note
Both dispatches depend on Wave 3 (UI Kit) + Wave 4 (Composites) completing first.
F2-F4 and F5 are in Wave 5 Parallel Group A per FRONTEND_WAVE_EXECUTION_PLAN.md.

---
