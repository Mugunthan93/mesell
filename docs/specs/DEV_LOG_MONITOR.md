# DEV_LOG_MONITOR — design spec

> **Status:** DESIGN SPEC (not built). Owner: `meesell-infra-builder`.
> **Scope:** **dev-only** live log monitoring + "listening" for the local dev stack,
> delivered as an extension of the read-only env-dashboard
> ([`tools/meesell_env.py dashboard`](../dev/ENV_DASHBOARD.md), port `:7700`).
> **Ethos:** stdlib-only Python 3, RAM-light (in-memory ring buffers, NO log DB /
> ELK), reuses the existing `/api/log` tail pattern + `data-testid` convention.
> **Hard rule:** secrets are redacted before display *or* storage; this whole feature
> is gated off in any non-dev build. Prod uses real observability (Langfuse), never this.

---

## 0. Why

This dev session repeatedly lost diagnostic round-trips (OTP `404`, catalog-logout,
stale federation bundles, refresh-token storms) because there was **no live view of
what the running stack emitted**. The fix is to give the existing dashboard a *live
log stream + an error radar that listens for the signatures that bite us*, so a human
(or a browser-agent) sees the failure the moment it happens instead of reconstructing
it from a curl loop.

This spec is **additive** to the dashboard. It does not change the dashboard's safety
properties: it still **never builds, never holds the build lock**.

---

## 1. Premise correction (read before estimating effort)

The brief states *"today only the backend logs to a file; the serves don't."* That is
**not** the live state. Verified against `tools/meesell_env.py`:

| Process | Spawn fn | Already logs to | Keyed by |
|---|---|---|---|
| FastAPI uvicorn | `serve_backend()` (L846) | `.nexus/backend-<port>.log` | **port** |
| shell + each MFE (`serve.js`) | `serve_static()` (L822) | `.nexus/serve-<port>.log` | **port** |
| `ng build` (one-shot) | `ng_build()` (L764) | `.nexus/build-<project>.log` | project name |

So the real gaps are **three**, and the spec is sized against *these*, not against
"add file logging from scratch":

1. **Naming is port-keyed, not service-keyed.** `serve-4203.log` tells you nothing about
   *which* MFE it is without re-deriving the slot→port map. The merged timeline needs a
   stable, human-readable `<service>` key (`backend`, `shell`, `mfe-pricing`, …).
2. **`/api/log` only serves BUILD logs** (`build-<name>.log`). Runtime serve/backend logs
   are written but **not exposed** by any endpoint.
3. **Celery, Postgres, Valkey are NOT spawned by the tool.** The dashboard tracks
   "backend + shell + 7 MFEs" (9 roles) and that is *all the tool owns*. Celery workers,
   brew-Postgres (`:5432`) and Valkey (`:6379`) run out-of-band. We can *tail* their logs
   **if** they write to a predictable path, but the tool can't redirect a process it
   didn't start. This is handled in §3.4 as a best-effort, opt-in tail — not a guarantee.

---

## 2. V1 vs V2 (the split)

| | **V1 — centralized server-log stream + error radar** | **V2 — browser console/network capture** |
|---|---|---|
| What | Tail + merge every dev-process log into a live timeline; pattern-match error signatures into a radar. | FE posts its own `console.error` + failed `fetch`/XHR to a dev-only `/devlog` endpoint; same radar surfaces them. |
| Source | server-side files the tool already controls (`.nexus/*.log`). | the browser (client-side — where most real bugs here live). |
| New endpoints | `GET /api/logs`, `GET /api/logstream` (SSE), `GET /api/radar`. | `POST /devlog` (FLAG-GATED, dev-only). |
| Touches | `tools/meesell_env.py` + `tools/env_dashboard/index.html` only. | adds a **backend** `/devlog` route + a tiny FE bootstrap shim → **cross-lead handoff**. |
| Risk | low — read-only over local files. | higher — a write endpoint + a FE code path that must NEVER ship to prod. |
| Decision | build in this workstream. | **gated on founder sign-off** (§7) — spec'd, not built. |

