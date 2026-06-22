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

## QA Wave 1 — VERIFIED LIVE (2026-06-22)

- **`[testId]` passthrough silently no-ops when the SHELL ships a STALE shared
  `@mesell/ui-kit` singleton (HIGH-VALUE).** During Wave-1 codify the slot-1 shell
  was COPIED from the baseline (slot-0) shell dist built at 22:53 — BEFORE #381 added
  the `[testId]` signal-input to the 5 ui-kit wrappers (input/button/otp-input/
  textarea/file-upload). Native Federation shares `@mesell/ui-kit` as a singleton
  hosted by the SHELL, so EVERY remote loaded the stale ui-kit → every
  `[testId]="'…'"` binding compiled against a wrapper with no `testId` input →
  produced NO `data-testid` attribute. Symptom: `getByTestId('login-phone-input')`
  timed out even though the rebuilt mfe-auth bundle contained the string, while a
  LITERAL `data-testid=` (login-google-host) DID render. FIX: rebuilding the remotes
  is NOT enough — you must REBUILD THE SHELL too (the singleton host) so its shared
  ui-kit chunk carries the new input. Practically: `meesell_env.py up --mfe <list>`
  only rebuilds the shell if git sees a shell diff; when running E2E against the
  CURRENT develop while the baseline is older, force a shell rebuild (`ng build
  frontend`) and swap it into the slot dist (preserving the per-env manifest). This
  is the federation analogue of "stale remote bundle" but for the SHARED LIB.

- **Single-use refresh-token rotation BREAKS shared `storageState` across tests
  (CRITICAL for auth setup).** Decision #14/FE-D5 + the iam Lua rotation make the
  refresh token SINGLE-USE: every POST /auth/refresh DELetes the old allowlist entry
  and SETs a new one. The shell's APP_INITIALIZER `bootstrap()` ALWAYS refreshes on
  every page load (it can't carry the in-memory access token). Consequence: the
  standard Playwright pattern (auth.setup saves ONE storageState.json → all flows
  reuse it) makes only the FIRST flow's first navigation succeed (refresh→200); the
  SECOND flow reusing the SAME saved cookie gets refresh→**401**→/login, because the
  cookie was already rotated away. VERIFIED: ctxA(/dashboard)=200 authed, ctxB(same
  file, /dashboard)=401 /login. WORKING PATTERN: a worker-scoped fixture that logs in
  ONCE per worker into a SHARED browser context and gives each test a fresh PAGE in
  that SAME context — the rotating cookie stays valid within the one context.
  VERIFIED: login once → 4 sequential pages on different routes all stayed authed
  (refresh 200 each). With `--workers=1` (required for RAM) this is exactly ONE OTP
  login for the whole authed suite (also dodges the OTP-send rate limit below). The
  scaffold's `auth.setup.ts` + project `storageState` is KEPT (it produces a real
  login proof) but the authed FLOWS use the shared-context fixture.

- **OTP send is rate-limited 3/3600s PER IP (not per phone).** `meesell:rl:route:
  otp_send:ip:127.0.0.1:3600` in Valkey DB0. Even a fresh phone is 429'd once the IP
  budget is spent (auth-builder D2: anonymous routes key per-IP). OTP verify is
  10/3600s. Debugging the login flow exhausts this fast. Mitigation for a test RUN:
  clear `meesell:rl:*` keys in Valkey DB0 right BEFORE the run (a dev-env reset, NOT
  in the spec — keeps specs infra-free). One worker + one login keeps the actual run
  under budget.

## PRODUCT BUGS found live during Wave-1 codify (file to qa-coordinator → owners)

- **EXPORT productId is a HARDCODED PLACEHOLDER (mfe-export).** `export.component.ts`
  `onGenerate()` line ~431: `const productId = 'current-product-id';` — it NEVER reads
  `ActivatedRoute.snapshot.params['id']` (the `ngOnInit` comment admits it: "Route
  param reading would go here… For V1: product ID read from ActivatedRoute in
  onGenerate()" — but it wasn't). VERIFIED LIVE: clicking `export-trigger` on
  /catalogs/{realPid}/export POSTs `/api/v1/products/current-product-id/export-xlsx`
  → 422 (validation). The `ready` state + `export-download` link are UNREACHABLE
  through the UI regardless of the real product. Owner: meesell-frontend-coordinator
  → angular-component-builder (read the route param). This is the placeholder the
  Wave-1 brief flagged.

## ENVIRONMENT limitations (block E2E assertions in LOCAL dev only)

- **Image upload → GCS Forbidden → 502 in local dev.** `POST /products/{id}/images`
  returns 502 `gcs.unavailable` ("GCS upload failed: Forbidden") — the dev backend
  has no working GCS bucket/creds. So the image-precheck flow cannot reach a
  `precheck-card`/`precheck-status` through the UI locally; the upload 502s BEFORE any
  rembg precheck runs (`FEATURE_IMAGE_PRECHECK_ENABLED=True`, so it's purely the
  storage credential gap). The PrimeNG advanced uploader interaction itself WORKS
  (setInputFiles on `p-fileupload input` + click the `Upload` button → real POST).
  image-precheck is `test.fixme()` pending a GCS-credentialed env (or a fake/MinIO).


## Wave-3 build/dep quirks (catalog vertical)
- STALE-REMOTE-DIST analogue (the shell ui-kit singleton): after a [testId] passthrough
  or any ui-kit/component change lands on develop, REBUILD THE REMOTE TOO, not just the
  shell. Wave-3 exploration ran on baseline shell :4200 only after a fresh
  `ng build mfe-auth` + `ng build mfe-dashboard` so the shell's ui-kit singleton carried
  the [testId] passthrough; without rebuilding the remote the shell federates the OLD
  remote dist and the new testids/passthrough are absent. (Same class as the stale-bundle
  logout in master-session memory.)
- ng-build 0%-CPU post-write HANG: `ng build <remote>` sometimes drops to 0% CPU AFTER
  the dist is already written to disk (the process does not exit). The dist IS complete —
  verify the dist files exist, then KILL the PID. Do not wait for a clean exit.
- @playwright/test@1.52.0 was DECLARED in frontend/package.json but NOT installed in
  node_modules. pnpm-add'd it OFFLINE (it matches the cached chromium-1169, no browser
  download needed). Infra should add it to the lockfile so CI does not re-resolve.
