# Sub-Session Prompts — MeeSell Backend Construction & Verification

This directory contains **26 self-contained sub-session prompt files** for the MeeSell backend construction phase, plus this README. Every prompt is ready for the founder to copy-paste into a NEW Claude Code session window to spawn that section's dedicated sub-session.

## Overview

Per `docs/SECTION_SUB_SESSION_PROTOCOL.md`, the MeeSell backend is built and audited via 26 dedicated sub-sessions (one per locked section of `docs/BACKEND_ARCHITECTURE.md`):

- **16 CONSTRUCTION prompts** — code-bearing sections (§4, §5, §5A, §6, §6A, §7-§14, §18, §19, §20). Use the §3 protocol template. Each dispatches one or more `meesell-*` specialists.
- **10 VERIFICATION prompts** — pure-documentation / audit sections (§0, §1, §2, §3, §15, §16, §17, §21, §22, §22A). Use the §3A protocol template. Read-only audit; no specialist dispatch.

The master session (the parent Claude window that authored the architecture) reviews each sub-session report, updates `docs/status/STATUS_MASTER.md`, and dispatches the next wave.

## Dispatch Order (10 Waves)

Per `docs/SECTION_SUB_SESSION_PROTOCOL.md` §1.3:

| Wave | Shape | Files | Notes |
|---|---|---|---|
| 1 — Foundation construction | CONSTRUCTION | `wave_1_foundation_construction/01-section-5-shared-construction.md` → `02-section-4-core-construction.md` → `03-section-5A-i18n-construction.md` → `04-section-6-adapters-construction.md` → `05-section-6A-aiops-construction.md` | Sequential. `shared/` first (every other module imports it). |
| 2 — IAM construction | CONSTRUCTION | `wave_2_iam_construction/06-section-7-iam-construction.md` | The unblocker — every authenticated route needs `get_current_user`. |
| 3 — Leaf modules construction (parallel-safe) | CONSTRUCTION | `wave_3_leaf_modules_construction/07-section-8-customer-construction.md`, `08-section-9-category-construction.md` | §8 + §9 can run in parallel. |
| 4 — Spine construction | CONSTRUCTION | `wave_4_spine_construction/09-section-10-catalog-construction.md` | Central spine; calls §8 + §9; called by §11 + §12 + §13 + §14. |
| 5 — Catalog dependents construction (parallel-safe) | CONSTRUCTION | `wave_5_catalog_dependents_construction/10-section-11-image-construction.md`, `11-section-12-pricing-construction.md`, `12-section-13-dashboard-construction.md` | §11 + §12 + §13 can run in parallel. |
| 6 — Export construction | CONSTRUCTION | `wave_6_export_construction/13-section-14-export-construction.md` | Most cross-module module; needs §8 + §9 + §10 + §11 all done. |
| 7 — Wiring + tests + deployment construction | CONSTRUCTION | `wave_7_wiring_construction/14-section-18-celery-construction.md` → `15-section-19-tests-construction.md` → `16-section-20-deployment-construction.md` | Sequential after all modules built. |
| 8 — Foundation + module audits (parallel-safe) | VERIFICATION | `wave_8_audits_parallel/17-section-0-premises-verification.md`, `18-section-1-topology-verification.md`, `19-section-2-modules-verification.md`, `20-section-3-files-verification.md`, `21-section-17-endpoints-verification.md` | All 5 read-only audits can run in parallel. |
| 9 — Cross-cutting + integration audits (parallel-safe) | VERIFICATION | `wave_9_audits_parallel/22-section-15-crosscutting-verification.md`, `23-section-16-rules-verification.md`, `24-section-21-extraction-verification.md`, `25-section-22A-risks-verification.md` | All 4 read-only audits can run in parallel. |
| 10 — Final acceptance sign-off | VERIFICATION | `wave_10_final_signoff/26-section-22-acceptance-verification.md` | LAST. Runs against the completed codebase + all 9 prior wave reports; produces V1 GO/NO-GO. |

## Parallel-Safe Groupings

Per protocol §6:

- **Wave 3:** `07-section-8-customer-construction.md` + `08-section-9-category-construction.md` (leaf modules; no cross-module dependency between them).
- **Wave 5:** `10-section-11-image-construction.md` + `11-section-12-pricing-construction.md` + `12-section-13-dashboard-construction.md` (all call catalog; can run in parallel after catalog locks).
- **Wave 8:** `17-section-0-premises-verification.md` + `18-section-1-topology-verification.md` + `19-section-2-modules-verification.md` + `20-section-3-files-verification.md` + `21-section-17-endpoints-verification.md` (all read-only).
- **Wave 9:** `22-section-15-crosscutting-verification.md` + `23-section-16-rules-verification.md` + `24-section-21-extraction-verification.md` + `25-section-22A-risks-verification.md` (all read-only).

