---
name: project_gcp_account
description: GCP project for MeeSell is under vaishnaviramoorthy@gmail.com — always use this account for ADC, gcloud, and IAM operations
metadata:
  type: project
---

GCP project `project-1f5cbf72-2820-4cdb-949` is owned by `vaishnaviramoorthy@gmail.com`.

**Why:** The environment was migrated from `mugunthanks93@gmail.com` to `vaishnaviramoorthy@gmail.com`. The `vaishnaviramoorthy` account is the active gcloud account locally and owns the GCS bucket `meesell-dev` and the GCP VM at `34.93.9.139`.

**How to apply:**
- Always use `vaishnaviramoorthy@gmail.com` as the active gcloud account for MeeSell operations
- ADC on the GCP VM (`/home/mugunthansrinivasan/gcp-adc.json`) must be the credentials for `vaishnaviramoorthy@gmail.com` — copy from `~/.config/gcloud/application_default_credentials.json` (local) when refreshing
- If a 403 GCS error references `mugunthanks93@gmail.com`, it means the ADC on the VM is stale — re-copy the local ADC to the VM and restart the worker
- `GOOGLE_APPLICATION_CREDENTIALS=/home/mugunthansrinivasan/gcp-adc.json` must be set as a shell env var when starting the Celery worker (not in .env — pydantic forbids extra fields)
