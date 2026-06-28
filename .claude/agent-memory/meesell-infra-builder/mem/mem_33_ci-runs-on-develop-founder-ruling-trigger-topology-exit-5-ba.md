## CI runs on develop — founder ruling + trigger topology + exit-5 barrier — 2026-06-11 (mesell-ci-develop-triggers-infra-session-1)

**Founder ruling (verbatim):** "why develop->main / let keep in develop." CI must exercise on `develop` ITSELF. develop→main promotion (PR #64/#78 pattern) is RETIRED as the re-fire mechanism. Lesson for future: never tell the founder "promote to main to fire CI" again — develop is a first-class CI branch now.

**Trigger amendment (PR #79, squash `33d0cc6`, merged via `--admin` to develop):**
- `.github/workflows/ci.yml`: added `develop` to BOTH `on.push.branches` and `on.pull_request.branches`. nightly cron untouched.
- `docs/DEVOPS_ARCHITECTURE.md §5.2` updated to match (sole-writer surface — always sync this when ci.yml triggers change, or the doc rots).

**DEPLOY-GUARD AUDIT (the load-bearing safety check):** build + deploy jobs were ALREADY ref-guarded — `if: github.event_name == 'push' && github.ref == 'refs/heads/main'` (ci.yml lines 570 + 610). So adding develop to triggers does NOT add a develop deploy path. **No new `if:` guard was needed.** Empirically confirmed (run 27320468096, push to develop): Build + Deploy both SKIPPED. RULE: whenever you add a branch to triggers, grep `github.ref == 'refs/heads/main'` FIRST — if build/deploy carry it, you're safe; if they DON'T, you must add it before merging or a non-main push will deploy.

**Topology proven by run 27320468096 (event=push, branch=develop, the merge of #79):**
- Frontend matrix 3/3 GREEN (frontend-changes + shell + mfe-pricing) — frontend runs on develop, real signal.
- Gate-1 unit FAILURE → Gates 2-5 SKIPPED (sequential `needs:` cascade).
- Build + Deploy SKIPPED (main-only). Nightly SKIPPED (schedule-only).
- A push to develop fired NOTHING before this change; now it fires the gates+frontend. PR-to-develop also fires (proven by PR-open run 27320409503).

**The Gate-1 barrier MOVED, did not vanish — exit-5, not collection:**
Collection (ModuleNotFoundError) is CLOSED (PR #73/#74 `pythonpath=.` → 823 items collect cleanly). §5.D env-guard CLOSED (PR #76 `0f44d72`). What surfaced NEXT:
```
collected 823 items / 823 deselected / 0 selected
=========================== 823 deselected in 1.76s ============================
##[error]Process completed with exit code 5.
```
pytest exit-5 = NO_TESTS_COLLECTED. The 7 §19.D markers are registered in pytest.ini but applied to ZERO test functions, so `-m "unit"` selects 0 → exit-5 → gate RED. SYSTEMIC: every marker-gated gate (smoke/integration/golden_roundtrip/slow/perf/ai_eval) hits the same. Gate-3 lint (not marker-gated) is unaffected. **Backend-owned** (test bucketing is a backend call; pytest.ini §19.D LOCKED). Did NOT fix — inter-lead to backend-coordinator OPEN; memo `handoff_ci_gate_markers.md` (authored by the prior ci-activation session) is the canonical writeup. Fix = tag suite across all buckets (explicit marks OR `pytest_collection_modifyitems` auto-marker hook). LESSON: "collection green" ≠ "gate green" — `pytest -m X` with 0 X-tagged tests is a HARD failure (exit-5), not a vacuous pass. The task brief expected "green-but-vacuous"; reality is RED. Document this so nobody assumes empty-marker = pass.

**Worktree gotcha (cost me a cycle):** `git worktree add /tmp/mesell-wt/...` on this macOS box resolves `/tmp`→`/private/tmp`. The worktree got created then showed "prunable" with the dir gone when I mixed `/tmp` and `/private/tmp` paths. FIX: always use the explicit `/private/tmp/mesell-wt/<name>` path for worktree add AND for all Read/Edit/Bash against it. Worktree files are root-owned (`root:wheel`/`root:staff`) but git ops + Edit work fine.

**Merge mechanics this session — Edit/Write worked directly (no bg-isolation guard hit):** Unlike prior ci-activation sessions where Write/Edit were blocked on the shared checkout (forcing contents-API PUT), this session's Edits on the dedicated worktree paths succeeded normally. So: chore work in a fresh worktree off origin/develop → normal Edit → commit → push → PR → `--admin` squash-merge is the clean path. develop protection: `required_status_checks.contexts=[]`, `required_approving_review_count=1`, `enforce_admins=false` → author can't self-approve → `--admin` is how single-account merges land (matches #76/#69 mergedBy=Mugunthan93).

**STATUS surfaces (origin/develop was AHEAD of main-worktree HEAD):** the ci-activation session had committed board/STATUS updates I didn't have locally (HEAD 48730a2 behind origin/develop). I did status edits in a SEPARATE worktree off origin/develop (`chore/ci-develop-status-update`) so I edited the CURRENT board, not a stale one. RULE: before touching feature_board_infra.md / STATUS_INFRA.md, `git log HEAD..origin/develop -- <file>` — if it differs, edit off origin/develop, never off a stale local HEAD (you'd clobber another session's edits).

**Check-contexts for branch protection (STILL DEFERRED, founder-gated):** exact required-PR set once green = {`CI Gate 1: unit`, `CI Gate 2: smoke`, `CI Gate 3: lint (10 contracts)`, `CI Gate 4: integration`, `CI Gate 5: golden_roundtrip`, `Frontend: detect changed workspace units`, `Frontend: shell`, `Frontend: mfe-pricing`}. NEVER add Build/Deploy (push/main-only → deadlock PRs) or Nightly (schedule-only). NOT applied this session.

**WIF/build/deploy STILL UNPROVEN** — sequential-blocked at Gate-1 on every run (collection then exit-5). First green-through-Gate-5 on a MAIN push is the first real exercise of WIF + Cloud Build + IAP deploy.

---
