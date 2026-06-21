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
