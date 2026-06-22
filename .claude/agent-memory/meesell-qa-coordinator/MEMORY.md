# Memory — meesell-qa-coordinator

## Agent Identity
QA Lead for MeeSell — the fourth coordinator pillar (peer to backend / frontend / ai).
Owns QA wave strategy, the per-specialist test specs, the merge gate for
`feature/qa-wave-N/<group>` → `feature/qa-wave-N/integration` PRs, and
`docs/status/feature_board_qa.md` (sole writer). Dispatches 3 test specialists:
`meesell-backend-test-writer` (sonnet), `meesell-frontend-test-writer` (sonnet),
`meesell-e2e-test-writer` (opus). Decentralized memory ecosystem — read own memory
+ the 3 feature coordinators' memory at task start; never write to another agent's
memory.

## Index of topic files
- [qa_waves.md](qa_waves.md) — wave history, coverage per wave, exit criteria met
- [coverage_gaps.md](coverage_gaps.md) — accumulated gaps across waves (survives between sessions)
- [coordinator_patterns.md](coordinator_patterns.md) — recurring omissions in builder PRs (cross-wave learning)

## Bootstrap note (2026-06-22)
Pillar created via `feature/qa-wave-infra` (QA pillar bootstrap, fleet 19→23). No
wave has run yet. First expected dispatch: "Run QA Wave 1 against: auth-otp,
xlsx-export, catalog-wizard." Read `docs/superpowers/specs/2026-06-22-meesell-testing-agent-design.md`
for the full design.

## Wave 3 — catalog vertical EXECUTED + MERGED to integration (2026-06-22)
Merge-gate (session `mesell-qa-wave-3-coord-session-1`): backend #396 (squash `edb875f`, 59 passed/0 failed) + frontend #394 (squash `4571048`, all 5 authored files GREEN) → both PASS → squash-merged into `feature/qa-wave-3/integration` (fast-forwarded base `6a02669`→develop `3c63b55` first). Backend memory scribed PR #400 `804d317`. Board published PR #401 `4ea1974`. `integration → develop` is READY for the FOUNDER and contains BOTH backend + frontend lanes. E2E lane (W3-E2-*) NOT dispatched; W3-FE-6/E2-3 gated on the mfe-export productId fix (branch exists, not on develop); W3-BE-11 (cost ceiling) + W3-E2-5 (GCS env) deferred. See qa_waves.md + coordinator_patterns.md for the stale-integration-base merge lesson + the pure-function-mirror gate stance.
