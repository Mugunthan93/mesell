# MeeSell Platform Layer — plug-and-play GCP ⇄ Fly.io/GitHub Pages

MeeSell can run its backend + frontend on **either** of two independently-provisioned
platforms. This directory is the **decoupled Terraform switch** between them. Each
platform has its **own root module, its own state, and a matching output contract** —
so you can bring up, tear down, or adopt either one without touching the other.

> The GCP root already exists at [`/terraform`](../terraform) and is **not** recreated
> here (that stack stays byte-identical). This `platform/` directory adds the **new**
> Fly.io + GitHub Pages root and the guide that ties the two together.

---

## 1. Platform matrix

| | **GCP — K3s** | **Fly.io + GitHub Pages** |
|---|---|---|
| Terraform root | [`/terraform`](../terraform) (+ project bootstrap in `/infra/terraform`) | [`platform/flyio-ghpages`](./flyio-ghpages) |
| Status | **TERMINATED** — VM `meesell-dev` stopped 2026-06-30 (GCP credit stop). Code preserved. | **LIVE** — https://meesell-api.fly.dev + https://mugunthan93.github.io/mesell/ |
| Backend host | FastAPI on K3s (`api` Deployment, 2 replicas) behind Traefik | Fly.io app `meesell-api` (region `bom`): `api` + `worker` processes from one image |
| Database | PostgreSQL 16 StatefulSet on K3s | Fly Postgres cluster `meesell-db` (attached) |
| Cache / queue | Valkey 8 StatefulSet on K3s | **self-hosted Valkey 8** app `meesell-valkey` (config-as-code in [`platform/fly/valkey`](./fly/valkey)) — replaced Upstash `meesell-cache`, which supported only DB 0 and 500'd the locked 4-DB topology. Deployed `sin` (bom-capacity fallback), private 6PN only. |
| Frontend host | Angular shell + 7 remotes served on K3s (nginx) behind Traefik | GitHub Pages `build_type=workflow` under `/mesell/` |
| Object storage | GCS via **ADC** (VM/pod metadata SA) | GCS via **base64 SA key** in Fly secret `GCS_SA_KEY_B64` |
| CI deploy jobs | `ci.yml` `build` + `deploy` (K3s) — currently `if: false` | `ci.yml` `deploy-backend` (Fly) + `deploy-frontend.yml` (Pages) |
| State backend | local (`/terraform`) + GCS `gs://meesell-tfstate` (`/infra/terraform`) | **local** (mirrors `/terraform`) |
| Provider reality | real `hashicorp/google` resources throughout | `google` for the SA/IAM; **flyctl/gh shims** for Fly + Pages (no maintained provider) |

**Provider decision (Fly.io), evidence checked 2026-07-03:**
`fly-apps/fly` (official) is archived at **v0.0.23 (2023-06-22)**; `andrewbaxter/fly`
(community fork) is stale at **v0.1.18 (2024-10-28)**. Neither is safe for adopting live
production infra, so Fly is modelled with **idempotent `terraform_data` + `local-exec`
flyctl shims** (create-if-absent / update-in-place; the destroy provisioner is a no-op
that prints a manual runbook line — it deletes nothing). GitHub uses the maintained
`integrations/github` provider (**v6.12.1**); the repo is a **data source** (Terraform
can never delete it) and Pages is set via a `gh api` shim.

---

## 2. SWITCH CHECKLIST — what actually changes when you flip platforms

The two roots are decoupled, but the **application** is coupled to whichever platform is
live at exactly these surfaces. Flipping platforms = walking this list. Nothing else in
the app changes.

### 2.1 Frontend API base — `frontend/libs/env/environment.prod.ts`
- **K3s:** `apiBase = ''` (same-origin — FE and API share the ingress host).
- **Fly/Pages:** `apiBase = 'https://meesell-api.fly.dev'` (CROSS-origin — Pages FE calls Fly API).
- Every FE call is `apiBase + '/api/v1/...'` (see `libs/core/services/auth-api.service.ts`), so this single constant is the whole client-side switch. Do **not** change it without the CORS/cookie secrets in 2.3 changing in lockstep.

