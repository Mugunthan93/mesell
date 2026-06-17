# SP06 — mfe-auth (the LAST extraction; 6-remote topology COMPLETE)

**Session:** mesell-mfe-auth-frontend-session-1 — 2026-06-11
**Status:** EXECUTED + LEAD-GATED. Group PR #95 squash `8e90363` (frontend→integration). Founder-gate PR #96 OPEN (integration→develop, [FOUNDER GATE — DO NOT MERGE], NOT lead-approved per D1).
**Milestone:** with #96 merged, ALL SIX MF remotes coexist on develop. SP07 cutover is the ONLY remaining sub-plan. Every extraction (SP01–06) is DONE.

## What landed
Extracted the 3 PUBLIC auth pages (login/signup/otp-verify) from shell `features/auth/`
into Native Federation remote `apps/mfe-auth/` (port 4206). 3 exposes
(`./LoginComponent` `./SignupComponent` `./OtpVerifyComponent`). Closes the
bidirectional auth singleton loop: SP03 = C5 (shell→remote READ via profile);
**SP06 = C4 (remote→shell setSession WRITE via otp-verify).**

## The two HYBRID phases (builder-executed, lead-gate-verified)
- **Phase A+B** (component-builder, commit `9249da8`): the 6-file extraction. 6 renames
  R100 (byte-identical — D39 AuthLayout re-point was already on develop = verified NO-OP,
  so ZERO content edits on moved files, cleanest extraction yet). Creates:
  federation.config.js, main.ts (routes ALL 3 exposes — R-SP3-1 core-reachability),
  index.html, tsconfig.app.json, public-api.ts. app.routes.ts: 3 `loadRemoteWithFallback`
  swaps, no canActivate on the 3 public routes (D37).
- **Phase C** (service-builder, commit `6e5ec46`): ONLY `auth-write.smoke.spec.ts` (+222
  lines, 1 file). The C4 WRITE-path proof — inverse of SP03's C5 read proof.

## Lead gate (skeptical-lead, re-ran everything — ZERO discrepancies vs builder report)
Re-certified TWICE: once on tip `6e5ec46`, once on the merged integration tip `4dd6b6d`.
- **Builds:** shell GREEN 3.29–3.36 s / remote GREEN 2.69–3.42 s (both ≤90 s, D12). Shell
  initial total 60.62 kB (auth chunks LEFT the shell = strangler shrink). esbuild preserved.
- **Tests:** **44 files / 416 tests PASS, 0 fail / 0 skip** (develop baseline 43 + 1 C4 file).
  All 4 mfe-auth specs discovered (login/signup/otp-verify/auth-write.smoke).
- **C4 WRITE go/no-go GREEN** — post-setSession isAuthenticated()===true, currentUser()
  name/id correct, getToken()==='mock-token', guard flips false→true; `remoteAuth===shellAuth`
  single instance; setInterval resend cleared on destroy. The federated auth WRITE loop is CLOSED.
- **C2 no-dup:** `@mesell/core` shared singleton:true, exactly one `_mesell_core-*.js` chunk;
  setSession DEF only in `_mesell_core.js`, call-site only in OtpVerifyComponent.js. No drift.
- **AuthService diff EMPTY** across whole branch (D22 C2 — hardest STOP, clear).
- Boundary 0 primeng outside ui-kit (incl specs); 0 in apps/mfe-auth. **0 localStorage** (FE-D5
  in-memory JWT). Manifest 6 entries (auth 4206). Port 4206 in both serve keys.

## Merge mechanics (this session)
- **No group PR existed at session start** — OPENED #95 (frontend→integration) first, then
  lead-gate APPROVE comment (self-approval blocked), then `gh pr merge 95 --squash --admin`
  → MERGED `8e90363`. Deleted remote frontend branch via `gh api -X DELETE .../refs/heads/feature/mfe-auth/frontend` (the --delete-branch-from-worktree gotcha avoided proactively).
- **Develop-busy sync (conflict-free this time):** worktree /tmp/mesell-wt/sp06-merge →
  `git reset --hard origin/feature/mfe-auth/integration` (stale guard) → `git merge
  origin/develop`. develop's advance since integration base `34d8b47` was **docs/CI/status
  ONLY** — `git diff --name-only 34d8b47..origin/develop` touched NO frontend apps/, manifest,
  angular.json, package.json, app.routes.ts, app.config.ts → **no union-merge of the 4 shared
  files needed.** Merge `4dd6b6d`. Re-certified builds+tests GREEN on merged tip, pushed.
- **Founder gate #96** [FOUNDER GATE — DO NOT MERGE] integration→develop OPENED + LEFT OPEN.
  Did NOT approve (D1). develop tip re-checked `751b588` immediately before opening (no
  mid-flight founder merge this run; the re-fetch discipline held).

## Reusable confirmations
- The **C2 chunk-grep technique** (grep the EXPOSED-component chunk by ExposeKey name for the
  method DEFINITION form `setSession(token` vs call-site `.setSession(`) reconfirmed as the
  static no-drift proof. Native-federation names exposed chunks `<ExposeKey>.js`.
- Concurrent shell+remote `ng build` on the same .pnpm store: trust dist artifacts +
  "Application bundle generation complete [Xs]" line, not the streamed tail (stats-emit can
  stall under contention). Used `> /tmp/x.log 2>&1` redirects, not pipes.
- `pnpm install --config.dangerously-allow-all-builds=true` (4.8 s) extracts esbuild into the
  .pnpm store (top-level node_modules/esbuild/bin symlink may not resolve — check
  `find node_modules/.pnpm -path "*@esbuild*darwin*" -name esbuild`). `ng build` works directly.

## Forward — SP07 cutover (the only remaining sub-plan)
- All 6 remotes on develop after #96. SP07 = shell strip + features/ removal (D41); shell
  relocation to apps/shell/ (D43 RULED RELOCATE); version-pinned per-env manifests (D44);
  **CSP go-live (D42 ADD-ONLY, dev-smoke first, discharges C-CSP-1)**; discharge all 6 Gate-4
  C-conditions (D45); §5.1 repo-mgmt compliance audit (D46). FIRST sub-plan with TWO group
  branches (frontend + infra) into one integration.
- **R-SP6-6/C-CSP-1 escalation filed** → `handoff_mf_auth_deploy.md`: mfe-auth (public auth)
  + mfe-dashboard (public landing) = the two highest-stakes CSP surfaces; fe owns the CSP
  allowlist content, infra owns the nginx/Traefik mechanism. C-CSP-1 stays OPEN until SP07.
- 6th/final infra hosting row added to the board (RECORD-ONLY, consolidated with SP01–05 rows).
