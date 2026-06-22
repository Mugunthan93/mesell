# HANDOFF — federation manifest port-mapping is a TWO-REGIME conflict (infra → frontend)

**Opened:** 2026-06-22 by `meesell-infra-builder` (session `mesell-stale-federation-manifest-infra-session-1`)
**Target lead:** `meesell-frontend-coordinator` (owns `angular.json`, `package.json`, `frontend/tools/dev/*`, the CI frontend smoke job)
**Status:** OPEN — NOT a blocker on any feature; a correctness/consistency decision needed before the committed dev manifest is "corrected"
**Branch left in place:** `fix/stale-federation-manifest/infra` (worktree `/private/tmp/mesell-wt/stale-fed-manifest`) — CLEAN (no commits, edits reverted). Safe to delete; I made NO change.

## TL;DR

I was asked (founder-pre-approved) to "fix the stale committed `frontend/apps/shell/public/federation.manifest.json`" so its port→remote mapping matches the running stack / `meesell_env.py` sorted default:

```
mfe-auth→:4201  mfe-billing→:4202  mfe-catalog→:4203  mfe-dashboard→:4204
mfe-export→:4205  mfe-onboarding→:4206  mfe-pricing→:4207   (SORTED-dir order)
```

**I did NOT make this change, because it would break the CI boot-smoke gate (and `ng serve`/`start:all` locally).** The committed manifest is NOT random cruft — it is load-bearing for a SECOND, internally-consistent port regime that disagrees with the running stack.

## The two regimes (both currently consistent within themselves)

**Regime A — `ng serve` / `start:all` / CI (consumes the COMMITTED manifest):**
- `frontend/angular.json` serve `port` per remote: `mfe-pricing=4201, mfe-export=4202, mfe-onboarding=4203, mfe-dashboard=4204, mfe-catalog=4205, mfe-auth=4206, mfe-billing=4207` (OLD order).
- `package.json` `start:mfe-*` = bare `ng serve <app>` (no `--port`) → inherits the angular.json ports above.
- `frontend/tools/dev/start-all.mjs` SERVERS array + printed banner (lines 49-57, 76-82) = same OLD order.
- `frontend/tools/dev/serve-static.mjs` SERVERS array (lines 57-66) = same OLD order, header says `// port map MUST match federation.manifest.json`.
- `frontend/tools/boot-smoke/README.md` port-map table + serve block = same OLD order (and omits mfe-billing).
- `.github/workflows/ci.yml` boot-smoke job: `setsid pnpm run start:all` (line 811) → `ng serve` (Regime A) → shell serves the COMMITTED `public/federation.manifest.json` verbatim (angular.json esbuild assets glob = `apps/shell/public/**/*`; `main.ts` does `initFederation('federation.manifest.json')` origin-relative; NO manifest regeneration anywhere; CI does NOT run meesell_env.py). CI readiness loop waits :4201-:4206 (6 ports — already MISSING :4207/mfe-billing, latent bug).
- The COMMITTED manifest (`mfe-pricing→:4201 ... mfe-auth→:4206 ... mfe-billing→:4207`) is CORRECT for Regime A.

**Regime B — `tools/meesell_env.py` / boot-smoke `serve.js` (the CURRENTLY-RUNNING stack):**
- `meesell_env.py` assigns `mfe[i] = 4201 + N*10 + i` over `sorted(frontend/apps/mfe-*)` = `[auth,billing,catalog,dashboard,export,onboarding,pricing]` → SORTED order (auth→:4201 ... pricing→:4207).
- It GENERATES and OVERRIDES the served `federation.manifest.json` at runtime per slot.
- VERIFIED LIVE this session (2026-06-22): all 7 ports up via `tools/boot-smoke/serve.js`; `curl :420X/remoteEntry.json` "name" = sorted (auth@:4201 ... pricing@:4207); the live shell at `:4200` serves a runtime manifest already in SORTED order. So Regime B is working as designed — the live shell is correct.

## Why the committed file "looked stale" (the debugging-cost the brief cites)

