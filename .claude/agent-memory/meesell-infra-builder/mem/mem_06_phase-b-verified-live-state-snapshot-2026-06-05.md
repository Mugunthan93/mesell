## Phase B Verified Live State (snapshot 2026-06-05)

For quick recall without re-querying GCP / K8s:
- 5 LE certs Ready=True on: `studio.mesell.xyz` (issued 2026-06-04), `api.mesell.xyz`, `dev.mesell.xyz`, `testing.mesell.xyz`, `staging.mesell.xyz` (issued 2026-06-05).
- All 7 Secret Manager secrets at version 1, populated. Local backups at `~/.meesell-secrets/`.
- VM SA `888244156264-compute@...` has `artifactregistry.reader` on `meesell-prod-images` and `storage.objectAdmin` on `gs://meesell-prod-assets`.
- Valkey args confirmed live: `--maxmemory 128mb --maxmemory-policy allkeys-lru`. Runtime verified via `valkey-cli config get`.
- TF state: clean (last drift check during PASS2B-COMPLETE / Phase A applies). Local file at `infra/terraform/terraform.tfstate`.
- Outstanding application work: `dev/api`, `dev/worker`, `dev/frontend` Deployments not yet created (Phase D — gated on image builds).

---
