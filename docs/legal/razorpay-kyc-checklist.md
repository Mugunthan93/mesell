# Razorpay KYC Onboarding Checklist

> **Entity ruling 2026-06-11: OPC immediately. Sole Prop path removed.**

**Operator:** **Stellaxis (OPC) Private Limited** operating the **MeeSell** service
**Purpose:** Single checklist for Razorpay merchant onboarding — document set + name-match invariant + verification timeline + TEST → LIVE key rotation. **OPC path only** (§15.1 ruled OPC, founder ruling 2026-06-11).
**Status:** DRAFT — founder runbook; lawyer review not required (operational doc)
**Drafted by:** `meesell-legal-writer` 2026-06-05; single-pathed to OPC 2026-06-11
**Source:** `docs/LEGAL_ARCHITECTURE.md` §12.1 + §12.2; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §5; `docs/INFRASTRUCTURE_ARCHITECTURE.md` §4 (secret rotation)

> **When to use this checklist:**
> Stellaxis (OPC) Private Limited has completed incorporation as a One Person Company and is ready to activate **live** Razorpay payments. The 4 public-facing legal docs (Privacy, ToS, Refund, Cookie) must be live on `meesell.in` BEFORE starting Razorpay KYC — Razorpay verifies these as part of onboarding.

---

## 0. Prerequisites — must be true before starting

- [ ] Stellaxis (OPC) Private Limited is **legally incorporated** as an OPC (company PAN issued)
- [ ] **GST registration complete** (GSTIN issued, ~7-10 working days after application) — see `gst-registration-checklist.md`
- [ ] **Current Account** opened in Stellaxis's exact legal name
- [ ] **Privacy Policy, Terms of Service, Refund Policy, Cookie Policy** live at `https://www.meesell.in/legal/...` URLs with HTTPS
- [ ] **Contact Us page** live with `support@meesell.in` + Stellaxis's registered phone (optional but recommended)
- [ ] **Domain WHOIS** registered in Stellaxis's legal name (or WHOIS privacy enabled)
- [ ] The TEST Razorpay keys in `razorpay-key-id` and `razorpay-key-secret` GCP secrets (IA §4) are in place and the integration is verified end-to-end on `dev.mesell.xyz`

---

## 1. THE name-match rule (the #1 KYC rejection cause)

> **Per LACI §5.2:** The bank account holder name, the PAN name, the GSTIN legal name, and the Razorpay merchant name **MUST match EXACTLY, letter for letter**. Even "&" vs "and" causes rejection.

Pre-flight check:

```
[ ] PAN holder name (Stellaxis name on PAN card):       __________________________
[ ] Bank account holder name (Stellaxis name on cheque): __________________________
[ ] GSTIN legal name (Stellaxis name on GST cert):       __________________________
[ ] Razorpay merchant name (will be entered in form):    __________________________

ALL FOUR MUST BE IDENTICAL.
```

If any of the above mismatches: STOP. Resolve the mismatch (typically: re-issue the bank account name, or update the GSTIN legal name) **before** submitting to Razorpay. A rejected Razorpay application requires a fresh submission and resets the verification clock.

---

## 2. Document set — One Person Company (OPC)

Stellaxis (OPC) Private Limited is a One Person Company. Gather the OPC document set below.

### 2.1 Documents to gather

| # | Document | Source | Notes |
|---|---|---|---|
| 1 | **Company PAN** | Income Tax Department | Issued at incorporation in the company name |
| 2 | **Certificate of Incorporation** | Ministry of Corporate Affairs (MCA) | Issued by Registrar of Companies |
| 3 | **MOA (Memorandum of Association)** | MCA | Authorised business activities + Stellaxis (OPC) Private Limited name |
| 4 | **AOA (Articles of Association)** | MCA | Internal governance — required for OPC |
| 5 | **Director's PAN + Aadhaar** | Income Tax + UIDAI | Founder, as the sole director |
| 6 | **GST certificate** | gst.gov.in | Mandatory once registered |
| 7 | **Cancelled cheque in company name** | Bank | Must show printed company name = PAN name = GSTIN name |
| 8 | **Registered office address proof** | Various — see below | |
| 9 | **Director's photograph** | — | JPEG / PNG |
| 10 | **Board Resolution** | Stellaxis internal | Authorising the director to onboard with Razorpay (sample template available from Razorpay docs) |
| 11 | **Nominee details** | MCA filing | Required for OPC — nominee PAN + Aadhaar + consent letter |

### 2.2 Registered office address proof — pick one

- [ ] **Rent agreement** + recent **electricity bill** (last 3 months) — if leased
- [ ] **Property tax receipt** + **NOC from owner** — if owned by founder
- [ ] **Property document** — if owned by Stellaxis (OPC) Private Limited

### 2.3 Website requirements (already live before KYC)

- [ ] `https://www.meesell.in/legal/privacy-policy` — 200 OK, content matches `docs/legal/privacy-policy.md` (placeholders resolved)
- [ ] `https://www.meesell.in/legal/terms-of-service` — same
- [ ] `https://www.meesell.in/legal/refund-policy` — same
- [ ] `https://www.meesell.in/legal/cookie-policy` — same
- [ ] `https://www.meesell.in/contact` — Contact Us with `support@meesell.in` + `grievance@meesell.in` + Stellaxis (OPC) Private Limited's registered address

The legal documents themselves carry `Stellaxis (OPC) Private Limited` matching the registered entity.

---

## 4. Razorpay merchant setup form — field-by-field

When filling the Razorpay sign-up form at `https://dashboard.razorpay.com/signup`:

