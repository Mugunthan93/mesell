# Sub-Plan 0 — Workspace Foundation: as-merged contract (for Sub-Plan 1+)

**Status:** EXECUTED 2026-06-10. PR#40 (frontend->integration) merged squash `e51761b`.
PR#41 (integration->develop) OPEN — founder gate. Once #41 merges, this is the develop shape.

## The `@mesell/*` alias map (tsconfig.json compilerOptions.paths, baseUrl ".")
```
@mesell/ui-kit        -> libs/ui-kit/index.ts        (barrel; 21 mee-* wrappers + 2 services + MeeDrawer + MeeMenu)
@mesell/ui-kit/*      -> libs/ui-kit/*               (deep: e.g. @mesell/ui-kit/providers, @mesell/ui-kit/input/input.component)
@mesell/composites    -> libs/composites/index.ts    (5 composites: stat-card, status-badge, empty-state, page-header, loading-skeleton)
@mesell/composites/*  -> libs/composites/*
@mesell/core          -> libs/core/index.ts          (AuthService, AuthUser, authGuard — NO HttpClient yet; §4 service layer born here in Wave 6)
@mesell/design-tokens -> libs/design-tokens          (CSS folder; _tokens.css; @use target if SCSS ever consumes it)
```

## libs/ layer mapping (the new home of the 4-layer architecture)
- Layer 0 -> `libs/core`        (auth singleton — federation `singleton:true` target, MASTER_PLAN §6.1)
- Layer 1 -> `libs/design-tokens` (CSS vars; loaded via src/styles.css `@import "../libs/design-tokens/_tokens.css"` + `@source "../libs"`)
- Layer 2 -> `libs/ui-kit`      (ONLY place primeng may be imported; incl. theme.ts + providers.ts config)
- Layer 3 -> `libs/composites`  (consume @mesell/ui-kit)

## Federation init shape (the stable contract for Sub-Plan 1 pilot)
- `federation.config.js`: `name: 'shell'`, `shareAll({ singleton:true, strictVersion:false, requiredVersion:'auto' })`, skip rxjs ajax/fetch/testing/webSocket, `features.ignoreUnusedDeps:true`.
- `public/federation.manifest.json` = `{}` (EMPTY). **Sub-Plan 1 adds the first remote here**: `{ "mfe-pricing": "https://.../remoteEntry.json" }`.
- Bootstrap split: `main.ts` -> `initFederation('federation.manifest.json')` -> dynamic import `./bootstrap` -> `bootstrapApplication(App, appConfig)`.
- angular.json: `build` + `serve` builder = `@angular-architects/native-federation:build`; the original `@angular/build:application` is KEPT as the `esbuild` target (esbuild preserved). `test` = `@angular/build:unit-test` with `include: ['**/*.spec.ts','../libs/**/*.spec.ts']`.
- Dep: `@angular-architects/native-federation@^21` (resolved 21.2.3) + transitive `@softarc/native-federation-node`, `es-module-shims`.

## Sub-Plan 1 (mfe-pricing pilot) preconditions
1. PR#41 merged to develop (founder gate).
2. Infra C-CI-1 ready (memo handoff_mf_ci_prep.md) — multi-project CI matrix when the FIRST remote lands.
3. The pricing feature page (features/pricing/) becomes the pilot remote: extract to its own project exposing its route via Native Federation `exposes`, register in the host manifest, add `loadRemoteModule` in app.routes. This is where the FIRST `loadRemoteModule` appears (Sub-Plan 0 has 0).
4. Re-confirm the `../libs/**/*.spec.ts` test-discovery glob in EVERY new project's angular.json test target — the sourceRoot-relative cwd gotcha recurs per project.