Founder coordinates parallel starts. The master session accumulates completion reports.

## How to Use a Prompt File

1. Open a **NEW Claude Code session** (separate from the master session) by launching a new `claude` window or tab.
2. Verify the project root: `cd /Users/mugunthansrinivasan/Project/mesell/`
3. Open the relevant prompt file (e.g. `wave_1_foundation_construction/01-section-5-shared-construction.md`).
4. Copy **the entire block between the `⬇ START SUB-SESSION PROMPT ⬇` and `⬆ END SUB-SESSION PROMPT ⬆` markers**.
5. Paste it as your **first message** in the new Claude Code session.
6. The sub-session will:
   - Rename itself via `/rename`.
   - Read the required context (architecture sections, memory, status).
   - Confirm the on-disk baseline.
   - Report "Ready to begin §X" or "Audit context loaded. Ready to begin §X verification."
   - **WAIT** for the master session's "go" before dispatching specialists or running audit queries.
7. Report sub-session reports back to the master session for review.

## After Dispatch (Master Session)

Per protocol §5.1 (construction) and §5.1A (verification):

- **PASS:** Master runs universal acceptance checks, updates `STATUS_MASTER.md`, saves memory entry, determines next dispatch per §1.3.
- **PARTIAL / FAIL:** Master reviews findings, dispatches remediation, then re-dispatches the verification sub-session.
- **ESCALATION:** Master decides — bug in implementation → re-attempt; bug in locked contract → master amends the LOCKED section with `**AMENDMENT YYYY-MM-DD**` block; cross-section blocker → master coordinates the blocking section first.

## Re-Attempt Protocol

If a sub-session fails its acceptance criteria or audit verdict is FAIL:

- The master decides remediation (per §5.1B / §5.2).
- A re-attempt prompt file is generated at the same directory with the filename pattern `XX-section-Y-{slug}-{construction|verification}-attempt-2.md` (and `-3.md`, `-4.md` etc. for further attempts).
- The re-attempt prompt fills `{{ATTEMPT_NUMBER}}` with `2` (or higher) and adds a **Prior attempt notes** block at the top of the paste block summarizing what failed and what to fix.
- The re-attempt prompt is generated FRESH by the master session — not by hand-editing the prior attempt file.

## Index of Files

```
docs/sub_session_prompts/
├── README.md                                                              (this file)
├── wave_1_foundation_construction/
│   ├── 01-section-5-shared-construction.md
│   ├── 02-section-4-core-construction.md
│   ├── 03-section-5A-i18n-construction.md
│   ├── 04-section-6-adapters-construction.md
│   └── 05-section-6A-aiops-construction.md
├── wave_2_iam_construction/
│   └── 06-section-7-iam-construction.md
├── wave_3_leaf_modules_construction/
│   ├── 07-section-8-customer-construction.md
│   └── 08-section-9-category-construction.md
├── wave_4_spine_construction/
│   └── 09-section-10-catalog-construction.md
├── wave_5_catalog_dependents_construction/
│   ├── 10-section-11-image-construction.md
│   ├── 11-section-12-pricing-construction.md
│   └── 12-section-13-dashboard-construction.md
├── wave_6_export_construction/
│   └── 13-section-14-export-construction.md
├── wave_7_wiring_construction/
│   ├── 14-section-18-celery-construction.md
│   ├── 15-section-19-tests-construction.md
│   └── 16-section-20-deployment-construction.md
├── wave_8_audits_parallel/
│   ├── 17-section-0-premises-verification.md
│   ├── 18-section-1-topology-verification.md
│   ├── 19-section-2-modules-verification.md
│   ├── 20-section-3-files-verification.md
│   └── 21-section-17-endpoints-verification.md
├── wave_9_audits_parallel/
│   ├── 22-section-15-crosscutting-verification.md
│   ├── 23-section-16-rules-verification.md
│   ├── 24-section-21-extraction-verification.md
│   └── 25-section-22A-risks-verification.md
└── wave_10_final_signoff/
    └── 26-section-22-acceptance-verification.md
```

Total: 26 prompt files + 1 README = 27 files.

**Authority:** `docs/SECTION_SUB_SESSION_PROTOCOL.md` (master session). Sub-session prompts may NOT amend the protocol — only master amends.
