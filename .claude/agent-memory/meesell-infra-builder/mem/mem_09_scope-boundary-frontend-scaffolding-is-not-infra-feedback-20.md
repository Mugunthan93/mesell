## Scope boundary — frontend scaffolding is NOT infra (feedback, 2026-06-08)

Received task "Wave 2B Step 1 — Scaffold new frontend" (git clone Sakai-ng, `npx @angular/cli@21 new frontend`, `pnpm add primeng @primeuix/themes`, Tailwind v4 wiring, `pnpm run build`). **DECLINED — out of scope. Made zero changes (no clone, no scaffold, no installs, no edits).**

**Rule established:** Angular app scaffolding / PrimeNG / Tailwind / `ng new` / `ng build` is FRONTEND-development work, NOT infra. My scope is the deploy boundary only: I take a built frontend image and run it in K8s (nginx pod, ingress, TLS). I do NOT run `ng new` or install npm/pnpm app deps. (CLAUDE.md rule 6: out-of-scope work is refused with a redirect to the right meesell-* agent.)

**Tells that a task is out of my lane (any one is enough to decline):**
- No matching `INFRASTRUCTURE_PLAYBOOK.md` section. Playbook §0–15 = VM/K3s/ns/Postgres/Valkey/Supabase/cert-manager/Traefik/ingress/secrets/cost. Angular appears only as "Angular (nginx)" deployed artifact. If I can't name the section + rule, I don't own it.
- A dedicated agent exists. Frontend owners: `meesell-frontend-coordinator`, `meesell-angular-component-builder`, `meesell-angular-service-builder`, `meesell-angular-ui-styler`.
- The work maps to a non-infra doc/wave: `docs/FRONTEND_ARCHITECTURE.md` ("Wave 2B scaffold → 2C UI Kit → 2D Shared → 2E+ Features", founder-APPROVED 2026-06-08). Note: this doc supersedes CLAUDE.md's older "Angular 18 + Material" stack — new target is Angular 21 + PrimeNG 21 + Sakai-ng + Tailwind 4.

**Correct route for such tasks:** `meesell-frontend-coordinator`.

**Frontend pre-state captured (for whoever picks this up; zero mutations made):**
- `themes/` and `frontend/` do NOT exist at repo root (clean slate for the scaffold).
- Rejected old stack archived at `archive/frontend_angular_material/`: Angular **20** + `@angular/material` + Tailwind **v3** + vitest.
- Old themes at `archive/themes/{signal-admin,spike-angular}` — signal-admin is the rejected theme (do not reuse).
- Toolchain on laptop: node v22.15.0, pnpm 11.5.2, npx 10.9.2. (PATH still needs `export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"` per Bash call.)
- `.gitignore` ignores `frontend/.angular/` only.

---
