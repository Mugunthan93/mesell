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
| Change type | Verify | Tool |
|---|---|---|
| fe-route | shell + route renders, HTTP 200 | **agent-browser** (behavioral) |
| fe-federation | remote loads, no logout on shell→remote nav | **agent-browser** (behavioral) |
| api-endpoint | targeted httpx 2xx with expected shape | httpx |
| migration | upgrade head succeeds on a disposable TEST_DATABASE_URL | alembic |

## Behavioral verification with agent-browser

The FE verify checks — route renders, shell→remote nav with **NO logout**, and the in-app
form flows — are **behavioral**: they cannot be confirmed by a diff-only `/code-review`. They
are performed by **agent-browser** driving a real headless Chrome against a live env. This is
the real behavioral gate that replaces the previously-deferred "logout smoke (8GB)" gap —
agent-browser does it for real, **one env at a time** (single-build mutex + RAM budget still
apply; never stand up two verify envs concurrently).

For the `fe-route` and `fe-federation` rows in the change-type table above, **agent-browser is
the tool.**

### Recipe

1. **Serve** the shell + only the touched MFE on the slot ports:
   `python3 tools/meesell_env.py up <worktree> --mfe <touched>`
2. **Drive** with agent-browser:
   - Navigate to the shell.
   - Log in using the dev OTP bypass (`000000`).
   - Navigate **shell → the touched remote**.
   - **ASSERT no redirect to `/login`** — i.e. the Native Federation singleton holds and the
     in-memory access token survives the nav (the #328 regression check).
   - Capture a **screenshot** of the rendered remote as the pass artifact.
3. **Tear down**: `python3 tools/meesell_env.py down <worktree>` + `gc` after.

### Per-dev prereq (one time)

```bash
npm i -g agent-browser && agent-browser install   # + a local Chrome
```

## Rules
- Pilot on the two open known bugs (federation-singleton logout, `size_in_ltrs` 422) before standardizing.
- Never run the full 8-app stack to verify one change. Never use the live dev DB for migration verify (disposable TEST_DATABASE_URL only).
- Reference `docs/dev/CLAUDE_FEATURE_ADOPTION.md` §3.5 and `docs/dev/REVIEW_GATES.md`.
