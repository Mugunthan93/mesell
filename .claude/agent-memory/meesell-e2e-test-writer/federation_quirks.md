# Federation quirks — shell→remote bugs observed live

The live-observed module-federation gotchas that make E2E flaky or that are real
product bugs. Append every recurrence; a `test.fixme()` should always point to an
entry here.

## Seeded from prior project memory (2026-06-22)
- **Auth-singleton logout regression:** shell→remote navigation logged the user out
  when `@mesell/core` (owns the in-memory access token) was shared with an EMPTY
  version + `strictVersion:false` → Native Federation dedup failed → >1 AuthService
  instance → the remote's token was null → authGuard → /login. Fix shipped (FED-1,
  PR #373): explicit identical `version` + singleton across all remotes. The
  `logout-guard` flow is the sentinel — assert the session survives shell→remote nav.
- **Stale remote bundle:** a remote serving an old build (worktree-port pinning, or
  `no-cache` instead of `no-store` on unhashed federation runtime files) makes
  "fixes don't show / logout persists." Always run against a freshly built stack;
  on the very first load an incognito/hard-reload may be needed to flush the tab cache.
- **`federation.manifest.json` port pinning:** committing worktree ng-serve ports
  into the manifest makes the :4200 shell load the wrong worktree's code. Local dev
  ports are shell :4200 + remotes :4201–4207.
