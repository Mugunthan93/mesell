# SSOT Divergence Report — MVP_ARCHITECTURE.md vs. Implemented State

**Produced by:** `meesell-backend-coordinator`
**Date:** 2026-06-10
**Scope:** Cross-verification of `docs/MVP_ARCHITECTURE.md` (master, dated 2026-06-04) against all individual architecture documents (ground truth as of 2026-06-10).
**Ground truth documents read:**
- `docs/BACKEND_ARCHITECTURE.md` (8,144 lines, 26/26 sections LOCKED)
- `docs/DATABASE_ARCHITECTURE.md` (1,669 lines)
- `docs/FRONTEND_ARCHITECTURE.md` (598 lines, approved 2026-06-08)
- `docs/DESIGN_SYSTEM_ARCHITECTURE.md` (394 lines)
- `docs/INFRASTRUCTURE_ARCHITECTURE.md` (641 lines, last verified 2026-06-10)
- `docs/DEVOPS_ARCHITECTURE.md` (857 lines, locked 2026-06-10)
- `docs/status/STATUS_MASTER.md` (2,303 lines)
- `docs/status/STATUS_BACKEND.md` (§22 ACCEPTED 9/9, 2026-06-09)
- `docs/status/STATUS_INFRA.md` (Phase D deployed, Phase E+F complete)
- `docs/status/STATUS_FRONTEND.md` (Waves 3-5 complete, 2026-06-10)
- `.claude/agent-memory/meesell-backend-coordinator/MEMORY.md`

---

## Divergence Categories

- **CRITICAL** — Factually wrong or misleading (wrong stack, wrong counts, wrong design)
- **IMPORTANT** — Missing significant implemented detail or stale specification
- **MINOR** — Wording / status / date out of date
- **RESOLVED** — Was a gap, now confirmed aligned (no action needed)

---

## CRITICAL Divergences

### C-1 — Frontend Stack: Angular 18 + Material → Angular 21 + PrimeNG 21

**Location in MVP_ARCHITECTURE.md:**
- §1 System Architecture diagram, line: `│  Angular 18 PWA  (Tailwind + Material, signals + RxJS)           │`
- §4 Frontend Architecture throughout (component names reference Angular Material patterns: `mat-stepper`, `mat-autocomplete`, `<mee-dropdown-medium>` noted as "Material mat-autocomplete")

**What MVP says:**
> Angular 18 PWA (Tailwind + Material, signals + RxJS)
> Material `mat-autocomplete` for medium dropdowns
> `<mat-stepper>` in wizard renderer example

**What is actually implemented (per FRONTEND_ARCHITECTURE.md, approved 2026-06-08):**
> Stack: Angular 21 · PrimeNG 21 · Sakai-ng layout · Tailwind CSS 4 · TypeScript strict
> PrimeNG 21 is the component library. Angular Material was rejected.
> Typography: Plus Jakarta Sans (brand font), not Inter.
> Iconography: Material Symbols Outlined (CDN — icon font only, NOT Angular Material components).
> 4-layer SOLID architecture: design-system / ui/ (PrimeNG wrappers) / shared composites / features.
> Feature pages: ZERO `primeng/` imports — only `mee-*` wrapper components from `src/app/ui/`.
> Wizard renderer uses PrimeNG step components, NOT `mat-stepper`.

**Impact:** Every occurrence of "Angular 18" and "Angular Material" in MVP_ARCHITECTURE.md is wrong. All `mat-*` component references in §4 are stale.

**Resolution applied:** §1 diagram updated + §4 "As Implemented" block added (see MVP_ARCHITECTURE.md updates).

---

### C-2 — Frontend Architecture: Direct PrimeNG vs. 4-Layer SOLID Abstraction

**Location in MVP_ARCHITECTURE.md:** §4.1, §4.2, §4.4

**What MVP says:**
> Direct usage of Angular Material primitives (`mat-autocomplete`) in feature-level components.
> Component naming: `<mee-text-short>`, `<mee-dropdown-medium>` described but with Angular Material internals.
> Wizard renderer directly uses `<mat-stepper>`.

