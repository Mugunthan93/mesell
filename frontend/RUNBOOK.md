# MeeSell Frontend — Localhost Boot Runbook

**Audience:** founder / anyone who wants the full MeeSell UI running on their machine.
**What this gives you:** the complete Native-Federation app — shell on `:4200` plus all 6
remotes (`:4201`–`:4206`) — served live with hot reload, talking to the local backend API.

This is the exact mechanism the CI **boot-smoke** gate exercises on every push
(GitHub Actions job *"Frontend: boot smoke"*, last green run
[`27487357896`](https://github.com/Mugunthan93/mesell/actions/runs/27487357896), sha `ebb700e`).
If CI is green, these two terminals will boot the same way locally.

---

## Two-command boot

### Terminal 1 — backend stack

```bash
make dev
```

This runs `docker compose -f docker-compose.dev.yml up --build` — FastAPI API + PostgreSQL +
Valkey. **Wait until the API answers health** before starting the frontend:

```bash
curl localhost:8000/health     # expect HTTP 200, {"status":"ok", ...}
```

### Terminal 2 — the full frontend (shell + 6 remotes)

```bash
cd frontend
pnpm install          # first time only
pnpm run start:all
```

`start:all` runs `node tools/dev/start-all.mjs`, which spawns **7 `ng serve` processes in
parallel** (one shell + six remotes) with colour-coded per-server log output and a clean
Ctrl-C teardown that kills all 7. Wait for all 7 servers to print "Compiled successfully"
(the shell takes longest on a cold start).

Then open:

```
http://localhost:4200
```

The landing page renders immediately (public). `/login` renders the real federated `mfe-auth`
form. Authenticated routes (e.g. `/dashboard`, `/profile`) redirect to `/login` until you sign in.

---

## Port → remote map

Authoritative source: `frontend/tools/dev/start-all.mjs` (banner) and each project's
`serve.options.port` in `frontend/angular.json`. Verified 2026-06-14.

| Port | Project | Serves |
|------|---------|--------|
| **4200** | `frontend` (shell / host) | shell chrome + routing + auth/error interceptors + landing + dashboard (shell-local pages) |
| **4201** | `mfe-pricing` | `/catalogs/:id/pricing` |
| **4202** | `mfe-export` | `/catalogs/:id/export` |
| **4203** | `mfe-onboarding` | onboarding / profile |
| **4204** | `mfe-dashboard` | dashboard remote |
| **4205** | `mfe-catalog` | `/catalogs/*` (smart-picker, catalog-form, images, preview) |
| **4206** | `mfe-auth` | `/login`, `/signup`, `/otp-verify` |

> Note: the shell's `:4200` is set by the `start:shell` script (`ng serve frontend --port 4200`);
> the six remote ports are fixed in `angular.json`. Don't infer the remote ports from the shell
> script — use the table above.

---

## How requests reach the backend

The dev server proxies API calls to the local backend so there are no CORS hops in dev:

- `frontend/proxy.conf.json` maps `**/api**` → `http://localhost:8000` (`changeOrigin`, `secure:false`).
- So a frontend `fetch('/api/v1/...')` lands on the FastAPI container started by `make dev`.

---

## Gotchas

- **CORS allowlist.** The backend's `CORS_ALLOWED_ORIGINS` must include
  `http://localhost:4200`. It already does in CI and in the default dev config — only a problem
  if you've overridden it in a local `.env`.
- **OTP / MSG91.** Live OTP **submission** needs `MSG91_AUTH_KEY`. Every screen still
  **renders** without it (login form, OTP-entry screen, all routes) — only the live "verify OTP"
  network call fails without the key. You can review the entire UI without MSG91 configured.
- **Cold start is slow.** The shell's first compile after `pnpm install` can take a couple of
  minutes (Native Federation prepares the shared package import map). Subsequent rebuilds are fast.
- **First `pnpm install` runs native build scripts.** If you see `ERR_PNPM_IGNORED_BUILDS`
  (esbuild / @parcel/watcher not extracted), run
  `pnpm install --config.dangerously-allow-all-builds=true` once.
- **Stop everything cleanly.** Ctrl-C in Terminal 2 kills all 7 `ng serve` processes; Ctrl-C
  (or `make dev-down`) in Terminal 1 stops the backend stack.

---

## What "it works" looks like

Matching the green CI boot-smoke (`smoke-results.json`):

- `http://localhost:4200/` → landing renders (`app-landing` mounts, non-empty), HTTP 200.
- `http://localhost:4200/login` → real `mfe-auth` login form renders, HTTP 200.
- `http://localhost:4200/profile` → redirects to `/login` when unauthenticated (expected).
- Zero hard console errors / zero page errors at both 360px and 1280px widths.