It only looks wrong if you compare it to the RUNNING (Regime B) stack. But the committed file is the Regime A artifact, and `meesell_env.py` (Regime B) intentionally overrides it at runtime. The mismatch the founder hit was the EXPECTED runtime override — not a bug in the committed file per se. The real defect is that the repo carries TWO contradictory port regimes with no single source of truth.

## The decision needed (frontend lead + founder) — pick ONE

**Option 1 — Make SORTED order canonical (matches the brief + the running stack + meesell_env.py).**
Reconcile Regime A to sorted order, all in one frontend-owned change:
1. `angular.json` serve ports → auth=4201, billing=4202, catalog=4203, dashboard=4204, export=4205, onboarding=4206, pricing=4207.
2. `start-all.mjs` + `serve-static.mjs` SERVERS arrays + banner → sorted order.
3. `boot-smoke/README.md` port map + serve block → sorted order (+ add mfe-billing).
4. `.github/workflows/ci.yml` readiness loop → check :4201-:4207 (add the 7th).
5. THEN the committed `public/federation.manifest.json` → sorted order (this is the only file in MY lane; I'll ship it once A is reconciled).
This makes meesell_env.py and `ng serve` agree, and removes the override surprise entirely.

**Option 2 — Keep Regime A (old order) canonical; make meesell_env.py match angular.json.**
Change `meesell_env.py` to read each remote's port from `angular.json` serve config instead of sorted-index. Then the committed manifest stays as-is (already correct), the running stack flips to old order, and there's one SSOT (`angular.json`). No manifest edit needed. (meesell_env.py is dev-tooling — borderline mine, but it's tightly coupled to the frontend app layout; I'd want FE sign-off.)

**Recommendation:** Option 1. The running stack, the brief, and `meesell_env.py`'s sorted-index design all already point at sorted order; alphabetical-by-dir is the more robust rule (it auto-extends when a new `mfe-*` is added, which is exactly how mfe-billing drifted the old hand-pinned order). Option 1 also fixes the latent CI gap (readiness loop missing :4207) and the README's mfe-billing omission as part of the same sweep.

## What I need from the frontend lead

- A ruling on Option 1 vs 2 (with founder, since it touches CI behavior).
- If Option 1: you reconcile angular.json + start-all.mjs + serve-static.mjs + README + ci.yml readiness loop (all FE-owned). PING me (resolve this memo) and I'll ship the one-line manifest flip + the boot-smoke README note in `fix/stale-federation-manifest/infra` and run the merge.
- If Option 2: tell me and I'll close my branch with no change + (optionally) adjust meesell_env.py to read angular.json ports, with your review.

## Files inspected (evidence, all read-only)
- `frontend/apps/shell/public/federation.manifest.json` (committed = Regime A / old order)
- `frontend/apps/shell/public/federation.manifest.{prod,staging}.json` (real remotes.mesell.xyz hostnames + {ENV}/{VERSION}; NO localhost; CORRECT + out of scope; only 6 remotes — your D44 concern, not this)
- `frontend/angular.json` (serve ports = Regime A authoritative)
- `frontend/package.json` (start:mfe-* = bare ng serve)
- `frontend/tools/dev/{start-all,serve-static,dev-static}.mjs`
- `frontend/tools/boot-smoke/README.md`
- `frontend/apps/shell/src/main.ts` (initFederation origin-relative load)
- `frontend/apps/shell/federation.config.js` (host, runtime-loaded remotes, no manifest write)
- `node_modules/.pnpm/@softarc+native-federation-runtime@3.5.5/.../softarc-native-federation-runtime.mjs:244` — `loadManifest` uses `fetch().then(r=>r.json())` = STRICT JSON.parse → the manifest MUST stay comment-free (no `//` headers; the prod/staging siblings' `//` comments would break a real browser load — separate FE concern, those manifests aren't hosted yet per the parked D13).
- `.github/workflows/ci.yml` (boot-smoke job: start:all + readiness :4201-:4206)
