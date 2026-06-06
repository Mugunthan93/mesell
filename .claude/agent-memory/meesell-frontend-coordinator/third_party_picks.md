---
name: third-party-picks
description: V1 locked dependency set with rationale and rejected alternatives — referenced from FRONTEND_ARCHITECTURE.md §6
metadata:
  type: reference
---

# Third-party tool picks (V1)

The set is locked in FRONTEND_ARCHITECTURE.md §6. Memory entry exists so specialists can find the WHY without re-reading the full architecture doc.

## Picked (14 packages)

| Concern | Pick | Why over alternatives |
|---|---|---|
| UI primitives + a11y | `@angular/material` + `@angular/cdk` | M3 tokens native; CDK virtual scroll + drag-drop + a11y in one package |
| Styling | `tailwindcss` | Per Decision 11; aligns with §5A tokens |
| i18n | `@jsverse/transloco` | Runtime locale swap for V1.5 Tamil/Hindi; `@angular/i18n` rejected (build-time only) |
| HTTP client | native `HttpClient` + interceptors | Per CLAUDE.md; no axios |
| Forms | native Reactive Forms | Per CLAUDE.md; Signal Forms candidate for V2 |
| OTP input | `ng-otp-input` | Reactive Forms support + paste-aware (SMS auto-fill) |
| Image compress | `ngx-image-compress` | Client-side compress before upload (10 MB → ~1 MB) for 2G/3G Tirupur |
| Charts | `chart.js` + `ng2-charts` | 30 KB vs ApexCharts 611 KB; MeeSell uses only bar + waterfall |
| PWA service worker | `@angular/service-worker` (native ngsw) | Aligns with backend cache TTLs via ngsw-config.json |
| State (shared) | RxJS `BehaviorSubject` | Per Decision 10; no NgRx |
| State (local) | Angular signals | Per Decision 10; signal() + computed() |
| Test (unit/component) | `vitest` + `@analogjs/vitest-angular` + `@testing-library/angular` | New Angular CLI default; faster than Karma+Jasmine |
| Test (e2e) | `@playwright/test` | Mobile emulation for Tirupur device profiles |
| Lint/format | `@angular-eslint/*` + `eslint` + `prettier` | Standard |

## Rejected (8 candidates)

| Concern | Rejected | Why |
|---|---|---|
| Forms | React Hook Form + Zod | Not Angular (Decision 9) |
| State | NgRx | Boilerplate cost not justified for V1 (Decision 10) |
| State | NGXS | Same as NgRx |
| Icons | Heroicons | Material already ships icon font + Material symbols inline |
| Charts | ApexCharts | 611 KB core vs Chart.js 30 KB |
| Charts | Highcharts | Commercial license + bundle size |
| HTTP | axios | Native HttpClient handles everything; axios is a second framework |
| i18n | `@angular/i18n` built-in | No runtime locale swap; V1.5 needs runtime swap |
| Upload | `ngx-awesome-uploader` | Too broad (cropping etc. not in V1); custom CDK drag-drop is narrower |

## How to apply

**For specialists:**
- Do NOT introduce new dependencies without amending FRONTEND_ARCHITECTURE.md §6 and coordinator review
- When a feature spec mentions a tool, cross-check this list first — if not here, it's not approved

**For me (coordinator):**
- New dep proposals go through founder approval and update the architecture doc + this memory
- Quarterly review: any dep that hasn't shipped a security/feature update in 6 months → flag for replacement consideration
