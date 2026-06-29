# serve.js per-request logging (dashboard-radar gap) — 2026-06-29

**Session:** `mesell-dev-log-monitor-infra-session-1`
**Branch:** `feature/dev-log-monitor/infra-serve-logging` (off develop `4a0664c`) -> PR #507 -> develop. Worktree `/tmp/mesell-wt/serve-logging`. Status IN REVIEW (founder gate, D1 — I do NOT merge feature/{name}/infra->develop).

## Problem
The dev-manager dashboard radar tails `.nexus/serve-<port>.log` per MFE/shell, but `serve.js` (`frontend/tools/boot-smoke/serve.js`) only ever logged its ONE startup banner line — no per-request logging. So the federation shell + 7 remotes produced zero runtime signal (unlike `uvicorn`, which logs every backend request). Sibling task `dev-log-monitor` (PR #504) builds the radar; this PR feeds it the serve-side signal.

## Fix (surgical, 1 file, Rs.0)
Single `res.on('finish')` hook at the TOP of the shared `serve(req, res)` handler. KEY insight: both the reverse-proxy branch (`/api|/health|/docs|/openapi.json`) and the static-SPA branch funnel through the same `serve()` function, so ONE hook at the top covers every response — no need to touch `proxy()` or the static path separately. The `finish` event fires for both (proxy `res.pipe` end and `res.end(data)`).

Line format: `[ISO-timestamp] METHOD /path STATUS_CODE duration_ms`, e.g. `2026-06-29T02:16:46.197Z POST /whatever 200 0ms`.

Implementation details that matter:
- Start time = `process.hrtime.bigint()` captured BEFORE any branching; duration = `Math.round(Number(hrtime.bigint()-start)/1e6)`.
- **Path only** — `req.url.split('?')[0]` — so query-param VALUES never leak into the log (explicit task constraint).
- **No new deps** — Node built-in `http` + `process.hrtime`.
- `console.log` -> stdout, already redirected to `.nexus/serve-<port>.log` by the manager.

## Validation
`node --check` clean. Live smoke against a throwaway dist (mktemp index.html+main.js, port 4399): `GET /main.js 200 4ms`, `GET /remoteEntry.json 200 1ms` (SPA-fallback 200, expected), `POST /whatever 200 0ms`, and `/path?secret=shhh` logged as `GET /path` (query stripped — leak guard confirmed).

## Reusable
- serve.js has ONE choke-point handler `serve()` — hook cross-cutting concerns (logging/metrics) there, at the top, not in the proxy/static branches.
- For a static dev server, SPA fallback means non-file GETs log `200` (they return index.html), not `404`. A true `404` only appears if `index.html` itself is missing (-> 500). The task spec's `GET /nonexistent 404` example does NOT match this server's SPA-fallback semantics — by design every unknown path is 200+index.html (anti-false-pass guarantee). Logging is honest about whatever status actually goes out.
- `.claude/` writes are guarded in the shared master checkout (bgIsolation) — had to persist memory via the git-plumbing route on a `chore/*-scribe` branch (Rule A). Direct Write/Edit to `.claude/agent-memory/**` is blocked from a non-isolated session.
