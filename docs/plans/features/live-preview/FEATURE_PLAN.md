# Feature Plan — Live Product Preview (Meesho-Style Render Before Publish)

**Feature slug:** `live-preview`
**Session:** `mesell-live-preview-planning-session-1`
**Date authored:** 2026-06-10
**Status:** PLAN READY — awaiting master consolidation
**Output of session:** This document. No production code was written. No branch was cut. No PR was opened.

**Drives:** `meesell-backend-coordinator` · `meesell-frontend-coordinator` · `meesell-infra-builder`
**Prerequisite for ship:** `catalog-form` LOCKED (reads `products.fields_jsonb`) AND `image-precheck` LOCKED (reads `image.service.get_image_urls`)
**Sibling-parallel-safe with:** `price-calculator` (no shared code surface)

---

## Decisions

Founder answers recorded verbatim from `mesell-live-preview-planning-session-1` on 2026-06-10.

### D1 — V1 scope confirmation

**Answer:** Confirm `V1_FEATURE_SPEC.md §F6` as specified — no scope flexes.

The feature matches `V1_FEATURE_SPEC.md §F6` exactly:
- **3 views** rendered against the same `PreviewResponse`:
  - **Feed thumbnail** — the marketplace card seen in Meesho's listing grid (small image, truncated title at ~30 chars, price + MRP strike-through, single variant swatch)
  - **Product detail page (PDP)** — the full product detail render (large image carousel, full title, truncated description, full pricing block, all variant swatches as a row)
  - **Mobile card** — the mobile-app-style card (image at top, title at ~30 chars, price block compact)
- **Render budget:** all three render within 1s after page load (measured from `app-preview` mount to first contentful frame). Validated by `meesell-angular-component-builder` per its dispatch acceptance criterion.
- **Title truncation:** ~30 chars on feed thumbnail and mobile card. **Server-side only** (see D2). Frontend renders `title_truncated_30` verbatim.
- **Image carousel:** uploaded slot order (slot index 0 → 3 per `BACKEND_ARCHITECTURE.md §11.B.1` 4-slot rule). Mobile swipe via Angular CDK drag gestures (no HammerJS dependency).
- **Missing-fields CTA:** when product has <1 uploaded image OR title is empty/null OR title is < 5 chars, render placeholder image + "Fill required fields to preview your listing" CTA button that deep-links back to `/catalogs/:id/edit` with the relevant field focused via query param.
- **V1 limitation:** variant swatches show **first variant only** — full variant matrix (selector grid + dependent image switching) deferred to V1.5.
- **V1 limitation:** descriptions truncated at 200 chars in detail preview — full description deferred to V1.5 layout work.
- **Visual diff vs real Meesho:** qualitative ≤10%, founder manual check during PR review. **No automated visual regression bar in V1** — Percy/Chromatic deferred to V1.5 along with the variant matrix.

No flexes accepted. The single-variant + 200-char-description constraints are deliberate V1 simplifications; founder confirmed they are tradeable-against-ship-velocity, not future-blockers.

### D2 — Preview-transformation location

**Answer:** Backend — structured `PreviewResponse` pre-shape.

The backend pre-computes the full preview shape. `PreviewResponse` contains explicit fields the frontend renders verbatim:

| Field | Type | Source |
|-------|------|--------|
| `title_full` | `str` | `products.fields_jsonb.title` |
| `title_truncated_30` | `str` | server-side unicode-safe slice of `title_full[:30]` |
| `description_full` | `str` | `products.fields_jsonb.description` |
| `description_truncated_200` | `str` | server-side unicode-safe slice of `description_full[:200]` |
| `mrp` | `Decimal` | `products.fields_jsonb.mrp` |
| `meesho_price` | `Decimal` | `products.fields_jsonb.meesho_price` |
| `first_image_url` | `str` | first entry of `image.service.get_image_urls(product_id, user_id)` |
| `image_carousel_urls` | `list[str]` | full `get_image_urls(...)` result in slot-index order |
| `variant_swatches` | `list[VariantSwatch]` | V1: max 1 entry (first variant); shape locked for V1.5 expansion |
| `is_complete` | `bool` | `True` iff title >= 5 chars AND `len(image_carousel_urls) >= 1` |
| `missing_fields` | `list[str]` | when `is_complete=False`, which field(s) are missing — drives the CTA copy |

**Reason backend pre-shapes:**
1. **Truncation consistency** — all 3 frontend components render the SAME `title_truncated_30` value. No drift risk.
2. **UTF-8 / emoji / RTL safety** — Python's string slicing is character-aware (`title[:30]` slices by code points, not bytes). JavaScript's `.slice(0, 30)` also handles BMP characters correctly but emoji + combining characters + RTL combining marks can split mid-grapheme. Centralizing the slicer in Python with explicit grapheme handling (via `regex` library with `\X` cluster matching for V1.5; V1 ships with simple `str[:30]` which is character-correct but grapheme-naive) gives ONE place to fix bugs.
3. **Testability** — `test_get_preview_truncation_emoji` becomes a deterministic backend unit test against `PreviewResponse.title_truncated_30`, not a brittle frontend snapshot test.
4. **OpenAPI contract clarity** — the truncation fields are documented in the OpenAPI schema with their semantics ("server-side, ~30 char visible — exact char count may vary for graphemes/emoji"), so frontend implementations across web and mobile (Phase 2 Ionic) stay consistent.

Frontend renders `title_truncated_30` verbatim. Frontend MUST NOT compute its own truncation. Frontend MUST NOT use CSS `text-overflow: ellipsis` for the listing truncation (that hides text rather than respecting the ~30-char Meesho convention).

### D3 — Feature flag posture

**Answer:** `FEATURE_LIVE_PREVIEW_ENABLED` — gated rollout.

| Env | Default |
|-----|---------|
| Dev | `true` |
| Staging | `true` AFTER a single round of founder visual-diff approval against a real Meesho listing (qualitative, no automated gate) |
| Prod | `true` AFTER staging visual-diff approval |

**When disabled:**
- `GET /api/v1/products/{id}/preview` returns `404 Not Found` with response body `{ "detail": "Preview unavailable", "code": "feature.live_preview.disabled" }`
- Frontend route `/catalogs/:id/preview` shows a "Preview unavailable" placeholder card with no spinner, no retry, no auth prompt. Layout: Tailwind utility centered card with the message + "Back to catalog" link.

**Implementation seam:**
- Backend: `settings.FEATURE_LIVE_PREVIEW_ENABLED: bool = False` (default OFF in `config.py`). Router-level dependency `Depends(require_feature_flag("live_preview"))` raises `FeatureDisabledError` → 404 if false.
- Frontend: `environment.featureLivePreviewEnabled: boolean` (build-time constant from `.env.{env}`). Route guard `livePreviewFeatureGuard` redirects to placeholder when false.

**Pre-condition for staging promotion:** the visual-diff approval is logged in the merge PR's body with founder approval comment + screenshot pair (MeeSell preview vs real Meesho listing for the same product). This is the gate item that flips staging from `false` → `true`.

### D4 — Priority ordering vs sibling features

**Answer:** Ships AFTER `catalog-form` AND `image-precheck`, in PARALLEL with `price-calculator`.

| Dependency | Why |
|-----------|-----|
| `catalog-form` LOCKED to develop | Live-preview reads `products.fields_jsonb` shape written by catalog-form. The `get_preview` method may have been scaffolded in catalog-form's services-builder dispatch — verify before writing (one of the 4 D1-D2 contract checks). |
| `image-precheck` LOCKED to develop | Live-preview reads images via `image.service.get_image_urls(product_id, user_id)` — the cross-module surface locked at `BACKEND_ARCHITECTURE.md §11.C` + §16.A. Image-precheck's services-builder writes that method. |
| Parallel-safe with `price-calculator` | No shared file surface. Pricing operates on `products.fields_jsonb.mrp/meesho_price` (read in `pricing.service.calculate(...)`) — pricing writes nothing live-preview reads, and vice versa. Both can have open PRs simultaneously without conflict. |

Per `docs/plans/features/feature_planning_master.md` cross-feature dependency map (line 73): "live-preview depends on catalog-form" — confirmed and extended with image-precheck per `BACKEND_ARCHITECTURE.md §11.C`.

### D5 — Agent lineup

**Answer:** 3 leads + 6 specialists, infra in scope (driven by D3 gated rollout).

| Track | Lead | Specialists |
|-------|------|-------------|
| Backend | `meesell-backend-coordinator` | `meesell-api-routes-builder`, `meesell-services-builder` |
| Frontend | `meesell-frontend-coordinator` | `meesell-angular-component-builder`, `meesell-angular-service-builder`, `meesell-angular-ui-styler` |
| Infra | `meesell-infra-builder` (standalone) | — |

**Tracks explicitly with NO work:**
- **AI:** `meesell-ai-coordinator` and its 3 specialists (`prompt-engineer`, `category-picker-builder`, `image-precheck-builder`) — preview is non-AI. Image carousel renders pre-computed `image_carousel_urls`; no Gemini call sites.
- **Data:** `meesell-data-engineer` + `xlsx-parser` + `scraper-maintainer` — no data work (no XLSX parsing, no scraper changes).
- **Legal:** `meesell-legal-writer` — no compliance text changes (preview is transactional, not promotional).
- **Database:** `meesell-database-builder` — read-only composition. No new tables, no new indexes (composed from existing `products.fields_jsonb` + `product_images` per `BACKEND_ARCHITECTURE.md §10` + §11).
- **Auth:** `meesell-auth-builder` — existing `Depends(get_current_user)` from `core/auth.py` is sufficient. No JWT contract changes.

### D6 — Maximum iteration count before escalation

**Answer:** 3 iterations per specialist (default), 4 iterations for `meesell-angular-ui-styler` (visual-diff exception).

| Specialist | Iteration cap |
|-----------|---------------|
| `meesell-api-routes-builder` | 3 |
| `meesell-services-builder` | 3 |
| `meesell-angular-component-builder` | 3 |
| `meesell-angular-service-builder` | 3 |
| `meesell-angular-ui-styler` | **4** (visual-diff is qualitative; multiple passes expected on Meesho-clone fidelity) |
| `meesell-infra-builder` | 3 |

On the 3rd (or 4th for ui-styler) failed iteration: freeze the branch, open a blocker row on `docs/status/feature_board_{group}.md`, escalate to founder. Do NOT continue dispatching; do NOT merge a partial fix.

---

## Agent lineup

| Lead | Specialists dispatched | What each specialist builds |
|---|---|---|
| `meesell-backend-coordinator` | `meesell-services-builder` (primary) | `app/modules/catalog/service.py` — finalize `get_preview(product_id, user_id) → PreviewResponse`; UTF-8 safe truncation; cross-module call to `image.service.get_image_urls` per §16.A; `core/feature_flags.py` (NEW) — generic `require_feature_flag("live_preview")` dependency factory |
| | `meesell-api-routes-builder` | `app/modules/catalog/routes.py` — add `GET /api/v1/products/{id}/preview` if not already added in catalog-form dispatch (verify first); `app/modules/catalog/schemas.py` — `PreviewResponse` + sub-shapes (`VariantSwatch`); amend `config.py` — add `FEATURE_LIVE_PREVIEW_ENABLED: bool = False` |
| `meesell-frontend-coordinator` | `meesell-angular-service-builder` | `frontend/src/app/services/preview.service.ts` (NEW) — HTTP client wrapping `GET /products/{id}/preview`; auto-refresh on form-save signal so preview reflects latest `fields_jsonb` without manual reload; route guard `livePreviewFeatureGuard`; amend `app.routes.ts` — register `/catalogs/:id/preview` |
| | `meesell-angular-component-builder` | `frontend/src/app/pages/preview/preview.component.ts` (NEW — page container, view switcher); `feed-thumbnail.component.ts` (NEW); `detail-page.component.ts` (NEW); `mobile-card.component.ts` (NEW); `preview.component.spec.ts` (NEW — including title truncation index test against the locked ~30-char rule); CDK drag for carousel swipe |
| | `meesell-angular-ui-styler` | `frontend/src/app/pages/preview/preview.scss` (NEW — Meesho-clone styles, single file, Tailwind-exception documented in header); founder visual-diff screenshot pair (MeeSell preview vs real Meesho listing for the same product) attached to merge PR |
| `meesell-infra-builder` (standalone) | — | Wires `FEATURE_LIVE_PREVIEW_ENABLED` into K8s `dev` / `staging` / `prod` manifests; `docs/runbooks/live-preview-rollout.md` (NEW) — staging visual-diff approval protocol |

