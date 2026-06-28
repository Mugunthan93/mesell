## Secret Manager Population Status — 2026-06-04

GCP project: `project-1f5cbf72-2820-4cdb-949` (numeric: `888244156264`)
Secret Manager secrets created in Pass 1. Populate via:
`gcloud secrets versions add <secret-id> --project=project-1f5cbf72-2820-4cdb-949 --data-file=- <<< "$VALUE"`
Local backup directory: `~/.meesell-secrets/` (chmod 700, each file chmod 600)

| Secret ID | Status | Notes |
|-----------|--------|-------|
| `msg91-auth-key` | ✅ VERSION 1 LIVE | Service name: DEVOTP. IP whitelisted: 122.164.85.200 (NOTE: founder IP rotated to 122.164.85.51 on 2026-06-05 — MSG91 whitelist may need update if OTP calls fail). Local backup: ~/.meesell-secrets/msg91-auth-key |
| `msg91-template-id` | ✅ VERSION 1 LIVE (2026-06-05) | Sourced from R&D meesell-msg91-template-id (11 chars). Phase A. |
| `gemini-api-key` | ✅ VERSION 1 LIVE | AIzaSyB... (populated 2026-06-04). Local backup: ~/.meesell-secrets/gemini-api-key |
| `jwt-secret` | ✅ VERSION 1 LIVE | Auto-generated 64-byte hex (openssl rand -hex 64). Local backup: ~/.meesell-secrets/jwt-secret |
| `razorpay-key-id` | ✅ VERSION 2 LIVE (2026-06-09) | TEST key (rzp_test_*). v1+v2 both ENABLED; `latest`=v2 (23 bytes, no trailing newline, hexdump-verified). Rotated 2026-06-09. Local backup: ~/.meesell-secrets/razorpay-key-id |
| `razorpay-key-secret` | ✅ VERSION 2 LIVE (2026-06-09) | TEST secret. v1+v2 both ENABLED; `latest`=v2 (24 bytes, no trailing newline). Rotated 2026-06-09. Local backup: ~/.meesell-secrets/razorpay-key-secret |
| `audit-pii-salt` | ✅ VERSION 1 LIVE (2026-06-05) | Generated `openssl rand -hex 32` (64 chars). Local backup: ~/.meesell-secrets/audit-pii-salt (chmod 600). Phase A. |

Verify any secret: `gcloud secrets versions access latest --secret=<id> --project=project-1f5cbf72-2820-4cdb-949`

---
