## Session mesell-gate4-confirmation-infra-session-1 (MF §9 Gate 4) — 2026-06-10

**VERDICT: CONFIRMED-WITH-CONDITIONS** (6: C-RES-1, C-RES-2, C-ROUTE-1, C-CI-1, C-CSP-1, C-STAGING-1).

Key findings:
- dev node 2000m alloc / 1650m requested (82%) → ~350m headroom → in-cluster remotes (~500m) DO NOT FIT.
- Confirmed architecture = **Option C**: shell in-cluster (backend-service swap on dev.mesell.xyz, no cert churn) + 6 remotes as GCS/CDN static at remotes.mesell.xyz outside K3s (zero pods).
- CSP greenfield (no CSP/nginx.conf/Middleware exists) — author via shell nginx.conf or CSP-only Traefik Middleware, MUST NOT disturb CORS/refresh-cookie.
- CI = paths-filter matrix + 2 cloudbuild files, single AR repo.

Deliverable `docs/plans/infra/GATE4_CONFIRMATION.md`, commit `69546bb`, PR **#33** merged `f30d61f`, board+STATUS follow-up `b3e76cd`. Zero cluster/TF/manifest mutations.

**Learning:** `gh graphql` 401s recurred — REST + retry remains the pattern; background memory writes auto-deny — end-of-session memory appends need foreground or pre-granted permission.

---
