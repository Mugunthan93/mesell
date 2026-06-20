# Static Dev — memory-safe local boot for low-RAM machines

**Audience:** anyone booting the full 8-app Native Federation frontend on a machine that
cannot afford 8 concurrent `ng serve` watchers (e.g. the founder's 8 GB dev machine).
**Owner:** meesell-frontend-coordinator (Frontend Lead). **Validated:** 2026-06-14.

> TL;DR — `pnpm run start:all` (8 live `ng serve` processes) hangs an 8 GB machine. Instead:
> **build each app once**, then **serve the static `dist/<app>/browser` output** with the
> zero-dep `serve.js`. Eight static servers hold **~147 MB** total (vs **3–5 GB** for
> `start:all`). All shell routes render clean through federation: **verified all-clean**.

---

## 1. The problem — why `start:all` hangs an 8 GB machine

`pnpm run start:all` spawns all 8 Native Federation dev servers as live `ng serve`
processes. Each one holds a Node + esbuild incremental watcher resident in memory
(~0.4–0.8 GB each), so **8 of them = 3–5 GB** on top of VS Code + Claude. Adding the
backend (`make dev`) makes it worse.

Observed on the 8 GB machine under `start:all`:

| Metric            | Under `start:all`        |
|-------------------|--------------------------|
| Swap used         | **86% full (6.2 GB)**    |
| Swapouts          | **21M+**                 |
| Load average      | **8.6**                  |
| Result            | **machine HANGS**        |

---

## 2. The fix — build once, serve static

Build each app a single time, then serve the produced static bundle
(`dist/<app>/browser`) with the existing zero-dep `tools/boot-smoke/serve.js` (a tiny Node
http server with SPA fallback + CORS, ~15 MB RSS each). No esbuild watchers stay resident.

Measured steady state for the static path:

| Path                         | Resident memory      | Swap        | All 8 serve HTTP 200 |
|------------------------------|----------------------|-------------|----------------------|
| `start:all` (8 × `ng serve`) | **3–5 GB**           | fills, hangs | —                    |
| static serve (8 × `serve.js`)| **147 MB total**     | did not grow | ✅ yes               |

This is the sustainable local-dev path on low-RAM machines.

---

## 3. Two findings baked into the tooling

### 3a. `dev:true` builds never exit (the "build hung at 90m" symptom)

`ng build <app> --configuration development` sets `dev: true` on the native-federation
builder. It writes the full browser bundle + `remoteEntry.json` in **~3.5s**, but the
process then **never exits** — it drops into an incremental watch mode. This is exactly the
"build hung at 90m" symptom in the git history.

**Workaround (the WATCHDOG in `build-static.mjs`):** start the build, poll until both
`dist/<app>/browser/index.html` **and** `remoteEntry.json` exist, settle ~3s for trailing
chunk writes, then kill the build process tree and move on. **One build at a time** keeps it
memory-safe.

### 3b. EventSource console noise when serving a dev build statically

A dev build's embedded live-reload client opens an `EventSource`. When the dev bundle is
served **statically** (no live-reload server behind `serve.js`), the browser logs repeated:

```
EventSource's response has a MIME type ("text/html") that is not "text/event-stream".
```

This is a **benign artifact** of static-serving a dev build — it does not exist in a prod
build and does not affect rendering. `route-check.mjs` filters it (plus Angular dev-mode
chatter) so it cannot mask real errors.

---

## 4. Verified result

All **12 shell routes render clean** through federation against the static-served dev builds:

- **12/12**, zero console errors (after filtering the dev live-reload noise),
- zero uncaught exceptions, zero network failures,
- no `RemoteFailureComponent` fallback on any route.

No frontend code bugs were found. The only problem was the 8 GB memory hang — fixed by the
static-serve path above.

---

## 5. Fast local dev loop (copy-paste)

All commands run from `frontend/`. Node built-ins only — **zero new npm deps**.

### Step-by-step (one terminal, leave serve running in another)

```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend

# 1. Build all 8 apps once (watchdog, one at a time — memory-safe).
pnpm run dev:build-static
#    or a subset:  pnpm run dev:build-static mfe-auth mfe-pricing

# 2. Serve the built apps on 4200–4207 (leave this running; Ctrl-C stops all 8).
pnpm run dev:serve-static

# 3. In another terminal — assert all 12 routes render clean through federation.
pnpm run dev:check-routes
#    webkit instead of chromium:  pnpm run dev:check-routes webkit
```

Then open **http://localhost:4200**.

### One-shot (build → serve in background → check → report → stop)

```bash
cd /Users/mugunthansrinivasan/Project/mesell/frontend
pnpm run dev:static all
```

`dev:static all` exits **0** only if the route-check reports **12/12** clean, and stops the
background servers when it finishes. Other subcommands:

```bash
pnpm run dev:static build [apps...]   # build only (optionally a subset)
pnpm run dev:static serve             # serve only (foreground)
pnpm run dev:static check [engine]    # check only (chromium|webkit)
pnpm run dev:static up                # build, then serve in the foreground
```

### Port map (must match `apps/shell/public/federation.manifest.json`)

| Port | App           |
|------|---------------|
| 4200 | shell (`frontend` project, the host) |
| 4201 | mfe-pricing   |
| 4202 | mfe-export    |
| 4203 | mfe-onboarding|
| 4204 | mfe-dashboard |
| 4205 | mfe-catalog   |
| 4206 | mfe-auth      |
| 4207 | mfe-billing   |

---

## 6. When to use which path

| You want…                                              | Use                          |
|--------------------------------------------------------|------------------------------|
| Live HMR, ample RAM (16 GB+), actively editing code    | `pnpm run start:all` (RUNBOOK) |
| Boot the whole app on a low-RAM machine to *see* it    | `dev:build-static` + `dev:serve-static` |
| A quick "does federation still render 12/12?" gate     | `pnpm run dev:static all`    |

> Note: the static path serves a **built** snapshot — it does **not** hot-reload on source
> edits. Re-run `dev:build-static <app>` (subset is fine) after changing an app, then refresh.

---

## 7. Caveats

- **No live reload** on the static path — it serves a built snapshot (see §6 note).
- **`route-check.mjs` mocks auth** (`/api/v1/auth/refresh` + `/api/v1/auth/me`) so protected
  routes render without a live backend. It does **not** exercise real OTP / data flows — for
  that, use the `start:all` + `make dev` path in `RUNBOOK.md`.
- **Do NOT run `pnpm run start:all` on the 8 GB machine** — it is the exact thing this path
  exists to avoid.
