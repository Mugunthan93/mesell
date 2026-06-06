---
name: reference-surface-to-doc-mapping
description: Quick lookup — which legal document closes which system surface in MeeSell V1
metadata:
  type: reference
---

# Surface → Legal Document Mapping (quick reference)

Source: `docs/LEGAL_ARCHITECTURE.md` §14 traceability matrix.

| If a code change touches… | Update these docs |
|---|---|
| `iam` module / OTP / consent UI | Privacy Policy §"What we collect" + §"Your rights"; ToS §"Account & Eligibility"; in-product consent string |
| `customer` module / seller profile | Privacy Policy §"What we collect"; ToS §"Seller Representations" |
| `compliance_extensions` JSONB (any super-category) | Privacy Policy §"What we collect"; ToS §"Seller Representations" + per-statute disclaimer (LEGAL_ARCHITECTURE §13) |
| `catalog` module / products | Privacy + ToS §"Acceptable Use" + §"IP" |
| AI Auto-fill / Smart Picker / Gemini call site | Privacy §"AI processing" + §"Cross-border"; ToS §"AI Output IP"; DPA Annex 2 sub-processor (Gemini) |
| `image` module / GCS upload | Privacy §"What we collect"; ToS §"Acceptable Use" + §"Takedown procedure" |
| Pricing surface / GST display | ToS §"Payment Terms" + §"Pricing"; Refund Policy §"Eligibility"; Invoice Template |
| `export` module / XLSX generation | Privacy §"How we use"; ToS §"Service Description" + §"Data Portability" |
| `audit_events` write path | Privacy §"How long we keep" + §"How we protect" |
| Auth tokens (FE-D5 model) | Privacy §"How we protect"; Cookie Policy §"Functional cookies"; DPA Annex 2 TOMs |
| Razorpay webhook / payment flow | Privacy §"Who we share with"; ToS §"Payment Terms"; Refund Policy §"Refund process"; DPA Annex 1 sub-processor |
| Sub-processor change (add/remove vendor) | Privacy §"Who we share with"; DPA Annex 1; sub-processor register §4 of LEGAL_ARCHITECTURE |
| Tenant-isolation change (RLS migration etc.) | Privacy §"How we protect"; DPA Annex 2 TOMs |
| Data-subject rights workflow change | Privacy §"Your rights" SLA; ToS §"Termination"; DPA Annex 4 |
| Breach detected | Breach Response Runbook + notifications per LEGAL_ARCHITECTURE §8 |
| Retention period change (any table) | Privacy §"How long we keep"; DPA Annex 3 |
| Grievance Officer contact change | Privacy footer; ToS §"Notices"; in-product footer; Refund Policy §"Refund disputes"; DPA Annex 4 |
| Takedown procedure | ToS §"Takedown procedure" only (IT Act §79 safe-harbour) |

## Use this map
Whenever a feature ticket arrives, scan the change description, look up the touched surface, and update the corresponding legal docs in the SAME PR. Drifting legal docs from system reality is the #1 cause of audit findings.
