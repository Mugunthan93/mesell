# UI Design-System Decoupling — Phase 5 BUILD SPEC (Seal & DAG contracts — capstone)

**Status:** BUILD SPEC (Step 1 of the MeeSell HYBRID dispatch — **no code in this doc**).
**Date:** 2026-06-17
**Author:** `meesell-frontend-coordinator` (Frontend Lead).
**Parent plan:** `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` → §3 decision #5 (enforcement), §3.4 (the 5 contracts), §4 "Phase 5 — Seal & DAG contracts", §7 (FE-5 allow-list open item).
**Preconditions (all MERGED to develop `8994735`):**
- **P1 `#259`** — FE-2 strict (icon seal).
- **P2 `#260`** — ui-kit aggregators.
- **P3 `#265`** — `@mesell/layout` page primitives + `MEE_LAYOUT`.
- **P4 `#267`** — chrome primitives + thin-host shell + **FE-3 strict** (`ci.yml --strict=fe2,fe3`).

**Phase 5 mandate (verbatim from parent §4):** "Finalize scanners **FE-1** (lock the already-true PrimeNG seal), **FE-4** (lib DAG), **FE-5** (public barrels). Flip the **FE Gate to blocking** (required status check on `develop`). **Deliverable:** all 5 contracts enforced; gate required. **Depends on:** Phases 1–4."

---

## 0. Measured baseline (verified 2026-06-17 against develop `8994735`)

| Fact | Evidence |
|---|---|
| All 5 FE contracts report **0 violations** | `node tools/contracts/run-all.mjs` → FE-1..FE-5 all OK, Total 0 |
| `--strict` (ALL five) already exits **0** | `node tools/contracts/run-all.mjs --strict; echo $?` → `0` |
| **Zero** deep `@mesell/<lib>/<subpath>` imports in `apps/**` (non-spec) | `grep -rnE "from ['\"]@mesell/[a-z-]+/[^'\"]+['\"]" apps/` → no matches |
| CI FE-gate step today | `run: node tools/contracts/run-all.mjs --strict=fe2,fe3` (P4 state) |
| FE Gate job posture today | **non-required**, NOT in `build.needs`/`deploy.needs` (P0 design, preserved through P4) |
| FE-5 Phase-0 seed allow-list | `PHASE0_ALLOWED_DEEP_PREFIXES = ['@mesell/ui-kit/', '@mesell/composites/', '@mesell/core/models']` — **vestigial** (the SP0 lean-bundle deep imports were anticipated but never committed; 0 deep imports exist) |

**Reframe:** the decoupling work is already *true* on develop — every contract is clean, and `--strict` (all) is green **right now**. Phase 5 is the **enforcement capstone**: it (a) makes CI fail on *any* future regression of *any* contract, and (b) makes the gate a **required status check** so a red gate actually blocks merge. There is no code/markup migration left — this is a config + finalize phase.

---

## 1. Scope (small, infra-focused)

**In:**
1. **CI strict-all flip** — `ci.yml` FE-gate step `--strict=fe2,fe3` → `--strict` (fail on ANY of the 5).
2. **FE-5 finalize** — empty the vestigial `PHASE0_ALLOWED_DEEP_PREFIXES` (0 deep imports exist → the list guards nothing; the seal becomes the clean "apps import barrel roots only, no exceptions"). Update the scanner header doc accordingly.
3. **FE-1 / FE-4 finalize** — no code change needed (already 0 violations, scanners final); update their header doc-comments from "Phase-0 expectation" to "Phase 5: enforced (strict, required gate)".
4. **README finalize** — `tools/contracts/README.md`: mark all 5 strict + the gate required; record the FE-5 allow-list emptied.
5. **Branch-protection required-check** — add `FE Gate: lint (5 contracts)` to develop's required status checks. **FOUNDER-GATED** (repo-settings change) — see §4. The PR ships the code; the founder flips the setting (or authorizes the coordinator to run the documented `gh api` call).

**Out:**
- Adding the FE-gate job to `build.needs`/`deploy.needs` — **NOT** how "required" is implemented. "Required status check" = branch protection (§4), which gates *merge*, not the build/deploy DAG. Keep the job decoupled from build/deploy (it is Node-only, dependency-free, and must stay fast + independent).
- Any scanner LOGIC change beyond emptying the FE-5 allow-list + doc-comments. The five scanners are already correct (proven by 4 phases of green).
- Any app/lib/component code change. Phase 5 touches **only** `frontend/tools/contracts/**` + `.github/workflows/ci.yml` + (founder) branch protection.
- New contracts, theme/token, MFE adoption (Phase 6), swap-proof (Phase 7).

