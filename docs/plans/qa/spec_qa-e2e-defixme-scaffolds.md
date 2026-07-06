# SPEC B — de-FIXME the 9 E2E scaffolds

**Author:** `meesell-qa-coordinator` (session `mesell-qa-wave-pricing-coord-session-1`)
**Date:** 2026-07-06
**Target specialist:** `meesell-e2e-test-writer` (opus) + cross-lead enablement (infra / backend / data / frontend)
**Baseline:** develop @ `9ebc0d9`
**Skill:** `.claude/skills/meesell-e2e-testing/SKILL.md`

> This is a **test-enablement spec**, not an implementation. It tells the e2e writer + the
> enabling leads exactly what each `test.fixme` needs to become a real green test, and makes
> the no-spend storage + Gemini calls. OPEN QUESTIONs are flagged, not blocking.

---

## 1. Inventory — all 9 `test.fixme` blocks, RE-VERIFIED against develop `9ebc0d9`

There are exactly **9** `test.fixme()` blocks in `frontend/e2e/` (the other 4 grep hits are
comments/docstrings). Several fixme *reasons* were written against the older develop `a94e013`
and are now STALE — I re-verified each blocker in current source:

| # | Test | File:line | Fixme reason (as written) | RE-VERIFIED blocker @ `9ebc0d9` | Group |
|---|---|---|---|---|---|
| 1 | CAT-E2E-03 browse-fallback link | `flows/category-picker.spec.ts:126` | link ships no data-testid; role/name not live-verified (env-blocked exploration) | STILL TRUE — `browseIfNoneMatch` targeted by `getByRole('button',…)`, no testid | **F** frontend/live-verify |
| 2 | CAT-E2E-07 empty-state | `flows/category-picker.spec.ts:157` | empty-state + CTA no data-testid; role/name not live-verified | STILL TRUE — `getByRole('status',/no automatic suggestions/)` + `getByRole('button',/browse all categories/)`, no testid | **F** frontend/live-verify |
| 3 | CAT-E2E-05 autosave-across-reload | `flows/catalog-creation.spec.ts:62` | category-schema 404 for picker-chosen cats (seeded ~100, tree 3,772) → no inputs | STILL TRUE as an **env/seed** gap — data model is complete (3,772 leaves each have a valid `template_id`, proven by CAT-BE-17-GUARD #474); the E2E DB is schema-only | **S** seed |
| 4 | CAT-E2E-06 AI auto-fill | `flows/catalog-creation.spec.ts:100` | same seed gap; autofill POST 200 but no inputs to populate | STILL TRUE — needs the seed (inputs) **AND** an autofill response (Gemini) | **S + G** seed + Gemini |
| 5 | PQE-E2E-05 export download | `flows/export.spec.ts:68` | `POST /images` 502 gcs.unavailable; ready→signed-URL needs GCS | STILL TRUE — no storage backend in dev/CI | **ST** storage |
| 6 | W3-E2-2 live-preview | `flows/live-preview.spec.ts:28` | frontend preview page RETIRED (#278); button repointed to `/edit` (#395) | STILL TRUE — `app.routes.ts:66` confirms `:id/preview` retired; no surface exists | **P** product gap → escalate, do NOT enable |
| 7 | W3-E2-6 price-apply-export | `flows/price-apply-export.spec.ts:30` | mfe-pricing "no apply control, zero testids" + export productId not fixed | **STALE — RESOLVED.** `pricing-apply-btn` exists (#439/SPEC-C); export productId fixed (`resolveExportProductId`) | **R** resolved → **SPEC A** |
| 8 | image-precheck valid-JPEG | `flows/image-precheck.spec.ts:38` | `POST /images` 502 gcs.unavailable before rembg runs | STILL TRUE — no storage backend | **ST** storage |
| 9 | W3-E2-4 catalog-edit-delete | `flows/catalog-edit-delete.spec.ts:32` | catalog-list "no delete control + no per-row testids" | **STALE — RESOLVED.** PR #425 (`77b5db0`) added per-row delete + testids: `catalog-row`, `catalog-delete-btn`, `catalog-delete-confirm`, `catalog-delete-cancel`, `catalog-edit-btn`, `catalog-empty` | **R** resolved (frontend done) |

### Group summary
- **R — Resolvable NOW, no external dependency (2):** W3-E2-6 (→ SPEC A), W3-E2-4 (#425 landed the delete UI + testids).
- **F — Frontend selector / live-verify (2):** CAT-E2E-03, CAT-E2E-07.
- **S — Category-schema seed (2):** CAT-E2E-05, CAT-E2E-06.
- **G — Gemini no-spend fixture (1, overlaps S):** CAT-E2E-06.
- **ST — Storage / fake-gcs-server (2):** PQE-E2E-05, image-precheck.
- **P — Product gap, NOT a test-enablement (1):** W3-E2-2 live-preview.

---

## 2. Storage decision — **fake-gcs-server**, NOT MinIO, NOT a paid GCS bucket

**The adapter is `google.cloud.storage` (GCS JSON API), not S3.** `backend/app/adapters/gcs.py`
builds a `storage.Client` and calls `upload_bytes` / `download_bytes` / `generate_signed_url` /
`delete`. This drives the decision:

| Option | Verdict | Why |
|---|---|---|
| **`fsouza/fake-gcs-server`** (GCS-JSON-API emulator, Docker) | **CHOSEN** | Speaks the SAME API the adapter already uses. `google-cloud-storage` honors `STORAGE_EMULATOR_HOST` → the existing adapter points at the emulator with **zero backend code change** for upload/download. Free, hermetic, self-contained, wires into CI as a service container exactly like the `postgres:16-alpine` / `valkey:8-alpine` containers in Gate-4 (`ci.yml` L289/L299). |
| **MinIO** | **REJECTED** | MinIO speaks **S3**, not the GCS JSON API. Using it would require rewriting `adapters/gcs.py` to an S3 client (boto3) or adding an S3 code path — a product change far outside a test lane, and it would diverge the test seam from the prod seam (GCS). The task framed the choice as "MinIO vs GCS bucket"; the correct GCS-native analog of MinIO here is fake-gcs-server. |
| **Paid GCS test bucket** | **REJECTED** | Spend (violates the no-spend constraint), needs real service-account creds in CI (secret-management burden), and is **non-hermetic** (shared network state, flaky, cleanup required). Only justifiable if signed-URL fidelity forces it — see OQ-1. |

### 2.1 fake-gcs-server enablement (infra + a thin backend confirm)
1. **CI + local:** add a `fsouza/fake-gcs-server` service to the E2E job (and optionally
   `docker-compose.dev.yml`), started with `-scheme http -public-host localhost:4443` (or chosen port).
2. **Pre-create the bucket** the app expects (`GCS_BUCKET`) at container start (fake-gcs-server can
   seed buckets from a mounted dir or a startup `mkdir`/init request).
3. **Point the backend at it:** set `STORAGE_EMULATOR_HOST=http://localhost:4443` on the E2E backend
   process. Backend confirm task (backend-coordinator): verify `_get_client()` (gcs.py L69-101)
   actually routes to the emulator when `STORAGE_EMULATOR_HOST` is set — if the explicit
   `from_service_account_info` / `project=` construction overrides the emulator, add a small
   `if settings.STORAGE_EMULATOR_HOST:` anonymous-client branch (surgical, adapter-local).
4. **Result:** `POST /products/{id}/images` now 200s (upload to the emulator) → the rembg precheck
   pipeline runs → **image-precheck un-fixme'd**. Export `upload_bytes`/`download_bytes` legs work too.

### 2.2 The signed-URL nuance (export-download, PQE-E2E-05) — see OQ-1
`export/service.py` L268 returns a **signed** GCS URL for the ready xlsx. fake-gcs-server's
signed-URL support is partial (signing needs a private key; the emulator can serve objects but
v4-signed-URL validation differs). Two fallbacks if the signed URL won't download in-emulator:
- **(preferred, hermetic)** a backend env-flagged fake-storage mode (`STORAGE_BACKEND=fake`) that
  mirrors the pytest `mock_gcs_adapter` (in-memory dict, conftest L838-890) and returns a **local
  backend-served URL** instead of a GCS signed URL. No container at all; fully hermetic. Backend change.
- **(fallback)** run fake-gcs-server in public-object mode and have the ready-export path return the
  public object URL under the emulator when `STORAGE_EMULATOR_HOST` is set.

---

## 3. No-spend Gemini fixture — **Playwright route-interception (canned JSON)**

**CI already runs real Gemini ONLY in the nightly `ai_eval` job** (`GEMINI_API_KEY_CI`, a low-quota
key; `ci.yml` L56/L76). All PR gates use `GEMINI_API_KEY: ci-dummy-gemini-key` (`ci.yml` L333) — i.e.
**no real AI call in the gate path**. The pytest layer stubs Gemini via `monkeypatch` of
`app.ai_ops.client.call_gemini` (conftest L784/L799). E2E cannot use `monkeypatch` (it drives a real
uvicorn), so the no-spend seam must be at a boundary the test controls:

| Approach | Verdict | Notes |
|---|---|---|
| **Playwright `page.route()` canned-JSON stub of `POST /products/{id}/autofill`** | **CHOSEN (primary)** | Hermetic, zero spend, zero backend change, and it is the SAME pattern CAT-E2E-03/07 already use to stub `POST /categories/suggest`. E2E asserts the **frontend applies + renders** the AI response; the **quality** of the real AI output is covered by the nightly `ai_eval` (real low-quota key) + pytest golden fixtures — E2E must not duplicate that. |
| **Backend env-flagged fake-Gemini mode** (`FAKE_GEMINI=1` → canned response from a fixtures dir) | **ALTERNATIVE** | More faithful (exercises the real route + parse), but needs a backend change (ai-coordinator/backend scope). Use only if we want the autofill *route* in the E2E path rather than a network stub. |
| Real Gemini in the E2E job | **REJECTED** | Spend + non-deterministic + rate-limited. The nightly `ai_eval` already owns real-AI verification. |

**Design of the canned autofill stub (CAT-E2E-06):** intercept `**/products/*/autofill`, fulfill 200
with a body whose keys are the **seeded category's** field canonicals (so the values land in rendered
inputs — this is WHY CAT-E2E-06 needs the seed too). Then assert the visible outcome: filled-input
count rises after the click (the spec's existing `expect.poll(...).toBeGreaterThan(filledBefore)`).

---

## 4. Per-fixme enablement steps

| # | Test | Enablement steps | Owner(s) |
|---|---|---|---|
| 7 | **W3-E2-6** | Rewrite per **SPEC A §3.3** (apply→export-page-reachable). No external dep. | e2e-writer |
| 9 | **W3-E2-4** | Live-verify the #425 testids (`catalog-row`, `catalog-edit-btn`, `catalog-delete-btn`, `catalog-delete-confirm`, `catalog-delete-cancel`, `catalog-empty`) into `selector_registry.md`; codify: create product → open list → click `catalog-delete-btn` on its `catalog-row` → click `catalog-delete-confirm` → assert the row's `catalog-row` count drops / `catalog-empty` shows. Edit leg already covered by W3-E2-1. | e2e-writer |
| 1 | **CAT-E2E-03** | Live-verify the `getByRole('button',/browse|none match/)` fallback link on the running stack; if it resolves stably, un-fixme as-is (semantic role selector is acceptable per the skill). If NOT stable, request a `data-testid` (e.g. `smart-picker-browse-fallback`) on `smart-picker.component.ts` via a frontend-coordinator memo. | e2e-writer (+ frontend if testid needed) |
| 2 | **CAT-E2E-07** | Same as CAT-E2E-03 for `getByRole('status',/no automatic suggestions/)` + `getByRole('button',/browse all categories/)` (empty-state + CTA). Un-fixme on live-verify, else request `data-testid` (`smart-picker-empty` / `smart-picker-empty-browse`). | e2e-writer (+ frontend if testid needed) |
| 3 | **CAT-E2E-05** | Seed the E2E DB with categories + templates + `field_enum_values` for the categories the flow will use. Recommended: **pin a known-schema'd category** and stub `/suggest` to return it (light, hermetic — see OQ-3) so the edit form renders inputs; then the autosave-across-reload assertion runs unchanged. | data-engineer / infra (seed) + e2e-writer |
| 4 | **CAT-E2E-06** | Seed (as #3) **so inputs render**, AND stub `POST /autofill` with canned JSON keyed to the seeded category's fields (§3). Assert filled-count rises. | data-engineer/infra (seed) + e2e-writer (stub) |
| 5 | **PQE-E2E-05** | Stand up fake-gcs-server + `STORAGE_EMULATOR_HOST` (§2.1). Reach a `ready` product (all required fields + a front image that passes the gate). If the signed-URL download won't serve from the emulator, apply the backend fake-storage fallback (§2.2 / OQ-1). Then assert the download event + non-empty `.xlsx`. | infra (container) + backend (emulator confirm / fake-signed-URL) + e2e-writer |
| 8 | **image-precheck** | fake-gcs-server + `STORAGE_EMULATOR_HOST` (§2.1) → `POST /images` 200 → rembg precheck runs → assert `precheck-card` + `precheck-status` visible. Simpler than PQE-E2E-05 (no signed-URL leg). | infra (container) + backend (emulator confirm) + e2e-writer |
| 6 | **W3-E2-2** | **NOT a test-enablement.** The preview page was retired (#278). Either DELETE the scaffold (accept the product decision) or hold pending a founder/frontend decision to re-introduce a preview page — see OQ-2. Do NOT invent a selector for a page that doesn't exist. | founder / frontend-coordinator |

### 4.1 CI wiring prerequisite (standing debt → infra)
The E2E suite is **not yet wired into CI** (Playwright browsers + a slot stack; see
`coverage_gaps.md` "CI wiring memo owed → infra"). fake-gcs-server + a seeded DB must be added to
that same (not-yet-existing) E2E CI job. This spec's storage/seed steps assume the E2E CI job is
created; that job's creation is the infra prerequisite, tracked separately.

---

## 5. OPEN QUESTIONS (flagged, NOT blocking)

- **OQ-1 (infra + backend):** Does `fsouza/fake-gcs-server` serve a **v4-signed URL** that the browser
  can actually download for the export-ready xlsx (PQE-E2E-05)? If not, adopt the backend env-flagged
  fake-storage mode returning a backend-served URL (§2.2). Image-precheck (#8) does **not** hit this —
  it only needs upload — so #8 can un-fixme independently of OQ-1.
- **OQ-2 (founder / frontend-coordinator):** The Live Product Preview page was retired (#278) and the
  "Preview" button repointed to `/edit` (#395). Should the `live-preview.spec.ts` scaffold be **deleted**
  (accept the retirement) or **retained** pending a product decision to re-introduce a preview page? The
  backend `GET /products/{id}/preview` is still covered by the backend lane. Recommendation: **delete the
  E2E scaffold** and note the backend-only coverage, unless a preview page is on the roadmap.
- **OQ-3 (data-engineer / founder):** For CAT-E2E-05/06, seed the **full 3,772-leaf tree** in the E2E DB
  (heavy; highest fidelity to the live picker) OR **pin a known-schema'd category** + stub `/suggest`
  (light, hermetic, deterministic)? Recommendation: **pin + stub** for the E2E layer — the full-tree
  resolve is already guarded at the backend layer by CAT-BE-17-GUARD (#474). A paid/heavy seed is not
  justified for two E2E tests.
- **OQ-4 (founder / infra):** fake-gcs-server is free but adds a CI service container + minor runtime to
  the (future) E2E job. Confirm that is acceptable vs. deferring storage-dependent E2E (#5, #8) to a
  nightly slow lane. No spend either way.

---

## 6. Recommended dispatches (after enablement decisions land)

1. **`meesell-e2e-test-writer`** — *"Un-fixme the 2 already-resolved scaffolds: W3-E2-4 (catalog-edit-delete,
   #425 testids) + W3-E2-6 (via SPEC A). Live-verify CAT-E2E-03/07 role selectors; un-fixme if stable,
   else file a testid memo. Flip your board row to IN REVIEW on PR open."* — no external dependency; do this first.
2. **Cross-lead memos (QA-coordinator authors):** infra (fake-gcs-server + E2E CI job + `STORAGE_EMULATOR_HOST`);
   backend (emulator-routing confirm in `adapters/gcs.py`, optional fake-signed-URL); data-engineer (pin-and-seed
   or full-seed decision per OQ-3). Then a second e2e dispatch for CAT-E2E-05/06 + PQE-E2E-05 + image-precheck.
3. **Founder ruling** requested on OQ-2 (delete vs retain live-preview scaffold).