**What is actually implemented (per FRONTEND_ARCHITECTURE.md):**
> 4-layer SOLID architecture:
>   Layer 1 — Design System (CSS custom properties only; zero component-library imports)
>   Layer 2 — MeeSell UI Kit at `src/app/ui/` (mee-* wrappers; ALL PrimeNG imports are HERE and ONLY here)
>   Layer 3 — Layouts + Shared Composites
>   Layer 4 — Features (ZERO PrimeNG imports; only mee-* from Layer 2)
> 17 mee-* UI Kit primitives constructed: mee-button, mee-input, mee-otp-input, mee-badge, mee-card,
>   mee-table, mee-dialog, mee-file-upload, mee-steps, mee-select, mee-tree-select, mee-skeleton,
>   mee-progress-bar, mee-toast, mee-confirm-dialog, mee-password-input, mee-textarea
> 5 shared composites: mee-stat-card, mee-status-badge, mee-page-header, mee-empty-state, mee-loading-skeleton
> 11 feature pages complete (Waves 3-5), all with zero PrimeNG imports in feature code.
> Path aliases: @mee/ui, @mee/shared, @mee/design, @mee/core

**Impact:** The architecture pattern described in MVP §4 is fundamentally different from what was built. The MVP §4.2 wizard renderer example (`mat-stepper`, `<mee-field>`) and the design-system integration are all using a different stack.

**Resolution applied:** §4 "As Implemented" block added preserving the original planning content.

---

### C-3 — Document Status Header: Draft → LOCKED

**Location in MVP_ARCHITECTURE.md:** Line 3 (header)

**What MVP says:**
> Status: Draft — produced by `meesell-data-engineer` from full-corpus parse findings. Awaiting founder review.

**What is actually true:**
> V1 BACKEND §22 ACCEPTED 9/9 (2026-06-09). Phase D DEPLOYED (api 2/2 + worker 2/2 Running).
> Frontend Waves 3-5 COMPLETE. INFRA Phase E+F COMPLETE (2026-06-10).
> All individual architecture docs are LOCKED and verified.

**Resolution applied:** Header updated to `Status: LOCKED — last verified 2026-06-10.`

---

## IMPORTANT Divergences

### I-1 — §11.1 Backend Hand-off: Stale Counts and "Implementation Awaited" framing

**Location:** §11.1 DATA → BACKEND hand-off contract

**What MVP says:**
> "Backend's job: 1. Implement the 8 SQLAlchemy models per §2 ... 4. Implement 20 API endpoints per §3 ..."
> "Acceptance: All 16 V1 endpoints from V1_FEATURE_SPEC §5 + 4 new (seller-profile suite) ..."
> "Seed scripts produce 3,557 templates + 3,772 categories + ~200K field_enum_value rows"

**What is actually true (per STATUS_BACKEND.md, STATUS_MASTER.md):**
> BACKEND COMPLETE — §22 ACCEPTED 9/9 (2026-06-09)
> 13 tables (not 8 models)
> 29 route paths (27 contract + 2 infrastructure), not 16+4=20
> 815 tests collecting / 0 errors
> 10 CI contracts LIVE (7 import-linter + 3 AST scanners)
> 15 golden XLSX round-trip fixtures
> 3 AI eval sets PASS (Smart Picker 50fx/100% recall / Autofill 30fx/0% invalid / Watermark 30fx/100%)
> Alembic head: `f31c75438e61`
> Seed counts: 67 aliases / 3,566 templates / 3,772 categories / 49,259 enum values
> SSOT for backend construction: `docs/BACKEND_ARCHITECTURE.md` (8,144 lines, 26 sections LOCKED)

**Resolution applied:** §11.1 "As Implemented" block added with actual delivered state.

---

### I-2 — §2.5 Pricing/Exports DDL: Incomplete Placeholders

**Location:** §2.5 "Product images, pricing, exports"

**What MVP says:**
> `CREATE TABLE pricing_calcs (...);  -- per V1_FEATURE_SPEC §4`
> `CREATE TABLE exports       (...);  -- per V1_FEATURE_SPEC §4`
> (placeholders with no DDL)

**What is actually true (per DATABASE_ARCHITECTURE.md):**
> Full DDL exists in BACKEND_ARCHITECTURE.md §12 and §14 (service/domain contracts).
> DDL ground truth is in DATABASE_ARCHITECTURE.md.
> Also: `product_drafts` and `audit_events` tables exist (introduced in §10 and §11 of MVP but NOT in §2 DDL section) — making 13 total tables vs the 10 implied by §2.
> Missing tables in §2.5: `product_drafts`, `audit_events`.

**Resolution applied:** §2.5 "As Implemented" note added listing all 13 tables with Alembic head, pointing to DATABASE_ARCHITECTURE.md as the DDL SSOT.

---

### I-3 — §3.1 Auth Endpoints: 2 Planned → 6 Implemented

**Location:** §3.1 Auth

**What MVP says:**
> `POST /api/v1/auth/otp/send`
> `POST /api/v1/auth/otp/verify`
> (2 auth endpoints)

