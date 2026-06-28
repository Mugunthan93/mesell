## project: auth_onboarding_responsive_polish (2026-06-18)

Task: Audit and fix mfe-auth + mfe-onboarding responsive layout at 360px.
Branch: design-figma-ui-screens (worktree)

Pages / components touched:
  - auth-layout.component.ts (libs/composites) — used by login, signup, otp-verify, onboarding
  - otp-verify.component.ts (mfe-auth)
  - input.component.ts (libs/ui-kit) — used across all forms
  - onboarding.component.ts (mfe-onboarding)
  - profile.component.ts (mfe-onboarding)

### Gaps found and fixes applied

GAP-A1: auth-card had flat padding:32px at all breakpoints.
  Fix: auth-layout.component.ts — padding:20px mobile / 32px sm+ (≥640px).
  auth-wrapper outer gutter: 12px mobile / 16px sm+.
  360px result: card = 336px wide; content area = 296px.

GAP-A2: p-inputotp host was inline-unknown-width; OTP cells had no explicit sizing.
  Fix: otp-verify.component.ts — ::ng-deep rules:
    mee-otp-input: display:block; width:100%
    p-inputotp: display:flex; width:100%
    .p-inputotp-input: flex:1; min-width:0; min-height:44px; font-size:18px; text-align:center

GAP-A3 (a11y): orphaned <label>Enter OTP</label> — no [for], not linkable to PrimeNG auto-IDs.
  WCAG 1.3.1 failure.
  Fix: replaced with <p class="otp-label"> + aria-label="One-time password entry" on wrapper div.

GAP-A4: font-size on <input pInputText> was not explicit — cascade from PrimeNG base.
  Fix: input.component.ts — added font-size:16px inline style.
  Guarantees no iOS auto-zoom on any MeeSell form field.
  RULE: all MeeSell form inputs must carry explicit font-size:16px.

GAP-O1 (onboarding): p-steps had no overflow guard.
  Fix: onboarding.component.ts — .steps-wrap { overflow:hidden } + ::ng-deep .p-steps-title
  { font-size:12px; white-space:nowrap; text-overflow:ellipsis; max-width:64px }

NOT a gap (profile bottom): ProfileComponent pb-8 is correct as-is.
  Shell .page-content already adds padding-bottom:calc(60px+env(safe-area-inset-bottom))
  at ≤639px. Inner content divs must NOT double-compensate. Added comment in template.
  RE-CONFIRMED: NEVER add pb-[60px] or pb-[92px] to MFE inner content — shell owns tab-bar clearance.

### Design token math — 360px auth layout

| Measurement | Value |
|---|---|
| Viewport | 360px |
| auth-wrapper padding mobile | 12px × 2 = 24px |
| auth-card width at 360px | 336px |
| auth-card padding mobile | 20px × 2 = 40px |
| Content area | 296px |
| OTP cell width (6 cells, 5×8px gaps) | 42.7px |
| OTP cell min-height | 44px (enforced) |

### tsc result
tsc --noEmit: ZERO errors (mfe-auth), ZERO errors (mfe-onboarding).

---