### 2.2 Federation manifest — `apps/shell/src/main.ts` (env-aware) + `deploy-frontend.yml`
- **K3s:** shell fetches `federation.manifest.json` with remote paths behind the K3s ingress.
- **Fly/Pages:** the `deploy-frontend.yml` **assemble step overwrites** the shipped dev manifest with absolute Pages URLs — `https://mugunthan93.github.io/mesell/remotes/<name>/remoteEntry.json` — laid out as shell-at-root + `remotes/<name>/`. `main.ts` must **not** import `@mesell/env` to choose a manifest (import-map chicken-and-egg — the prod manifest is inlined/served instead).
- Remotes (7): `mfe-auth mfe-billing mfe-catalog mfe-dashboard mfe-export mfe-onboarding mfe-pricing`. The host project in `angular.json` is **`frontend`** (root `apps/shell`), NOT `shell`.

### 2.3 Secrets: CORS + cookie (Fly `fly secrets` ⇄ K8s Secret)
| Key | K3s value | Fly/Pages value |
|---|---|---|
| `CORS_ALLOWED_ORIGINS` | K3s ingress host(s) | must include `https://Mugunthan93.github.io` (+ fly + localhost) |
| `COOKIE_DOMAIN` | the K3s app host | `.fly.dev` (interim) — cross-site refresh cookie |
| `COOKIE_SECURE` | `true` | `true` |
| `CORS_ALLOW_CREDENTIALS` | `true` | `true` (HttpOnly refresh cookie) |
- **Caveat (durable fix):** the github.io → fly.dev refresh cookie is **third-party** (`SameSite=None; Secure; Domain=.fly.dev`) and browser-policy fragile. A custom apex domain spanning both FE + API (`mesell.xyz` + `api.mesell.xyz`, `COOKIE_DOMAIN=.mesell.xyz`) is the first-party fix.

### 2.4 CI jobs — `.github/workflows/ci.yml` + `deploy-frontend.yml`
- **Fly/Pages (current):** `deploy-backend` (Fly) runs on push to `develop` after the 5 backend gates; `deploy-frontend.yml` publishes Pages.
- **K3s `build` + `deploy` jobs are disabled** with `if: false` (VM terminated). To flip back to K3s, restore their original condition — **preserved verbatim in the job comments**:
  ```
  if: github.event_name == 'push' && github.ref == 'refs/heads/develop'
  ```
  (and set `deploy-backend`'s `if:` to `false`, restart the VM, refresh kubeconfig/DNS/firewall for the VM's NEW ephemeral IP).

### 2.5 GCS auth — `backend/app/adapters/gcs.py` (handles both automatically)
- **K3s:** Application Default Credentials from the pod/VM metadata SA (no key material).
- **Fly/Pages:** `GCS_SA_KEY_B64` env var (base64 SA JSON) — the adapter decodes it first, else falls back to ADC. No app code change needed to switch; only the secret's presence differs.

---

## 3. Import / adoption runbook (Fly + Pages estate is already LIVE)

Everything the Fly/Pages root models **already exists** (created imperatively via
`flyctl`/`gh`). Adopt it into Terraform state **without recreating or destroying**
anything:

```bash
cd platform/flyio-ghpages

# 1) Auth (no secret values are committed anywhere):
gcloud auth application-default login                      # GCP ADC
export GITHUB_TOKEN=<PAT with repo scope>                  # github provider
export TF_VAR_fly_github_actions_token=<same FLY_API_TOKEN value>

# 2) Init (local backend) + adopt live resources:
terraform init
./import.sh          # imports the SA + 3 bucket IAM members + FLY_API_TOKEN secret

# 3) Prove no destroy/replace BEFORE any apply:
terraform plan       # expect: imported google_*/github_* show NO change;
                     # the 3 terraform_data shims show "to create" — EXPECTED + safe
                     # (their provisioners are idempotent no-ops on the live estate).
```

**What `import.sh` imports:** `google_service_account.fly` (`meesell-fly-sa`),
`google_storage_bucket_iam_member.fly_object_admin[*]` (objectAdmin on `meesell-dev`,
`meesell-images`, `meesell-prod-assets`), and `github_actions_secret.fly_api_token`.

