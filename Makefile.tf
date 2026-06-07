# Purpose: Account-lock wrapper for all Terraform operations on the MeeSell production infra.
# Plan reference: docs/INFRASTRUCTURE_TERRAFORM_PLAN.md §19 Layer D.
# Scoping rules:
#   - NEVER uses `gcloud config set` — that mutates global gcloud state and can affect
#     other terminal sessions. All account/project binding is done via env vars
#     (CLOUDSDK_CORE_ACCOUNT, CLOUDSDK_CORE_PROJECT) scoped to the subprocess only.
#   - All state-changing targets run tf-preflight first (via the `tf-preflight` dependency).
#   - Every state-changing target writes a dated log to $(LOG_DIR)/ for audit.
#   - FOUNDER_IP is required for targets that touch the firewall module. The Makefile
#     fails fast with a clear error if it is not set.
#   - tf-plan-pass1 uses -target to restrict the plan to Pass 1 modules only.
#     This prevents terraform from attempting to configure the kubernetes provider
#     before the K3s cluster exists (the bootstrap chicken-and-egg problem, §3).

TF_DIR            := infra/terraform
EXPECTED_ACCOUNT  := vaishnaviramoorthy@gmail.com
EXPECTED_PROJECT  := project-1f5cbf72-2820-4cdb-949
EXPECTED_BILLING  := 01620D-6785AB-0E4698
LOG_DIR           := .tflogs
LOG_DIR_ABS       := $(CURDIR)/.tflogs

.PHONY: tf-preflight tf-init tf-init-pass2 tf-fmt tf-plan-pass1 tf-apply-pass1 \
        tf-plan-pass2 tf-apply-pass2 tf-destroy-check

# ---------------------------------------------------------------------------
# tf-preflight — identity + environment gate (run before any state change)
# ---------------------------------------------------------------------------
tf-preflight:
	@mkdir -p $(LOG_DIR_ABS)
	@chmod +x scripts/tf-preflight.sh
	@FOUNDER_IP="$(FOUNDER_IP)" scripts/tf-preflight.sh

