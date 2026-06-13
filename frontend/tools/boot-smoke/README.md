# boot-smoke — Browser-Boot Smoke Gate

Catches the F-001 class of failures: **build-green / browser-dead** from a native-federation
import-map subpath miss (or any other Angular bootstrap failure mode that a TypeScript build
silently passes).

## Why this gate exists

The round-1 smoke gate had a critical flaw: it served the built `dist/` with
`python -m http.server`, which returns a real HTTP 404 for any path that is not an exact
file (e.g. `/login`, `/profile`). The assertions — `body.length > 0` and
`zeroSpecifierErrors` — trivially passed on the Python 404 error page body because Angular
never ran. This is the **false-pass** that shipped with PR #203.

This gate is immune to that failure mode because:
1. `serve.js` implements a proper SPA history-fallback (all non-file GETs return `200 + index.html`).
2. `boot-smoke.js` assertion (a) captures the top-level document HTTP status via
   `page.on('response')` and FAILS immediately on any non-200 document.

## Port map (must match `apps/shell/public/federation.manifest.json`)

| App            | Port |
|----------------|------|
| shell          | 4200 |
| mfe-pricing    | 4201 |
| mfe-export     | 4202 |
| mfe-onboarding | 4203 |
| mfe-dashboard  | 4204 |
| mfe-catalog    | 4205 |
| mfe-auth       | 4206 |

## SPA fallback requirement

`serve.js` MUST return `200 + index.html` for any path that is not an existing file.
This is non-negotiable: without this, navigating to `/login` or `/profile` returns 404,
Angular never boots, and the gate cannot see component selectors or specifier errors.

Verify it works:

```bash
node serve.js dist/frontend/browser 4200 &
curl -s -o /dev/null -w '%{http_code}' http://localhost:4200/login
# Must print: 200   (NOT 404)
```

## CORS requirement

`serve.js` sets `Access-Control-Allow-Origin: *` on ALL responses. This is required
because the shell (port 4200) fetches `remoteEntry.json` from the remote ports (4201-4206)
via cross-origin `fetch()`. Without CORS headers, the browser blocks those fetches and
the federation runtime falls back to `RemoteFailureComponent` for every remote — which
would cause the gate to FAIL even on a clean build (false negative).

In production (Traefik ingress), CORS is handled at the ingress level. In CI, the
static server must handle it explicitly.

## How to run locally

Prerequisites: Node 22, pnpm 11.5.2, Playwright chromium installed.

```bash
# 1. Build all apps (from frontend/)
pnpm exec ng build frontend --configuration production
pnpm exec ng build mfe-pricing --configuration production
pnpm exec ng build mfe-export --configuration production
pnpm exec ng build mfe-onboarding --configuration production
pnpm exec ng build mfe-dashboard --configuration production
pnpm exec ng build mfe-catalog --configuration production
pnpm exec ng build mfe-auth --configuration production

# 2. Install Playwright chromium (if not already installed)
cd frontend && npx playwright install chromium

# 3. Start the 7 static servers (from frontend/)
node tools/boot-smoke/serve.js dist/frontend/browser    4200 &
node tools/boot-smoke/serve.js dist/mfe-pricing/browser 4201 &
node tools/boot-smoke/serve.js dist/mfe-export/browser  4202 &
node tools/boot-smoke/serve.js dist/mfe-onboarding/browser 4203 &
node tools/boot-smoke/serve.js dist/mfe-dashboard/browser  4204 &
node tools/boot-smoke/serve.js dist/mfe-catalog/browser    4205 &
node tools/boot-smoke/serve.js dist/mfe-auth/browser    4206 &

# 4. Wait for remoteEntry.json readiness
until curl -sf http://localhost:4201/remoteEntry.json >/dev/null; do sleep 1; done
until curl -sf http://localhost:4206/remoteEntry.json >/dev/null; do sleep 1; done
# ... (repeat for all remotes)

# 5. Run the gate (from frontend/)
node tools/boot-smoke/boot-smoke.js

# 6. Check exit code
echo "Exit: $?"   # 0 = all pass, 1 = failure
```

Or use the npm script:

```bash
cd frontend && pnpm run smoke:boot
```

## Assertions (ALL must hold per route × width)

| # | Assertion | False-pass it prevents |
|---|-----------|------------------------|
| (a) | Document HTTP status = 200 | 404 body from server-without-SPA-fallback |
| (b-1) | `app-root` present in DOM | Angular never mounted |
| (b-2) | Real selector mounted (`app-landing`, `mee-login`) | MFE remote failed silently |
| (b-3) | NO `RemoteFailureComponent` (`cloud_off` / `app-remote-failure`) | D12 fallback rendered instead of real component |
| (c) | ZERO `Unable to resolve specifier` console messages | F-001 import-map subpath miss |
| (d) | ZERO uncaught JS exceptions / unhandled rejections | F-001 unhandled rejection (second symptom) |

Routes tested: `/`, `/login`, `/profile` at **360px** and **1280px** viewport widths.

## Negative-test procedure

This procedure PROVES the gate goes RED on a real F-001 regression.
Run it once before merging to establish the evidence baseline.

```bash
# Step 1: Reintroduce a subpath import (the F-001 trigger).
# In frontend/apps/mfe-auth/src/app/login.component.ts, change:
#   import { MeeInputComponent, MeeButtonComponent } from '@mesell/ui-kit';
# to:
#   import { MeeInputComponent } from '@mesell/ui-kit/input/input.component';
#   import { MeeButtonComponent } from '@mesell/ui-kit/button/button.component';

# Step 2: Rebuild mfe-auth only (fast).
pnpm exec ng build mfe-auth --configuration production

# Step 3: Restart the mfe-auth server.
kill <mfe-auth-pid> 2>/dev/null
node tools/boot-smoke/serve.js dist/mfe-auth/browser 4206 &

# Step 4: Run the gate — expect RED.
node tools/boot-smoke/boot-smoke.js
# Expected output: FAIL on /login @ 360 and 1280
#   hardConsoleErrors: "Unable to resolve specifier '@mesell/ui-kit/input/input.component'"
#   pageErrors: unhandled rejection
#   OVERALL: FAIL

# Step 5: Revert the subpath import.
git restore frontend/apps/mfe-auth/src/app/login.component.ts

# Step 6: Rebuild + re-run — expect GREEN.
pnpm exec ng build mfe-auth --configuration production
node tools/boot-smoke/boot-smoke.js
# OVERALL: PASS
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SMOKE_SHELL_URL` | `http://localhost:4200` | Base URL for the shell app |
| `SMOKE_SCREENSHOT_DIR` | `frontend/tools/boot-smoke/screenshots/` | Screenshot output directory |
| `SMOKE_RESULTS_FILE` | `frontend/tools/boot-smoke/smoke-results.json` | JSON results output path |

## CI job

The gate runs as the **advisory** job `"Frontend: boot smoke"` in `.github/workflows/ci.yml`.
It is **not yet a required status check** — the founder promotes it to required via
GitHub branch protection settings (Settings → Branches → Require status checks → add
`Frontend: boot smoke`) after the first green CI run confirms reliability.

Timeout: 25 minutes (build 7 apps + boot + run Playwright).