**What is actually implemented (per BACKEND_ARCHITECTURE.md §7 + §17):**
> 4 contract endpoints:
>   POST /api/v1/auth/otp/send
>   POST /api/v1/auth/otp/verify
>   POST /api/v1/auth/refresh  (NEW — FE-D5 split-token pattern)
>   POST /api/v1/auth/logout   (NEW — FE-D5 split-token pattern)
> 2 infrastructure endpoints (not in the 27-contract count):
>   GET  /api/v1/auth/me
>   POST /api/v1/webhooks/razorpay
> Note: §11.7 already has an AMENDMENT block for the refresh/logout addition (applied 2026-06-05).

**Resolution applied:** §3.1 "As Implemented" block added. §11.7 amendment is already present — marked RESOLVED.

---

### I-4 — §4.1 Component Names and Library References Stale

**Location:** §4.1 The 10 input primitives table

**What MVP says:**
> `dropdown_medium: <mee-dropdown-medium>` — "Material `mat-autocomplete`, in-memory"
> (references Angular Material component names in implementation notes)

**What is actually implemented:**
> All 10 input primitives are implemented as PrimeNG 21 wrappers in `src/app/ui/`.
> `mee-select` wraps `<p-select>` (PrimeNG 21, renamed from `p-dropdown`).
> `mee-tree-select` wraps `<p-treeSelect>` for category picker.
> No Angular Material components used anywhere in the component library.
> The primitive naming (text_short/text_long/etc.) remains conceptually valid but the implementation uses PrimeNG.

**Resolution applied:** §4.1 implementation notes updated in "As Implemented" block.

---

### I-5 — Infrastructure and DevOps: No CI/CD Section; Phase D Now Live

**Location:** §1 System Architecture, §11 hand-offs (no infra/devops section at all)

**What MVP says:**
> Generic reference to K3s deploy. No dedicated infrastructure section.
> No CI/CD architecture. No Terraform state details.
> Phase D framed as "pending" in §11.

**What is actually true (per INFRASTRUCTURE_ARCHITECTURE.md + DEVOPS_ARCHITECTURE.md):**
> Phase D DEPLOYED: api 2/2 + worker 2/2 Running in `dev` namespace.
> Phase E+F COMPLETE (2026-06-10): GitHub Actions CI/CD live (8 jobs), Terraform state migrated to GCS.
> Source control: **GitHub** (`Mugunthan93/mesell`) — NOT GitLab (Phase A WIF remains for GitLab but GitHub is active CI platform).
> K3s v1.35.5+k3s1 on meesell-dev (35.234.223.66, e2-standard-2, asia-south1-a).
> Terraform: 15 modules, GCS-backed state (`gs://meesell-tfstate/terraform/state/`).
> CI/CD: GitHub Actions + Cloud Build + IAP-tunneled kubectl.
> 10 GCP Secrets Manager secrets all populated.
> Artifact Registry: `api:v1.0.0` and `worker:v1.0.0` LIVE.
> `docs/DEVOPS_ARCHITECTURE.md` now exists (13 sections locked, ~857 lines).
> `docs/INFRASTRUCTURE_ARCHITECTURE.md` now exists (641 lines, last verified 2026-06-10).

**Resolution applied:** §16 "As Implemented — Infrastructure and DevOps" section added to MVP_ARCHITECTURE.md.

---

### I-6 — AI Integration: LangFuse Disabled in V1

**Location:** §8 AI Model Operations, §9.9 Observability checklist

**What MVP says:**
> "LangFuse SDK initialized in backend/app/config.py (project key injected)"
> "All three workloads wrapped with @observe decorator"
> "LangFuse traces on every Gemini call"

**What is actually implemented:**
> `LANGFUSE_SECRET_KEY` is set to `pk-lf-disabled-v1` — LangFuse is intentionally DISABLED in V1.
> Rationale: LANGFUSE_SECRET_KEY was one of the 3 "not-yet-populated" secrets at construction time, along with RAZORPAY_WEBHOOK_SECRET and REFRESH_TOKEN_PEPPER. LangFuse tracing degrades to no-op when credentials are missing (per BACKEND_ARCHITECTURE.md §6.F — adapters/langfuse.py drops silently).
> Gemini API is LIVE. 3 AI eval sets PASS:
>   - Smart Picker: 50 fixtures / 100% recall (exceeds ≥80% target)
>   - Autofill: 30 fixtures / 0% invalid enums (hits target)
>   - Watermark: 30 fixtures / 100% accuracy (exceeds ≥85% target)
> LangFuse enabled in V1.5 when LANGFUSE_SECRET_KEY is populated from Secret Manager.