---

## 2. Files to edit (manifest)

| # | Path | Action | Builder |
|---|---|---|---|
| C1 | `.github/workflows/ci.yml` | **EDIT** — FE-gate step `--strict=fe2,fe3` → `--strict`; update the step name + comments (Phase 5: all 5 strict; note the job is now intended to be a **required** check, wired in branch protection). Do NOT add to `build.needs`/`deploy.needs`. | infra-builder |
| C2 | `frontend/tools/contracts/fe5_public_barrels_only.mjs` | **EDIT** — set `PHASE0_ALLOWED_DEEP_PREFIXES = []` (finalize: no deep imports exist; the allow-list is emptied per plan §3.4). Update the header doc-comment (remove the Phase-0 lean-bundle allowance narrative; state the seal is final). | infra-builder |
| C3 | `frontend/tools/contracts/fe1_no_primeng_outside_uikit.mjs` | **EDIT (doc only)** — header comment: "Phase 5: strict + required." No logic change. | infra-builder |
| C4 | `frontend/tools/contracts/fe4_lib_dag.mjs` | **EDIT (doc only)** — header comment: "Phase 5: strict + required." No logic change. | infra-builder |
| C5 | `frontend/tools/contracts/run-all.mjs` | **EDIT (doc only)** — update the usage/Phase header comment block: Phase 5 = `--strict` (all), gate required. No logic change (the `--strict` machinery already exists). | infra-builder |
| C6 | `frontend/tools/contracts/README.md` | **EDIT** — mark all 5 contracts strict + the FE Gate a required status check on develop; record FE-5 allow-list emptied; the swap-proof note points to Phase 7. | infra-builder |

> **No FE-2 / FE-3 change** — already strict (P1/P4). `--strict` (all) supersedes `--strict=fe2,fe3`, so FE-2/FE-3 stay strict and FE-1/FE-4/FE-5 join them.

---

## 3. Per-file detail

### C1 — `ci.yml` FE-gate step
- `run: node tools/contracts/run-all.mjs --strict=fe2,fe3` → `run: node tools/contracts/run-all.mjs --strict`.
- Step name `Run FE contract scanners (strict FE-2,FE-3)` → `Run FE contract scanners (strict — all 5)`.
- Comment: Phase 5 — all five contracts strict; the job is now a **required status check** on develop (wired in branch protection, §4). Still NOT in `build.needs`/`deploy.needs` (required-check gates merge, not the build DAG). Still Node-only (no pnpm install).
- The higher-level phase comment block (the `# Phase 1/4/5` notes near the job) → mark Phase 5 active.

### C2 — `fe5_public_barrels_only.mjs`
- `const PHASE0_ALLOWED_DEEP_PREFIXES = [];` (emptied).
- The `isAllowed` note logic can stay (now always false → no "[allowed]" suffix appears) OR be simplified; **keep the diff minimal** — just empty the array + update the header doc. The scanner already pushes a violation for ANY deep `@mesell/<lib>/<subpath>` import; with strict-all + an empty allow-list, any such import fails CI. (0 exist today → clean.)
- Header doc: replace the "Phase-0 seed allow-list (warn-only baseline)" narrative with: "Phase 5: the seal is final — apps import `@mesell/*` barrel roots ONLY; no deep subpath, no cross-MFE. The SP0 lean-bundle deep-import allowance was never used (0 deep imports) and is removed."

### C3/C4/C5 — doc-comment-only
Flip "Phase-0 expectation: 0 violations" → "Phase 5: enforced (strict; FE Gate is a required check on develop)". No logic edits — the scanners are final.

### C6 — `README.md`
A short "Phase 5 — sealed" section: all 5 strict, gate required, FE-5 allow-list emptied. Pointer that the icon/theme swap-proof demonstration is Phase 7.

---

## 4. The required-status-check wiring (FOUNDER-GATED — the "gate required" deliverable)

Making the FE Gate a **required status check** is a **branch-protection (repo-settings) change**, not a file in this PR. Per the established pattern (the `ci.yml` comments since Phase 0: *"founder wires required-check in branch protection at Phase 5"*), this step is **founder-gated**.

