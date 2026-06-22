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

## QA Wave C — qa-pricing VERIFIED LIVE (2026-06-22)

- **STALE BASELINE REMOTE DIST — mfe-export served a 22:54 build PRE-testids
  (recurrence of "stale remote bundle", HIGH-VALUE).** The slot-0 baseline stack
  (`/mesell:dev`) served `frontend/dist/mfe-export/browser/main.js` built `Jun 21 22:54`
  — BEFORE `export-trigger`/`export-download` testids landed. Symptom: `getByTestId('export-
  trigger')` count 0 even though the export REMOTE rendered fine (body showed "Generate
  Export"), and the manifest fix was applied (remote-failure-fallback count 0). The string
  `export-trigger` was simply absent from the served bundle. FIX: rebuild mfe-export from
  current source into `frontend/dist/mfe-export/browser` + restart its `:4205` serve.js.
  After the rebuild, `export-trigger` count → 1. LESSON: before exploring a remote's NEW
  testids, CHECK the served dist's mtime (`stat -f %Sm dist/<remote>/browser/main.js`) and
  `grep` the testid string in the dist — a baseline `/mesell:dev` stack can be a day stale.
  (mfe-pricing was rebuilt the same way for the #439 testids — a 4.5s build.)

- **MASTER-TREE WORKING COPY WAS CONTAMINATED — export.component.ts reverted to the
  productId placeholder.** While rebuilding mfe-export I found the master tree's
  `frontend/apps/mfe-export/src/app/export.component.ts` had been REVERTED by another
  session to the OLD bug (`const productId = 'current-product-id'` + a TODO comment),
  even though develop AND the integration tip carry the fix (`resolveExportProductId`).
  A naive `ng build mfe-export` from the master tree would have baked the PLACEHOLDER bug
  back into the dist. FIX: overwrote the master-tree export.component.ts + export.model.ts
  from `origin/feature/qa-pricing/integration` BEFORE rebuilding. LESSON: never trust the
  master tree's working copy for a remote rebuild — restore the file from the branch you
  are testing first, then build.

- **PRODUCTID BUG IS FIXED (Wave-1 reds closed).** `export.component.ts onGenerate()` now
  calls `resolveExportProductId(this.route.snapshot.paramMap)` (line ~425). VERIFIED LIVE:
  Generate on `/catalogs/{realPid}/export` POSTs `/api/v1/products/{realPid}/export-xlsx`
  (the REAL UUID). For a DRAFT product → 422 → real not-ready checklist renders. The
  Wave-1 PRODUCT BUG memo (export productId placeholder) is CLOSED. The export-download
  `test.fixme` reason CHANGED: no longer the placeholder bug, now an ENV limit (no ready
  product + no GCS signed URL in local dev). Un-fixme on a GCS-credentialed env.

- **MANIFEST PORT-MAPPING MISMATCH confirmed again on slot-0.** The running baseline stack
  binds remotes ALPHABETICALLY (mfe-auth :4201 … mfe-pricing :4207) but the shell's served
  `federation.manifest.json` maps DECLARATION-order (mfe-pricing→:4201 which actually serves
  mfe-auth, mfe-billing→:4207 which serves mfe-pricing). Drove the suite with
  `MEESELL_FIX_MANIFEST_PORTS=1` + the ALPHABETICAL port env overrides
  (MEESELL_MFE_PRICING_PORT=4207 etc.) so the `applyManifestPortFix` shim rewrites the
  manifest to the real ports. NOTE: playwright.config.ts's default REMOTE_PORTS are
  DECLARATION-order — which also does NOT match an alphabetical baseline; always set the
  per-remote port env to the ACTUAL running ports for the shim to be correct.

## Exploration harness note (Wave C)
- Ran agent-browser via Playwright `chromium.launch()` in a throwaway `.mjs` probe
  (deleted after exploration). @playwright/test is CommonJS → import as
  `import pw from '<abs>/@playwright/test/index.js'; const { chromium } = pw;` and run with
  `PLAYWRIGHT_BROWSERS_PATH=$HOME/Library/Caches/ms-playwright`. The product list API
  (`GET /api/v1/products`) returns `data[].product_id` (NOT `id`). `page.request.get` is a
  SEPARATE API context with NO in-memory token → 401; capture product ids via a
  `page.on('response')` listener on the browser's own authed fetch instead.