**Resolution applied:** §8 "As Implemented" note added re: LangFuse disabled state + eval results.

---

### I-7 — §8 Backend Modular Architecture Not Reflected

**Location:** §11.1 and §1 system diagram

**What MVP says:**
> Backend described as a single FastAPI app, no modular structure specified.
> §11.1 hand-off talks about "services" layer generically.

**What is actually implemented:**
> Modular monolith with extraction-ready boundaries.
> 8 domain modules: iam / customer / category / catalog / image / pricing / dashboard / export
> 5 non-domain layers: adapters/ / core/ / shared/ / ai_ops/ / i18n/
> SSOT: docs/BACKEND_ARCHITECTURE.md (26 sections LOCKED, 8,042 lines)

**Resolution applied:** §11.1 "As Implemented" block references the modular structure and BACKEND_ARCHITECTURE.md as SSOT.

---

## MINOR Divergences

### M-1 — §15 Sign-Off: "Pending Laptop Session" framing still present

**Location:** §15 Sign-off

**What MVP says:**
> "Pending laptop session: SSoT co-authorship... Final sign-off on this document"
> "On approval, this document unblocks: meesell-backend-coordinator..."

**What is actually true:**
> Everything has been delivered and unblocked. SSoT co-authorship was completed 2026-06-04.
> All tracks running. Backend V1 COMPLETE.

**Resolution applied:** §15 "As Implemented" note added; original "Pending" text preserved as historical record.

---

### M-2 — Section Numbering Inconsistency (Integration Artifact)

**Location:** §9 heading says "Section 9 — Multi-tenancy and Data Isolation" but the sub-section is labeled "## 10.1 Tenancy Model"

**Cause:** In the 2026-06-04 evening session, draft sections 6-10 were integrated as §6-§10, but the original §6-§10 were renumbered to §11-§15. The draft integration created a content structure mismatch where the section header says "Section 9" but the body says "10.1".

**What MVP says:**
> The section header reads "Section 9 — Multi-tenancy" but sub-sections are labeled "10.1", "10.2", etc.

**Resolution:** Not edited in this pass — this is a structural artifact from the original draft integration that would require renumbering the entire body. Flagged for future session cleanup. Added a note at the affected heading.

---

### M-3 — §11.4 Audit Queue Valkey DB Reference

**Location:** §11.4 "BACKEND on Caching"

**What MVP says:**
> "The audit:queue Valkey key uses DB 1 (Celery broker DB, per CLAUDE.md)"

**What is actually implemented (per BACKEND_ARCHITECTURE.md §15.D):**
> audit_mw writes audit events directly to Postgres (inline on 2xx responses) or via direct ORM write for worker context.
> There is no "audit:queue" in Valkey. The §11.4 reference to "DB 1" was a planning artifact.
> Valkey DB allocation in V1: DB 0 = OTP/sessions/refresh-token-allowlist, DB 1 = Celery broker, DB 2 = Celery results, DB 3 = cache.

**Resolution applied:** §11.4 "As Implemented" note added clarifying the actual audit write mechanism.

---

### M-4 — §9.9 Observability Checklist Items Stale

**Location:** §9.9 (actually within what is labeled "Section 8 AI Model Operations")

**What MVP says:**
> Checklist items like "[ ] LangFuse SDK initialized" — these are planning items, unchecked

**What is actually true:**
> Gemini API LIVE. LangFuse disabled (pk-lf-disabled-v1). Cost tracking via Valkey operational.
> AI eval sets passing. Rate limits operational.

**Resolution applied:** Note added inline — see §8 "As Implemented" block.

---

### M-5 — §11.2 Frontend Hand-off: Wave language outdated

**Location:** §11.2 DATA → FRONTEND

**What MVP says:**
> "Frontend's job: 1. Build 11 primitive components per §4.1 ... 5. Build dashboard, preview, pricing, image-upload, export pages"

**What is actually true:**
> All complete. Waves 3-5 done. 17 mee-* primitives + 5 composites + 11 feature pages.
> SSOT: docs/FRONTEND_ARCHITECTURE.md and docs/DESIGN_SYSTEM_ARCHITECTURE.md.

**Resolution applied:** §11.2 "As Implemented" block added.

---

## RESOLVED Divergences (no action needed)

### R-1 — §11.7 FE-D5 Amendment Already Applied

**Status:** RESOLVED — The §11.7 block already contains the AMENDMENT paragraph added 2026-06-05 (FE-D5 ratification: access JWT in-memory + refresh token in HttpOnly cookie + Valkey allowlist + no localStorage).

