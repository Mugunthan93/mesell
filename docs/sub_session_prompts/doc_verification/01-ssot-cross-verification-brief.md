# SSOT Cross-Verification — Dispatch Brief

**Agent:** `meesell-backend-coordinator`
**Session name:** `mesell-doc-verification-session-1`
**Task type:** Documentation audit + alignment (no code changes, no infra changes)
**Output:** `docs/MVP_ARCHITECTURE.md` — updated to reflect actual implemented state

---

## PROJECT BOUNDARY

You are working on project "mesell" at `/Users/mugunthansrinivasan/Project/mesell`.
DO NOT read, write, or reference files outside that path.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).
ONLY dispatch `meesell-*` agents. NEVER dispatch `nexus:level-*` or `general-purpose`.

---

## PROMPT

```
You are meesell-backend-coordinator. You are operating on the MeeSell project.

PROJECT BOUNDARY: You are working on project "mesell" at /Users/mugunthansrinivasan/Project/mesell.
DO NOT read, write, or reference files outside /Users/mugunthansrinivasan/Project/mesell/.
DO NOT touch any other project (Aletheia, Prospero, JETK, etc.).
ONLY dispatch meesell-* agents. NEVER dispatch nexus:level-*, general-purpose, or Explore.

---

MISSION: SSOT Cross-Verification — bottom-up documentation alignment.

MVP_ARCHITECTURE.md is the master document that all individual architecture docs branch from.
It was written in 2026-06-04 (pre-implementation). Since then, every individual doc was updated
during construction but NONE of those changes were propagated back to MVP_ARCHITECTURE.md.

Your job is to:
  1. Read all individual architecture documents (ground truth — these are correct)
  2. Read MVP_ARCHITECTURE.md (the stale master)
  3. Produce a divergence report (doc section by section)
  4. Update MVP_ARCHITECTURE.md to align with actual implemented state
  5. Update its status from "Draft" to "LOCKED — last verified 2026-06-10"

This is DOCUMENTATION ONLY. Zero code changes. Zero infrastructure changes. Zero K8s changes.

---

READING LIST — read ALL of these before writing anything:

Layer 0 (implementation ground truth — read first):
  1.  .claude/agent-memory/meesell-backend-coordinator/MEMORY.md
  2.  docs/BACKEND_ARCHITECTURE.md           (8,144 lines — V1 LOCKED, 26 sections)
  3.  docs/DATABASE_ARCHITECTURE.md          (1,669 lines)
  4.  docs/FRONTEND_ARCHITECTURE.md          (598 lines)
  5.  docs/DESIGN_SYSTEM_ARCHITECTURE.md     (394 lines)
  6.  docs/INFRASTRUCTURE_ARCHITECTURE.md    (641 lines)
  7.  docs/DEVOPS_ARCHITECTURE.md            (857 lines — new, 2026-06-10)

Layer 1 (implementation status — understand what is actually live):
  8.  docs/status/STATUS_MASTER.md           (cross-track dashboard)
  9.  docs/status/STATUS_BACKEND.md          (§22 acceptance, D-flags, construction log)
  10. docs/status/STATUS_INFRA.md            (Phase D + E+F completion)
  11. docs/status/STATUS_FRONTEND.md         (Waves 3-5 complete)

Layer 2 (the stale master — read last so you have full context before evaluating):
  12. docs/MVP_ARCHITECTURE.md               (2,799 lines — "Draft", dated 2026-06-04)
  13. docs/MVP_ARCHITECTURE_GAP_ANALYSIS.md  (prior gap analysis, may be outdated)
  14. docs/MVP_ARCHITECTURE_GAP_DATABASE.md  (database-specific gaps)

Draft sections (may need merging into MVP_ARCHITECTURE.md):
  15. docs/draft_architecture_section_6_caching.md
  16. docs/draft_architecture_section_7_search.md
  17. docs/draft_architecture_section_9_ai_ops.md
  18. docs/draft_architecture_section_10_multitenancy.md
  19. docs/draft_architecture_section_11_audit_log.md

---

KNOWN DIVERGENCES (pre-identified — must be resolved):

  STACK CHANGE (critical):
    MVP says:    "Angular 18 PWA (Tailwind + Material, signals + RxJS)"
    Actual:      Angular 21 + PrimeNG 21 + Tailwind 4 + Plus Jakarta Sans
                 (Material was rejected; PrimeNG 21 selected per FRONTEND_ARCHITECTURE.md)
    Update:      All stack references in MVP_ARCHITECTURE.md

  FRONTEND ARCHITECTURE (critical):
    MVP says:    Direct Material/PrimeNG component usage in features
    Actual:      4-layer SOLID architecture — PrimeNG imports ONLY in src/app/ui/ (mee-* wrappers)
                 Feature pages use mee-* components, zero primeng/* imports in features/
    Update:      Section 4 (Frontend Architecture) in MVP_ARCHITECTURE.md

  BACKEND MODULES (important):
    MVP says:    Planned module boundaries
    Actual:      8 domain modules CONSTRUCTED and §22-accepted:
                 iam / customer / category / catalog / image / pricing / dashboard / export
                 28 route paths mounted, 815 tests, 10 CI contracts
    Update:      Section 3 (or equivalent backend section) in MVP_ARCHITECTURE.md

  DATABASE (important):
    MVP says:    Planned schema
    Actual:      13 tables, Alembic head f31c75438e61, 3 GIN trgm indexes,
                 67 field aliases / 3,566 templates / 3,772 categories / 49,259 enum values
    Update:      Database section in MVP_ARCHITECTURE.md

  INFRASTRUCTURE + DEVOPS (important):
    MVP says:    No CI/CD section, generic "deploy to GCP" reference
    Actual:      K3s v1.35.5 on meesell-dev (35.234.223.66, e2-standard-2, asia-south1-a)
                 GitHub Actions + Cloud Build + IAP tunnel deploy
                 docs/DEVOPS_ARCHITECTURE.md now exists (13 sections)
    Update:      Add infrastructure + DevOps summary section to MVP_ARCHITECTURE.md

  CELERY QUEUES (minor):
    MVP says:    May reference queue names from planning
    Actual:      V1 Celery uses image.precheck + export.xlsx queues only
                 (scoped by celery_app.py INCLUDE list, no -Q flag)
    Update:      AI/async section in MVP_ARCHITECTURE.md

  AI INTEGRATION:
    MVP says:    Planned LangFuse + Gemini integration
    Actual:      LangFuse disabled in V1 (pk-lf-disabled-v1), Gemini API LIVE
                 3 AI eval sets PASS (Smart Picker 50fx/100% / Autofill 30fx / Watermark 30fx)
    Update:      AI section in MVP_ARCHITECTURE.md

  DEPLOYMENT STATUS:
    MVP says:    "Draft — awaiting founder review"
    Actual:      V1 BACKEND §22 ACCEPTED (9/9), Phase D DEPLOYED, Phase E+F CI/CD live
    Update:      Status header + deployment section

---

DRAFT SECTIONS — decide for each:
  docs/draft_architecture_section_6_caching.md   → merge into MVP §6 if content adds value
  docs/draft_architecture_section_7_search.md    → merge into MVP §7 if content adds value
  docs/draft_architecture_section_9_ai_ops.md    → merge into MVP §9 if content adds value
  docs/draft_architecture_section_10_multitenancy.md → merge into MVP §10 if new content
  docs/draft_architecture_section_11_audit_log.md    → merge into MVP §11 if new content

  Rule: if a draft section adds content NOT already in MVP_ARCHITECTURE.md, fold it in.
  If it duplicates what's already there, discard it (note the decision in STATUS update).

---

TASK EXECUTION PROTOCOL:

  Phase 1 — Divergence Report (produce before making any edits):
    Create docs/doc_verification/SSOT_DIVERGENCE_REPORT.md listing every divergence found,
    categorised as:
      CRITICAL   — factually wrong or misleading (e.g. wrong stack)
      IMPORTANT  — missing significant implemented detail
      MINOR      — wording/status/date out of date
      RESOLVED   — was a gap, now confirmed aligned

  Phase 2 — Update MVP_ARCHITECTURE.md (section by section):
    Work through each CRITICAL and IMPORTANT divergence in order.
    For each section update:
      - State what the section said (old)
      - State what it now says (new)
      - Mark the section LOCKED with date if content is final
    Do NOT delete historical planning content — add an "As Implemented" block where the
    planned vs actual diverges, so the document preserves both the design intent and reality.

  Phase 3 — Update header:
    Change the status line from:
      "Status: Draft — produced by meesell-data-engineer from full-corpus parse findings."
    To:
      "Status: LOCKED — last verified 2026-06-10. Individual architecture docs are the SSOT
       for each domain; this document is the cross-cutting system map."
    Update the date to 2026-06-10.

  Phase 4 — Cross-reference check:
    For each individual architecture document, verify it cross-references MVP_ARCHITECTURE.md
    correctly (or note where it doesn't). Do NOT edit individual docs — just flag misalignments
    in the divergence report for a future session.

---

OUTPUT FILES:
  1. docs/doc_verification/SSOT_DIVERGENCE_REPORT.md (NEW)
     - All divergences categorised
     - Draft section disposition decisions
     - Cross-doc misalignments flagged for future fix
  2. docs/MVP_ARCHITECTURE.md (UPDATED)
     - All CRITICAL + IMPORTANT divergences resolved
     - Status updated to LOCKED
     - Draft sections merged or discarded
  3. docs/status/STATUS_MASTER.md — append a one-line note:
     "MVP_ARCHITECTURE.md cross-verified and LOCKED 2026-06-10 — N divergences resolved."
     (Do NOT rewrite other rows — append only to the last-update line or add a note section)

---

DO NOT:
  - Change any code file (backend/, frontend/, k8s/, infra/)
  - Change individual architecture docs (BACKEND_ARCHITECTURE.md, FRONTEND_ARCHITECTURE.md,
    INFRASTRUCTURE_ARCHITECTURE.md, DEVOPS_ARCHITECTURE.md, DATABASE_ARCHITECTURE.md,
    DESIGN_SYSTEM_ARCHITECTURE.md) — these are the ground truth
  - Delete historical planning content from MVP_ARCHITECTURE.md — preserve it with an
    "As Implemented" annotation
  - Make any git commits
  - Dispatch non-meesell agents

---

SUCCESS CRITERIA:
  - docs/doc_verification/SSOT_DIVERGENCE_REPORT.md created
  - docs/MVP_ARCHITECTURE.md status = "LOCKED — last verified 2026-06-10"
  - All CRITICAL divergences resolved in MVP_ARCHITECTURE.md
  - All IMPORTANT divergences resolved
  - Stack references updated throughout (Angular 18 + Material → Angular 21 + PrimeNG 21)
  - Draft sections merged or explicitly discarded
  - STATUS_MASTER.md note appended
  - .claude/agent-memory/meesell-backend-coordinator/MEMORY.md updated
```

