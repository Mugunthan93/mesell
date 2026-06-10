---
name: live-preview-feature
description: live-preview Feature 6 — frontend coordinator role, specialist dispatch order, contracts to enforce in PR review
metadata:
  type: project
---

# Live Preview (Feature 6) — Frontend Coordinator Brief

**Status:** PLAN READY (FEATURE_PLAN.md awaiting master consolidation 2026-06-10)
**FEATURE_PLAN.md:** `docs/plans/features/live-preview/FEATURE_PLAN.md` (~1100 lines)
**Your role:** Frontend lead — reviews frontend group PR (`feature/live-preview/frontend` → `feature/live-preview`). This is the most-involved track for this feature (10h frontend vs 3h backend per V1_FEATURE_SPEC §F6 budget).
**Branch you own:** `feature/live-preview/frontend` (cut by master from `feature/live-preview` integration branch)

## Your dispatch order

Three specialists in 3 phases:

1. **PHASE A — `meesell-angular-service-builder`** (in parallel with backend): publishes `PreviewResponse` TypeScript interface (snake_case to match backend exactly), builds `PreviewService` with `get(productId) → Observable<PreviewResponse>` + `refreshTrigger$: Observable<string>`, creates `livePreviewFeatureGuard`, wires `/catalogs/:id/preview` lazy route in `app.routes.ts`. 7 acceptance items in Template C.

2. **PHASE C — `meesell-angular-component-builder`** (after service-builder): 4 components — page container `PreviewComponent` + `FeedThumbnailComponent` + `DetailPageComponent` + `MobileCardComponent`. All standalone, OnPush. Image carousel uses Angular CDK drag for swipe (NOT HammerJS). Templates render `{{ preview.title_truncated_30 }}` VERBATIM. 6 spec tests.

3. **PHASE D — `meesell-angular-ui-styler`** (LAST — components must exist first): single SCSS file `preview.scss` with the Meesho design-language clone. Tailwind-exception documented in file header. All colors via CSS custom properties (token-swap-friendly for V1.5 brand refresh). Founder visual-diff screenshots at 360px + 1280px attached to PR.

## The Meesho-clone IS the differentiator

The user-trust value proposition (T4 IMAGE PREVIEW MISSING per VALIDATED_PAIN_POINTS.md) hinges on a faithful Meesho-looking render. ui-styler's work is the highest-leverage in this feature. Visual-diff iteration cap is **4** (D6 exception — qualitative bar may need extra passes); all other specialists are capped at 3.

## Key contracts to enforce in your PR review

The 17-check review protocol is in FEATURE_PLAN.md §Review + iteration protocol. Top 7 hot items:

1. **Templates render `{{ preview.title_truncated_30 }}` VERBATIM.** Any `| slice:0:30` operator on `title_full` in templates = re-dispatch component-builder citing D2 server-side contract. Grep clean.
2. **`PreviewResponse` interface field names = backend snake_case EXACTLY.** Renaming to camelCase requires runtime transformation and breaks OpenAPI contract.
3. **Image carousel uses CDK drag-drop.** No HammerJS (dep bloat), no raw touch events (cross-browser pain).
4. **`livePreviewFeatureGuard` is SYNCHRONOUS.** Environment is build-time, not runtime.
5. **preview.scss header has Tailwind-exception rationale documented** + Meesho reference URL + CSS custom properties contract.
6. **preview.scss: no hex literals in selector bodies, no `!important`, no direct PrimeNG class overrides.** Color values via `var(--meesho-...)` only.
7. **Visual diff vs real Meesho ≤10% qualitative** — founder sign-off comment on PR + 4 screenshot pairs (FeedThumbnail 360px, DetailPage 360px, DetailPage 1280px, MobileCard 360px).

## Cross-feature dependency

Live-preview reads catalog-form's `products.fields_jsonb` (via backend). UI auto-refresh subscribes to `previewService.refreshTrigger$` — catalog-form's autosave success handler calls `previewService.notifySaved(productId)` to trigger re-fetch. This is a loose-coupling contract (no direct service dependency between catalog-form and live-preview).

## Iteration cap

3 iterations default; **4 for `meesell-angular-ui-styler` visual-diff exception** per D6.

## After feature merges to develop

- Update `docs/status/feature_board_frontend.md` row: live-preview → MERGED
- The PR uses `.github/PULL_REQUEST_TEMPLATE/frontend.md` (frontend is the most-involved track for this feature)
