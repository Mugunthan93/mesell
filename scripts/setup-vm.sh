#!/usr/bin/env bash
# MeeSell single-node K3s setup script. Run as root on a fresh Ubuntu 24.04 VM.
set -euo pipefail

NAMESPACE=meesell
K3S_VERSION="${K3S_VERSION:-v1.30.6+k3s1}"

# --- 1. Base packages ---------------------------------------------------------
apt-get update -y
apt-get install -y --no-install-recommends curl ca-certificates gnupg jq

# --- 2. K3s -------------------------------------------------------------------
if ! command -v k3s >/dev/null; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="${K3S_VERSION}" sh -s - \
    --write-kubeconfig-mode 644 \
    --disable=servicelb
fi
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# --- 3. cert-manager ----------------------------------------------------------
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.15.3/cert-manager.yaml
kubectl -n cert-manager rollout status deploy/cert-manager --timeout=180s
kubectl -n cert-manager rollout status deploy/cert-manager-webhook --timeout=180s

# --- 4. MeeSell namespace + manifests ----------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K8S_DIR="${SCRIPT_DIR}/../k8s"

kubectl apply -f "${K8S_DIR}/namespace.yaml"
kubectl apply -f "${K8S_DIR}/config.yaml"

if [ ! -f "${K8S_DIR}/secrets.yaml" ]; then
  echo "ERROR: ${K8S_DIR}/secrets.yaml is missing." >&2
  echo "  Copy secrets.yaml.example and fill in real values before re-running." >&2
  exit 1
fi
kubectl apply -f "${K8S_DIR}/secrets.yaml"

kubectl apply -f "${K8S_DIR}/postgres.yaml"
kubectl apply -f "${K8S_DIR}/valkey.yaml"
kubectl -n "${NAMESPACE}" rollout status deploy/postgres --timeout=180s
kubectl -n "${NAMESPACE}" rollout status deploy/valkey --timeout=120s

kubectl apply -f "${K8S_DIR}/api.yaml"
kubectl apply -f "${K8S_DIR}/worker.yaml"
kubectl apply -f "${K8S_DIR}/frontend.yaml"
kubectl apply -f "${K8S_DIR}/ingress.yaml"
kubectl apply -f "${K8S_DIR}/backup-cronjob.yaml"

kubectl -n "${NAMESPACE}" rollout status deploy/api --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/worker --timeout=240s
kubectl -n "${NAMESPACE}" rollout status deploy/frontend --timeout=180s

echo "MeeSell stack is up. Run \`kubectl -n ${NAMESPACE} get pods\` to inspect."