# ---------------------------------------------------------------------------
# tf-init — initialise providers and local backend
# ---------------------------------------------------------------------------
tf-init: tf-preflight
	@mkdir -p $(LOG_DIR_ABS)
	@echo "[$(shell date -u +%Y-%m-%dT%H:%M:%SZ)] target=tf-init" >> $(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-init.log
	@echo "Observed account: $$(CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) gcloud --account=$(EXPECTED_ACCOUNT) config list account --format='value(core.account)' 2>/dev/null || echo unknown)" \
	  >> $(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-init.log || true
	CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	  terraform -chdir=$(TF_DIR) init

# ---------------------------------------------------------------------------
# tf-fmt — format all .tf files recursively (no state change, no preflight needed)
# ---------------------------------------------------------------------------
tf-fmt:
	terraform fmt -recursive $(TF_DIR)

# ---------------------------------------------------------------------------
# tf-plan-pass1 — plan Pass 1 (GCP-layer modules only)
# Requires: FOUNDER_IP env var set to your current public IPv4.
#   export FOUNDER_IP=$(curl -4 ifconfig.me)
#   FOUNDER_IP=$FOUNDER_IP make -f Makefile.tf tf-plan-pass1
# ---------------------------------------------------------------------------
tf-plan-pass1: tf-preflight
	@if [ -z "$(FOUNDER_IP)" ]; then \
	  echo "ERROR: FOUNDER_IP is not set. Run: export FOUNDER_IP=\$$(curl -4 ifconfig.me)" >&2; \
	  exit 1; \
	fi
	@mkdir -p $(LOG_DIR_ABS)
	@LOG_FILE=$(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-plan-pass1.log; \
	  echo "[$(shell date -u +%Y-%m-%dT%H:%M:%SZ)] target=tf-plan-pass1 FOUNDER_IP=$(FOUNDER_IP)" >> $$LOG_FILE; \
	  echo "Observed account: $$(CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) gcloud --account=$(EXPECTED_ACCOUNT) config list account --format='value(core.account)' 2>/dev/null || echo unknown)" >> $$LOG_FILE; \
	  echo "Observed project: $$(CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) gcloud config get-value project 2>/dev/null || echo unknown)" >> $$LOG_FILE
	CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	  terraform -chdir=$(TF_DIR) plan \
	    -var-file=environments/dev.tfvars \
	    \
	    -target=google_project_service.required \
	    -target=module.ci_identity \
	    -target=module.artifact_registry \
	    -target=module.asset_bucket \
	    -target=module.app_secrets \
	    -target=module.vm \
	    -target=module.firewall \
	    -target=module.billing_budget \
	    -out=$(LOG_DIR_ABS)/pass1.tfplan
	@LOG_FILE=$(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-plan-pass1.log; \
	  echo "Plan file sha256: $$(shasum -a 256 $(LOG_DIR_ABS)/pass1.tfplan 2>/dev/null | awk '{print $$1}' || echo n/a)" >> $$LOG_FILE || true
	@echo ""
	@echo "Plan written to $(LOG_DIR_ABS)/pass1.tfplan"
	@echo "Review the output above, then run: FOUNDER_IP=$(FOUNDER_IP) make -f Makefile.tf tf-apply-pass1"

# ---------------------------------------------------------------------------
# tf-apply-pass1 — apply the saved pass1 plan (requires confirmation)
# ---------------------------------------------------------------------------
tf-apply-pass1: tf-preflight
	@if [ ! -f "$(LOG_DIR_ABS)/pass1.tfplan" ]; then \
	  echo "ERROR: $(LOG_DIR_ABS)/pass1.tfplan not found. Run tf-plan-pass1 first." >&2; \
	  exit 1; \
	fi
	@mkdir -p $(LOG_DIR_ABS)
	@read -p "Apply Pass 1? Review the plan above before confirming. [yes/N] " ans && [ "$$ans" = "yes" ] || (echo "Aborted." && exit 1)
	@LOG_FILE=$(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-apply-pass1.log; \
	  echo "[$(shell date -u +%Y-%m-%dT%H:%M:%SZ)] target=tf-apply-pass1" >> $$LOG_FILE; \
	  echo "Plan file sha256: $$(shasum -a 256 $(LOG_DIR_ABS)/pass1.tfplan 2>/dev/null | awk '{print $$1}' || echo n/a)" >> $$LOG_FILE
	CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	  terraform -chdir=$(TF_DIR) apply $(LOG_DIR_ABS)/pass1.tfplan

# ---------------------------------------------------------------------------
# tf-init-pass2 — reinitialise providers after kubernetes + helm are uncommented
# Downloads kubernetes and helm providers (~30s). Run once after providers.tf edit.
# ---------------------------------------------------------------------------
tf-init-pass2: tf-preflight
	@mkdir -p $(LOG_DIR_ABS)
	@LOG_FILE=$(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-init-pass2.log; \
	  echo "[$(shell date -u +%Y-%m-%dT%H:%M:%SZ)] target=tf-init-pass2" >> $$LOG_FILE; \
	  cd $(TF_DIR) && \
	    KUBECONFIG=$(HOME)/.kube/meesell-dev.yaml \
	    CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	    CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	    terraform init -upgrade 2>&1 | tee -a $$LOG_FILE

# ---------------------------------------------------------------------------
# tf-plan-pass2 — plan Pass 2 (K8s workloads: namespaces, postgres, valkey,
#                  supabase_studio, traefik_stack)
# Requires: FOUNDER_IP, POSTGRES_PASSWORD, VALKEY_PASSWORD env vars.
#   export FOUNDER_IP=$(curl -4 -s ifconfig.me)
#   export POSTGRES_PASSWORD=$(cat ~/.meesell-secrets/dev-postgres-password)
#   export VALKEY_PASSWORD=$(cat ~/.meesell-secrets/dev-valkey-password)
#   FOUNDER_IP=$FOUNDER_IP POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
#     VALKEY_PASSWORD=$VALKEY_PASSWORD make -f Makefile.tf tf-plan-pass2
# ---------------------------------------------------------------------------
tf-plan-pass2: tf-preflight
	@if [ -z "$(POSTGRES_PASSWORD)" ]; then echo "ERROR: set POSTGRES_PASSWORD" >&2; exit 1; fi
	@if [ -z "$(VALKEY_PASSWORD)" ]; then echo "ERROR: set VALKEY_PASSWORD" >&2; exit 1; fi
	@mkdir -p $(LOG_DIR_ABS)
	@LOG_FILE=$(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-plan-pass2.log; \
	  echo "[$(shell date -u +%Y-%m-%dT%H:%M:%SZ)] target=tf-plan-pass2 FOUNDER_IP=$(FOUNDER_IP)" >> $$LOG_FILE
	cd $(TF_DIR) && \
	  KUBECONFIG=$(HOME)/.kube/meesell-dev.yaml \
	  CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	  CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	  terraform plan \
	    -var-file=environments/dev.tfvars \
	    \
	    -var="postgres_password=$(POSTGRES_PASSWORD)" \
	    -var="valkey_password=$(VALKEY_PASSWORD)" \
	    -target=module.namespaces \
	    -target=module.postgres_dev \
	    -target=module.valkey_dev \
	    -target=module.supabase_studio_dev \
	    -target=module.traefik_stack \
	    -out=$(LOG_DIR_ABS)/pass2.tfplan
	@echo "Plan written to $(LOG_DIR_ABS)/pass2.tfplan"

# ---------------------------------------------------------------------------
# tf-apply-pass2 — apply the saved pass2 plan (requires confirmation)
# Run tf-plan-pass2 first. Prompts for interactive yes/N confirmation.
# ---------------------------------------------------------------------------
tf-apply-pass2: tf-preflight
	@if [ ! -f "$(LOG_DIR_ABS)/pass2.tfplan" ]; then \
	  echo "ERROR: $(LOG_DIR_ABS)/pass2.tfplan not found. Run tf-plan-pass2 first." >&2; \
	  exit 1; \
	fi
	@mkdir -p $(LOG_DIR_ABS)
	@LOG_FILE=$(LOG_DIR_ABS)/$(shell date -u +%Y%m%dT%H%M%SZ)-tf-apply-pass2.log; \
	  echo "[$(shell date -u +%Y-%m-%dT%H:%M:%SZ)] target=tf-apply-pass2" >> $$LOG_FILE; \
	  echo "Plan sha256: $$(shasum -a 256 $(LOG_DIR_ABS)/pass2.tfplan | awk '{print $$1}')" >> $$LOG_FILE
	@read -p "Apply Pass 2? [yes/N] " ans && [ "$$ans" = "yes" ] || { echo "Aborted."; exit 1; }
	cd $(TF_DIR) && \
	  KUBECONFIG=$(HOME)/.kube/meesell-dev.yaml \
	  CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	  CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	  terraform apply $(LOG_DIR_ABS)/pass2.tfplan

# ---------------------------------------------------------------------------
# tf-destroy-check — dry-run destroy to see what would be deleted
# Fails the target (exit 1) if any prevent_destroy resource would be destroyed.
# Safe to run — does NOT apply any changes.
# Requires: FOUNDER_IP env var.
# ---------------------------------------------------------------------------
tf-destroy-check: tf-preflight
	@if [ -z "$(FOUNDER_IP)" ]; then \
	  echo "ERROR: FOUNDER_IP is not set. Run: export FOUNDER_IP=\$$(curl -4 ifconfig.me)" >&2; \
	  exit 1; \
	fi
	@mkdir -p $(LOG_DIR_ABS)
	@echo "Running destroy dry-run. This does NOT apply any changes."
	CLOUDSDK_CORE_ACCOUNT=$(EXPECTED_ACCOUNT) \
	CLOUDSDK_CORE_PROJECT=$(EXPECTED_PROJECT) \
	  terraform -chdir=$(TF_DIR) plan \
	    -destroy \
	    -var-file=environments/dev.tfvars \
	    \
	    2>&1 | tee $(LOG_DIR_ABS)/destroy-check.log | grep -E "(prevent_destroy|will be destroyed|google_)" || true
	@echo ""
	@echo "Full destroy plan written to $(LOG_DIR_ABS)/destroy-check.log"
	@if grep -q "prevent_destroy" $(LOG_DIR_ABS)/destroy-check.log 2>/dev/null; then \
	  echo "WARN: One or more resources have prevent_destroy = true." \
	       "Terraform will refuse to destroy them unless you remove that flag." >&2; \
	fi
