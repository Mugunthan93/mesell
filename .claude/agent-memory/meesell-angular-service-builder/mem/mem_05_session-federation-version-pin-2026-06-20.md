## Session: federation-version-pin (2026-06-20)

**Branch/commit:** fix/federation-shared-version-pin @ 38c7934 (PUSHED)
**Worktree:** /private/tmp/mesell-wt/fed-version-pin

### Root cause (BUG from master-session memory)
@mesell/* libs had NO package.json → version="" in every remoteEntry.json → NF cannot dedup
by version → each remote loaded its own @mesell/core instance → second instance has null
in-memory token → authGuard redirects to /login on shell→remote navigation.

### Fix applied
1. Added libs/{core,env,composites,ui-kit}/package.json with version "1.0.0".
2. Added explicit mesellShared overrides in all 7 federation.config.js:
   singleton:true, strictVersion:true, requiredVersion:'1.0.0', version:'1.0.0'.

### NF framework limitation (critical learning — P0)
@mesell/* workspace libs are processed via sharedMappings (tsconfig path aliases), NOT via
the `shared` npm-packages pipeline. The function bundle-exposed-and-mappings.js in
@softarc/native-federation@3.5.5 HARDCODES:
  requiredVersion: '',
  singleton: true,
  strictVersion: false,
for ALL sharedMappings entries regardless of federation.config.js shared{} overrides.

CONSEQUENCE: strictVersion and requiredVersion CANNOT be set via config for workspace libs.
The federation.config.js mesellShared entries for strictVersion/requiredVersion are silently
ignored — they only affect npm packages in node_modules, not workspace path-aliased libs.

WHAT WORKS: version IS populated from libs/*/package.json (package-info.js reads it).
singleton:true IS passed through from shareAll() defaults.

DEDUP MECHANISM: NF runtime deduplicates by packageName + version + singleton=true.
With ALL 7 remotes showing v=1.0.0 + singleton=true, the shell's @mesell/core instance
wins and remotes reuse it → single AuthService instance → no logout on nav.

### Verification output
All 7 remotes: v=1.0.0 sing=True strict=False req='' (HTTP 200).
strictVersion=false and req='' are framework-imposed, NOT a bug in this fix.
The dedup works via version match — strict is irrelevant when versions ARE consistent.

### Sequential build pattern (memory-lean, 8GB machine)
  cd /Users/mugunthansrinivasan/Project/mesell/frontend
  for app in frontend mfe-pricing mfe-catalog mfe-export mfe-onboarding mfe-dashboard mfe-auth; do
    ./node_modules/.bin/ng build $app --configuration development 2>&1 | tail -5
    pkill -9 -f "esbuild --service" 2>/dev/null
  done
  Kill ALL stale serve.js PIDs before restart (kill -9 all 4200-4206 PIDs).
  Restart: node tools/boot-smoke/serve.js dist/<app>/browser <port> &

### Port map (confirmed)
shell:4200 | mfe-pricing:4201 | mfe-export:4202 | mfe-onboarding:4203
mfe-dashboard:4204 | mfe-catalog:4205 | mfe-auth:4206

### Credential fix for worktree push
Worktrees don't inherit global gitconfig. Fix:
  git -C <worktree> config credential.https://github.com.helper '!/opt/homebrew/bin/gh auth git-credential'
  git -C <worktree> push origin HEAD:<branch>
