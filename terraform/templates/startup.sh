#!/usr/bin/env bash
# MeeSell VM bootstrap. Runs once via cloud-init on first boot.
# Goal: prepare the box so that `setup-vm.sh` from the repo can run unattended.
set -euo pipefail

LOG=/var/log/meesell-bootstrap.log
exec > >(tee -a "$LOG") 2>&1
echo "==> MeeSell bootstrap starting $(date -u +%FT%TZ)"

export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y --no-install-recommends \
  ca-certificates curl gnupg jq git make \
  apt-transport-https lsb-release

# --- gcloud CLI (used by setup-vm.sh to pull from Secret Manager) -----------
if ! command -v gcloud >/dev/null 2>&1; then
  echo "==> Installing gcloud CLI"
  curl -fsSL https://packages.cloud.google.com/apt/doc/apt-key.gpg \
    | gpg --dearmor -o /usr/share/keyrings/cloud.google.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" \
    > /etc/apt/sources.list.d/google-cloud-sdk.list
  apt-get update -y
  apt-get install -y --no-install-recommends google-cloud-cli
fi

# --- Hand off the deployment params so setup-vm.sh / secrets-from-gcp.sh
#     can find them without re-deriving anything.
cat > /etc/meesell.env <<EOF
PROJECT_ID="${project_id}"
REGION="${region}"
NAME_PREFIX="${name_prefix}"
BUCKET="${bucket_name}"
REGISTRY="${registry_url}"
WORKLOAD_SA="${workload_sa_email}"
DOMAIN="${domain}"
EOF
chmod 0644 /etc/meesell.env

echo "==> MeeSell bootstrap finished $(date -u +%FT%TZ)"
echo "Next: SSH in, clone the repo, then run scripts/secrets-from-gcp.sh && sudo scripts/setup-vm.sh"
