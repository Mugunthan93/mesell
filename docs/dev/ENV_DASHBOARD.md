# Dev Env Dashboard (`tools/meesell_env.py dashboard`)

A **read-only** web monitor over the dev-environment manager
([`ENV_MANAGER.md`](ENV_MANAGER.md)). One pane of glass for every build
environment running across all worktrees: live RAM/swap budget, per-env service
health, build history, and quick-launch links into each env for UI/UX testing.

> Stdlib-only Python 3 (`http.server.ThreadingHTTPServer` + `urllib`). No new
> dependencies. The dashboard **only reads** state — it never acquires the build
> lock and never triggers a build.

---

## What it shows

- **Top bar** — free-RAM dial (vs the 1500 MB floor), swap dial (vs the 70 %
  ceiling), a build-lock indicator (is an `ng build` in progress right now?),
  and a running-env count.
- **Env grid** — one card per worktree (the union of `git worktree list` and the
  slot registry, so reserved-but-idle worktrees still appear). Each card shows
  the slot badge, branch, **9 service status dots** (backend + shell + 7 MFEs)
  coloured by health, and quick-launch links.
- **Build history + log viewer** — each card lists recent builds for its
  projects; click a project to tail its `.nexus/build-<project>.log` in a modal.

It is **not** a control panel: there are no start/stop/rebuild buttons and no
built-in test runner — drive lifecycle through the CLI (`up`/`down`/`baseline`),
and drive UI testing through the [`agent-browser`](#browser-agent-integration)
skill against the quick-launch URLs.

---

## Usage

```bash
# Default port 7700 (outside every slot range: backend 8000-8090,
# shell 4200-4290, mfe 4201-4297).
python3 tools/meesell_env.py dashboard

# Custom port
python3 tools/meesell_env.py dashboard --port 7800
```

Open <http://127.0.0.1:7700/>. The page polls `/api/state` every 3 s. `Ctrl-C`
to stop. The server can run from any worktree copy — it discovers the baseline
(`develop`) tree's `.nexus/` the same way the rest of the tool does, so it always
reflects the **shared** live state.

### Endpoints

| Route | Returns |
|---|---|
| `GET /` | the self-contained SPA (`tools/env_dashboard/index.html`) |
| `GET /api/state` | the full JSON model (see below) |
| `GET /api/log?project=<name>` | tail (≤64 KB, ANSI-stripped) of `.nexus/build-<name>.log` |

`project` is validated against `^[A-Za-z0-9_.-]+$` (path-traversal is rejected
with `400`). A project with no log yet returns `{"exists": false, ...}`.

---

## Safety properties

- **Never builds, never locks.** The build-lock state is read via a *non-blocking*
  `flock` probe on a read-only file descriptor — if the probe would block, a
  build is running; the dashboard reports it and moves on. It never holds the
  lock.
- **Never blocks on a mid-build slot.** Health probes use `urllib` with a **1 s**
  timeout and are **cached for 3 s** per port, so a slot that is mid-build (port
  not yet answering) cannot stall the page.
- **Shared code path.** `/api/state` and the CLI `status` command both call
  `collect_dashboard_state()` — one model, two surfaces. (`status` passes
  `probe=False` to stay instant.)
- **Footprint.** A single `ThreadingHTTPServer`; idle RAM is a few MB.

---

## `/api/state` shape

```jsonc
{
  "free_mb": 1557,            // free RAM (pages free+inactive+speculative)
  "min_free_mb": 1500,        // the budget floor
  "swap_pct": 71.7,           // swap used %
  "max_swap_pct": 70.0,       // the budget ceiling
  "build_lock_held": false,   // is an ng build running anywhere right now?
  "env_count": 1,             // number of running envs tracked
  "generated_iso": "2026-06-21T13:51:18Z",
  "envs": [
    {
      "worktree": "mesell",           // worktree dir basename
      "slot": 0,                      // assigned slot (null if unreserved)
      "branch": "develop",
      "path": "/Users/.../mesell",
      "exists": true,                 // present in `git worktree list`
      "running": true,                // has tracked live processes
      "drift": false,                 // a reserved port is LISTENING but the
                                      // manager tracks no process for it
                                      // (running OUTSIDE the manager)
      "ports": {
        "backend": 8000,
        "shell": 4200,
        "mfes": { "mfe-auth": 4201, "mfe-billing": 4202, ... }
      },
      "services": [
        // tracked: came from env-state. health is a LIVE port probe, so a stale
        // pid on a silent port reads down/dead (never a false up).
        { "role": "backend", "pid": 67328, "port": 8000,
          "alive": true, "health": "up", "tracked": true, "drift": false },
        // drift: this port is LISTENING on the slot's block but no tracked
        // process owns it — surfaced so it isn't silently omitted. pid is null
        // (we don't know it); alive is false (no tracked pid); health is "up".
        { "role": "mfe-catalog", "pid": null, "port": 4203,
          "alive": false, "health": "up", "tracked": false, "drift": true }
        // ... one per tracked role, plus one per untracked-but-listening port
      ],
      "builds": [
        { "project": "mfe-pricing", "status": "ok",
          "when": "2026-06-21T12:30:37Z", "duration_s": 30.0 }
        // ... most-recent-first, capped
      ]
    }
    // ... one per worktree (union of git worktrees + slot registry)
  ]
}
```

### `health` values (the service dot colours)

`health` is **derived from a live probe, not from the tracked PID** — a service
killed and relaunched outside the tool leaves a stale PID, so the verdict comes
from whether the **port actually answers**.

| `health` | Meaning | Dot |
|---|---|---|
| `up` | the port answers HTTP (any status, incl. 404) — live, regardless of whether the recorded PID still matches | green |
| `dead` | the probe is inconclusive (no known port for the role) **and** a tracked PID is gone (crashed/exited) | red |
| `down` | a known port that is **not** answering (nothing listening / silent), or no process tracked and no live PID | amber |
| `unknown` | health not probed (only when `collect_dashboard_state(probe=False)`) | grey |

### `drift` / `tracked` (reconciliation fields)

Each env carries a top-level `drift` boolean, and each service carries `tracked`
and `drift` booleans:

- `tracked: true` — the service comes from `env-state.json` (a process the manager
  started). Its `health` is the live-probe verdict above.
- `tracked: false, drift: true` — **nothing in `env-state.json` records this
  port, but it is LISTENING** within the slot's reserved block (a serve.js /
  uvicorn started outside the manager, or a `down` that crashed mid-teardown).
  `pid` is `null`, `alive` is `false`, `health` is `up` (the port answers).