**V1 ships first and stands alone.** V2 is purely additive: it just becomes one more
*source* feeding the same radar + timeline, so the V1 UI is built source-agnostic.

---

## 3. V1 — centralized server-log stream + error radar

### 3.1 Foundation: a service-keyed log registry (`meesell_env.py`)

Do **not** rip out the existing per-port log files — keep them (they are the source of
truth on disk). Add a thin **name→path resolver** so the rest of the feature speaks in
`<service>` names, and make every spawned process discoverable by name.

**Component:** `meesell_env.py`.

1. **Add a canonical service-name helper.** Given the live slot/port model already in
   `collect_dashboard_state()`, derive the service key for a port:
   - `backend` ← `ports.backend` (e.g. `:8000`)
   - `shell` ← `ports.shell` (e.g. `:4200`)
   - `mfe-<name>` ← `ports.mfes[name]` (e.g. `mfe-pricing` ← `:4206`)

   Surface this as a function `service_log_index(env) -> dict[str, Path]` that maps each
   service key to its on-disk log:
   - `backend` → `.nexus/backend-<port>.log`
   - `shell` / `mfe-*` → `.nexus/serve-<port>.log`
   - (build logs stay separate — `build-<project>.log`, already exposed.)

2. **Optionally** write a stable symlink/alias per service for human convenience:
   `.nexus/logs/<service>.log` → the real `.nexus/<kind>-<port>.log`. This is the
   "predictable `.nexus/logs/<service>.log`" the brief asks for, realised as a **symlink
   farm over the existing files** rather than a second write target (no double-writing,
   no extra RAM, no log duplication). Created at `up`/`baseline up` time; pruned at
   `down`/`gc`. **Decision flag DF-1** (§7): symlink farm vs. pure in-memory resolver —
   recommend symlink farm (zero cost, makes `tail -f .nexus/logs/backend.log` work for a
   human with no tooling).

3. **No change to *what* is captured.** uvicorn already runs with `--reload` and inherits
   `stdout+stderr` into its file; `serve.js` already pipes both. The spec adds **naming +
   exposure**, not new capture.

