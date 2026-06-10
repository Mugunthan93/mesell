---
name: live-preview-feature
description: live-preview Feature 6 — backend coordinator role, specialist dispatch order, contracts to enforce in PR review
metadata:
  type: project
---

# Live Preview (Feature 6) — Backend Coordinator Brief

**Status:** PLAN READY (FEATURE_PLAN.md awaiting master consolidation 2026-06-10)
**FEATURE_PLAN.md:** `docs/plans/features/live-preview/FEATURE_PLAN.md` (~1100 lines)
**Your role:** Backend lead — reviews backend group PR (`feature/live-preview/backend` → `feature/live-preview`)
**Branch you own:** `feature/live-preview/backend` (cut by master from `feature/live-preview` integration branch)

## Your dispatch order

Two specialists in sequence:

1. **PHASE A — `meesell-services-builder`** (no deps): finalizes `catalog.service.get_preview(product_id, user_id) → PreviewResponse` per Template A in FEATURE_PLAN.md §Dispatch templates. Creates `core/feature_flags.py` generic `require_feature_flag(name)` factory. 7 unit tests including emoji-at-position-28 truncation fixture.

2. **PHASE B — `meesell-api-routes-builder`** (after services-builder): adds `PreviewResponse` + `VariantSwatch` Pydantic schemas (11 fields); adds (or verifies) `GET /{product_id}/preview` route with `Depends(require_feature_flag("live_preview"))`; amends `config.py` with `FEATURE_LIVE_PREVIEW_ENABLED: bool = False`. 5 integration tests covering happy + flag-off + non-owner + missing-images + missing-title.

**Critical:** verify whether catalog-form dispatch already added the `/preview` route stub before authoring. Run `git log feature/catalog-form/backend -- backend/app/modules/catalog/routes.py` first. If route exists: modify to add the feature-flag dep. If not: add from scratch.

## Key contracts to enforce in your PR review

The 13-check review protocol is in FEATURE_PLAN.md §Review + iteration protocol. Top 5 hot items:

1. **Server-side truncation is non-negotiable.** `title_truncated_30 = title_full[:30]` (Python char-correct slicing). NOT bytewise, NOT client-computed. The emoji-at-28 unit test must pass.
2. **`assert_owned` BEFORE products fetch** (per BACKEND_ARCHITECTURE §4.C) — 404 masks 403; non-owner must get 404 not 403.
3. **`image.service.get_image_urls` is the ONLY cross-module call** in get_preview (per §16.A allowed-edges matrix). Direct `product_images` table query is a violation.
4. **`variant_swatches` returns max 1 entry in V1** — full variant matrix is V1.5 scope per D1.
5. **Route uses `Depends(require_feature_flag("live_preview"))`** — NOT inline `if not settings.FEATURE_...`. The generic factory makes the dep reusable.

## Cross-module surfaces this feature consumes (read-only)

- `image.service.get_image_urls(product_id, user_id) → list[str]` per §11.C — returns image URLs in slot-index order. DO NOT re-sort. `[0]` IS first slot.
- `core/tenancy.assert_owned(product_id, user_id)` per §4.C — raises NotFoundError on mismatch (masks 403 as 404).
- `core/auth.get_current_user` dep per §4.A — unchanged auth contract.

## Cross-module surfaces this feature publishes

- `GET /api/v1/products/{id}/preview` — frontend consumes. Frontend's `PreviewResponse` TypeScript interface mirrors backend Pydantic snake_case exactly (lint rule disabled for that file).
- The route is one of the 6 catalog endpoints per §0.C 27-contract.

## Iteration cap

3 iterations per specialist (D6 default). If a specialist exceeds 3 failed iterations, freeze the branch, open a blocker row on `docs/status/feature_board_backend.md`, escalate to founder.

## Memory hygiene

This file is `live_preview_feature.md` — feature-scoped. Do NOT mix with other features' work. When you also work on catalog-form / xlsx-export / etc., write to their respective `{feature}_feature.md` files. Your `MEMORY.md` index lists them under separate `### {feature-slug}` headings.

## After feature merges to develop

- Stamp `docs/V1_FEATURE_SPEC.md §F6` with "implemented YYYY-MM-DD PR#N"
- Add sentinel comment to `docs/BACKEND_ARCHITECTURE.md §10.C` referencing the merge commit
- Update `docs/status/feature_board_backend.md` row: live-preview → MERGED
