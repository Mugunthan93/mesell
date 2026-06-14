# tools/dev — One-command dev boot

Two boot paths live here:

- **`start:all`** — 7 live `ng serve` dev servers with HMR. Needs 3–5 GB RAM. Best on
  16 GB+ machines while actively editing.
- **static dev** (`dev:build-static` / `dev:serve-static` / `dev:check-routes` /
  `dev:static`) — build once, serve the static bundles (~129 MB total). The memory-safe
  path for **low-RAM machines (≤ 8 GB)**, where `start:all` hangs. Full diagnosis,
  numbers, and the verified 11/11 route-check result: **[`STATIC_DEV.md`](STATIC_DEV.md)**.

## start:all

```
pnpm run start:all
```

Spawns all 7 Native Federation dev servers in a single terminal.

Internally calls `node tools/dev/start-all.mjs`, which uses only Node built-ins
(`node:child_process`, `node:process`) — zero extra npm dependencies.

Each server is started by delegating to its existing pnpm script, so ports are
always sourced from `angular.json` (nothing is hardcoded in start-all.mjs).

### Port map

| Port | Project |
|------|---------|
| 4200 | shell (host application) |
| 4201 | mfe-pricing |
| 4202 | mfe-export |
| 4203 | mfe-onboarding |
| 4204 | mfe-dashboard |
| 4205 | mfe-catalog |
| 4206 | mfe-auth |

### Log prefixes

Each child's stdout and stderr lines are prefixed with a colour-coded label,
e.g. `[shell]`, `[mfe-auth]`, so interleaved output from 7 servers is readable.

### Ctrl-C teardown

Pressing Ctrl-C (or sending SIGTERM to the process) sends SIGTERM to all 7
child processes and waits up to 3 seconds before escalating to SIGKILL.
The parent process then exits 0.

If any single child exits with a non-zero code before you press Ctrl-C, the
script names that child in a clear error message, tears down all remaining
servers, and exits 1.

### FRONTEND ONLY — additional prerequisites

`pnpm run start:all` boots the Angular layer only. A fully working session also
requires:

1. **Backend on :8000** — run `make dev` (docker-compose) or ensure k3s pods are
   up. The Angular dev proxy forwards `/api/*` to `:8000`.
2. **Dev proxy merged (PR #212)** — `frontend/proxy.conf.json` and the
   `proxyConfig` key in `angular.json` must be present. Without the proxy,
   every API call from the shell returns a CORS or connection-refused error.
3. **Real `MSG91_AUTH_KEY` in `backend/.env`** — OTP flows go live to MSG91.
   There is no test/sandbox mode for V1; a missing or placeholder key causes
   all OTP requests to fail with a 5xx from the backend.

## static dev (low-RAM machines)

For machines that cannot afford 7 concurrent `ng serve` watchers. Build each app once,
then serve the static `dist/<app>/browser` output with the zero-dep `serve.js`. Full write-up
(8 GB hang diagnosis, 129 MB vs 3–5 GB numbers, the `dev:true` watchdog finding, the
EventSource-noise note, and the verified 11/11 result) is in **[`STATIC_DEV.md`](STATIC_DEV.md)**.

| Script | File | Does |
|--------|------|------|
| `pnpm run dev:build-static [apps...]` | `build-static.mjs` | Watchdog-build all 7 apps (dev config), one at a time. Optional app subset. |
| `pnpm run dev:serve-static` | `serve-static.mjs` | Serve the built apps on 4200–4206 (7 × `serve.js`). Fails fast if an app is not built. |
| `pnpm run dev:check-routes [engine]` | `route-check.mjs` | Drive the 11 shell routes through federation; assert 11/11 clean. `chromium` (default) or `webkit`. |
| `pnpm run dev:static <cmd>` | `dev-static.mjs` | Orchestrator: `build` / `serve` / `check` / `up` / `all`. |

Fast loop:

```bash
pnpm run dev:build-static     # build all 7 once
pnpm run dev:serve-static     # leave running (Ctrl-C stops all 7)
pnpm run dev:check-routes     # in another terminal — expect 11/11
```

One-shot (build → serve in background → check → report → stop):

```bash
pnpm run dev:static all       # exit 0 only if route-check is 11/11
```

All four scripts are zero-dep Node built-ins, except `route-check.mjs` which uses the
already-present `playwright` devDependency. Nothing new was added to `package.json` deps.
