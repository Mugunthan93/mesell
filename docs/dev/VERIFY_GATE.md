# MeeSell /verify Gate (HYBRID step 3 obligation)

> The coordinator runs the built-in `/verify` skill on a specialist's change BEFORE accepting the PR, using the MeeSell recipe below. A specialist PR without a `/verify` pass artifact is rejected. Advisory→obligation for change types that touch runnable surfaces.

## Frontend verify recipe
- Bring up ONLY the touched MFE(s) via the env-manager: `python3 tools/meesell_env.py up <worktree> --mfe <touched-only>` (honors the single-build mutex + RAM budget — NEVER rebuild all 7, NEVER run concurrent verify envs).
- Run a boot-smoke against the assigned shell/MFE port block (HTTP 200 on shell + the touched MFE + its remoteEntry.json).
- For federation changes specifically: confirm NO shell→remote logout (the singleton stays deduped) — the #328 regression check.
- Always tear down after: `python3 tools/meesell_env.py down <worktree>` + `gc`.

## Backend verify recipe
- Targeted httpx assertion against the worktree's backend port (e.g. autofill 200 with `product_name` seed; PATCH accepts a valid `size_in_ltrs` enum) — the exact assertion depends on the change.
- Tear down after.

## Change-type → assertion
| Change type | Verify |
|---|---|
| fe-route | shell + route renders, HTTP 200 |
| fe-federation | remote loads, no logout on shell→remote nav |
| api-endpoint | targeted httpx 2xx with expected shape |
| migration | upgrade head succeeds on a disposable TEST_DATABASE_URL |

## Rules
- Pilot on the two open known bugs (federation-singleton logout, `size_in_ltrs` 422) before standardizing.
- Never run the full 8-app stack to verify one change. Never use the live dev DB for migration verify (disposable TEST_DATABASE_URL only).
- Reference `docs/dev/CLAUDE_FEATURE_ADOPTION.md` §3.5 and `docs/dev/REVIEW_GATES.md`.
