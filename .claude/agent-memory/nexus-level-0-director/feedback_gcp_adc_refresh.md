---
name: feedback-gcp-adc-refresh
description: Local GCP ADC credentials go stale — terraform apply needs GOOGLE_OAUTH_ACCESS_TOKEN workaround or re-login
metadata:
  type: feedback
---

ADC credentials at `~/.config/gcloud/application_default_credentials.json` on this machine go stale (empty `account` field). Last confirmed stale: 2026-05-31.

**Why:** `gcloud auth application-default login` was not refreshed. The file exists but has no valid account, causing `terraform apply` and other GCP SDK calls to fail silently or with auth errors.

**How to apply:** Before any `terraform apply` for the mesell project, check if ADC is fresh:
```bash
gcloud auth application-default print-access-token 2>/dev/null || echo "STALE"
```
If stale, either:
- Interactive refresh: `gcloud auth application-default login`
- One-shot workaround: `GOOGLE_OAUTH_ACCESS_TOKEN=$(gcloud auth print-access-token) terraform apply`
  (requires `gcloud auth login` as vaishnaviramoorthy@gmail.com to be current)
