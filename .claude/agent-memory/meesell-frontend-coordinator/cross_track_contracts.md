---
name: cross-track-contracts
description: What the frontend needs from BACKEND, DATA, AI tracks before specialists can dispatch — the hand-off matrix
metadata:
  type: reference
---

# Cross-track contracts (what others must hand us)

## From BACKEND track

| Need | Status | Endpoint(s) | Blocker for |
|---|---|---|---|
| Auth contract | Section §7 SKELETON | `POST /auth/otp/send`, `POST /auth/otp/verify` | `auth` feature |
| Schema contract | LOCKED (MVP §5.6.1) | `GET /categories/:id/schema` | `catalog-form` feature |
| Product CRUD | Section §10 SKELETON | `POST/PATCH/GET /products` | `catalog-form` feature |
| Autofill contract | Section §10 SKELETON | `POST /products/:id/autofill` | `catalog-form` feature |
| Draft recovery | LOCKED (§0.C, ruling D3) | `GET /products/:id/draft` | `catalog-form` feature |
| Image upload + precheck | Section §11 SKELETON | `POST/GET /products/:id/images` | `images` feature |
| Preview JSON | Section §10 SKELETON | `GET /products/:id/preview` | `preview` feature |
| Price calc | Section §12 SKELETON | `POST /products/:id/price-calc` | `pricing` feature |
| Export trigger + poll | Section §14 SKELETON | `POST /products/:id/export-xlsx`, `GET /exports/:id` | `export` feature |
| Smart picker + browse | Section §9 SKELETON | `GET /categories/suggest`, `GET /categories/browse` | `smart-picker` feature |
| Seller profile | Section §8 SKELETON | `GET/PUT /seller-profile`, `/required-fields` | `onboarding` feature |
| Field enum lookup | Section §9 SKELETON | `GET /categories/:id/enum/:field_name?q=` | `catalog-form` (`dropdown_api_search` primitive) |

**Critical path:** BACKEND `iam` module (§7) must ship before any auth-guarded feature can be tested end-to-end. Until then, frontend specialists work against MSW mocks shaped to MVP §3 contracts.

## From DATA track

| Need | Status | What it provides | Blocker for |
|---|---|---|---|
| schema_jsonb shape | LOCKED (MVP §5.6.1) | The three-layer per-field metadata | `catalog-form` renderer |
| Category tree | Phase 1-3 COMPLETE | 3,772 leaves, super-category mapping | `smart-picker` browse fallback |
| Enum entries | Phase 1-3 COMPLETE | 49,259 per-(category, field) enum sets | `dropdown_*` primitives |
| Field aliases | Phase 1-3 COMPLETE | 67 canonical-to-Meesho mappings — backend-only consumer | (not consumed by frontend per philosophy F1) |
| Friendly labels (Tier A/B) | PENDING (founder writes) | Hand-curated display_label + display_help for top 28 + 10 fields | First wave of seller-facing copy quality |

## From AI track

| Need | Status | What it provides | Blocker for |
|---|---|---|---|
| Smart Picker response shape | Pending | `[{leaf_id, confidence, sample_attrs[]}]` per MVP §5.1 | `smart-picker` feature |
| Autofill response shape | LOCKED (DB §4.5) | `{[canonical_name]: {value, confidence, source, accepted}}` | `catalog-form` autofill overlay |
| Watermark check response | LOCKED (DB §4.6) | `precheck_jsonb` with 6 booleans + score | `images` precheck report |

## What the frontend hands BACK to other tracks

| Output | Receiver | Status |
|---|---|---|
| Route inventory | BACKEND coordinator | LOCKED (FRONTEND_ARCH §23) — for cross-check against BACKEND §17 |
| Performance budget | DEVOPS / INFRA | DRAFT (FRONTEND_ARCH §19) — for K3s pod sizing of frontend nginx |
| Dockerfile + nginx config | INFRA | SKELETON (FRONTEND_ARCH §20) — author when ready to ship |
| ngsw-config.json | INFRA | SKELETON (FRONTEND_ARCH §16) — must match backend §6.3 TTLs |

## How to apply

When a specialist proposes work that depends on a still-SKELETON cross-track item:
1. Surface it in STATUS_FRONTEND.md "Blockers" section
2. Reference the specific MVP/BACKEND_ARCH section that must lock first
3. Recommend the founder unblock by either (a) locking the upstream section, (b) authorising us to proceed against an MSW mock, (c) descoping the feature

Do NOT proceed on assumed contracts — that's how Frontend ends up rewriting half its code when the contract finally locks.