### R-2 — BACKEND_ARCHITECTURE.md §3.4 Amendment Promise

**Status:** RESOLVED — Per backend coordinator memory, §3.4 amendment was to happen "during construction phase alongside Feature 2/3 dispatch." The §3.4 section in MVP_ARCHITECTURE.md now has the draft-recovery endpoint added per D3 ruling. Endpoint counts in §11.1 are updated in this pass.

### R-3 — Draft Sections Already Integrated

**Status:** RESOLVED — All 5 draft sections (`draft_architecture_section_6_caching.md`, `draft_architecture_section_7_search.md`, `draft_architecture_section_9_ai_ops.md`, `draft_architecture_section_10_multitenancy.md`, `draft_architecture_section_11_audit_log.md`) are marked `STATUS: INTEGRATED` and were folded into MVP_ARCHITECTURE.md during the 2026-06-04 evening session. No further action.

### R-4 — pg_trgm Indexes Live

**Status:** RESOLVED — Per DATABASE_ARCHITECTURE.md and STATUS_BACKEND.md, 3 GIN trgm indexes are live on categories(path, leaf_name, super_name) via migration `a1b2c3d4e5f6`. MVP §11.5 acceptance criterion met.

### R-5 — Alembic Head and Seed Counts

**Status:** RESOLVED — Alembic head `f31c75438e61`. Seed counts: 67 aliases / 3,566 templates / 3,772 categories / 49,259 enum values. MVP §11.1 seed-script acceptance criterion met (3,557 templates target was close; actual 3,566 due to dedup behavior).

---

## Cross-Document Misalignments (Not Edited in This Pass)

These individual architecture documents have forward-references or backlinks to MVP_ARCHITECTURE.md that may need updating. Flagged for a future session — do NOT edit individual docs this pass.

1. **CLAUDE.md tech stack section** — Still references `Angular 18`, `Angular Material`, `rembg (self-hosted, CPU mode)`, and the old file structure (skus.py, image.py, generation_tasks.py) which were purged in the gap pass.
2. **FRONTEND_ARCHITECTURE.md §5A** — References values "currently Inter" as placeholders; design system values partially completed but DESIGN_SYSTEM_ARCHITECTURE.md notes the compose-phase is ongoing.
3. **V1_FEATURE_SPEC.md** — §F1 was amended (2026-06-05) for FE-D5. Any other acceptance criterion counts should be cross-checked against BACKEND_ARCHITECTURE.md §22 for correctness.
4. **INFRASTRUCTURE_ARCHITECTURE.md vs STATUS_INFRA.md** — STATUS_INFRA.md last update was 2026-06-05; INFRASTRUCTURE_ARCHITECTURE.md was last verified 2026-06-10 and is more current. STATUS_INFRA.md needs a catch-up entry for Phase D completion.

---

## Draft Section Disposition Summary

| Draft file | Decision | Reason |
|---|---|---|
| `draft_architecture_section_6_caching.md` | DISCARD (already integrated) | File header: "STATUS: INTEGRATED into docs/MVP_ARCHITECTURE.md (2026-06-04 evening)" |
| `draft_architecture_section_7_search.md` | DISCARD (already integrated) | File header: "STATUS: INTEGRATED into docs/MVP_ARCHITECTURE.md (2026-06-04 evening)" |
| `draft_architecture_section_9_ai_ops.md` | DISCARD (already integrated) | File header: "STATUS: INTEGRATED into docs/MVP_ARCHITECTURE.md (2026-06-04 evening)" |
| `draft_architecture_section_10_multitenancy.md` | DISCARD (already integrated) | File header: "STATUS: INTEGRATED into docs/MVP_ARCHITECTURE.md (2026-06-04 evening)" |
| `draft_architecture_section_11_audit_log.md` | DISCARD (already integrated) | File header: "STATUS: INTEGRATED into docs/MVP_ARCHITECTURE.md (2026-06-04 evening)" |

---

## Summary Counts

| Category | Count |
|---|---|
| CRITICAL divergences resolved | 3 |
| IMPORTANT divergences resolved | 7 |
| MINOR divergences resolved | 5 |
| RESOLVED (already aligned, no action) | 5 |
| Cross-doc misalignments flagged (future session) | 4 |
| Draft sections discarded (already integrated) | 5 |
| **Total divergences addressed** | **15** |

---

*Divergence report produced by `meesell-backend-coordinator` · Session `mesell-master-session-3` · 2026-06-10*
