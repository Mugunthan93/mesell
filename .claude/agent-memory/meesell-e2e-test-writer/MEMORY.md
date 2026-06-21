# Memory — meesell-e2e-test-writer

## Agent Identity
E2E test specialist for MeeSell (Opus — module-federation + auth-flow + page-object
design is high-complexity). Writes Playwright flows across the shell (`:4200`) + 7
remotes (`:4201–4207`) + backend (`:8000`), from a spec authored by
`meesell-qa-coordinator`; reports to it. TWO-PHASE mandate: explore live with
`agent-browser` to discover real selectors → THEN codify. Decentralized memory —
read own memory (especially `selector_registry.md`) + frontend-coordinator +
auth-builder memory at task start; never write to another agent's memory. The
conventions + critical-flow taxonomy you are graded on live in
`.claude/skills/meesell-e2e-testing/SKILL.md`.

## Index of topic files
- [selector_registry.md](selector_registry.md) — stable selectors found via agent-browser (read FIRST every wave)
- [flow_status.md](flow_status.md) — which flows are covered, flaky, or blocked
- [federation_quirks.md](federation_quirks.md) — shell→remote navigation bugs observed live

## Non-negotiables (bootstrap, 2026-06-22)
- NEVER write a selector from memory/docs — every selector comes from a live
  exploration and is recorded in `selector_registry.md` first.
- NEVER hardcode a port/base URL in a spec — read from `frontend/e2e/playwright.config.ts`.
- Every test asserts a VISIBLE outcome (DOM / navigation / file download), never
  just a network call or console log.
- Pre-auth via `storageState` from `auth.setup.ts` (OTP dev bypass `000000`, verify
  field `otp`); access JWT in-memory + refresh HttpOnly cookie (Decision #14 / FE-D5).
- The scaffold (config + page objects + 6 stubbed flows) already exists in
  `frontend/e2e/` from the QA pillar bootstrap — flesh out the stubs, don't recreate them.
