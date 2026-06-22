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
| `GET /api/log?project=<name>&slot=<N>` | tail (≤64 KB, ANSI-stripped) of the per-env log `.nexus/build-slot<N>-<name>.log` |

Both `project` and `slot` are validated against `^[A-Za-z0-9_.-]+$` (path-traversal
is rejected with `400`); `slot` must additionally parse as an int. `slot` is the
per-env key — three slots building the same project keep separate logs, and the
dashboard passes each build row's own `slot` so the viewer tails the right one.
`slot` omitted ⇒ slot 0. If the per-env log is absent the handler falls back to a
legacy project-only `.nexus/build-<name>.log` (so old logs still tail). A project
with no log at all returns `{"exists": false, ...}`.

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
      "ports": {
        "backend": 8000,
        "shell": 4200,
        "mfes": { "mfe-auth": 4201, "mfe-billing": 4202, ... }
      },
      "services": [
        { "role": "backend", "pid": 67328, "port": 8000,
          "alive": true, "health": "up" },
        { "role": "shell",   "pid": 67320, "port": 4200,
          "alive": true, "health": "up" }
        // ... one per tracked role
      ],
      "builds": [
        { "project": "mfe-pricing", "slot": 0, "status": "ok",
          "when": "2026-06-21T12:30:37Z", "duration_s": 30.0 }
        // ... most-recent-first, capped. Only THIS env's builds (joined by
        // (slot, project)); `slot` is echoed so the log viewer tails the
        // matching .nexus/build-slot<N>-<project>.log.
      ]
    }
    // ... one per worktree (union of git worktrees + slot registry)
  ]
}
```

### `health` values (the service dot colours)

| `health` | Meaning | Dot |
|---|---|---|
| `up` | process alive **and** the port answers HTTP (any status, incl. 404) | green |
| `dead` | a pid was tracked but the process is gone (crashed/exited) | red |
| `down` | no process tracked for this role (e.g. reusing the baseline backend), or alive-but-not-yet-answering (mid-serve) | amber |
| `unknown` | health not probed (CLI `status` only) | grey |

### Build history (`.nexus/build-history.jsonl`)

Each completed `ng build` appends one JSON line: `{project, worktree, slot,
start_iso, end_iso, status, duration_s}` (`status` ∈ `ok` | `failed`).
Append-only, generated, never committed (gitignored).

The dashboard joins rows onto an env card by **`(slot, project)`** — not by
project alone — so when slot 0, slot 1 and slot 2 all build `mfe-catalog`, each
build appears only on its own card. (Shell project name is `frontend`.) Rows
written before per-env keying lack `worktree`/`slot`; the reader normalises a
missing/unparseable `slot` to **slot 0** so old history still attaches to the
baseline card rather than vanishing.

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