**What the founder does** (after this PR's CI proves the gate green on develop): add the check named **`FE Gate: lint (5 contracts)`** to develop's required status checks. Documented command (the coordinator can run it **only on founder authorization** — it changes settings for all future PRs):

```
# View current required checks:
gh api repos/Mugunthan93/mesell/branches/develop/protection/required_status_checks -q '.contexts'
# Add the FE Gate (PATCH preserves the existing 13 + adds the 14th):
gh api -X PATCH repos/Mugunthan93/mesell/branches/develop/protection/required_status_checks \
  -f 'contexts[]=FE Gate: lint (5 contracts)'   # plus the existing contexts
```

> **Ordering:** flip CI strict (this PR) FIRST, confirm the gate runs green on develop post-merge, THEN add it as a required check. Adding a required check that has never produced a green run on the target branch can wedge merges. The PR's own CI run demonstrates green; the founder adds the required check immediately after merge (or pre-merge once the PR shows the gate green).

**Why not `build.needs`/`deploy.needs`:** those gate the build/deploy *jobs*, not *merge*. "Required status check" is the correct, surgical mechanism — it blocks merging a PR whose FE Gate is red, without coupling the design-system lint to the container build or K3s deploy. Keep them decoupled.

---

## 5. Which specialist builds this + coordination (HYBRID)
**Primary builder: `meesell-infra-builder`** — Phase 5 is entirely CI/contract-harness wiring (`ci.yml` + `tools/contracts/**`), which is infra territory (it owns `ci.yml`, the gate, branch-protection posture). No component/service/styler work (no app/lib/markup change).
**Coordinator (this session) runs the merge-gate** (§7) and opens the PR.
**Branch protection** (§4) is **founder-gated** — surfaced in the PR body + the founder report, not applied in this PR.

---

## 6. Out-of-scope (refuse if asked)
- Branch-protection mutation inside this PR (founder-gated; documented, not executed).
- Adding the gate to `build.needs`/`deploy.needs`.
- Scanner logic changes beyond emptying the FE-5 allow-list.
- Any app/lib/component/theme/token edit; MFE adoption (Phase 6); swap-proof (Phase 7).
- Backend/k8s; LOCKED docs.

---

## 7. Verification checklist (merge-gate evidence in the PR)
1. **Strict-all green:** `cd frontend && node tools/contracts/run-all.mjs --strict; echo $?` → **0**, all 5 CLEAN. Paste the table.
2. **FE-5 empty-allow-list still clean:** confirm `PHASE0_ALLOWED_DEEP_PREFIXES` is `[]` and FE-5 reports 0 (no deep imports exist). Paste.
3. **CI diff surgical:** `git diff .github/workflows/ci.yml` shows ONLY `--strict=fe2,fe3` → `--strict` (+ name/comment), job still NOT in `build.needs`/`deploy.needs`. Paste.
4. **No logic regression in scanners:** `git diff tools/contracts/*.mjs` shows only the FE-5 array empty + doc-comments (no other logic line changed). Paste `git diff --stat`.
5. **Sanity build/test unaffected** (scanners are dependency-free; no app change) — a quick `node tools/contracts/run-all.mjs` (warn mode) still 0, and (optional) `npx ng build frontend --configuration development` green (no app code changed, so parity trivially holds). Paste exit codes.
6. **Diff scope:** only `tools/contracts/**`, `.github/workflows/ci.yml`, this spec, README. No app/lib/component, no backend.

---

## 8. Risks & mitigations
| Risk | Mitigation |
|------|-----------|
| Required check wedges merges if added before a green run exists | §4 ordering: flip strict + merge, confirm green on develop, THEN founder adds the required check. |
| Emptying FE-5 allow-list breaks a real deep import | Baseline proves 0 deep imports in apps; strict-all already exits 0 → emptying changes nothing today. |
| `--strict` (all) surfaces a latent FE-1/4/5 violation | Baseline: `--strict` already exits 0 on develop — there is none. |
| Scanner doc edits accidentally change logic | §7.4: `git diff` must show only the FE-5 array + comments. |

---

## 9. Decisions for the founder to confirm
1. **[ACTION — branch protection] §4:** add `FE Gate: lint (5 contracts)` to develop's required status checks after this PR merges green. Authorize the coordinator to run the `gh api` PATCH, or do it in the GitHub UI. **This is the step that delivers "gate required."**
2. **[CONFIRM — FE-5 allow-list emptied] §3-C2:** 0 deep imports exist, so the Phase-0 lean-bundle allowance is removed (seal = barrel-roots only). Confirm (vs ratifying the 3 prefixes as permanent — not needed, nothing uses them).
3. **[CONFIRM — not in build/deploy needs] §4:** required *status check* (merge gate), NOT a `needs:` edge. Confirm.

---

*End of Phase 5 BUILD SPEC. Next HYBRID step: this session dispatches `meesell-infra-builder` (ci.yml strict-all + FE-5 empty-allow-list + scanner/README doc finalize), runs the §7 merge-gate, opens the PR, and surfaces the founder branch-protection action.*

End the eventual commit body with:
Co-Authored-By: Claude Opus 4.8 (1M context)
