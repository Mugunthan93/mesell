# Feature Planning Master Tracker

**Owner:** Master Director session
**Purpose:** Single source of truth for the state of all 9 V1 feature planning sessions
**Last updated:** 2026-06-10 (planning lockdown — canonical v2 amendments merged)
**This file is updated by sub-sessions only. The master Director session reads it.**
**Lockdown pass 2026-06-10:** all 9 FEATURE_PLAN.md files were amended to canonical pattern v2 (11 h2 sections in locked order) and merged to `develop` via amendment PRs #14–#22. All 9 `_status/{slug}.yaml` files and every row below are now `LOCKED`. The planning stage is complete; the coding stage is unblocked. The canonical pattern itself is at v2.1 (fence-aware audit command, PR #12).

---

## Planning state — 9 V1 features

| # | Feature              | Session                                          | Status       | FEATURE_PLAN.md path                                | Last updated | Notes |
|---|----------------------|--------------------------------------------------|--------------|-----------------------------------------------------|--------------|-------|
| 1 | auth-otp             | mesell-auth-otp-amendment-session-1              | LOCKED       | docs/plans/features/auth-otp/FEATURE_PLAN.md        | 2026-06-10   | canonical v2 amendment merged via PR #21 (base plan PR #3) |
| 2 | smart-picker         | mesell-smart-picker-amendment-session-1          | LOCKED       | docs/plans/features/smart-picker/FEATURE_PLAN.md    | 2026-06-10   | canonical v2 amendment merged via PR #17 (base plan PR #6) |
| 3 | catalog-form         | mesell-catalog-form-amendment-session-1          | LOCKED       | docs/plans/features/catalog-form/FEATURE_PLAN.md    | 2026-06-10   | canonical v2 amendment merged via PR #15 (base plan PR #7) |
| 4 | ai-autofill          | mesell-ai-autofill-amendment-session-1           | LOCKED       | docs/plans/features/ai-autofill/FEATURE_PLAN.md     | 2026-06-10   | canonical v2 amendment merged via PR #18 (base plan PR #4) |
| 5 | image-precheck       | mesell-image-precheck-amendment-session-1        | LOCKED       | docs/plans/features/image-precheck/FEATURE_PLAN.md  | 2026-06-10   | canonical v2 amendment merged via PR #14 (base plan PR #8) |
| 6 | live-preview         | mesell-live-preview-amendment-session-1          | LOCKED       | docs/plans/features/live-preview/FEATURE_PLAN.md    | 2026-06-10   | canonical v2 amendment merged via PR #16 (base plan PR #10) |
| 7 | price-calculator     | mesell-price-calculator-amendment-session-1      | LOCKED       | docs/plans/features/price-calculator/FEATURE_PLAN.md | 2026-06-10  | canonical v2 amendment merged via PR #20 (base plan PR #5) |
| 8 | tracking-dashboard   | mesell-tracking-dashboard-amendment-session-1    | LOCKED       | docs/plans/features/tracking-dashboard/FEATURE_PLAN.md | 2026-06-10 | canonical v2 amendment merged via PR #19 (base plan PR #11) |
| 9 | xlsx-export          | mesell-xlsx-export-amendment-session-1           | LOCKED       | docs/plans/features/xlsx-export/FEATURE_PLAN.md     | 2026-06-10   | canonical v2 amendment merged via PR #22 (base plan PR #9) |

## Status vocabulary (canonical — 5 values)

| Status        | Meaning |
|---------------|---------|
| `NOT STARTED` | No planning session has been opened yet |
| `IN PROGRESS` | Sub-session is actively planning the feature |
| `PLAN READY`  | FEATURE_PLAN.md exists and is complete; awaiting founder review |
| `IN REVIEW`   | PR open with FEATURE_PLAN.md; founder is reviewing |
| `LOCKED`      | Founder has merged FEATURE_PLAN.md to develop; feature is ready for coding-stage dispatch |

## Protocol — how a sub-session updates this file

A sub-session for feature `{feature-slug}` MUST:

### At session start (after reading master plan + V1 spec)
1. Read this file in full
2. Update your row's `Status` from `NOT STARTED` → `IN PROGRESS`
3. Update your row's `Last updated` to today's date
4. Append a one-line entry under "## Recent updates log" with the session start

