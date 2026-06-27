## Session 2026-06-07 — Auth Dispatch 3 — OtpVerifyComponent body {#auth-dispatch-3}

### Route touched
`/signup` + `/login` — features/auth/components/otp-verify/

### Services consumed
`AuthApiService` (verifyOtp + sendOtp) + `ApiClient` (GET /seller-profile) + `ErrorService` (core)

### Pattern: ng-otp-input is an NgModule package (NOT standalone)
- `ng-otp-input` v1.9.3 exports `NgOtpInputModule` (NgModule) and `NgOtpInputComponent`.
- In the component's `imports[]` array: use `NgOtpInputModule` (the NgModule) — NOT `NgOtpInputComponent` directly.
- Import `NgOtpInputComponent` type-only for the `@ViewChild` type annotation.
- `NgOtpInputComponent.setValue(value)` — method for programmatic OTP reset (called on resend + verify error).
- `NgOtpInputComponent` has `onInputChange: EventEmitter<string>` output — bind as `(onInputChange)="onOtpChange($event)"`.
- The `config` input accepts `{ length, allowNumbersOnly, inputStyles }` object.
- Import path for both: `'ng-otp-input'` (the public_api.d.ts re-exports both).

### Pattern: DestroyRef + takeUntilDestroyed for interval countdown
- Inject `DestroyRef` explicitly: `private readonly destroyRef = inject(DestroyRef)`.
- `interval(1000).pipe(take(60), takeUntilDestroyed(this.destroyRef)).subscribe(...)` — 60-tick countdown.
- `take(60)` + `timeLeft.update(t => Math.max(0, t - 1))` caps at 0 without going negative.
- `startCountdown()` extracted as a private method — call from `ngOnInit()` AND `onResend()`.
- New call to `startCountdown()` on resend resets `timeLeft.set(60)` before starting interval.
- CRITICAL: `takeUntilDestroyed(destroyRef)` prevents RxJS subscriptions from leaking when component unmounts mid-countdown.

### Pattern: Post-verify routing with nested subscribe (Q-AUTH-003 Option A)
- After verifyOtp() success: call `apiClient.get<SellerProfile>('/seller-profile')` to check `profile.profile_complete`.
- 200 + `profile_complete: true` → navigate to `/dashboard`.
- 200 + `profile_complete: false` → navigate to `/onboarding`.
- 404 or any other error from /seller-profile → navigate to `/onboarding` (safe fallback).
- `verifying` stays `true` throughout the nested call — component unmounts on navigate, signal is abandoned.
- Do NOT call `verifying.set(false)` in the next handler — it would briefly flash UI before unmount.

### Pattern: attempts() counter — increment then check (post-increment semantics)
- `this.attempts.update(a => a + 1)` increments the signal.
- `if (this.attempts() >= 3)` reads the new value AFTER the update.
- This means on the 3rd wrong OTP: attempts goes 2→3, then the ≥3 branch fires showing "too many attempts".
- The Verify button also disables when `attempts() >= 3` via template binding.

### Pattern: displayPhone as computed() reading a @Input() property
- `displayPhone = computed<string>(() => { const p = this.phone; if (p.startsWith('+91')) return p.slice(3); return p; })`
- `this.phone` is a plain `@Input()` property (not a signal), NOT `this.phone()`.
- `computed()` that reads non-signal properties will NOT reactively update if `phone` changes.
- This is acceptable here because `phone` is set once by parent and never changes during the component's lifetime.
- If the parent could dynamically change phone, use `input()` signal instead of `@Input()`.

### Pattern: @ViewChild with null guard on setValue
- `@ViewChild('otpInput') otpInput!: NgOtpInputComponent;`
- Call with null guard: `if (this.otpInput) { this.otpInput.setValue(''); }` — ViewChild is defined after view init; guard prevents error if called before init.

### Pattern: NG0303 warning resolved by proper @Input declarations
- The stub had `@Input() phone = ''` and `@Input() requestId = ''` (no required).
- Signup + login specs were logging NG0303 "Can't bind to 'phone'" warnings because the stub's @Input wasn't being recognized in the TestBed context for those parent component tests.
- Full body with `@Input({ required: true })` properly resolves the binding — NG0303 warnings from signup/login specs disappear.

### Build result (Auth Dispatch 3)
- ng build --configuration=production: EXIT 0, zero errors
- 6/6 new OtpVerify tests pass; 229/242 total; 13 pre-existing failures (unchanged)
  Pre-existing failures: 7 export.spec (NG0300) + 1 shell.spec (Jasmine) + 6 dashboard.spec (styleUrl)
  Note: The "7 pre-existing" count in Wave 2c memory undercounts — actual pre-existing count is 13
  (dashboard.component.spec.ts has 6 styleUrl failures that also pre-exist)

---