> **Surgical-change note (Engineering Discipline #2):** this touches only the dashboard
> code path + log-naming helpers in `meesell_env.py`. It must NOT change build behaviour,
> the build lock, slot assignment, or serve/proxy logic.

### 3.2 Live stream + merged timeline (dashboard)

**Component:** `tools/meesell_env.py` (new endpoints) + `tools/env_dashboard/index.html`
(new tab/panel).

**New endpoints** (mirror the existing `/api/log` guards — `^[A-Za-z0-9_.-]+$` validation,
ANSI strip, byte-bounded read):

| Route | Returns |
|---|---|
| `GET /api/logs?service=<name>&since=<offset>&n=<lines>` | poll-tail of one service's runtime log; `since` = byte offset for incremental fetch (so the client only pulls new bytes), `n` = max lines fallback. Each line pre-parsed into `{ts, service, level, msg}` after **redaction (§6)**. |
| `GET /api/logstream` (SSE) | a single `text/event-stream` that merges *all* services, newest-appended-last, each event = one redacted parsed line. This is the "combined timeline". |
| `GET /api/radar` | the current error-radar counters + recent alerts (see §3.3). |

**Transport choice — SSE vs poll-tail (DF-2, §7):**
- **Poll-tail** (`/api/logs?since=`) is the safest reuse of the existing pattern — the
  dashboard already polls `/api/state` every 3 s; add a 1 s tail poll per open log.
  Zero new server machinery, trivially stdlib.
- **SSE** (`/api/logstream`) is nicer for a live merged feed but needs a long-lived
  `ThreadingHTTPServer` connection + a tail thread per client. Still stdlib
  (`BaseHTTPRequestHandler` can stream), but it's more moving parts.
- **Recommendation:** ship **poll-tail first** (matches dashboard ethos, lowest risk);
  add SSE as a follow-up only if 1 s polling feels laggy. The UI is written against a
  normalized line shape so swapping transports later is invisible to the view.

**The combined timeline view** (new panel/tab in `index.html`, default-collapsed so the
existing env-grid is unchanged on load):
- One scrolling pane, newest at bottom, auto-follow toggle.
- **Per-service colour** (reuse the dot palette: backend / shell / each mfe gets a stable
  hue; legend chips double as toggles to show/hide a service).
- **LEVEL filter** — `ERROR` / `WARN` / `INFO` pill toggles. Level is parsed from the
  line (uvicorn/Python `logging` emit `LEVEL` tokens; `serve.js` lines are tagged `INFO`
  unless they match an error signature → upgraded to `ERROR`/`WARN`).
- **Text search** — a debounced client-side filter box over the buffered lines.
- **In-memory ring buffer** — the client holds the last *N* (e.g. 2 000) lines; the
  server holds nothing beyond the file it already has on disk + a small per-service
  tail cursor. No log DB.

**`data-testid` additions** (extend the existing catalog in `ENV_DASHBOARD.md`):

| `data-testid` | Element |
|---|---|
| `logs-tab` / `logs-panel` | the timeline tab toggle / its container |
| `log-filter-level-error`, `-warn`, `-info` | level filter pills |
| `log-filter-service-<name>` | per-service show/hide chip (e.g. `log-filter-service-mfe-pricing`) |
| `log-search` | the text-search input |
| `log-follow-toggle` | auto-scroll-to-bottom toggle |
| `log-line` | one rendered line; carries `data-service` + `data-level` attrs |
| `log-stream-status` | connected / polling / stalled indicator |

### 3.3 Error radar (the "listening" payoff)

**Component:** a small pattern-matcher in `meesell_env.py` (server-side, so a line is
classified once) + a radar panel in `index.html`.

The radar is a set of **named detectors**, each a regex (or small predicate) + a
**rolling window counter** (in-memory, e.g. count in the last 60 s). When a detector's
window count crosses a threshold it emits an **alert** (a row with severity, the matched
sample line — *redacted* — service, and the count). The radar is the first thing the eye
hits: a row of counters that go red when something is wrong.

Seed detectors (the signatures that have actually bitten this stack — from
`MEMORY.md` / the master-session findings):

| Detector | Signature (illustrative) | Why it matters |
|---|---|---|
| `auth-401-storm` | ≥3× `401` on `/auth/me` or `/auth/refresh` within 60 s | the refresh-storm → forced-logout bug |
| `python-traceback` | `Traceback (most recent call last):` … `Error:` | backend crash / 500 root cause |
| `http-500` | ` 500 ` in an access line, or `Internal Server Error` | server fault (e.g. the pricing-calc INSERT 500) |
| `csp-violation` | `Content-Security-Policy` / `Refused to load` (V2 source) | the GIS/CSP whitelist gaps |
| `login-redirect` | repeated `→ /login` / authGuard redirect lines | the federation-singleton logout regression |
| `federation-singleton` | Native-Federation `singleton`/`shared` mismatch warnings | the `@mesell/core` version-drift logout bug |
| `route-404` | ` 404 ` on a `/api/...` path (e.g. `/auth/google/verify`) | the OTP/google-verify 404 confusion |

Each detector is **data-driven** (a list of `{name, pattern, window_s, threshold,
severity}` dicts) so adding a new signature is a one-line edit, not new code.

`GET /api/radar` returns:
```jsonc
{
  "generated_iso": "2026-06-21T14:00:00Z",
  "counters": [
    { "name": "auth-401-storm", "window_s": 60, "count": 3,
      "threshold": 3, "severity": "error", "firing": true,
      "sample": "WARNING 401 GET /api/v1/auth/me",   // redacted
      "service": "backend" }
    // ... one per detector
  ]
}
```

**Radar UI** (`data-testid`):

| `data-testid` | Element |
|---|---|
| `radar-panel` | the radar strip |
| `radar-counter-<name>` | one detector counter; class `firing` when over threshold |
| `radar-count-<name>` | the numeric count |
| `radar-alert` | a fired-alert row (e.g. "3× 401 on /auth/me in 60s") |

Counters that are firing pulse (reuse the existing build-lock `pulse` keyframe).

### 3.4 Best-effort tail of out-of-band processes (Celery / Postgres / Valkey)

The tool does not start these, so it cannot redirect their output. The spec offers a
**best-effort, opt-in** tail so they can still appear on the timeline *when* they log to
a known path:

- **Celery** — if a worker is started via the documented dev command into
  `.nexus/celery-<n>.log`, register it under service key `celery` and tail it like any
  serve log. (The dev-command/`/mesell:dev` runbook should be updated to redirect Celery
  there — a small docs follow-up, noted not built.)
- **Postgres / Valkey** — brew services log to their own dirs (e.g.
  `/opt/homebrew/var/log/postgresql@16.log`, `/opt/homebrew/var/log/valkey.log`) and the
  K3s pods log via `kubectl logs`. For local dev, the spec allows an **optional config
  list** of extra log paths (`.nexus/logmonitor.json` → `{ "extra": {"postgres": "/opt/.../postgresql@16.log"} }`).
  If the path is missing/unreadable, the service simply shows as "no log" (same as a
  not-built MFE today). **Never** shell out to `kubectl logs` from the dashboard — that
  could block and is out of the read-local-files ethos. **DF-3** (§7): ship the optional
  extra-path config, or defer Postgres/Valkey tailing entirely to V1.5? Recommend ship the
  config but leave it empty by default (zero behaviour change unless a dev opts in).

---

## 4. V2 — browser console/network capture (the client-side bug-catcher)

> **V2. FLAG-GATED. DEV-ONLY. NEVER IN THE PROD BUILD.** Requires founder sign-off (§7).

Most real bugs in this stack are client-side (stale bundles, federation logout, CSP).
Server logs can't see a browser `console.error` or a request that failed *before* it
reached the proxy. V2 closes that gap.

**Shape:**

1. **FE bootstrap shim** (frontend lead — cross-lead handoff). A tiny dev-only module,
   loaded ONLY when a build-time flag is set (e.g. `FEATURE_DEV_LOG_MONITOR` /
   `import.meta.env`-style dev guard), that:
   - wraps `window.console.error`/`.warn` and `window.onerror` /
     `window.onunhandledrejection`,
   - patches `fetch` (and optionally `XMLHttpRequest`) to record failed/4xx/5xx requests
     (method, path, status, duration — **never** the request/response *body*, never
     headers),
   - POSTs a small batched payload to `/devlog`.
   It MUST be **tree-shaken out of any non-dev build** — gated behind the dev flag so the
   production bundle contains zero bytes of it (mirrors the `FEATURE_GOOGLE_AUTH_ENABLED`
   flag-gating discipline already in the repo).

2. **`POST /devlog` endpoint** (backend lead — cross-lead handoff). Dev-only:
   - mounted ONLY when an env flag is set (default OFF), exactly like
     `FEATURE_GOOGLE_AUTH_ENABLED` is mounted per-namespace (dev only; staging/prod NEVER);
   - accepts `{events: [{ts, kind: "console"|"error"|"netfail", level, msg, path?, status?}]}`,
     applies **the same §6 redaction** server-side (defence in depth — never trust the
     client to have redacted), and appends to `.nexus/devlog.jsonl` (capped, rotating)
     **or** straight into the radar's in-memory ring;
   - rate-limited + size-capped so a runaway FE loop can't fill the disk;
   - returns `204`. No auth required in dev (it's localhost-only), but it MUST refuse to
     mount in any non-dev `APP_ENV`.

3. **Surfaced in the same radar + timeline** — `/devlog` events become service key
   `browser`, flow through the same detectors (so `csp-violation`, `login-redirect`,
   `route-404` now also catch *client-observed* instances), and render on the timeline
   with their own colour.

**Why V2 is a separate gate:** it introduces (a) a **write** endpoint and (b) a FE code
path that must never reach production. Both are blast-radius items that need explicit
founder approval on the flag-gating contract before any code is written.

---

## 5. Component → owner map (and cross-lead handoffs)

| Piece | Component / file | Owner | V1/V2 |
|---|---|---|---|
| Service-name log registry / symlink farm | `tools/meesell_env.py` | `meesell-infra-builder` | V1 |
| `/api/logs` (poll-tail) + `/api/logstream` (SSE) | `tools/meesell_env.py` | `meesell-infra-builder` | V1 |
| `/api/radar` + detector table | `tools/meesell_env.py` | `meesell-infra-builder` | V1 |
| Redaction filter (server-side) | `tools/meesell_env.py` | `meesell-infra-builder` | V1 (+ reused in V2) |
| Timeline panel, level/service filters, search, follow | `tools/env_dashboard/index.html` | `meesell-infra-builder` | V1 |
| Radar panel | `tools/env_dashboard/index.html` | `meesell-infra-builder` | V1 |
| `data-testid` catalog update + dashboard docs | `docs/dev/ENV_DASHBOARD.md` | `meesell-infra-builder` | V1 |
| Celery → `.nexus/celery-*.log` redirect | dev runbook / `/mesell:dev` | `meesell-infra-builder` (docs) | V1 (opt-in) |
| **FE dev console/network shim (flag-gated)** | `frontend/` bootstrap | **`meesell-frontend-coordinator`** (handoff) | **V2** |
| **`POST /devlog` dev-only endpoint (flag-gated)** | `backend/app/` | **`meesell-backend-coordinator`** (handoff) | **V2** |

The two V2 rows are **cross-lead handoffs** authored via the decentralized memo protocol
(`.claude/agent-memory/meesell-infra-builder/handoff_<topic>.md` + an Inter-lead-requests
row on `feature_board_infra.md`) **only after** the founder signs off §7.

---

## 6. NON-NEGOTIABLE — secret redaction

Every line is passed through a **redaction filter before it is parsed, displayed, *or*
stored** — at the server boundary, in *both* the V1 file-tail path and the V2 `/devlog`
ingest path (defence in depth; the client's own redaction is never trusted). This is a
hard never-echo-creds rule.

Mask, at minimum, these patterns (replace the sensitive span with `***REDACTED***`):

- `Authorization:` headers and any `Bearer <token>` → `Bearer ***`
- JWTs — the `xxxxx.yyyyy.zzzzz` three-segment base64url shape
- OTP codes — `otp`/`code` field values, and any standalone 4–8 digit code near an
  `otp`/`verify` context (the dev bypass `000000` is itself a secret-shaped value — mask it)
- email addresses → keep the domain, mask the local part (`a***@gmail.com`) so account-link
  debugging is still possible without leaking PII
- phone numbers (`+91` + 10 digits) → mask the middle
- known secret env-var names if ever echoed (`JWT_SECRET`, `MSG91_AUTH_KEY`,
  `GEMINI_API_KEY`, `RAZORPAY_KEY_SECRET`, `refresh-token-pepper`, …) → value masked
- cookie values (`set-cookie:` / `cookie:`) → masked

Implementation: a single ordered list of `(compiled_regex, replacement)` pairs applied in
`meesell_env.py`, reused by every ingest path. The redaction list is the **one** place
patterns live — adding a pattern is a one-line edit. **DF-4** (§7): founder ratifies the
redaction list as the canonical policy (especially email-partial vs full-mask, and whether
to log paths-with-IDs at all).

> The existing `/api/log` build-log tail does **not** redact today (build logs don't carry
> creds). This spec routes the *new* runtime-log + radar + devlog paths through redaction
> unconditionally. Recommend retrofitting the build-log path through the same filter too,
> for uniformity (cheap, additive).

---

## 7. Founder decisions flagged

| ID | Decision needed | Recommendation |
|---|---|---|
| **DF-0 (gate)** | **Approve V2 at all** — a dev-only `POST /devlog` write endpoint + a flag-gated FE shim that must NEVER ship to prod. | Approve V2 *as flag-gated, dev-only, default-OFF*, mounted exactly like `FEATURE_GOOGLE_AUTH_ENABLED` (dev only; staging/prod NEVER until/unless V1.5 revisits). |
| **DF-1** | Service-log naming: symlink farm `.nexus/logs/<service>.log` vs pure in-memory resolver. | Symlink farm — ₹0, makes `tail -f` work for a human with no tooling. |
| **DF-2** | Transport: poll-tail (`?since=`) vs SSE for the live stream. | Poll-tail first (matches dashboard ethos / lowest risk); SSE only if laggy. |
| **DF-3** | Tail Postgres/Valkey via an optional extra-path config now, or defer to V1.5. | Ship the config but default-empty (zero behaviour change unless a dev opts in). |
| **DF-4** | Ratify the §6 redaction list as canonical policy (esp. email partial-mask + whether to keep IDs in paths). | Ratify as written; email partial-mask (keep domain) to preserve account-link debuggability. |
| **DF-5** | V2 `/devlog` flag name + which lead owns the FE shim vs the BE route. | `FEATURE_DEV_LOG_MONITOR` (BE env flag) + a matching FE build-time dev guard; FE shim → frontend-coordinator, route → backend-coordinator, both via memo handoff. |

**Nothing in V2 (and no `/devlog` write endpoint, and no FE shim) is built until DF-0 is
approved.** V1 (the read-only server-log stream + radar + redaction) is self-contained
and within `meesell-infra-builder`'s tooling scope; it can proceed on founder go without
DF-0, gated only by DF-1..DF-4.

---

## 8. Constraints honoured

- **Stdlib only.** New endpoints use the same `BaseHTTPRequestHandler` /
  `ThreadingHTTPServer` already in `meesell_env.py`; redaction + detectors use `re`. No
  new dependency, no ELK, no log DB.
- **RAM-light.** Server holds only per-service tail cursors + small rolling-window deques
  for the radar; the client holds a bounded ring buffer. Idle footprint stays "a few MB"
  like the current dashboard.
- **Read-only / never builds / never locks.** All V1 endpoints read local files; the
  dashboard's existing safety properties are untouched.
- **Dev-only, never prod.** Prod uses real observability (Langfuse). The whole feature —
  and *especially* the V2 `/devlog` endpoint + FE shim — is flag-gated OFF outside dev.
- **Additive UI.** The timeline + radar are a new (default-collapsed) tab/panel; the
  existing env-grid renders unchanged on load, so no `data-testid` is removed.

---

## 9. References

- [`docs/dev/ENV_DASHBOARD.md`](../dev/ENV_DASHBOARD.md) — the dashboard this extends
  (endpoints, `/api/state` shape, `data-testid` catalog, safety properties).
- `tools/meesell_env.py` — `serve_static` (L822), `serve_backend` (L846), `ng_build`
  (L764), `_serve_log` (L1264), `_DashboardHandler` (L1219), `collect_dashboard_state`
  (L522). The existing `/api/log` guards (`_PROJECT_RE`, ANSI strip, `_LOG_TAIL_BYTES`)
  are the template the new endpoints copy.
- `tools/env_dashboard/index.html` — the SPA the new panels are added to.
- CLAUDE.md Decision #14 (in-memory access JWT; refresh in HttpOnly cookie — informs which
  credential shapes the redaction filter must catch) and the
  `FEATURE_GOOGLE_AUTH_ENABLED` flag-gating amendment (the per-namespace flag-mount
  pattern V2's `/devlog` mirrors).
</content>
</invoke>
