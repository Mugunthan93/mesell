# MeeSell Operational Runbooks

Index of infra/ops runbooks. Each runbook is a deploy-time / ops-time procedure —
nothing in a runbook is executed during a manifests/docs authoring session.

**Owner:** `meesell-infra-builder` (infra lead). Runbooks are appended as features land.

| Runbook | Feature | Scope |
|---|---|---|
| [`auth-secret-rotation.md`](auth-secret-rotation.md) | auth-otp (Feature 1) | Rotation of the `refresh-token-pepper` Secret Manager secret + dual-pepper grace window + emergency refresh-session mass-revocation. |
| [`image-pipeline-troubleshooting.md`](image-pipeline-troubleshooting.md) | image-precheck (Feature 5) | Stuck/failed pre-check Celery job introspection, re-enqueue, GCS tenant-isolation verification (D2 Gate 3), and `meesell-images` cost monitoring. |
| [`razorpay-golive.md`](razorpay-golive.md) | razorpay-integration (PR #323) | Razorpay subscriptions go-live: Celery `beat` deploy (`k8s/beat.yaml`, first beat_schedule), the 9 `RAZORPAY_*` secrets + 5 dashboard Plan ids, webhook registration, the checkout.js CSP allowlist, and the ordered go-live + rollback checklist. |

## Conventions

- Always scope `kubectl` with `-n <namespace>` (`dev` | `staging`). `prod` does not
  exist until V1.5 (repo MASTER §3.1).
- Never paste secret values into a runbook, a PR, or a log.
- Companion source-of-truth docs: `docs/INFRASTRUCTURE_PLAYBOOK.md` (manual procedures),
  `docs/INFRASTRUCTURE_ARCHITECTURE.md` (live infra SSOT),
  `docs/DEVOPS_ARCHITECTURE.md` (CI/CD).