**What it does NOT import (by design):**
- The **flyctl/gh shims** (`terraform_data.fly_app / fly_secrets / pages_build_type`).
  On first `apply` they "create" and run their **idempotent** scripts: `fly_app` detects
  the existing app → no-op; `fly_secrets` with no `TF_VAR_fly_secret_*` set → stages
  nothing; `pages_build_type` PUTs `build_type=workflow` → already workflow → no-op.
- A **`google_service_account_key`** — the live key was made out-of-band and its private
  material can't be read back. Adoption default `manage_sa_key = false` creates no key.
  The live key already lives in the Fly `GCS_SA_KEY_B64` secret; leave it be. Set
  `manage_sa_key = true` **only** for a deliberate rotation (that writes new key material
  into local state — keep state encrypted).

**Secrets, always:** the ~40 live Fly secrets stay as-is on adoption. To (re)stage a
secret, export its `TF_VAR_fly_secret_*` value, bump `secrets_revision`, and apply —
`fly_secrets.sh` stages it with `--stage` (no machine restart) and never prints the value.

**Follow-up — adopt `meesell-valkey` (NOT built here):** a new imperatively-created
Fly app **`meesell-valkey`** (self-hosted Valkey 8, config-as-code in
[`platform/fly/valkey`](./fly/valkey)) now exists and replaces Upstash `meesell-cache`.
It is **not yet modelled in Terraform**. When this root is next revised, add it as an
idempotent flyctl-shim `terraform_data.fly_valkey_app` (create-if-absent, destroy =
no-op runbook line, mirroring `fly_app`) driven by `platform/fly/valkey/fly.toml`, add
its `VALKEY_PASSWORD` to the `fly_secrets` shim, and extend `import.sh`/the switch
checklist accordingly. **Do the full Terraform later — flagged only.** (Its config-as-code
+ runbook already live in `platform/fly/valkey/README.md`.)

---

## 4. State isolation

- **Each root owns its own state.** `platform/flyio-ghpages` uses **local** state (mirrors
  `/terraform`; `.gitignore` excludes `*.tfstate*` + `terraform.tfvars` + `.terraform/`).
  It does **not** use the `gs://meesell-tfstate` GCS backend that `/infra/terraform` uses.
- **No cross-root references.** The roots never read each other's state or outputs. The
  only contract between them is the **matching output names** — `platform`, `api_base_url`,
  `frontend_url`, `deploy_notes` — which a caller can read identically from either.
  (The GCP root predates this contract and is not modified; its equivalents are
  `api_base_url ≈ https://api.mesell.xyz`, `frontend_url ≈ https://dev.mesell.xyz`, both
  derived from `/terraform` output `vm_external_ip` + the Traefik ingress.)
- **State holds secret material only when `manage_sa_key = true`** (a rotation). Keep local
  state encrypted at rest and never commit it (enforced by `.gitignore`). No secret VALUES
  are ever stored for Fly/GitHub secrets — those flow from the environment (`TF_VAR_*`)
  straight to the shims; only a `secrets_revision` counter lives in state.

---

## Files

```
platform/
├── README.md                     ← this guide
└── flyio-ghpages/
    ├── versions.tf providers.tf variables.tf terraform.tfvars.example
    ├── fly.tf                    ← Fly app + secrets (flyctl shims; no provider)
    ├── github.tf                 ← Pages build_type shim + FLY_API_TOKEN secret + repo data source
    ├── gcp_sa.tf                 ← meesell-fly-sa + 3× bucket objectAdmin + optional key
    ├── outputs.tf                ← contract: platform · api_base_url · frontend_url · deploy_notes
    ├── import.sh                 ← adopt the live estate into state (no recreate/destroy)
    └── scripts/                  ← idempotent flyctl/gh shim scripts (never destroy live infra)
```

> **Playbook note:** `docs/INFRASTRUCTURE_PLAYBOOK.md` has no Fly.io / GitHub Pages
> section (it is GCP/K3s only). A playbook amendment to add a Fly/Pages runbook needs
> **founder approval** (§7.3) — it is flagged, not made here.
