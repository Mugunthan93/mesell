---
name: project-mesell-billing-inr
description: MeeSell GCP billing account 01620D-6785AB-0E4698 is INR-denominated — google_billing_budget needs currency_code INR, not USD
metadata:
  type: project
---

MeeSell GCP project `project-1f5cbf72-2820-4cdb-949` uses billing account `01620D-6785AB-0E4698` which is denominated in **INR** (Indian Rupees), confirmed via the Cloud Billing API (`currencyCode: "INR"`). Discovered 2026-06-04 during Pass 1 apply when `google_billing_budget` failed with 400 due to USD/INR currency mismatch.

**Why:** Free credit accounts created in India are INR-denominated. The $300 free credit shows up as roughly ₹25,000 in the account.

**How to apply:** Any `google_billing_budget` resource against this billing account MUST use `currency_code = "INR"` and amounts in INR. ₹25,000 ≈ $300 ≈ free-credit-equivalent. Do not assume USD for any GCP billing budget on Indian projects — always query the billing account currency first via `curl https://cloudbilling.googleapis.com/v1/billingAccounts/<id>` before writing the resource.

Related: see [[feedback-gcp-adc-refresh]] for ADC token handling on this machine.
