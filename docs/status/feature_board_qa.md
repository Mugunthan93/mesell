# Feature Board — QA Lead

**Lead agent:** `meesell-qa-coordinator`
**Domain:** qa (test pillar — the fourth coordinator, peer to backend / frontend / ai)
**Last updated:** 2026-06-22 (**QA PILLAR BOOTSTRAPPED — fleet 19 → 23.** The QA infrastructure landed via `feature/qa-wave-infra` (built by `meesell-infra-builder` per the APPROVED design `docs/superpowers/specs/2026-06-22-meesell-testing-agent-design.md`): 4 agent specs (`meesell-qa-coordinator` opus + `meesell-backend-test-writer`/`meesell-frontend-test-writer` sonnet + `meesell-e2e-test-writer` opus), 3 testing skills (`meesell-backend-testing`/`meesell-frontend-testing`/`meesell-e2e-testing`), the 4 memory dirs (seeded), and the Playwright E2E scaffold under `frontend/e2e/` (config + auth.setup + 4 page-objects + 6 STUBBED flows). **No QA wave has run yet** — the first is explicitly dispatched by the master session after a feature batch merges to develop. This board is the QA coordinator's single domain surface; `meesell-qa-coordinator` is its sole writer from here on.)
**This file is the single domain-level status surface for the QA lead.**

---

## Active waves

| Wave | Group branch | Status | Current session | Last touched | Blocking | Notes |
|---|---|---|---|---|---|---|
| _(none active — pillar just bootstrapped; first wave awaits a master-session dispatch)_ | | | | | | |

## Recently merged (last 14 days)

| Wave | Merged to | Date | PR | Notes |
|---|---|---|---|---|
| qa-wave-infra (pillar bootstrap) | develop | 2026-06-22 | `feature/qa-wave-infra/integration` → develop (founder-gated) | **QA pillar bootstrap — 4 agents + 3 skills + 4 memory dirs + Playwright E2E scaffold + registry updates.** Built by `meesell-infra-builder` per the APPROVED design. `.claude/**` artifacts landed via the git-plumbing route (write-protected). E2E flow specs are intentional STUBS (`test.fixme`) — the first QA wave fleshes them out after a live agent-browser exploration phase. Fleet count: CLAUDE.md + MEESELL_AGENT_REGISTRY.md updated 19 → 23. |

## Inter-lead requests open

| To lead | About wave | Request | Opened | Status |
|---|---|---|---|---|
| frontend-coordinator | qa-wave-1 (E2E) | The app ships ZERO `data-testid` attributes today. Before the E2E flows can move off `test.fixme`, the components behind the 8 critical seller flows need stable `data-testid`s (the E2E writer supplies the exact selector list from its live exploration phase, recorded in `selector_registry.md`). NOT yet opened as a formal memo — will be raised by `meesell-qa-coordinator` at the first wave dispatch. | (pre-wave note) | NOT YET OPENED |

---

## Status vocabulary

| Status | Meaning |
|---|---|
| `PENDING` | Wave is on the QA backlog; no branch exists yet. |
| `IN PROGRESS` | A `feature/qa-wave-N/<group>` branch exists; a test specialist is actively committing. |
| `IN REVIEW` | A PR is open against `feature/qa-wave-N/integration`; awaiting the QA coordinator's merge-gate review. |
| `MERGED` | The group's test PR has merged to `feature/qa-wave-N/integration`. |
| `BLOCKED` | Work stopped pending a missing selector / fixture, an inter-lead request, or a founder decision. |

A wave row stays on Active waves until its group PR merges to `feature/qa-wave-N/integration`; then it moves to "Recently merged" for 14 days before being removed.

---

## Acceptance gate

Group-PR approval (the QA coordinator's merge-gate review) requires every box:

- [ ] Tests actually run — `pytest` / `ng test` / `playwright test` output pasted in the PR description
- [ ] `TEST_DATABASE_URL` safety guard (`_resolved_db.endswith("_test")`) not bypassed (backend)
- [ ] No real external calls — Gemini / MSG91 / Razorpay / GCS all mocked at the adapter boundary
- [ ] Coverage target from the test spec is met (the measurable exit criterion)
- [ ] No assertion-free test (none that passes while asserting nothing)
- [ ] E2E: selectors came from a live exploration (present in `selector_registry.md`), not from memory; no hardcoded ports
- [ ] PR template filled completely (no `<>` placeholders)
- [ ] The board row for this wave/group is `IN REVIEW`

The QA wave runs as a dedicated sprint AFTER feature waves merge to develop — it never blocks an individual feature PR. The `feature/qa-wave-N/integration` → `develop` merge is the **founder's** gate (D1); the QA coordinator owns only the `feature/qa-wave-N/<group>` → `feature/qa-wave-N/integration` gate.