---

## REFERENCE: Document Inventory

| Document | Lines | Owner | Last updated | Ground truth for |
|----------|-------|-------|-------------|-----------------|
| `docs/MVP_ARCHITECTURE.md` | 2,799 | master session | 2026-06-04 | **MASTER — being updated** |
| `docs/BACKEND_ARCHITECTURE.md` | 8,144 | `meesell-backend-coordinator` | 2026-06-09 | All backend (26 sections LOCKED) |
| `docs/DATABASE_ARCHITECTURE.md` | 1,669 | `meesell-database-builder` | 2026-06-05 | Schema, migrations, seeding |
| `docs/FRONTEND_ARCHITECTURE.md` | 598 | `meesell-frontend-coordinator` | 2026-06-08 | 4-layer SOLID, mee-* pattern |
| `docs/DESIGN_SYSTEM_ARCHITECTURE.md` | 394 | `meesell-angular-ui-styler` | 2026-06-08 | Tokens, Tailwind, PrimeNG theming |
| `docs/INFRASTRUCTURE_ARCHITECTURE.md` | 641 | `meesell-infra-builder` | 2026-06-10 | GCP, K3s, Terraform (49 resources) |
| `docs/DEVOPS_ARCHITECTURE.md` | 857 | `meesell-infra-builder` | 2026-06-10 | CI/CD, GitHub Actions, deploy |
| `docs/draft_architecture_section_*.md` | varies | master session | 2026-06-04 | Planning drafts — may be superseded |

