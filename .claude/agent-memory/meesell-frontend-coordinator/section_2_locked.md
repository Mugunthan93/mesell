---
name: section-2-locked
description: FRONTEND_ARCHITECTURE.md §2 (Feature Catalog) LOCKED 2026-06-05 with auth+onboarding merged into single account feature; propagated as AMENDMENT 2026-06-05B to §3 + §6 + §7 + §8 (reserved) + §23 + TOC
metadata:
  type: project
---

# FRONTEND_ARCHITECTURE.md §2 LOCKED 2026-06-05

## Founder revision — auth + onboarding merger

**Original proposal:** 10 feature folders including separate `auth/` (signup + login) and `onboarding/` (seller-profile wizard + /profile edit).

**Founder ratification with revision:** merge into a single `account/` feature.

**Rationale:**
- The seller journey (phone → OTP → seller-profile compliance → dashboard) is structurally one identity-flow
- Same actor, same dependency on `core/auth/AuthService`
- The `/profile` edit-existing-profile use case is a return-user surface that benefits from sharing component vocabulary with onboarding (the compliance form is the same form, populated differently)
- Net feature count: 10 → 9

## What `account/` owns post-merger

**4 routes:**
- `/signup` — phone entry → OTP screen
- `/login` — phone entry → OTP screen (different copy)
- `/onboarding` — 3-phase seller-profile wizard (Base 9 compliance fields + Country of Origin / Super-category multi-select / Conditional compliance extensions)
- `/profile` — edit existing profile

**7 endpoints (via `AccountApiService`):**
- `POST /api/v1/auth/otp/send`
- `POST /api/v1/auth/otp/verify`
- `POST /api/v1/auth/refresh` (cross-cutting — UI not directly here; AuthService in core/ owns the call)
- `POST /api/v1/auth/logout` (cross-cutting — same)
- `GET /api/v1/seller-profile/required-fields`
- `GET /api/v1/seller-profile`
- `PUT /api/v1/seller-profile`

**Internal structure:**
```
features/account/
├── account.routes.ts
├── account-api.service.ts
├── signup/
├── login/
├── onboarding/
├── profile/
├── components/
│   ├── otp-verify/           (used by signup + login)
│   ├── compliance-step/      (used by onboarding + profile)
│   └── super-category-chips/ (onboarding only)
└── account.model.ts
```

**Backend peers:** `iam` (otp + refresh + logout) **AND** `customer` (seller-profile CRUD). Two backend modules feeding one frontend feature is acceptable here because the frontend surface is unified — the seller doesn't mentally separate "I logged in" from "I declared compliance".

## Propagation as AMENDMENT 2026-06-05B

The merger affected 5 sections — applied as amendments rather than re-locks:

| Section | Status before | Action taken |
|---|---|---|
| §2 | DRAFT | LOCKED with merger applied |
| §3 (LOCKED) | LOCKED | AMENDMENT 2026-06-05B added to STATUS line; tree + 7-file example + edge-case updated in-place |
| §6 (LOCKED) | LOCKED | Single reference updated (ng-otp-input row path); no STATUS amendment needed (mechanical) |
| §7 | SKELETON | Renamed to "Feature: `account`"; content folded from prior §7 + §8 |
| §8 | SKELETON | Marked "(Reserved — content merged into §7)"; section number preserved so cross-references `§7-§15` resolve |
| §23 | SKELETON | 5 table rows updated (4 routes + 1 cross-cutting row change owner to `account`) |
| TOC | (top of doc) | §7 entry renamed; §8 entry marked merged |

## How to apply when dispatching specialists

**For `meesell-angular-service-builder` (when scaffolding lands eventually):**
- Scaffold `features/account/` per §7 + §3.D
- Generate `account.routes.ts` with 4 routes: `/signup`, `/login`, `/onboarding`, `/profile`
- Generate `account-api.service.ts` wrapping all 7 endpoints
- The 3 sanctioned cross-feature channels (§17) — `account` is NOT imported by any other feature; outgoing imports limited to `core/` + `shared/`

**For `meesell-angular-component-builder` (when scaffolding lands):**
- 4 page components + 3 sub-components in `features/account/`
- `otp-verify` wraps `ng-otp-input` from §6 pick #6
- `compliance-step` renders the 9 Legal Metrology fields with Reactive Forms validators
- `super-category-chips` is a `MatChipListbox` multi-select

## Why this is not a major retroactive change

The merger is a **folder name + ownership consolidation**, not a structural change:
- Internal file pattern (§3.D 7-file pattern) is unchanged
- Cross-feature communication rules (§17) are unchanged
- Backend module peers are unchanged (still `iam` + `customer`)
- Endpoint contract is unchanged (still 27 on backend, 26 consumed on frontend)
- Route table is unchanged (still 12 routes total)

The only structural difference is that one feature now spans two backend modules — which §17 rule 1 (no cross-feature imports) accommodates because the feature owns its own API service that internally hits both modules.

## Future renumbering question

§8 is currently "(Reserved — content merged into §7)" to preserve cross-references like "§7-§15 deep specs" in §17 + §22. A separate founder-review turn could close this gap by renumbering §9-§15 → §8-§14 + updating all cross-references. Not urgent; the placeholder is honest and readable.