| Field | Value to enter | Source |
|---|---|---|
| **Business name (legal)** | `Stellaxis (OPC) Private Limited` — exact match with PAN / GST / bank | §1 above |
| **Business type** | "OPC" (One Person Company) | §15.1 ruling — OPC |
| **Display name (customer-facing)** | "MeeSell" | Product brand — `reference_brand_vs_legal_name.md` |
| **Industry** | "Software / SaaS" | Service category |
| **Website URL** | `https://www.meesell.in` | IA §7 |
| **Business description** | "MeeSell is a SaaS platform that helps Indian sellers prepare product catalogs for the Meesho marketplace. Operated by Stellaxis." | One-sentence — keep tight |
| **Monthly transaction volume estimate** | "Up to ₹5 lakh" — Year 1 estimate | PRICING_LOCKED §10 |
| **Average transaction value** | "₹499 - ₹4,999" | PRICING_LOCKED §5 |
| **Settlement bank account** | The Stellaxis Current Account opened in §0 | Must match cheque exactly |
| **GSTIN** | Stellaxis's GSTIN | From GST registration |
| **PAN** | Stellaxis's PAN | From PAN card |
| **Authorised signatory** | `[FOUNDER: Name on PAN]` (= founder) | |
| **Director DIN** | Founder's DIN (mandatory for OPC) | |

---

## 5. Verification timeline

Per LACI §5.3: **1 to 3 working days** from complete document submission to live activation. If Razorpay requests clarification, the clock resets to the resolution date.

Common delays:
- Name mismatch (§1) — instant rejection
- Blurry document scans — clarification request
- Missing Privacy / ToS / Refund URLs — clarification request
- Industry mismatch (e.g., MeeSell as "e-commerce" instead of "SaaS") — clarification request

---

## 6. After Razorpay activates — secrets rotation

Per `docs/INFRASTRUCTURE_ARCHITECTURE.md` §4, the TEST `razorpay-key-id` and `razorpay-key-secret` secrets must be replaced with LIVE values. Procedure:

```bash
# Apply on the founder workstation, with GCP auth active (per IA §12.2)
gcloud secrets versions add razorpay-key-id \
  --data-file=<(echo -n "<LIVE_KEY_ID>") \
  --project=project-1f5cbf72-2820-4cdb-949

gcloud secrets versions add razorpay-key-secret \
  --data-file=<(echo -n "<LIVE_KEY_SECRET>") \
  --project=project-1f5cbf72-2820-4cdb-949
```

Then trigger a rolling restart of the FastAPI deployment so pods pick up the new secret versions:

```bash
kubectl -n dev rollout restart deployment/api
kubectl -n dev rollout status deployment/api
```

Verify on the dev frontend (`dev.mesell.xyz`) that a TEST-mode subscription cannot be created any more (since the keys are now LIVE).

---

## 7. Webhook configuration

Razorpay webhook MUST be configured before going live. URL:

```
POST https://api.mesell.in/api/v1/webhooks/razorpay
```

- Webhook signature secret: separately issued by Razorpay; store in a new GCP secret `razorpay-webhook-secret` (to be added per IA §4 if not yet present)
- Events to subscribe: `subscription.charged`, `subscription.completed`, `subscription.cancelled`, `payment.failed`, `refund.processed`
- The `iam` module verifies signature on every webhook (BEA §1.E) — V1 captures payload only; V1.5 wires business logic

---

## 8. Post-activation checklist

- [ ] First live ₹1 test transaction succeeds end-to-end (use founder's personal card)
- [ ] First live refund succeeds (refund the ₹1 test transaction)
- [ ] Razorpay sub-merchant dashboard shows correct settlement account
- [ ] First settlement T+2 (working days) reaches Stellaxis Current Account
- [ ] First GST-compliant invoice is issued by Razorpay (cross-check against `invoice-template.md` field list)
- [ ] Webhook endpoint receives at least one event in production

---

## 9. Common rejection causes — pre-empt these

Per LACI §5 implicit + Razorpay community forums:

| Rejection cause | How to pre-empt |
|---|---|
| Name mismatch (PAN / GST / bank / merchant name not identical) | §1 pre-flight check |
| Missing or incorrect HTTPS | IA §7 — Let's Encrypt certs already live on all 5 subdomains |
| Privacy / ToS / Refund pages not live | Publish at `meesell.in/legal/...` before submitting |
| Industry category mismatch | Select "Software / SaaS", NOT "e-commerce" — MeeSell sells software, not goods |
| Pricing page lists non-INR currency | All pricing is in ₹ — confirmed in PRICING_LOCKED §5 and ToS §5.1 |
| Refund policy is "no refunds, all sales final" | We adopted Variant B (7-day money-back on LTD) — Razorpay accepts this comfortably |
| Bank account is Savings (not Current) | Must be Current Account |
| GSTIN not provided | Mandatory for OPC; obtain GSTIN first |

---

## 10. Document control

| Field | Value |
|---|---|
| Document | Razorpay KYC Onboarding Checklist v1.0 |
| Operator | Stellaxis (OPC) Private Limited |
| Status | DRAFT — operational runbook (no lawyer review required); OPC-only as of 2026-06-11 |
| Drafted by | `meesell-legal-writer` 2026-06-05; single-pathed to OPC 2026-06-11 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §12.1 + §12.2 + §15.1; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §5; `docs/INFRASTRUCTURE_ARCHITECTURE.md` §4 + §7 |
| Founder placeholders | `[FOUNDER: Name on PAN]` |
| Paired docs | `gst-registration-checklist.md` (prerequisite), `invoice-template.md` (consumed after onboarding) |