## REFERENCE: Known Stale References in MVP_ARCHITECTURE.md

| Location in MVP | Stale value | Correct value |
|----------------|-------------|---------------|
| System diagram | `Angular 18 PWA (Tailwind + Material)` | `Angular 21 + PrimeNG 21 + Tailwind 4` |
| Section 4 (Frontend) | Direct Material component usage | 4-layer: ui/ → shared/ → features/ → layouts/ |
| Section 3 (Backend) | Planned module list | iam/customer/category/catalog/image/pricing/dashboard/export |
| Section 5 (Database) | Planned schema | 13 tables, head f31c75438e61 |
| No DevOps section | N/A | GitHub Actions + Cloud Build + IAP tunnel (docs/DEVOPS_ARCHITECTURE.md) |
| AI section | LangFuse LIVE | LangFuse DISABLED in V1 (pk-lf-disabled-v1) |
| Celery queues | planning-era queue names | image.precheck + export.xlsx only |
| Status header | "Draft" | "LOCKED — last verified 2026-06-10" |

---

## AUTHORED BY

Master session (mesell-master-session-2), 2026-06-10.
Triggered by: post-Phase E+F documentation hygiene pass — MVP_ARCHITECTURE.md stale since
2026-06-04 pre-implementation. All individual architecture docs are ground truth; this
session propagates them back up to the master.
