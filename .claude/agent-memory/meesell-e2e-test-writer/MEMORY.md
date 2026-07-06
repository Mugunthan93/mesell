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

## Latest wave (2026-07-06) — qa-pricing e2e lane completion (commit `1794da3`, direct-to-develop) [SCRIBED BY QA-COORD]
De-fixme'd W3-E2-4 (catalog delete) + W3-E2-6 (price→apply→export chain) + authored PQE-E2E-04/04b (apply-price + error path). Suite fixme 9→7; `--list` clean 31/16. Gate PASS (KEEP ruling on the W3-E2-6/PQE-E2E-04 overlap). New knowledge: pricing apply trio = NATIVE testids (click directly); catalog rows = `[data-product-id]` + `<span>`-wrapped delete controls (`.locator('button')`); 5 DEPLOYED-stack quirks (reload-fragile cross-site auth, base-href `/mesell/`, deployed product-creation DOWN, onboarding not persisted, offline harness recipe). See the 3 topic files' 2026-07-06 sections.

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