- An env's `drift: true` ⇔ at least one of its services is `drift: true`.

Drift is detected with a cheap `socket.connect_ex` listen-probe (sub-second, 3 s
cached) over each reserved slot's expected ports, so it never blocks a mid-build
slot. It lets the dashboard/`status` say "running outside the manager" instead of
silently omitting an untracked-but-alive service.

### Build history (`.nexus/build-history.jsonl`)

Each completed `ng build` appends one JSON line: `{project, start_iso, end_iso,
status, duration_s}` (`status` ∈ `ok` | `failed`). Append-only, generated, never
committed (gitignored). The dashboard reads the newest rows per project and joins
them onto the matching env card (shell project name is `frontend`).

---

## Browser-agent integration

The dashboard is built for the [`agent-browser`](../../.claude/skills/agent-browser)
skill to navigate, assert, and screenshot. Every meaningful element carries a
**stable `data-testid`** so selectors never depend on layout or text.

### `data-testid` catalog

| `data-testid` | Element |
|---|---|
| `topbar` / `title` | header bar / page title |
| `gauge-ram`, `ram-value`, `ram-bar` | free-RAM dial |
| `gauge-swap`, `swap-value`, `swap-bar` | swap dial |
| `build-lock`, `build-lock-text` | build-lock pill |
| `env-count`, `env-count-value` | running-env count |
| `env-grid` | the card container |
| `empty-state` | shown when no envs exist |
| `env-card` | one per worktree; carries `data-worktree` + `data-slot` attrs |
| `slot-badge` | the slot number badge on a card |
| `env-worktree`, `env-branch`, `env-tag` | worktree name / branch / running\|idle\|missing tag |
| `svc-dots` | the dot row |
| `svc-<role>` | a service chip, e.g. `svc-backend`, `svc-mfe-pricing` |
| `svc-dot-<role>` | the coloured dot for that role (class `up`/`down`/`dead`) |
| `quicklinks` | the link row |
| `link-shell`, `link-api-docs`, `link-catalogs`, `link-pricing` | quick-launch anchors |
| `build-history`, `build-row`, `build-log-link` | build list, row, clickable project |
| `log-modal`, `log-modal-title`, `log-modal-body`, `log-modal-close` | log viewer modal |
| `last-update`, `footer` | poll timestamp / footer |

### Typical agent flow

```bash
agent-browser open http://127.0.0.1:7700/
agent-browser snapshot                       # see gauges + cards
# assert the live env card renders all 9 service dots as 'up':
agent-browser eval "document.querySelector('[data-testid=\"env-card\"][data-worktree=\"mesell\"]').querySelectorAll('.svc .dot.up').length"
# open a build log and screenshot it:
agent-browser eval "openLog('mfe-pricing')"
agent-browser screenshot dashboard.png
```

To launch into an env for UI/UX testing, follow a card's quick-launch link
(`link-shell` → the shell, `link-pricing` → `/pricing`, `link-api-docs` →
FastAPI `/docs`) and continue the browser-agent session there.