**AI track:** NO work.
**Data track:** NO work.
**Legal track:** NO work.
**Database/auth tracks:** NO work.

### Dispatch order (critical path)

```
PHASE A (parallel — no deps):
  meesell-services-builder        → catalog.service.get_preview + core/feature_flags.py
  meesell-infra-builder           → K8s env var wiring + rollout runbook
  meesell-angular-service-builder → PreviewService + livePreviewFeatureGuard + routes
                                    (can start from PreviewResponse type stub before backend lands)

PHASE B (after services-builder completes):
  meesell-api-routes-builder      → routes.py + schemas.py + config.py amendment
                                    (needs get_preview signature + PreviewResponse domain shape)

PHASE C (after api-routes-builder + angular-service-builder complete):
  meesell-angular-component-builder → 3 components (Feed, Detail, Mobile) + spec
                                       (needs stable PreviewService interface + PreviewResponse shape)

PHASE D (after component-builder complete):
  meesell-angular-ui-styler       → preview.scss Meesho-clone
                                    (components must exist before styler can target selectors)
```

**Critical insight:** services-builder can dispatch in parallel with angular-service-builder if a `PreviewResponse` TypeScript interface stub is published to the frontend repo at Phase A start. The backend coordinator generates the stub and shares via `.claude/agent-memory/meesell-backend-coordinator/live_preview_feature.md` for the frontend coord to pick up.

---

## Branch setup

> **Per parallel-sub-session coordination interrupt (2026-06-10):** this planning session DOES NOT cut any branch. The master Director session reconciles all 9 feature plans and creates feature branches centrally. The dispatch-order branch model below is the TARGET that master should create; the section is documented here so the implementing leads have the canonical map when work starts.

### Branches that master should create (all cut from `develop`)

| Branch | Cut from | Purpose | Who commits here |
|--------|----------|---------|-----------------|
| `feature/live-preview` | `develop` | Integration branch — sub-branches merge into here; final PR to `develop` | Only merge commits from sub-branches |
| `feature/live-preview/backend` | `feature/live-preview` | All backend specialist work | `meesell-services-builder`, `meesell-api-routes-builder` |
| `feature/live-preview/frontend` | `feature/live-preview` | All frontend specialist work | `meesell-angular-service-builder`, `meesell-angular-component-builder`, `meesell-angular-ui-styler` |
| `feature/live-preview/infra` | `feature/live-preview` | All infra work | `meesell-infra-builder` |

### PR flow (coding stage — to be executed AFTER master consolidates planning)

```
feature/live-preview/backend  ──┐
feature/live-preview/frontend ──┤──► feature/live-preview ──► develop
feature/live-preview/infra    ──┘
```

- Each group branch opens a PR to `feature/live-preview` (NOT directly to `develop`)
- `feature/live-preview/backend` PR reviewed and approved by `meesell-backend-coordinator`
- `feature/live-preview/frontend` PR reviewed and approved by `meesell-frontend-coordinator`
- `feature/live-preview/infra` PR self-reviewed by `meesell-infra-builder`, then founder gate
- Integration PR (`feature/live-preview` → `develop`) opened only after all 3 group PRs are merged; founder does final review with visual-diff screenshots attached

### PR templates

| PR | Template file |
|----|--------------|
| `feature/live-preview/backend` → `feature/live-preview` | `.github/PULL_REQUEST_TEMPLATE/backend.md` |
| `feature/live-preview/frontend` → `feature/live-preview` | `.github/PULL_REQUEST_TEMPLATE/frontend.md` |
| `feature/live-preview/infra` → `feature/live-preview` | `.github/PULL_REQUEST_TEMPLATE/infra.md` |
| `feature/live-preview` → `develop` | `.github/PULL_REQUEST_TEMPLATE/feature.md` (if exists, else `.github/PULL_REQUEST_TEMPLATE/frontend.md` — frontend is the most-involved track) |

---

## Code surfaces

### Backend

| # | File | Status | Owner |
|---|------|--------|-------|
| 1 | `backend/app/modules/catalog/service.py` | MODIFY | `meesell-services-builder` (finalize `get_preview` method per D2; UTF-8 safe truncation) |
| 2 | `backend/app/modules/catalog/schemas.py` | MODIFY | `meesell-api-routes-builder` (add `PreviewResponse` + `VariantSwatch` sub-shapes) |
| 3 | `backend/app/modules/catalog/routes.py` | MODIFY (conditional) | `meesell-api-routes-builder` (add `GET /products/{id}/preview` IF not in catalog-form scope — verify via `git log feature/catalog-form/backend`) |
| 4 | `backend/app/core/feature_flags.py` | NEW | `meesell-services-builder` (generic `require_feature_flag(name: str)` dependency factory; reads `getattr(settings, f"FEATURE_{name.upper()}_ENABLED", False)`) |
| 5 | `backend/app/config.py` | MODIFY | `meesell-api-routes-builder` (add `FEATURE_LIVE_PREVIEW_ENABLED: bool = False`) |
| 6 | `backend/tests/unit/catalog/test_get_preview.py` | NEW | `meesell-services-builder` (preview shape tests; mocked `image.service`; truncation edge cases including emoji + multibyte + 30-exactly + 29-chars + null title) |
| 7 | `backend/tests/integration/test_live_preview_integration.py` | NEW | `meesell-api-routes-builder` (full end-to-end: create product → upload image → GET preview → verify all 11 response fields; toggle `FEATURE_LIVE_PREVIEW_ENABLED=false` → expect 404) |

