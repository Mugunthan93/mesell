# tools/dev — One-command dev boot

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
