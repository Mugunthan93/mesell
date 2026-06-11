# Feature Board — AI Lead

**Lead agent:** `meesell-ai-coordinator`
**Domain:** ai
**Last updated:** 2026-06-11 (image-precheck AI session-2 STEP 3 — precheck_smoke gate PASS, flat-lane founder-gate PR opened)
**This file is the single domain-level status surface for the lead.**

---

## Active features

| Feature | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| _(none active — image-precheck precheck_smoke gate PASS, moved to Recently merged)_ | | | | | | |

## Recently merged (last 14 days)

| Feature | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| smart-picker | `feature/smart-picker/integration` | 2026-06-11 | [#54](https://github.com/Mugunthan93/mesell/pull/54) | F2. `smart_picker_v1` JSON closing schema. Eval 50/50 top-5 recall=100% (≥80%). Founder gate PR [#55](https://github.com/Mugunthan93/mesell/pull/55) open. |
| catalog-form | `feature/catalog-form/integration` | 2026-06-11 | [#56](https://github.com/Mugunthan93/mesell/pull/56) | F4. Autofill fixture-path fix + JSON closing. Eval invalid-enum=0% (=0%), drop controls 2/2. Founder gate PR [#57](https://github.com/Mugunthan93/mesell/pull/57) open. |
| image-precheck | `feature/image-precheck/integration` | 2026-06-11 | [#58](https://github.com/Mugunthan93/mesell/pull/58) | F5. `watermark_v1` docstring fix + R3 vision-cost AMENDMENT (≤₹0.08). Eval accuracy=100% (≥85%). Founder gate PR [#59](https://github.com/Mugunthan93/mesell/pull/59) open. |
| image-precheck (precheck_smoke) | `develop` (flat-lane founder gate) | 2026-06-11 | #PR_NUM | F5 D2 Gate 2. `tests/eval/precheck_smoke/` 20-image deterministic Pillow smoke (10 bad / 10 good). Gate PASS: 22/22, worst 0.028s vs 2s, 0 Gemini ₹0. G2 ruled keep-as-built 5×5/235 (plan amended). G3 ruled fix_hints=FE static map. FLAT-LANE founder-gate PR (avoids frozen #118). |

## Inter-lead requests open

| To lead | About feature | Request | Opened | Status |
|---|---|---|---|---|

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Feature is on the lead's backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/{name}/ai` branch exists; specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/{name}`; awaiting lead approval. |
| `MERGED` | The AI group's PR has merged to `feature/{name}` — the group is done for this feature. |
| `BLOCKED` | Work stopped pending an inter-lead request, infra change, or founder decision. |

A feature row stays on the Active features table until the AI group's PR merges to `feature/{name}`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

Group-PR approval criteria live in the AI PR template at `.github/PULL_REQUEST_TEMPLATE/ai.md`. The lead approves a `feature/{name}/ai` → `feature/{name}` PR only when the template is filled completely — including prompt registry version bump, eval evidence green (smart_picker top-5 recall ≥ 80 %, autofill invalid-enum rate = 0 %, watermark accuracy ≥ 85 %), per-call cost ≤ ₹0.05 documented, LangFuse trace sample link, and guardrail compliance — plus CI gate-1 (unit) green and nightly `ai_eval` green within the last 24 hours.