**Notes on `catalog/service.py` (MODIFY scope):**
- Method signature: `async def get_preview(self, product_id: UUID, user_id: UUID) → PreviewResponse`
- Flow: (1) `assert_product_ownership(product_id, user_id)` via `core/tenancy.assert_owned` per `BACKEND_ARCHITECTURE.md §4.C`; (2) fetch `products` row; (3) call `image.service.get_image_urls(product_id, user_id)` per §11.C + §16.A; (4) compute truncations server-side; (5) populate `PreviewResponse` and return
- `assert_product_ownership` is the locked cross-module signature (§10.C #10) consumed by image/pricing/dashboard/export — get_preview is a CONSUMER of it, not a writer
- Unicode-safe truncation: V1 ships with `title[:30]` (character-correct via Python slicing on str); V1.5 may upgrade to `regex.findall(r'\X', title)[:30]` for grapheme-cluster correctness

**Notes on `core/feature_flags.py` (NEW):**
- Pattern: `def require_feature_flag(name: str) → Callable[[], None]` factory returning a FastAPI dependency
- Dependency body: `if not getattr(settings, f"FEATURE_{name.upper()}_ENABLED", False): raise FeatureDisabledError(name)`
- `FeatureDisabledError` is a new `MeesellError` subclass; the global error handler maps it to 404 with `code="feature.{name}.disabled"`
- Generic by design — works for any future feature flag, not just live_preview

### Frontend

| # | File | Status | Owner |
|---|------|--------|-------|
| 1 | `frontend/src/app/services/preview.service.ts` | NEW | `meesell-angular-service-builder` |
| 2 | `frontend/src/app/core/guards/live-preview-feature.guard.ts` | NEW | `meesell-angular-service-builder` |
| 3 | `frontend/src/app/app.routes.ts` | MODIFY | `meesell-angular-service-builder` (register `/catalogs/:id/preview` lazy route, gated by `livePreviewFeatureGuard`) |
| 4 | `frontend/src/app/core/models/preview.model.ts` | NEW | `meesell-angular-service-builder` (TypeScript interface `PreviewResponse` matching backend schema exactly; published early so component-builder can stub against it) |
| 5 | `frontend/src/app/pages/preview/preview.component.ts` | NEW | `meesell-angular-component-builder` (page container; switches between 3 views via `[viewMode]` input or query param `?view=feed|detail|mobile`) |
| 6 | `frontend/src/app/pages/preview/feed-thumbnail.component.ts` | NEW | `meesell-angular-component-builder` |
| 7 | `frontend/src/app/pages/preview/feed-thumbnail.component.html` | NEW | `meesell-angular-component-builder` |
| 8 | `frontend/src/app/pages/preview/detail-page.component.ts` | NEW | `meesell-angular-component-builder` |
| 9 | `frontend/src/app/pages/preview/detail-page.component.html` | NEW | `meesell-angular-component-builder` |
| 10 | `frontend/src/app/pages/preview/mobile-card.component.ts` | NEW | `meesell-angular-component-builder` |
| 11 | `frontend/src/app/pages/preview/mobile-card.component.html` | NEW | `meesell-angular-component-builder` |
| 12 | `frontend/src/app/pages/preview/preview.component.spec.ts` | NEW | `meesell-angular-component-builder` (includes title truncation rendering test — assert that frontend renders `title_truncated_30` VERBATIM, never re-computes) |
| 13 | `frontend/src/app/services/preview.service.spec.ts` | NEW | `meesell-angular-service-builder` |
| 14 | `frontend/src/app/pages/preview/preview.scss` | NEW | `meesell-angular-ui-styler` (Meesho-clone styles, single file with documented Tailwind-exception rationale; references design tokens from Layer 1; ~150-300 lines) |
| 15 | `frontend/src/environments/environment.ts` and `environment.prod.ts` | MODIFY | `meesell-angular-service-builder` (add `featureLivePreviewEnabled: boolean` build-time constant) |

**Notes on `preview.component.ts` (NEW):**
- Standalone, OnPush change detection
- View switcher: reads `?view=feed|detail|mobile` query param (default: `detail`)
- Injects `PreviewService`; on init: `preview = signal<PreviewResponse | null>(null)` + fetches
- Renders 1 of 3 sub-components based on view mode
- Show `mat-spinner` (or PrimeNG equivalent) for <1s while loading; show placeholder + CTA if `preview.is_complete === false`
- Auto-refresh: subscribes to `previewService.refreshTrigger$` Subject that fires when catalog-form emits "saved" event; re-fetches preview on each emit

**Notes on `preview.scss` (NEW — the Meesho-clone):**
- **Tailwind-exception rationale (documented in file header):** Tailwind's utility-first model encodes one design system at a time. The Meesho-clone is a faithful copy of Meesho's design language (specific typography scale, card shadow depth, badge gold tone, price strike-through color, bottom border separator) which is NOT MeeSell's design system. Using Tailwind utilities would either (a) explode our `tailwind.config.js` with one-off colors/tokens that don't appear elsewhere, or (b) require `[style.x]="y"` inline overrides on dozens of elements. A scoped SCSS file with CSS custom properties for the Meesho tokens is cleaner — the file functions as a design-system-clone module isolated to this feature.
- File header comment block (~10 lines) documents this rationale and the EXACT Meesho design-language references (with Meesho URL the design was cloned from).
- All Meesho-specific tokens declared as CSS custom properties (`--meesho-card-shadow: ...; --meesho-price-gold: ...;`) so V1.5 brand refresh is a token-swap, not a rewrite.
- Selectors target `mee-*` wrapper components or component-host selectors only — never raw PrimeNG class names.

### Infra

| # | File / resource | Status | Owner |
|---|-----------------|--------|-------|
| 1 | K8s deployment for `dev` namespace API pod — add `FEATURE_LIVE_PREVIEW_ENABLED=true` | MODIFY | `meesell-infra-builder` |
| 2 | K8s deployment for `staging` namespace API pod — add `FEATURE_LIVE_PREVIEW_ENABLED=false` (default off; flips to true after founder visual-diff approval) | MODIFY | `meesell-infra-builder` |
| 3 | K8s deployment for `prod` namespace API pod — add `FEATURE_LIVE_PREVIEW_ENABLED=false` (default off; flips to true after staging is in steady state for ≥1 week) | MODIFY | `meesell-infra-builder` |
| 4 | Frontend build env vars — `NG_APP_FEATURE_LIVE_PREVIEW_ENABLED=true` (dev), `=false` (staging, prod default) | MODIFY | `meesell-infra-builder` |
| 5 | `docs/runbooks/live-preview-rollout.md` | NEW | `meesell-infra-builder` (staging visual-diff approval protocol: who signs off, where screenshots are archived, how the flag flips, how to roll back if Meesho redesigns mid-rollout) |

**Cost impact:** ₹0/month — env var additions only. No new pods, no new buckets, no new secrets, no new ingress rules.

### AI / Data / Legal

NONE — no changes in `ai_ops/`, `data/`, `i18n/` (no new validation messages — generic 404 handler covers `feature.live_preview.disabled`), `scripts/`, `themes/`, or any compliance copy.

### Docs (cross-cutting)

| # | File | Action |
|---|------|--------|
| 1 | `docs/V1_FEATURE_SPEC.md §F6` | Stamp "implemented YYYY-MM-DD PR#N" once `feature/live-preview` → `develop` merges. Done by backend coordinator post-merge. |
| 2 | `docs/BACKEND_ARCHITECTURE.md §10.C` | Sentinel comment referencing the merge commit that proves `get_preview` method #4 is locked-on-disk. Done by backend coordinator post-merge. |
| 3 | OpenAPI auto-regeneration | The `PreviewResponse` shape with `title_truncated_30` / `description_truncated_200` field semantics auto-documents via Pydantic v2 → OpenAPI. Reviewed in the backend group PR. |

---

## Documentation deliverables

These must exist alongside the merged code. Each is an acceptance gate item.

| # | Deliverable | Owner | When |
|---|-------------|-------|------|
| 1 | **OpenAPI entry** for `GET /api/v1/products/{id}/preview` with `PreviewResponse` shape; field-level descriptions on `title_truncated_30` and `description_truncated_200` explicitly noting server-side truncation contract (so frontend implementations across web + V1.5 Ionic stay consistent) | `meesell-api-routes-builder` | In PR `feature/live-preview/backend` |
| 2 | **`get_preview` service-method docstring** describing the cross-module call to `image.service.get_image_urls` per `BACKEND_ARCHITECTURE.md §16.A` + the ownership-assertion seam per §10.C | `meesell-services-builder` | In PR `feature/live-preview/backend` |
| 3 | **`PreviewComponent` docstring** describing view-switching logic (feed / detail / mobile) + the query-param contract `?view=` | `meesell-angular-component-builder` | In PR `feature/live-preview/frontend` |
| 4 | **`FeedThumbnailComponent` docstring** documenting the locked ~30-char title truncation contract — must explicitly state "renders `title_truncated_30` verbatim, no client-side truncation" | `meesell-angular-component-builder` | In PR `feature/live-preview/frontend` |
| 5 | **`preview.scss` header doc block** — ~10 lines documenting the Tailwind-exception rationale + Meesho design-language clone reference URL + CSS-custom-properties contract | `meesell-angular-ui-styler` | In PR `feature/live-preview/frontend` |
| 6 | **`live-preview-rollout.md` runbook** — how the staging visual-diff approval works, who signs off, where the founder's annotated Meesho screenshots are archived, the `FEATURE_LIVE_PREVIEW_ENABLED=false→true` flip procedure for each env | `meesell-infra-builder` | In PR `feature/live-preview/infra` |
| 7 | **`app.routes.ts` comment** — one-line comment on the `/catalogs/:id/preview` route documenting it is gated by `livePreviewFeatureGuard` and its layout (shell or full-page) | `meesell-angular-service-builder` | In PR `feature/live-preview/frontend` |
| 8 | **Founder visual-diff screenshot pair** — MeeSell preview vs real Meesho listing for the same product (one product, all 3 views: feed, detail, mobile) attached to the integration PR body | `meesell-angular-ui-styler` (captures) + founder (approves) | In PR `feature/live-preview` → `develop` |
| 9 | **`V1_FEATURE_SPEC.md §F6` implementation stamp** — "implemented YYYY-MM-DD PR#N" appended to the acceptance criteria block | `meesell-backend-coordinator` | After `feature/live-preview` → `develop` merges |
| 10 | **`BACKEND_ARCHITECTURE.md §10.C` sentinel** — one-line commit reference proving `get_preview` is on-disk | `meesell-backend-coordinator` | After `feature/live-preview` → `develop` merges |

---

## Dispatch templates

### Template A — `meesell-services-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** A (first, independent)
**Branch:** `feature/live-preview/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-live-preview-backend-session-1
Lead: meesell-backend-coordinator

## Your mission
Finalize `catalog.service.get_preview(product_id, user_id) → PreviewResponse` in `app/modules/catalog/service.py` (catalog-form may have scaffolded the method — your job is to make it return the structured PreviewResponse per D2). Also: create `app/core/feature_flags.py` with the generic `require_feature_flag(name)` dependency factory used by the route to gate on `FEATURE_LIVE_PREVIEW_ENABLED`.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §10.C (catalog service surface — `get_preview` is method #4)
2. docs/BACKEND_ARCHITECTURE.md §11.C (image service cross-module surface — `get_image_urls(product_id, user_id)` signature)
3. docs/BACKEND_ARCHITECTURE.md §16.A (inter-module call rules — catalog → image is an ALLOWED edge per the §2.D 8-call matrix)
4. docs/BACKEND_ARCHITECTURE.md §4.C (tenancy — `assert_owned(product_id, user_id)` is the ownership gate)
5. docs/V1_FEATURE_SPEC.md §F6 (acceptance criteria — the 11 fields of PreviewResponse, server-side truncation contract)
6. docs/plans/features/live-preview/FEATURE_PLAN.md §Decisions (D2 transformation-location lock + D3 flag posture)
7. .claude/agent-memory/meesell-services-builder/MEMORY.md
8. .claude/agent-memory/meesell-services-builder/live_preview_feature.md (pre-seeded by planning session)

## Acceptance criteria
- [ ] `backend/app/modules/catalog/service.py` `get_preview` method finalized:
  - Signature: `async def get_preview(self, product_id: UUID, user_id: UUID) -> PreviewResponse`
  - Step 1: `await self._tenancy.assert_owned(product_id, user_id)` (raises `NotFoundError` if mismatch — masking 404 over 403 per §4.C)
  - Step 2: Fetch products row via `self._repo.get_by_id(product_id)`
  - Step 3: `image_urls = await self._image_service.get_image_urls(product_id, user_id)` (cross-module call per §16.A)
  - Step 4: Compute truncations server-side:
    - `title_full = product.fields_jsonb.get("title", "")`
    - `title_truncated_30 = title_full[:30]` (Python char-correct slicing)
    - `description_full = product.fields_jsonb.get("description", "")`
    - `description_truncated_200 = description_full[:200]`
  - Step 5: `is_complete = len(title_full) >= 5 and len(image_urls) >= 1`
  - Step 6: `missing_fields = []` populated when `is_complete=False` (e.g., `["title"]` or `["images"]` or both)
  - Step 7: Build and return `PreviewResponse(title_full=..., title_truncated_30=..., description_full=..., description_truncated_200=..., mrp=Decimal(product.fields_jsonb["mrp"]), meesho_price=Decimal(product.fields_jsonb["meesho_price"]), first_image_url=image_urls[0] if image_urls else None, image_carousel_urls=image_urls, variant_swatches=[product.fields_jsonb["variants"][0]] if product.fields_jsonb.get("variants") else [], is_complete=is_complete, missing_fields=missing_fields)`
- [ ] `backend/app/core/feature_flags.py` created:
  - `def require_feature_flag(name: str) -> Callable[[], None]:` factory
  - Returns a FastAPI dep that raises `FeatureDisabledError(name)` if `not getattr(settings, f"FEATURE_{name.upper()}_ENABLED", False)`
  - `FeatureDisabledError(MeesellError)` subclass with `code = f"feature.{name}.disabled"`
- [ ] Global error handler updated to map `FeatureDisabledError` → HTTP 404 with `{ "detail": "Preview unavailable", "code": "feature.live_preview.disabled" }` envelope
- [ ] `backend/tests/unit/catalog/test_get_preview.py` created with at minimum 7 tests:
  1. happy path — 4 images, full title, full description — all fields populated correctly
  2. truncation: title exactly 30 chars → title_truncated_30 == title_full
  3. truncation: title 31 chars → title_truncated_30 is title_full[:30]
  4. truncation: title with 4-byte emoji (e.g., 🎉🎉🎉) at position 28 → title_truncated_30 keeps emoji intact (NOT split mid-codepoint)
  5. truncation: description 250 chars → description_truncated_200 is description_full[:200]
  6. incomplete: title=null → is_complete=False, missing_fields contains "title"
  7. incomplete: no images uploaded → is_complete=False, missing_fields contains "images"
- [ ] `image.service.get_image_urls` is MOCKED in tests (use `AsyncMock`) — do not depend on real GCS in unit tests

## Hard constraints
- Server-side truncation: `title_full[:30]` and `description_full[:200]` — DO NOT use `.encode()/.decode()` byte-slicing (would split UTF-8 chars). Python str slicing is code-point-correct.
- The `image.service.get_image_urls` call returns image URLs in SLOT-INDEX ORDER (per §11.C contract) — DO NOT re-sort. `image_carousel_urls[0]` IS the first slot, which is `first_image_url`.
- `assert_owned` MUST be called BEFORE fetching the products row (failing it should not leak existence of the product to non-owners — masks 403 as 404 per §4.C)
- `variant_swatches`: V1 returns max 1 entry (the first variant). DO NOT return full variant matrix — that is V1.5 scope per D1.
- `require_feature_flag(name)` MUST be generic — name is a parameter, NOT hard-coded "live_preview". This makes the dep reusable for every future feature flag.
- No `os.getenv()` anywhere — all settings come from `shared/config.settings` per §5.D + §6.G CI linter rule.
- The method is in `catalog.service.CatalogService` — DO NOT create a new service class.

## Files you MAY touch
- `backend/app/modules/catalog/service.py` (MODIFY — `get_preview` only; don't touch other methods)
- `backend/app/core/feature_flags.py` (NEW)
- `backend/app/core/errors.py` (MODIFY — add `FeatureDisabledError` class + error handler mapping)
- `backend/tests/unit/catalog/test_get_preview.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/catalog/routes.py` (owned by api-routes-builder)
- `backend/app/modules/catalog/schemas.py` (owned by api-routes-builder — your `get_preview` returns `PreviewResponse`, but the schema class definition is api-routes-builder's surface)
- `backend/app/modules/catalog/repository.py` (assume `get_by_id` exists; if not, surface as a blocker — do NOT add to repository)
- `backend/app/modules/image/` (READ-only)
- `backend/app/config.py` (owned by api-routes-builder — adds FEATURE_LIVE_PREVIEW_ENABLED)
- Any frontend or infra files
- Any other feature's planning docs

## Final report format
```
REPORT: meesell-services-builder
Session: mesell-live-preview-backend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/app/core/feature_flags.py
- backend/tests/unit/catalog/test_get_preview.py

Files modified:
- backend/app/modules/catalog/service.py (get_preview method finalized)
- backend/app/core/errors.py (FeatureDisabledError + handler)

get_preview signature implemented:
async def get_preview(self, product_id: UUID, user_id: UUID) -> PreviewResponse

PreviewResponse field count: 11 (verified against D2 table)
Truncation strategy: title_full[:30] / description_full[:200] (Python char-correct slicing)
image.service.get_image_urls integration: PASS | FAIL (mock asserted)

Unit test results:
pytest tests/unit/catalog/test_get_preview.py -v: PASS | FAIL (paste summary)
Tests: 7 of 7 passing | <count> of 7 passing

Memory update: DONE (.claude/agent-memory/meesell-services-builder/live_preview_feature.md written) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template B — `meesell-api-routes-builder`

**Dispatched by:** `meesell-backend-coordinator`
**Phase:** B (after services-builder completes — needs `PreviewResponse` semantic shape)
**Branch:** `feature/live-preview/backend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-live-preview-backend-session-1
Lead: meesell-backend-coordinator

## Your mission
Create the `PreviewResponse` Pydantic schema + `VariantSwatch` sub-shape; add (or verify) the `GET /api/v1/products/{id}/preview` route in `catalog/routes.py`; amend `config.py` with `FEATURE_LIVE_PREVIEW_ENABLED`; write the integration test for the full preview flow with feature-flag toggling.

## Mandatory reads (in this order)
1. docs/BACKEND_ARCHITECTURE.md §10.B (catalog endpoints — the 6-endpoint contract; `/preview` is one of them per §0.C)
2. docs/BACKEND_ARCHITECTURE.md §10.E (catalog schemas — existing `CatalogResponse`, `ProductResponse`; PreviewResponse is a NEW peer)
3. docs/BACKEND_ARCHITECTURE.md §5.D (config.py env-var registry — adding FEATURE_LIVE_PREVIEW_ENABLED)
4. docs/V1_FEATURE_SPEC.md §F6 (acceptance criteria)
5. docs/plans/features/live-preview/FEATURE_PLAN.md §Decisions D1+D2+D3 (scope + transformation location + flag)
6. .claude/agent-memory/meesell-api-routes-builder/MEMORY.md
7. .claude/agent-memory/meesell-api-routes-builder/live_preview_feature.md (pre-seeded by planning session)
8. VERIFY: `git log feature/catalog-form/backend -- backend/app/modules/catalog/routes.py 2>/dev/null` — check if `/preview` route was already added in catalog-form dispatch. If yes, the route exists and you MODIFY it to add the feature-flag dep; if no, you ADD the route from scratch.

## Acceptance criteria
- [ ] `backend/app/modules/catalog/schemas.py` updated:
  - `class VariantSwatch(BaseModel)`: fields per §10.E variant shape — `swatch_image_url: str`, `option_label: str` (e.g., "Blue"), `option_value: str` (e.g., "blue")
  - `class PreviewResponse(BaseModel)`: 11 fields exactly as per D2 table —
    - `title_full: str` with description="Full untruncated title"
    - `title_truncated_30: str` with description="Server-side ~30-char truncation for feed/mobile views. Frontend MUST render verbatim — do NOT recompute."
    - `description_full: str`
    - `description_truncated_200: str` with description="Server-side 200-char truncation for detail preview. V1 limitation."
    - `mrp: Decimal`
    - `meesho_price: Decimal`
    - `first_image_url: Optional[str]` (None if no images uploaded yet)
    - `image_carousel_urls: list[str]` (slot-index ordered)
    - `variant_swatches: list[VariantSwatch]` (V1: max 1)
    - `is_complete: bool`
    - `missing_fields: list[str]`
  - All Pydantic field descriptions are FILLED IN — these become the OpenAPI doc strings
- [ ] `backend/app/modules/catalog/routes.py`:
  - Route: `@router.get("/{product_id}/preview", response_model=PreviewResponse, dependencies=[Depends(require_feature_flag("live_preview"))])`
  - Handler: `async def get_preview(product_id: UUID, user: CurrentUser = Depends(get_current_user), service: CatalogService = Depends())`
  - Body: `return await service.get_preview(product_id, user.user_id)`
  - OpenAPI summary: "Get live preview of a product as Meesho will render it"
  - OpenAPI description: explains 3 views are rendered by the frontend against this single response; truncation fields are server-side and authoritative
- [ ] `backend/app/config.py` updated:
  - Add: `FEATURE_LIVE_PREVIEW_ENABLED: bool = False` with `Field(default=False, description="Gates GET /products/{id}/preview. When false: 404 with code=feature.live_preview.disabled.")`
- [ ] `backend/tests/integration/test_live_preview_integration.py` created with at minimum 5 tests:
  1. Happy path: create user → create product → upload 1 image → GET preview → assert 200 + all 11 fields populated correctly
  2. Feature flag OFF: `monkeypatch.setattr(settings, "FEATURE_LIVE_PREVIEW_ENABLED", False)` → GET preview → assert 404 + `code="feature.live_preview.disabled"`
  3. Non-owner: user A creates product, user B GETs preview → assert 404 (not 403 — ownership-masks-existence per §4.C)
  4. No images uploaded: GET preview → 200 + `is_complete=False` + `missing_fields=["images"]` + `first_image_url=None`
  5. Empty title: GET preview → 200 + `is_complete=False` + `missing_fields=["title"]`

## Hard constraints
- The route dependency MUST use `Depends(require_feature_flag("live_preview"))` — NOT inline `if not settings.FEATURE_...`. Use the generic factory from `core/feature_flags.py` (built by services-builder).
- `response_model=PreviewResponse` is REQUIRED for OpenAPI auto-generation
- All Pydantic fields have `description="..."` populated — this is the OpenAPI doc surface, treated as a contract by frontend teams
- The route prefix is `/api/v1/products` (NOT `/api/v1/catalog/products`) per the existing `catalog_router` mount in `main.py` — VERIFY with `grep "prefix=" backend/app/modules/catalog/routes.py` before adding
- DO NOT modify `get_current_user` or `core/auth.py` — auth is unchanged
- DO NOT add a new router file — extend the existing `catalog/routes.py`
- Integration test MUST use a real Valkey + real Postgres tunnel (not mocked) for the happy path; only the feature-flag-off test uses monkeypatch

## Files you MAY touch
- `backend/app/modules/catalog/schemas.py` (MODIFY — add PreviewResponse + VariantSwatch)
- `backend/app/modules/catalog/routes.py` (MODIFY — add /preview route)
- `backend/app/config.py` (MODIFY — add FEATURE_LIVE_PREVIEW_ENABLED)
- `backend/tests/integration/test_live_preview_integration.py` (NEW)

## Files you must NOT touch
- `backend/app/modules/catalog/service.py` (owned by services-builder — READ only)
- `backend/app/core/feature_flags.py` (owned by services-builder — READ only)
- `backend/app/core/errors.py` (owned by services-builder for the FeatureDisabledError addition)
- `backend/app/main.py` (router already mounted in catalog-form scope; don't touch)
- Any frontend or infra files

## Final report format
```
REPORT: meesell-api-routes-builder
Session: mesell-live-preview-backend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- backend/tests/integration/test_live_preview_integration.py (5 tests)

Files modified:
- backend/app/modules/catalog/schemas.py (PreviewResponse + VariantSwatch added)
- backend/app/modules/catalog/routes.py (GET /{product_id}/preview added)
- backend/app/config.py (FEATURE_LIVE_PREVIEW_ENABLED added)

PreviewResponse field list (verbatim from schema):
- <paste field name list>

Route line in routes.py:
@router.get("/{product_id}/preview", response_model=PreviewResponse, dependencies=[Depends(require_feature_flag("live_preview"))])

OpenAPI verification: openapi.json regenerates with PreviewResponse + /preview endpoint visible
Integration test results: PASS | FAIL (paste summary)
Was /preview already in catalog-form? YES — I modified existing route to add feature_flag dep | NO — I added the route from scratch

Memory update: DONE (.claude/agent-memory/meesell-api-routes-builder/live_preview_feature.md written) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template C — `meesell-angular-service-builder`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** A (can start in parallel with backend; uses TypeScript stub of PreviewResponse from planning session pre-seed)
**Branch:** `feature/live-preview/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-live-preview-frontend-session-1
Lead: meesell-frontend-coordinator

## Your mission
Build the frontend Angular service layer for live preview: `PreviewService` (HTTP client + auto-refresh on form-save), `livePreviewFeatureGuard` (route guard reading build-time env flag), `PreviewResponse` TypeScript interface (matching backend Pydantic shape), and register the `/catalogs/:id/preview` route.

## Mandatory reads (in this order)
1. docs/FRONTEND_ARCHITECTURE.md (full — service layer patterns, guard conventions, lazy-route registration)
2. docs/V1_FEATURE_SPEC.md §F6 (acceptance criteria including 1s render budget — service must not add network latency overhead)
3. docs/BACKEND_ARCHITECTURE.md §10.B (the GET /products/{id}/preview contract — request/response shape)
4. docs/plans/features/live-preview/FEATURE_PLAN.md §Decisions D2 (PreviewResponse shape — 11 fields)
5. .claude/agent-memory/meesell-angular-service-builder/MEMORY.md
6. .claude/agent-memory/meesell-angular-service-builder/live_preview_feature.md (pre-seeded by planning session)

## Acceptance criteria
- [ ] `frontend/src/app/core/models/preview.model.ts` created — TypeScript interface matching backend exactly:
  ```typescript
  export interface VariantSwatch {
    swatch_image_url: string;
    option_label: string;
    option_value: string;
  }
  export interface PreviewResponse {
    title_full: string;
    title_truncated_30: string;
    description_full: string;
    description_truncated_200: string;
    mrp: number;
    meesho_price: number;
    first_image_url: string | null;
    image_carousel_urls: string[];
    variant_swatches: VariantSwatch[];
    is_complete: boolean;
    missing_fields: string[];
  }
  ```
- [ ] `frontend/src/app/services/preview.service.ts` created:
  - Standalone-injectable (`@Injectable({ providedIn: 'root' })`)
  - `get(productId: string): Observable<PreviewResponse>` → GET /api/v1/products/{productId}/preview
  - `refreshTrigger$: Observable<string>` — emits productId whenever catalog-form saves; preview component subscribes and re-fetches
  - `notifySaved(productId: string): void` — exposed for catalog-form to call after PATCH succeeds (loose coupling — no direct dependency)
  - Inline docstring describing the auto-refresh contract: "PreviewComponent subscribes to refreshTrigger$ to re-fetch on form-save. The trigger is fired by catalog-form's autosave success handler."
- [ ] `frontend/src/app/core/guards/live-preview-feature.guard.ts` created:
  - `export const livePreviewFeatureGuard: CanActivateFn = () => { if (!environment.featureLivePreviewEnabled) return inject(Router).parseUrl('/catalogs'); return true; }`
  - Synchronous; reads build-time env constant
- [ ] `frontend/src/environments/environment.ts` MODIFIED:
  - Add: `featureLivePreviewEnabled: true` (dev default)
- [ ] `frontend/src/environments/environment.prod.ts` MODIFIED:
  - Add: `featureLivePreviewEnabled: false` (prod default; flips to true via env var override at build time)
- [ ] `frontend/src/app/app.routes.ts` MODIFIED:
  - Add lazy-loaded route:
    ```typescript
    {
      path: 'catalogs/:id/preview',
      canActivate: [livePreviewFeatureGuard, authGuard],
      loadComponent: () => import('./pages/preview/preview.component').then(m => m.PreviewComponent)
    }
    ```
  - Comment block: `// GATED by livePreviewFeatureGuard (reads environment.featureLivePreviewEnabled at build time) + authGuard`
- [ ] `frontend/src/app/services/preview.service.spec.ts` created:
  - get() returns Observable that hits correct URL
  - notifySaved triggers refreshTrigger$ emission for the matching productId
  - HttpClientTestingModule used for mocking; no real HTTP

## Hard constraints
- The PreviewResponse interface field names match backend EXACTLY (snake_case in TypeScript — disable lint rule for this file). DO NOT rename to camelCase; that would require runtime transformation and break the OpenAPI contract.
- `refreshTrigger$` MUST be a `Subject<string>` (or `BehaviorSubject<string | null>`) — NOT a callback chain. Preview component will subscribe via `async` pipe.
- `livePreviewFeatureGuard` MUST be SYNCHRONOUS — no async; environment is build-time, not runtime.
- DO NOT add a polling mechanism — `refreshTrigger$` is the only way to update preview. Polling would burn battery on mobile.
- No localStorage / sessionStorage anywhere
- No direct PrimeNG imports — service layer is UI-agnostic
- OnPush change detection on any component touched (you're not building components, but if you peek into shared, respect this)

## Files you MAY touch
- `frontend/src/app/core/models/preview.model.ts` (NEW)
- `frontend/src/app/services/preview.service.ts` (NEW)
- `frontend/src/app/services/preview.service.spec.ts` (NEW)
- `frontend/src/app/core/guards/live-preview-feature.guard.ts` (NEW)
- `frontend/src/app/app.routes.ts` (MODIFY — preview route only)
- `frontend/src/environments/environment.ts` (MODIFY — featureLivePreviewEnabled flag)
- `frontend/src/environments/environment.prod.ts` (MODIFY — same)

## Files you must NOT touch
- `frontend/src/app/pages/preview/` (owned by angular-component-builder)
- `frontend/src/app/core/services/auth.service.ts` (owned by auth-otp work — read-only)
- `frontend/src/app/core/interceptors/` (read-only — JWT interceptor already handles /api/v1/* including /preview)
- `frontend/src/app/ui/` (Layer 2 — read-only)
- `frontend/src/app/layouts/` (Layer 3 — read-only)
- Any backend or infra files

## Final report format
```
REPORT: meesell-angular-service-builder
Session: mesell-live-preview-frontend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/core/models/preview.model.ts
- frontend/src/app/services/preview.service.ts
- frontend/src/app/services/preview.service.spec.ts
- frontend/src/app/core/guards/live-preview-feature.guard.ts

Files modified:
- frontend/src/app/app.routes.ts (added /catalogs/:id/preview gated route)
- frontend/src/environments/environment.ts (featureLivePreviewEnabled: true)
- frontend/src/environments/environment.prod.ts (featureLivePreviewEnabled: false)

PreviewResponse field count in interface: 11 (verified vs backend D2 table)
PreviewService public API:
- get(productId): Observable<PreviewResponse>
- refreshTrigger$: Observable<string>
- notifySaved(productId): void

Spec results:
ng test -- --include='**/preview.service.spec.ts' : PASS | FAIL (paste)

Build check: pnpm build succeeded in <Xs> (target < 90s)

Memory update: DONE (.claude/agent-memory/meesell-angular-service-builder/live_preview_feature.md written) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template D — `meesell-angular-component-builder`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** C (after service-builder completes — components inject PreviewService)
**Branch:** `feature/live-preview/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-live-preview-frontend-session-1
Lead: meesell-frontend-coordinator

## Your mission
Build the 3 preview view components (FeedThumbnail, DetailPage, MobileCard) + the page container PreviewComponent that switches between them. All standalone, OnPush, mobile-first. Image carousel uses Angular CDK drag for swipe.

## Mandatory reads (in this order)
1. docs/FRONTEND_ARCHITECTURE.md (Layer 4 features/ structure — pages/ vs features/; OnPush + standalone conventions)
2. docs/V1_FEATURE_SPEC.md §F6 (3-view spec — what each view renders, the 1s budget)
3. docs/plans/features/live-preview/FEATURE_PLAN.md §Decisions D1 (V1 limitations — single variant, 200-char desc, ~30-char title), §D2 (the 11 PreviewResponse fields rendered verbatim)
4. frontend/src/app/core/models/preview.model.ts (READ — your `PreviewResponse` type)
5. frontend/src/app/services/preview.service.ts (READ — `PreviewService.get()` + `refreshTrigger$`)
6. .claude/agent-memory/meesell-angular-component-builder/MEMORY.md
7. .claude/agent-memory/meesell-angular-component-builder/live_preview_feature.md (pre-seeded by planning session)

## Acceptance criteria
- [ ] `frontend/src/app/pages/preview/preview.component.ts` created (PAGE CONTAINER):
  - Standalone, OnPush
  - Reads route param `:id` (productId) + query param `?view=feed|detail|mobile` (default: `detail`)
  - Injects `PreviewService`, `ActivatedRoute`, `Router`
  - `preview = signal<PreviewResponse | null>(null)`; `loading = signal(true)`
  - `ngOnInit`: fetches preview via `previewService.get(productId)`; subscribes to `previewService.refreshTrigger$.pipe(filter(id => id === productId))` for auto-refresh
  - Renders 1 of 3 sub-components based on `viewMode = signal<'feed' | 'detail' | 'mobile'>('detail')`
  - When `preview()?.is_complete === false`: renders placeholder + "Fill required fields to preview" CTA button that navigates to `/catalogs/{id}/edit?focus={missing_fields[0]}`
- [ ] `frontend/src/app/pages/preview/feed-thumbnail.component.ts` created:
  - Standalone, OnPush
  - `@Input({ required: true }) preview!: PreviewResponse`
  - Renders the marketplace card: small image (`first_image_url`), `title_truncated_30` VERBATIM (no client truncation), price row (`meesho_price` + strikethrough `mrp`), single variant swatch if present
  - Template MUST display `{{ preview.title_truncated_30 }}` — NOT `{{ preview.title_full | slice:0:30 }}`. The truncation contract is server-side.
- [ ] `frontend/src/app/pages/preview/detail-page.component.ts` created:
  - Standalone, OnPush
  - Same input shape
  - Renders the PDP: image carousel with CDK drag scrolling (horizontal), full `title_full`, `description_truncated_200`, full pricing block with discount %, all variant swatches as a horizontal scroll row (V1: only 1 swatch shown)
  - Image carousel uses `@angular/cdk/drag-drop` for swipe support — NOT HammerJS, NOT custom touch events
- [ ] `frontend/src/app/pages/preview/mobile-card.component.ts` created:
  - Standalone, OnPush
  - Same input shape
  - Renders the mobile-app-style card: image at top (full-width), `title_truncated_30` VERBATIM, compact price block, no description in this view
- [ ] `frontend/src/app/pages/preview/preview.component.spec.ts` created with at minimum 6 tests:
  1. Renders feed-thumbnail by default when query param is `?view=feed`
  2. Renders detail-page by default (no query param)
  3. Renders mobile-card when `?view=mobile`
  4. Truncation: assert that `preview.title_truncated_30` is rendered VERBATIM — provide a test fixture where `title_full="A"*40` and `title_truncated_30="A"*30`; the rendered DOM must show exactly the truncated string, NOT a client-computed slice
  5. Incomplete state: provide fixture with `is_complete=false, missing_fields=["images"]` → assert CTA renders + click navigates to /catalogs/{id}/edit?focus=images
  6. Auto-refresh: emit on `refreshTrigger$` → assert `previewService.get` was called again
- [ ] All 4 components:
  - `standalone: true`
  - `changeDetection: ChangeDetectionStrategy.OnPush`
  - Mobile-first: tested at 360px viewport
  - 1s render budget: measure with Performance API in spec OR document the manual timing test in the PR body

## Hard constraints
- **NEVER compute truncation client-side.** Template renders `preview.title_truncated_30` directly. If a code reviewer sees `| slice:` on `title_full` in a template, that's a re-dispatch trigger.
- **NEVER use `text-overflow: ellipsis` for the listing truncation.** The ~30 char rule is character-counted, not pixel-counted. Ellipsis is acceptable only if the server-truncated string itself overflows its container at a small viewport (genuine overflow), but NOT as a substitute for the server truncation.
- CDK drag is the swipe primitive — NOT HammerJS (avoids dep bloat) and NOT raw touch events (poor cross-browser).
- Image carousel preloads only the FIRST image; subsequent images lazy-load on intersection (use `loading="lazy"` + Intersection Observer if needed) — this keeps the 1s render budget.
- NO direct PrimeNG imports in components — use `@mee/ui` wrappers only.
- Reactive Forms only if forms are needed (this feature is read-only — no forms expected).
- Variant swatches: V1 renders only `preview.variant_swatches[0]` if present. NEVER iterate to show all swatches — that is V1.5 scope.

## Files you MAY touch
- `frontend/src/app/pages/preview/preview.component.ts` (NEW)
- `frontend/src/app/pages/preview/preview.component.html` (NEW)
- `frontend/src/app/pages/preview/preview.component.spec.ts` (NEW)
- `frontend/src/app/pages/preview/feed-thumbnail.component.ts` (NEW)
- `frontend/src/app/pages/preview/feed-thumbnail.component.html` (NEW)
- `frontend/src/app/pages/preview/detail-page.component.ts` (NEW)
- `frontend/src/app/pages/preview/detail-page.component.html` (NEW)
- `frontend/src/app/pages/preview/mobile-card.component.ts` (NEW)
- `frontend/src/app/pages/preview/mobile-card.component.html` (NEW)

## Files you must NOT touch
- `frontend/src/app/services/preview.service.ts` (owned by service-builder — READ only)
- `frontend/src/app/core/models/preview.model.ts` (owned by service-builder — READ only)
- `frontend/src/app/core/guards/live-preview-feature.guard.ts` (owned by service-builder)
- `frontend/src/app/app.routes.ts` (owned by service-builder)
- `frontend/src/app/pages/preview/preview.scss` (owned by ui-styler — DO NOT add SCSS now)
- `frontend/src/app/ui/`, `frontend/src/app/layouts/`, `frontend/src/app/design-system/` — all read-only
- Any backend or infra files

## Final report format
```
REPORT: meesell-angular-component-builder
Session: mesell-live-preview-frontend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/pages/preview/preview.component.ts + .html + .spec.ts
- frontend/src/app/pages/preview/feed-thumbnail.component.ts + .html
- frontend/src/app/pages/preview/detail-page.component.ts + .html
- frontend/src/app/pages/preview/mobile-card.component.ts + .html

Component summary:
- PreviewComponent: page container, view switching, refresh subscription, incomplete-state CTA
- FeedThumbnailComponent: marketplace card, renders title_truncated_30 verbatim
- DetailPageComponent: PDP with CDK-drag image carousel, description_truncated_200, full pricing
- MobileCardComponent: mobile-app card, compact

Truncation rendering: VERBATIM (template uses {{ preview.title_truncated_30 }} — no | slice operator)
Image carousel: CDK drag-drop attached for swipe support
1s render budget: <measured time> (target < 1000ms initial paint)

Spec results:
ng test -- --include='**/preview.component.spec.ts' : PASS | FAIL (paste summary)
All 6 component tests passing: yes | <count> of 6 passing

Build check: pnpm build succeeded in <Xs> (target < 90s)

Screenshots attached (raw, pre-styling):
- FeedThumbnail at 360px: yes/no
- DetailPage at 360px: yes/no
- DetailPage at 1280px: yes/no
- MobileCard at 360px: yes/no

Memory update: DONE (.claude/agent-memory/meesell-angular-component-builder/live_preview_feature.md written) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template E — `meesell-angular-ui-styler`

**Dispatched by:** `meesell-frontend-coordinator`
**Phase:** D (last — components must exist before styling)
**Branch:** `feature/live-preview/frontend`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-live-preview-frontend-session-1
Lead: meesell-frontend-coordinator

## Your mission
Author `frontend/src/app/pages/preview/preview.scss` — the Meesho design-language CSS clone. This is the highest-leverage file in the feature: a faithful Meesho-looking render is the entire user-trust value proposition (T4 IMAGE PREVIEW MISSING per VALIDATED_PAIN_POINTS.md). Single SCSS file scoped to the 4 preview components. Tailwind-exception is documented in the file header. Capture founder visual-diff screenshots.

## Mandatory reads (in this order)
1. docs/V1_FEATURE_SPEC.md §F6 (visual diff ≤10% qualitative bar — what "good" looks like)
2. docs/FRONTEND_ARCHITECTURE.md (Layer 1 design tokens — what tokens already exist, how to reference them; Layer 4 features styling rules)
3. docs/CORE_PHILOSOPHY.md (if exists — overall design philosophy is "Meesho seller's safe space"; aesthetic should signal trust + familiarity)
4. frontend/src/app/pages/preview/*.html (READ — understand the DOM shape you are styling)
5. .claude/agent-memory/meesell-angular-ui-styler/MEMORY.md
6. .claude/agent-memory/meesell-angular-ui-styler/live_preview_feature.md (pre-seeded by planning session — includes founder's Meesho reference screenshot URLs)
7. **Visual reference:** Open any live Meesho product listing in browser (e.g., https://www.meesho.com/product/<any-existing-product>) at 360px and 1280px viewports. These are the references you are matching.

## Acceptance criteria
- [ ] `frontend/src/app/pages/preview/preview.scss` created with:
  - ~10-line header doc block documenting:
    - The Tailwind-exception rationale (why we use scoped SCSS here, not Tailwind utilities — the Meesho design language is a clone, not our system)
    - Reference URL to a live Meesho product listing the clone is based on
    - CSS custom properties contract — all Meesho tokens declared at the top under `:host` or `.preview-root` selector so V1.5 brand refresh is a token swap
  - 4 component sub-sections clearly delimited by comment blocks: `/* === FeedThumbnail === */`, `/* === DetailPage === */`, `/* === MobileCard === */`, `/* === PreviewContainer === */`
  - All colors via CSS custom properties (e.g., `--meesho-price-gold: #F5B800`, `--meesho-card-shadow: 0 1px 3px rgba(0,0,0,0.12)`, `--meesho-discount-pink: #F43997`)
  - All spacing on Tailwind's 4-px scale (`0.25rem`, `0.5rem`, `1rem`, `1.5rem`)
  - Mobile-first media queries: base styles at 360px; `@media (min-width: 768px)` for tablet; `@media (min-width: 1280px)` for desktop
  - WCAG AA contrast on all text + interactive elements (test with a contrast checker — Chrome DevTools Lighthouse or axe-core)
- [ ] Visual fidelity: founder-acceptable visual diff vs real Meesho — ≤10% qualitative gap on:
  - Card border-radius (typically 4-8px on Meesho)
  - Card shadow depth (subtle, low elevation)
  - Title typography (font-weight 400-500, size ~14-16px on feed)
  - Price typography (font-weight 600-700, size ~16-18px, gold or dark)
  - Discount badge color + shape (pink/red rounded rect)
  - Image aspect ratio (~1:1 square for thumbnails, varies for detail)
  - Variant swatch styling (small circles or squares, ~24-32px)
- [ ] Build check: `pnpm build` clean in <90s after styles added
- [ ] **Screenshots (attached to PR body):**
  - FeedThumbnail at 360px: side-by-side with real Meesho mobile feed thumbnail
  - DetailPage at 360px: side-by-side with real Meesho mobile PDP
  - DetailPage at 1280px: side-by-side with real Meesho desktop PDP
  - MobileCard at 360px: side-by-side with real Meesho app card (use Meesho mobile app screenshot if accessible)
- [ ] Founder qualitative ≤10% diff sign-off comment posted on PR

## Hard constraints
- **Styling ONLY** — DO NOT modify `.component.ts`, `.component.html`, or `.spec.ts` files (those are component-builder's surface)
- The SCSS file is ONE file, scoped to the 4 preview components. Do NOT split into 4 files per component (the components share Meesho tokens; one file = one source of truth).
- The Tailwind-exception is locked to `preview.scss` only — do NOT extend the exception to other features. If your style would apply elsewhere, surface that as a blocker, do NOT add it here.
- All color values via CSS custom properties (`var(--meesho-...)`) — NO hard-coded hex literals in selector bodies. The custom properties block at the top is the ONLY place hex literals appear.
- NO `!important` — fix specificity by chaining, not by escaping.
- NO direct PrimeNG class overrides (e.g., `.p-card { ... }`) — target `mee-*` wrapper selectors or component host selectors only.
- Image elements use `object-fit: cover` to maintain aspect ratio under varying source dimensions.
- Image carousel scroll: horizontal `scroll-snap-type: x mandatory` + `scroll-snap-align: start` on items for smooth snap-scroll (CDK drag provides programmatic; CSS snap provides native momentum).

## Files you MAY touch
- `frontend/src/app/pages/preview/preview.scss` (NEW — the single Meesho-clone file)

## Files you must NOT touch
- `frontend/src/app/pages/preview/**/*.ts`, `**/*.html`, `**/*.spec.ts` (owned by component-builder)
- `frontend/src/app/services/preview.service.ts` (owned by service-builder)
- `frontend/src/app/core/`, `frontend/src/app/ui/`, `frontend/src/app/layouts/`, `frontend/src/app/design-system/` — all read-only
- `frontend/tailwind.config.js` — DO NOT add Meesho tokens here (the whole point of the exception is they live in preview.scss, not the global config)
- Any backend or infra files

## Final report format
```
REPORT: meesell-angular-ui-styler
Session: mesell-live-preview-frontend-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files created:
- frontend/src/app/pages/preview/preview.scss (<line count> lines)

Design decisions:
- Meesho design language: <font choices, color tokens, key visual primitives>
- CSS custom properties declared: <list e.g., --meesho-price-gold, --meesho-card-shadow, --meesho-discount-pink, ...>
- Card border-radius: <Npx>
- Card shadow: <CSS shadow value>

Visual diff vs real Meesho: <≤5% / ≤10% / >10% — founder will judge>
Mobile-first: designed at 360px | tested at 768px | tested at 1280px
WCAG AA contrast: confirmed (Lighthouse score X) | issues found: <list>

Build check: pnpm build succeeded in <Xs> (target < 90s)

Screenshots attached:
- FeedThumbnail 360px (MeeSell vs Meesho): yes
- DetailPage 360px (MeeSell vs Meesho): yes
- DetailPage 1280px (MeeSell vs Meesho): yes
- MobileCard 360px (MeeSell vs Meesho): yes

Iteration: <1 | 2 | 3 | 4 of 4>

Memory update: DONE (.claude/agent-memory/meesell-angular-ui-styler/live_preview_feature.md written) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

### Template F — `meesell-infra-builder`

**Dispatched by:** Founder (infra-builder is standalone — dispatched directly by founder, not by a lead)
**Phase:** A (can proceed in parallel with backend/frontend)
**Branch:** `feature/live-preview/infra`

```
PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside this path.

SESSION: mesell-live-preview-infra-session-1
Lead: meesell-infra-builder (standalone)

## Your mission
Wire `FEATURE_LIVE_PREVIEW_ENABLED` into the dev / staging / prod K8s deployment configs for both the API pod (backend) and the frontend pod build-env. Author the staging visual-diff approval runbook documenting the qualitative rollout protocol.

## Mandatory reads (in this order)
1. docs/INFRASTRUCTURE_PLAYBOOK.md (full — live state is SSOT; do NOT blindly apply CLAUDE.md k8s/ tree)
2. docs/BACKEND_ARCHITECTURE.md §5.D (env-var registry pattern)
3. docs/plans/features/live-preview/FEATURE_PLAN.md §Decisions D3 (gated rollout posture — dev=true, staging=true-after-approval, prod=true-after-staging-soak)
4. .claude/agent-memory/meesell-infra-builder/MEMORY.md
5. .claude/agent-memory/meesell-infra-builder/live_preview_feature.md (pre-seeded by planning session)

## Acceptance criteria
- [ ] K8s deployment for `dev` namespace API pod updated:
  - `FEATURE_LIVE_PREVIEW_ENABLED=true` (env literal, integer-safe string `"true"`)
- [ ] K8s deployment for `staging` namespace API pod updated:
  - `FEATURE_LIVE_PREVIEW_ENABLED=false` (default off; will flip to `true` after founder visual-diff approval)
- [ ] K8s deployment for `prod` namespace API pod updated:
  - `FEATURE_LIVE_PREVIEW_ENABLED=false` (default off; will flip to `true` after staging soaks ≥1 week with no rollback)
- [ ] Frontend build args:
  - Dev build: `NG_APP_FEATURE_LIVE_PREVIEW_ENABLED=true`
  - Staging build: `NG_APP_FEATURE_LIVE_PREVIEW_ENABLED=false` (flip to true post-approval; rebuild required)
  - Prod build: same as staging default
- [ ] `kubectl apply --dry-run=server -f <manifest>` ran clean for all 3 namespaces
- [ ] `docs/runbooks/live-preview-rollout.md` created documenting:
  - The 3-stage rollout: dev → staging-approval → prod-after-soak
  - **Stage 1 (dev → staging-approval):** Backend coordinator opens the integration PR `feature/live-preview` → `develop`. ui-styler attaches 4 visual-diff screenshot pairs (FeedThumbnail 360px, DetailPage 360px, DetailPage 1280px, MobileCard 360px — MeeSell vs Meesho side-by-side). Founder reviews qualitatively. Approval comment + screenshot pair on PR body is the gate. **Decision logged in the PR body** (NOT a separate doc).
  - **Stage 2 (staging flip):** After integration PR merges to `develop`, infra-builder updates the staging manifest to `FEATURE_LIVE_PREVIEW_ENABLED=true` AND rebuilds the frontend with `NG_APP_FEATURE_LIVE_PREVIEW_ENABLED=true`. Both deployments roll out. Soak monitoring: any user-reported issue on staging within 7 days triggers stage-2 rollback (`=false` again).
  - **Stage 3 (prod flip):** After 7 days clean on staging, infra-builder flips prod manifest + frontend build. Same rollback mechanism.
  - **Rollback procedure:** Set env var back to `false` in the relevant manifest; `kubectl rollout restart deployment/api-<namespace>`; rebuild and deploy frontend with `=false`. Total rollback time: ~5 minutes API + ~3 minutes frontend deploy.
- [ ] No changes to secrets (feature flags are non-secret env vars) — verify no Secret Manager references touched
- [ ] `docs/status/feature_board_infra.md` row for `live-preview` updated to `IN REVIEW` once the infra PR opens (NOT in this session — that happens when master consolidation creates the infra PR)

## Hard constraints
- Read `docs/INFRASTRUCTURE_PLAYBOOK.md` FIRST — live state differs from CLAUDE.md k8s/ snapshot; the playbook is SSOT
- Use STRING literal `"true"` / `"false"` for the K8s env var value (K8s env values are strings; Pydantic Settings parses them via `BaseSettings` coercion). DO NOT use integer 1/0 or unquoted true/false.
- `kubectl apply --dry-run=server` is MANDATORY before any live apply
- DO NOT touch any secrets — feature flags are non-secret config
- DO NOT touch any backend, frontend, or other docs/plans/ files
- Cost impact: ₹0/month (env var additions only). State explicitly in PR body.

## Files you MAY touch (consult INFRASTRUCTURE_PLAYBOOK.md for actual paths)
- K8s deployment manifest for `dev` namespace API pod (MODIFY)
- K8s deployment manifest for `staging` namespace API pod (MODIFY)
- K8s deployment manifest for `prod` namespace API pod (MODIFY)
- Frontend build config / Cloud Build yaml or equivalent (MODIFY — for NG_APP_FEATURE_LIVE_PREVIEW_ENABLED build args)
- `docs/runbooks/live-preview-rollout.md` (NEW)
- `docs/status/feature_board_infra.md` (MODIFY only AFTER infra PR opens — NOT in this session)

## Files you must NOT touch
- `k8s/postgres.yaml`, `k8s/valkey.yaml`, `k8s/ingress.yaml` — DOCUMENTATION-ONLY manifests per infra memory
- Any terraform files (no provisioning changes)
- Any backend, frontend, or other feature-planning files
- Any MASTER_PLAN or lead spec

## Final report format
```
REPORT: meesell-infra-builder
Session: mesell-live-preview-infra-session-1
Status: COMPLETE | BLOCKED | PARTIAL

Files modified:
- <actual k8s dev API manifest path> (FEATURE_LIVE_PREVIEW_ENABLED="true")
- <actual k8s staging API manifest path> (FEATURE_LIVE_PREVIEW_ENABLED="false")
- <actual k8s prod API manifest path> (FEATURE_LIVE_PREVIEW_ENABLED="false")
- <frontend build config path> (NG_APP_FEATURE_LIVE_PREVIEW_ENABLED build args added for 3 envs)

Files created:
- docs/runbooks/live-preview-rollout.md

Dry-run results:
kubectl apply --dry-run=server -f <dev manifest>: CLEAN | ERROR
kubectl apply --dry-run=server -f <staging manifest>: CLEAN | ERROR
kubectl apply --dry-run=server -f <prod manifest>: CLEAN | ERROR

Cost impact: ₹0/month (env var additions only)

Memory update: DONE (.claude/agent-memory/meesell-infra-builder/live_preview_feature.md written) | SKIPPED (reason: <why>)

Blockers / notes:
<none | specific issue>
```
```

---

## Review + iteration protocol

### Backend group PR (`feature/live-preview/backend` → `feature/live-preview`)

**Reviewer:** `meesell-backend-coordinator`
**Template:** `.github/PULL_REQUEST_TEMPLATE/backend.md`

**What the backend lead checks before approving:**

| # | Check | Pass | Fail → re-dispatch |
|---|-------|------|--------------------|
| 1 | `title_truncated_30 = title_full[:30]` (Python str slicing, NOT `.encode().decode()` bytewise) | exact | Bytewise truncation — re-dispatch services-builder citing D2 + the emoji test fixture |
| 2 | `description_truncated_200 = description_full[:200]` same pattern | exact | Same — re-dispatch |
| 3 | `assert_owned` called BEFORE products row fetch (404 masks 403) | confirmed | Order reversed → leaks product existence — re-dispatch services-builder citing §4.C |
| 4 | `image.service.get_image_urls(product_id, user_id)` is the only cross-module call (per §16.A) | confirmed | Direct `product_images` query or other module call — re-dispatch citing §16.A allowed-edges matrix |
| 5 | `image_carousel_urls` rendered in slot-index order (not re-sorted) | confirmed | Re-sorting found — re-dispatch services-builder citing §11.C contract |
| 6 | `variant_swatches` returns max 1 entry in V1 (not full matrix) | confirmed | Full matrix returned — re-dispatch citing D1 V1 limit |
| 7 | `PreviewResponse` has all 11 fields per D2 table with non-empty descriptions | exact field list | Missing field OR empty descriptions — re-dispatch api-routes-builder |
| 8 | Route uses `Depends(require_feature_flag("live_preview"))` — NOT inline if-statement | confirmed | Inline check — re-dispatch api-routes-builder citing generic-factory pattern |
| 9 | `FeatureDisabledError` returns 404 with `code="feature.live_preview.disabled"` envelope | confirmed | Different status/code — re-dispatch services-builder citing D3 |
| 10 | Unit tests: emoji-at-position-28 test passes (no codepoint split) | green | Splits emoji — re-dispatch services-builder; suggest `regex` library `\X` cluster match for V1.5 |
| 11 | Integration test: feature_flag=false returns 404 | green | Returns 200/500 — re-dispatch api-routes-builder |
| 12 | Integration test: non-owner returns 404 (not 403) | green | Returns 403 — re-dispatch services-builder citing §4.C |
| 13 | No `os.getenv()` anywhere | clean | Found — re-dispatch citing §6.G CI linter rule |

**Re-dispatch preamble template (use when any check above fails):**

```
PREVIOUS RUN FAILED — {check description}

[Paste original Template A or B here]

## Correction for this re-dispatch
The previous session failed check #{N}: {specific failure}.

Fix required: {exact fix per the check above}.

Read: docs/BACKEND_ARCHITECTURE.md {specific section}, docs/plans/features/live-preview/FEATURE_PLAN.md §Decisions.

This is iteration {M} of 3. If the fix is not applied by iteration 3, escalate to founder and open a blocker row on docs/status/feature_board_backend.md.
```

**Maximum iterations:** 3 per specialist (per D6).

---

### Frontend group PR (`feature/live-preview/frontend` → `feature/live-preview`)

**Reviewer:** `meesell-frontend-coordinator`
**Template:** `.github/PULL_REQUEST_TEMPLATE/frontend.md`

**What the frontend lead checks before approving:**

| # | Check | Pass | Fail → re-dispatch |
|---|-------|------|--------------------|
| 1 | Templates render `{{ preview.title_truncated_30 }}` VERBATIM — no `\| slice:` operator on `title_full` anywhere | grep clean | Client truncation found — re-dispatch component-builder citing D2 server-side contract |
| 2 | `PreviewResponse` interface field names match backend snake_case EXACTLY | confirmed | Renamed to camelCase — re-dispatch service-builder; would break API contract |
| 3 | Image carousel uses `@angular/cdk/drag-drop` for swipe — NOT HammerJS | confirmed | HammerJS imported — re-dispatch component-builder; install bloat |
| 4 | `livePreviewFeatureGuard` is SYNCHRONOUS (no async, no HTTP) | confirmed | Async found — re-dispatch service-builder; signal/env is sync |
| 5 | All 4 components: `standalone: true`, `OnPush` | confirmed | Missing either — re-dispatch component-builder |
| 6 | `pnpm build` < 90s | < 90s | ≥ 90s — stop, escalate to founder (build budget exceeded) |
| 7 | Initial paint < 1s (measured) | < 1000ms | ≥ 1000ms — re-dispatch component-builder; check image preload sizing, CDK lazy-load |
| 8 | Image carousel swipes correctly on touch device (manual test on iOS Safari + Android Chrome) | confirmed | Doesn't swipe — re-dispatch component-builder; verify CDK drag listener attached to scroll container |
| 9 | preview.scss header has Tailwind-exception rationale documented | present | Missing — re-dispatch ui-styler |
| 10 | preview.scss color values via CSS custom properties — no hex literals in selector bodies | grep clean | Hex literals found — re-dispatch ui-styler |
| 11 | preview.scss NO direct PrimeNG class overrides (`.p-card { ... }`) | grep clean | Override found — re-dispatch ui-styler; use mee-* wrapper selector |
| 12 | preview.scss NO `!important` | grep clean | Found — re-dispatch ui-styler; fix specificity by chaining |
| 13 | Founder visual-diff screenshots at 360px AND 1280px for FeedThumbnail + DetailPage + MobileCard attached to PR | present | Missing screenshots — return PR to ui-styler |
| 14 | Founder qualitative ≤10% diff sign-off comment on PR | present | Diff too large per founder — re-dispatch ui-styler with "Previous diff failed on {area} — examine: card shadow, badge colors, typography weights; reference the founder's annotated Meesho screenshot at <attached path>" |
| 15 | WCAG AA contrast confirmed via Lighthouse | green | Issues — re-dispatch ui-styler citing specific elements |
| 16 | Incomplete-state CTA navigates correctly to `/catalogs/{id}/edit?focus={missing_field}` | confirmed | Wrong navigation — re-dispatch component-builder |
| 17 | Auto-refresh works: trigger `previewService.refreshTrigger$.next(productId)` → preview re-fetches | confirmed | Doesn't refresh — re-dispatch service-builder; check Subject vs BehaviorSubject choice |

**Re-dispatch preamble template (frontend):**

```
PREVIOUS RUN FAILED — {check description}

[Paste original Template C, D, or E here]

## Correction for this re-dispatch
Previous session failed check #{N}: {specific failure}.
Fix: {exact fix}.
Read: {specific doc + section}.
Iteration {M} of {3 default | 4 for ui-styler visual-diff per D6}.
```

**Maximum iterations:** 3 per specialist; **4 for `meesell-angular-ui-styler` visual-diff** (per D6 exception — qualitative bar may need extra passes).

---

### Infra group PR (`feature/live-preview/infra` → `feature/live-preview`)

**Reviewer:** `meesell-infra-builder` (self-review, then founder gate)
**Template:** `.github/PULL_REQUEST_TEMPLATE/infra.md`

**What infra lead checks before self-approving:**

| # | Check | Pass | Fail → re-do |
|---|-------|------|--------------------|
| 1 | `kubectl apply --dry-run=server` clean for all 3 namespaces | all clean | Any error — fix before PR |
| 2 | `FEATURE_LIVE_PREVIEW_ENABLED="true"` in dev (string), `="false"` in staging + prod | strings | Integer / unquoted — fix manifest |
| 3 | Frontend build args set for all 3 envs (NG_APP_FEATURE_LIVE_PREVIEW_ENABLED) | confirmed | Missing — add build args |
| 4 | `live-preview-rollout.md` describes all 3 stages + rollback procedure | both present | Missing either — complete runbook |
| 5 | Cost impact stated in PR body as ₹0 | stated | Missing — add to PR body |
| 6 | No secrets touched | confirmed | Secret reference modified — revert |

---

## Memory management

Agents are stateless across sessions — the only continuity they have is their `MEMORY.md`. Without explicit memory updates after each specialist session, re-dispatches (retries, review-requested revisions, future cross-feature references) are blind to what was already built. This is the founder's #1 cross-cutting concern (mesell-live-preview-planning-session-1: "agent will become lack of which feature updated need to add in which area").

### Protocol — mandatory for every dispatch in this feature

Every dispatch template above ends with a **Memory update** block. The agent MUST:

1. Create (or update) `.claude/agent-memory/{agent-name}/live_preview_feature.md` — the feature memory file for this agent
2. Add a one-line pointer to it in their `MEMORY.md` index under `## live-preview` section
3. Commit both the code AND the memory file on the same branch (memory and code stay in sync; master consolidation handles the actual commit)
4. Include `Memory update: DONE | SKIPPED (reason)` in the final report sent back to the lead

If the agent cannot write to memory (e.g., a blocker prevented code completion), they still write a memory entry recording the blocker and their partial state.

### Pre-dispatch memory seeding

The 3 **lead agents** are seeded with live-preview awareness BY THIS PLANNING SESSION (files created below). Specialist agents write their own memory when they complete their session; they do not need pre-seeding because they receive a full dispatch template with all context.

**Lead memory files created by this planning session:**
- `.claude/agent-memory/meesell-backend-coordinator/live_preview_feature.md` ✅
- `.claude/agent-memory/meesell-frontend-coordinator/live_preview_feature.md` ✅
- `.claude/agent-memory/meesell-infra-builder/live_preview_feature.md` ✅

### Per-agent memory spec

What each agent MUST record in `live_preview_feature.md` when they complete their session:

| Agent | What to record |
|-------|----------------|
| `meesell-backend-coordinator` | Which specialists were dispatched, which phase, PR# of feature/live-preview/backend, blockers if any, feature_board_backend.md status row for live-preview |
| `meesell-frontend-coordinator` | Which specialists were dispatched, which phase, PR# of feature/live-preview/frontend, blockers if any, feature_board_frontend.md status row, ui-styler iteration count (especially if used the D6 4-iteration exception) |
| `meesell-infra-builder` | K8s manifests touched (exact paths), dry-run results, PR# of feature/live-preview/infra, rollout-runbook path, feature_board_infra.md status row |
| `meesell-services-builder` | `get_preview` final implementation summary (truncation strategy, ownership-assertion order, cross-module call to image), `core/feature_flags.py` summary, unit test count + pass status |
| `meesell-api-routes-builder` | `PreviewResponse` final 11-field shape, route line in `catalog/routes.py`, `FEATURE_LIVE_PREVIEW_ENABLED` config.py addition, integration test count |
| `meesell-angular-service-builder` | `PreviewService` public API (method signatures + refreshTrigger$ shape), guard registration in app.routes.ts, environment.* additions |
| `meesell-angular-component-builder` | Component selectors, view-switching strategy (query param contract), CDK drag attachment, image-preload strategy, spec test count |
| `meesell-angular-ui-styler` | Meesho design tokens (CSS custom property names + values), visual diff result (qualitative percentage per founder), iteration count, screenshots attached count |

### Memory file template (use this structure for `live_preview_feature.md`)

```markdown
---
name: live-preview-feature
description: live-preview Feature 6 — what this agent built, files it owns, contracts it implemented
metadata:
  type: project
---

Feature: live-preview (Feature 6 of 9)
Branch: feature/live-preview/{backend|frontend|infra}
Session: mesell-live-preview-{group}-session-{N}
Date: YYYY-MM-DD
Status: COMPLETE | PARTIAL | BLOCKED

## What I built
<list of files created/modified with one-line description of what each does>

## Key contracts I implemented
<critical decisions, method signatures, config values — anything the next specialist needs to know>

## What the next agent in the chain needs from my output
<specific outputs: schema shape, interface signatures, mounted paths, env var names, etc.>

## PR
feature/live-preview/{backend|frontend|infra} PR #<N> — <status: open|merged|blocked>

## Iteration count (for visibility into re-dispatches)
<N of 3 default, or N of 4 for ui-styler>

## Blockers
<none | specific blocker with context>
```

### Cross-feature memory hygiene (founder's stated concern)

When an agent works on multiple features in succession (e.g., `meesell-services-builder` works on catalog-form, then live-preview, then xlsx-export):

- Each feature has its OWN `{feature-slug}_feature.md` file — never mixed
- The agent's `MEMORY.md` index lists every feature they've touched under separate `### {feature-slug}` headings
- When dispatched on feature N, the agent reads `MEMORY.md` + the relevant `{feature-slug}_feature.md` — NOT the other features' files
- No file in `.claude/agent-memory/` belongs to multiple features. Cross-feature insights stay in the `MEMORY.md` index as separate `### sessions/observations` entries.

---

## Acceptance gate

This feature is "done" (ready for `feature/live-preview` → `develop` PR) when ALL of the following are true:

### All group PRs merged to `feature/live-preview`
- [ ] `feature/live-preview/backend` → `feature/live-preview` merged (backend coordinator approved per the 13-check review protocol)
- [ ] `feature/live-preview/frontend` → `feature/live-preview` merged (frontend coordinator approved per the 17-check review protocol)
- [ ] `feature/live-preview/infra` → `feature/live-preview` merged (infra lead self-approved per the 6-check review protocol)

### CI gates green on `feature/live-preview`
- [ ] gate-1 unit: all unit tests pass (backend unit/catalog/test_get_preview.py + frontend preview.service.spec.ts + preview.component.spec.ts)
- [ ] gate-2 smoke: GET /api/v1/products/{id}/preview returns expected 200 (happy) and 404 (flag off / non-owner)
- [ ] gate-3 lint: ruff (backend) + ng lint (frontend) both clean; no `os.getenv()` in services; no client-side truncation in templates
- [ ] gate-4 integration: `test_live_preview_integration.py` passes (5-test chain)
- [ ] gate-5 golden_roundtrip: N/A (no XLSX touched — gate-5 skipped for this feature)

### Manual acceptance criteria from `V1_FEATURE_SPEC.md §F6`
- [ ] All 3 views (feed thumbnail / detail page / mobile card) render < 1s after page load
- [ ] Title truncation marker at ~30 chars visible on feed thumbnail and mobile card (server-side `title_truncated_30` rendered verbatim)
- [ ] Image carousel: swipe works on touch device (verified on iOS Safari + Android Chrome); slot-index order preserved
- [ ] Missing-fields CTA renders when product has <1 image OR title < 5 chars; CTA deep-links to `/catalogs/{id}/edit?focus={field}`
- [ ] V1 limitation: only 1 variant swatch rendered (variant matrix deferred to V1.5)
- [ ] V1 limitation: descriptions truncated at 200 chars in detail preview
- [ ] Visual diff vs real Meesho ≤10% — founder qualitative sign-off comment on PR with the 4 screenshot pairs (FeedThumbnail 360px, DetailPage 360px, DetailPage 1280px, MobileCard 360px)

### Documentation deliverables present
- [ ] OpenAPI entry for `GET /api/v1/products/{id}/preview` with all 11 PreviewResponse fields' descriptions
- [ ] `get_preview` service-method docstring describing §16.A cross-module call to image
- [ ] `PreviewComponent` docstring describing view-switching logic
- [ ] `FeedThumbnailComponent` docstring documenting the locked truncation-renders-verbatim contract
- [ ] `preview.scss` header doc block with Tailwind-exception rationale + Meesho reference URL
- [ ] `live-preview-rollout.md` runbook with 3-stage rollout + rollback
- [ ] `app.routes.ts` comment block on the `/catalogs/:id/preview` route

### Feature flag posture verified
- [ ] Dev: `FEATURE_LIVE_PREVIEW_ENABLED=true` (manifests + frontend build) — preview accessible
- [ ] Staging: `FEATURE_LIVE_PREVIEW_ENABLED=false` initially — preview returns 404 + "Preview unavailable" placeholder; founder approval is the gate to flip to `true`
- [ ] Prod: `FEATURE_LIVE_PREVIEW_ENABLED=false` initially — same; staging soak ≥7 days is the gate

### Founder gate
- [ ] All CI gates green on `feature/live-preview`
- [ ] Founder qualitative ≤10% visual-diff sign-off (comment on integration PR body)
- [ ] Founder reviews and approves `feature/live-preview` → `develop` PR
- [ ] After merge to develop: backend coordinator stamps `V1_FEATURE_SPEC.md §F6` ("implemented YYYY-MM-DD PR#N") and `BACKEND_ARCHITECTURE.md §10.C` sentinel comment

---

## Risk register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| 1 | **Meesho redesigns their feed-card mid-V1, making our clone stale** | Medium — Meesho ships UI changes quarterly; we have no visibility into their roadmap | High — our differentiator (faithful render) erodes overnight; sellers lose trust in the preview accuracy | The feature flag (D3) IS the kill-switch. If Meesho redesigns: set `FEATURE_LIVE_PREVIEW_ENABLED=false` across all envs (5-minute rollback per the runbook), users see "Preview unavailable" placeholder, ui-styler dispatched for a re-clone iteration. The CSS custom properties contract in `preview.scss` makes token-swap re-cloning fast (no DOM changes needed). Rollback cost: ~5 minutes + 1-3 hours ui-styler re-clone vs the alternative of weeks of customer complaints. |
| 2 | **Mobile swipe fails on iOS Safari due to gesture handling quirks** | Medium — iOS Safari has historically been quirky with CDK drag-drop on horizontal scroll | High — Tirupur seller audience is heavily iOS Safari (per `BUSINESS_STRATEGY.md` — verify); broken swipe means broken core UX | Frontend lead checklist item #8 requires manual swipe test on iOS Safari + Android Chrome BEFORE PR approval. CDK drag-drop has documented iOS workarounds (use `cdkDragLockAxis="x"` + native CSS `scroll-snap-type: x mandatory` as fallback). If CDK fails on iOS: re-dispatch component-builder with "fallback to native horizontal scroll + scroll-snap-align" preserving the same user experience without the JS gesture handler. |
| 3 | **Image preload bandwidth blows the 1s render budget on slow 3G** | Medium-High — Tirupur audience on 4G/3G with varying signal; 4 images × ~200KB each = ~800KB initial load on detail page | High — fails the 1s spec criterion (D1); users see spinner instead of preview, defeats the purpose | Component-builder template (D) explicitly requires: only `first_image_url` is eagerly loaded; the rest of `image_carousel_urls` are lazy via `loading="lazy"` + Intersection Observer. The 1s budget is measured to FIRST CONTENTFUL PAINT of the feed-thumbnail OR detail PAGE-with-first-image, NOT all-images-loaded. If still over budget: pre-generate WebP variants in `image.service.upload` (V1.5 scope; V1 ships with whatever Pillow + the image_processor.py emits). |
| 4 | **Title truncation edge cases on emoji / RTL / combining-character strings** | Medium — Tirupur sellers may use Tamil (Brahmic combining marks) and emoji in product titles | Medium — incorrect truncation can split a combining mark from its base character (renders as ◌), or split a flag emoji into the two regional indicator code points (renders as separate letters) | The services-builder unit test plan (Template A) includes a fixture for emoji at position 28. V1 ships with `title[:30]` (Python code-point slicing) — correct for BMP code points AND most emoji as single code points, but NOT correct for ZWJ-joined emoji sequences (e.g., 👨‍👩‍👧 is 5 code points). V1.5 upgrade: use `regex` library `\X` (grapheme cluster) matching. Documented in the services-builder template hard constraints. If a real-world title triggers a split that looks broken, the fix is a re-dispatch services-builder with the V1.5 upgrade pulled forward (~2h of work). |
| 5 | **V1 single-variant limit becomes the support-load top complaint** | High — sellers often have 3-5 variants per product (color, size); rendering only 1 makes the preview look incomplete | Medium — sellers complain but don't churn (preview is a confidence aid, not a blocker on listing creation); supports increases but ship velocity preserved | The V1.5 variant-matrix is already scoped (`variant_swatches: list[VariantSwatch]` is plural-typed — frontend just iterates instead of `[0]`). When complaint volume crosses ~10/week, prioritize the V1.5 dispatch (estimated ~4-6h). Document in the rollout runbook as a known limitation with timeline ("variant matrix in V1.5, target Q3"). |

---

## Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1 | 2026-06-10 | mesell-live-preview-planning-session-1 | Initial FEATURE_PLAN.md authored. Decisions D1-D6 recorded verbatim. All 6 specialist dispatch templates drafted. Branch setup section documented as TBD by master consolidation (per parallel-sub-session coordination interrupt). Memory management section with cross-feature hygiene addressing founder's stated concern. Risk register with 5 risks (Meesho redesign, iOS swipe, 3G bandwidth, truncation edge cases, V1 variant limit). |
