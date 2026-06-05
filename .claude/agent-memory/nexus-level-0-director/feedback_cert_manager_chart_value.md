---
name: feedback-cert-manager-chart-value
description: cert-manager Helm chart CRD config key changed between v1.14 and v1.15 — wrong key silently skips CRD install and fails post-install Job
metadata:
  type: feedback
---

When pinning cert-manager Helm chart by version, the chart value name for CRD installation differs:

- **v1.14.x and earlier**: `installCRDs = true` (boolean)
- **v1.15.x and later**: `crds.enabled = true` + optional `crds.keep = true` (nested)

**Why:** A wrong key is SILENTLY IGNORED by Helm (no error, no warning). With CRDs missing, the cert-manager controller pods come up Running but no API resources are registered — `kubectl api-resources --api-group=cert-manager.io` returns empty. The Helm post-install Job `cert-manager-startupapicheck` then fails with `BackoffLimitExceeded` because it tries to call the missing API. The whole release ends up `status=failed`.

**How to apply:** When writing `helm_release` for cert-manager:
1. Look at `var.chart_version` first. If it starts with `v1.14`, use `installCRDs`. If `v1.15+`, use `crds.enabled`.
2. Also set `startupapicheck.enabled = false` if the cluster has slow webhook startup (saves time, no functional loss — controller readiness probes are enough).
3. After apply, ALWAYS verify CRDs:
   ```
   kubectl get crd | grep cert-manager
   kubectl api-resources --api-group=cert-manager.io
   ```
   Both must show 6 resources (Certificate, ClusterIssuer, Issuer, CertificateRequest, Order, Challenge).
4. If CRDs are missing despite Helm reporting deployed: chart value name is wrong.

Recovery from failed release: `terraform apply -replace=module.cert_manager.helm_release.cert_manager` after fixing the config — clean destroy + create through Terraform's normal flow, no state surgery needed.

Related: see [[reference-namecheap-lookup]] for the broader Pass 2b context.
