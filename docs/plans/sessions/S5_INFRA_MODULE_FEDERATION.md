# Session Dispatch: Infra — Module Federation
**Session name:** `mesell-infra-module-federation-infra-session-1`
**Project:** `/Users/mugunthansrinivasan/Project/mesell`
**Status:** BLOCKED — requires Session 1 complete; can run parallel with Session 3

---

## Prerequisite
Session 1 (repo-management) must be COMPLETE.
Session 3 (module federation) Sub-Plan 0 should be in progress or complete —
this session prepares the hosting infrastructure for when the first remote
(mfe-pricing) is ready to deploy.

---

## Mission
Review and ratify the Infra Module Federation Plan. Lock the hosting model
and CDN strategy. Set up the GCS infrastructure and CDN configuration so that
when Sub-Plan 1 (mfe-pricing pilot) lands, deployment is ready to go.

---

## Read first (in this order)
1. `docs/plans/infra/module_federation_infra_plan.md` — the plan to ratify
2. `docs/plans/module_federation/MASTER_PLAN.md` §4.3 — build pipeline changes
   that depend on infra (remote-entry URLs, CSP, GCS layout)
3. `docs/INFRASTRUCTURE_ARCHITECTURE.md` — current state
4. `docs/DEVOPS_ARCHITECTURE.md` — current CI/CD
5. `.claude/agent-memory/meesell-infra-builder/MEMORY.md`

---

## Open decisions — get founder answer in this session

1. **MF-HOST-1: Frontend hosting model**
   - Option A: All components (shell + all remotes) served from K3s nginx pods
   - Option B: All components served from GCS + Cloud CDN
   - **Option C (recommended): Hybrid — shell in K3s nginx + remotes in GCS + CDN**
     Shell needs cookie-based auth routing; remotes are pure static assets
     with content-hashed filenames. CDN for remotes = free cache invalidation
     via hash, fast global delivery, no pod pressure.
   - Confirm Option C or choose alternate

2. **MF-ENV-1: Remote GCS bucket layout**
   - Option A: Separate bucket per env
     (`gs://mesell-remotes-dev`, `gs://mesell-remotes-staging`)
   - Option B: Single bucket with env prefix
     (`gs://mesell-remotes/dev/`, `gs://mesell-remotes/staging/`)
   - Recommendation: Option A — separate IAM policies, no accidental
     cross-env serving

3. **CDN invalidation strategy**
   - Option A: Content-hash filenames only — no explicit invalidation needed
     (remoteEntry.js is the only non-hashed file — invalidate it on every deploy)
   - Option B: Version manifest pinned per env — shell's manifest.json points
     at exact remote-entry URLs per environment
   - Recommendation: Both — content-hash for chunks + manifest pins for
     remoteEntry.js. Invalidate only `remoteEntry.js` on deploy (cheap, targeted).

---

## What to produce

### Step 1 — Ratify the plan
- Change STATUS in `docs/plans/infra/module_federation_infra_plan.md` → APPROVED
- Record the 3 decisions

### Step 2 — Create the feature branch
- Create `feature/module-federation-infra-prep/infra` from `develop`

### Step 3 — Execute MF-HOST-1: GCS buckets + CDN
Dispatch `meesell-infra-builder` to:
- Create `gs://mesell-remotes-dev` and `gs://mesell-remotes-staging` buckets
  via Terraform (GCS module extension)
- Configure uniform-bucket-level-access, CORS for `dev.mesell.xyz`
- Set up Cloud CDN backend bucket for remotes
- IAM: CI SA (`meesell-github-ci`) gets `storage.objectAdmin` on both buckets

### Step 4 — Execute MF-K8S-1: Shell deployment update
Dispatch `meesell-infra-builder` to:
- Add `REMOTES_MANIFEST_URL` env var to shell K8s Deployment
  pointing at the GCS-hosted `remotes.manifest.json`
- Add ConfigMap `remotes-manifest` (initially empty — populated when first
  remote is deployed)
- Document the manifest update procedure in INFRASTRUCTURE_ARCHITECTURE.md

### Step 5 — Execute MF-CDN-1: CSP header
Dispatch `meesell-infra-builder` to:
- Add `Content-Security-Policy` header to the shell's Traefik middleware
  whitelisting `https://remotes-dev.mesell.xyz` (dev) /
  `https://remotes-staging.mesell.xyz` (staging)
- Test: shell loads from K3s, can fetch a static asset from GCS origin

### Step 6 — Commit + PR
Commit on `feature/module-federation-infra-prep/infra`
Open PR to `feature/module-federation-infra-prep`
Update `docs/status/feature_board_infra.md`
Update `docs/INFRASTRUCTURE_ARCHITECTURE.md` with all changes

---

## Acceptance gate — session is DONE when
- [ ] MASTER_PLAN.md status = APPROVED
- [ ] `gs://mesell-remotes-dev` and `gs://mesell-remotes-staging` buckets exist
- [ ] Cloud CDN backend bucket configured
- [ ] Shell deployment has `REMOTES_MANIFEST_URL` env var
- [ ] CSP header allows remote origins
- [ ] INFRASTRUCTURE_ARCHITECTURE.md updated
- [ ] PR open against `feature/module-federation-infra-prep`

---

## Constraints
- Do NOT deploy any actual remotes — infra scaffolding only
- Do NOT touch `frontend/` application code
- All GCS and CDN changes must be Terraform-managed
- INFRASTRUCTURE_ARCHITECTURE.md must be updated in the same commit as any live change
