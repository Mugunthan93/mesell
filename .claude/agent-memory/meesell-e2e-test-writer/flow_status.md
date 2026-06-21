# Flow status — coverage / flaky / blocked

One row per critical seller flow (design §5.3 taxonomy). Update after each wave.
Status ∈ STUB · EXPLORING · COVERED · FLAKY · BLOCKED.

| Flow | File | Status | Notes |
|---|---|---|---|
| Phone OTP onboarding | flows/onboarding.spec.ts | STUB | test.fixme; needs login DOM selectors verified live |
| Google Sign-In | flows/google-signin.spec.ts | NOT STUBBED | in taxonomy; add stub + explore GIS button |
| Catalog creation wizard | flows/catalog-creation.spec.ts | STUB | test.fixme; needs wizard step selectors |
| Image upload + precheck | flows/image-precheck.spec.ts | STUB | test.fixme; needs file input + result card + a fixture JPEG |
| Category smart-picker | flows/category-picker.spec.ts | NOT STUBBED | in taxonomy; add stub + explore suggestions list |
| Export download | flows/export.spec.ts | STUB | test.fixme; asserts a download event |
| Plan guard | flows/plan-guard.spec.ts | STUB | test.fixme; confirm which free-tier route is gated |
| Logout + back-nav guard | flows/logout-guard.spec.ts | STUB | test.fixme; sentinel for the federation auth-singleton regression |

_Bootstrapped 2026-06-22 — 6 stubs scaffolded; google-signin + category-picker still to add._