### At session close (after FEATURE_PLAN.md is authored AND committed)
1. Update your row's `Status` from `IN PROGRESS` → `PLAN READY` (or `IN REVIEW` once PR is opened)
2. Update your row's `Last updated` to today's date
3. Update your row's `Notes` with: PR number / outstanding founder decisions / blockers (one line)
4. Append a one-line entry under "## Recent updates log" with the session close + PR URL

### Cross-session rules
- Only ONE sub-session updates a given row at a time (no concurrent planning of the same feature)
- Sub-sessions DO NOT update other features' rows
- Sub-sessions DO NOT update the canonical `Status vocabulary` table or `Protocol` section — those are governance
- If the founder requests changes in PR review, the sub-session re-opens, transitions back to `IN PROGRESS`, then back to `PLAN READY` when done

## Recent updates log (newest first)

| Date | Feature | Event | Reference |
|------|---------|-------|-----------|
| 2026-06-10 | (governance) | Planning stage LOCKED — all 9 _status yamls + tracker rows flipped to LOCKED | mesell-repo-management-session-2 (planning-lockdown PR) |
| 2026-06-10 | (governance) | Canonical v2 amendment PRs #14–#22 merged to develop (one per feature) | mesell-repo-management-session-2 |
| 2026-06-10 | (governance) | Canonical pattern v2.1 — fence-aware audit command merged via PR #12 | mesell-repo-management-session-2 |
| 2026-06-10 | (governance) | All 9 feature blueprints MERGED to develop; planning phase complete | mesell-repo-management-session-1 |
| 2026-06-10 | (governance) | All 9 features moved to IN REVIEW; live-preview + tracking-dashboard shipped via worktree pattern | mesell-repo-management-session-1 |
| 2026-06-10 | tracking-dashboard | IN REVIEW — PR #11 open: https://github.com/Mugunthan93/mesell/pull/11 | mesell-repo-management-session-1 (Step 10 reconciliation, via worktree) |
| 2026-06-10 | live-preview | IN REVIEW — PR #10 open: https://github.com/Mugunthan93/mesell/pull/10 | mesell-repo-management-session-1 (Step 10 reconciliation, via worktree) |
| 2026-06-10 | live-preview | FEATURE_PLAN.md complete — awaiting master consolidation | (no PR yet) |
| 2026-06-10 | tracking-dashboard | FEATURE_PLAN.md complete — awaiting master consolidation | (no PR yet) |
| 2026-06-10 | auth-otp | FEATURE_PLAN.md complete — awaiting master consolidation | (no PR yet) |
| 2026-06-10 | catalog-form | FEATURE_PLAN.md complete — awaiting master consolidation | (no PR yet) |
| 2026-06-10 | smart-picker | FEATURE_PLAN.md complete — awaiting master consolidation | (no PR yet) |
| 2026-06-10 | auth-otp | IN REVIEW — PR #3 open: https://github.com/Mugunthan93/mesell/pull/3 | mesell-auth-otp-planning-session-1 |
| 2026-06-10 | auth-otp | PLAN READY — FEATURE_PLAN.md authored; PR opening on feature/auth-otp/planning | mesell-auth-otp-planning-session-1 |
| 2026-06-10 | auth-otp | IN PROGRESS — session opened, mandatory reads complete, D1/D2/D3 locked | mesell-auth-otp-planning-session-1 |
| 2026-06-10 | (governance) | Master tracker initialised | mesell-repo-management-session-1 |

## Cross-feature dependency map (informational — surfaces planning sequencing)

| Feature | Depends on (must plan first) | Why |
|---------|------------------------------|-----|
| smart-picker | auth-otp | Needs authenticated seller context |
| catalog-form | auth-otp, smart-picker | Catalog creation flow starts at picker |
| ai-autofill | catalog-form | Autofill UI lives inside catalog-form |
| image-precheck | catalog-form | Image upload happens in catalog flow |
| live-preview | catalog-form | Preview component reads the form draft |
| price-calculator | catalog-form | Price calc needs product in hand |
| tracking-dashboard | auth-otp, catalog-form | Listing requires products to exist |
| xlsx-export | catalog-form, tracking-dashboard | Export pulls from dashboard listing |

Reading: plan auth-otp first; smart-picker and catalog-form can plan in parallel after auth-otp is LOCKED; the remaining 6 can plan in parallel once catalog-form is LOCKED. This map is INFORMATIONAL — the founder may choose to plan multiple features in parallel even when this map suggests sequencing, as long as the dependency assumptions are noted in each FEATURE_PLAN.md.
