# In-Product Compliance Strings — Hand-Off Pack

**Operator:** **Stellaxis** `[ENTITY SUFFIX]` operating the **MeeSell** service
**For:** `meesell-angular-component-builder` (wires copy into the Angular 18 components per `docs/FRONTEND_ARCHITECTURE.md`)
**Status:** DRAFT — copy locked by `meesell-legal-writer`; wiring is the FE specialist's scope
**Drafted by:** `meesell-legal-writer` 2026-06-05
**Source:** `docs/LEGAL_ARCHITECTURE.md` §7, §11, §13, §14; `docs/legal/privacy-policy.md`; `docs/legal/terms-of-service.md`; `docs/legal/refund-policy.md`; `docs/legal/cookie-policy.md`

> **What this document is:**
> Every string in this pack appears somewhere in the user interface and carries a legal or compliance obligation. The wording is **locked by legal-writer**; the FE specialist is expected to wire each string into the right component without paraphrasing.
>
> **What this document is not:**
> A complete UI copy spec. Non-compliance strings (feature labels, button text, tooltips on neutral UI) are the FE designer / UI styler's scope.

---

## 1. Where each string lives

Per `docs/FRONTEND_ARCHITECTURE.md` §2 feature catalog. The 10 feature folders touched by this pack:

| Feature folder | Surface | Strings in this pack |
|---|---|---|
| `auth` | Signup OTP screen, login screen | §2 (Consent UI) |
| `onboarding` | First-time profile fill | §3 (Profile collection notices) |
| `dashboard` | Account settings → rights surfaces | §4 (Data-subject rights surfaces) |
| `catalog-form` | AI Auto-fill, draft autosave | §5 (AI labels) |
| `images` | Upload error messages | §6 (Image error wording) |
| `pricing` | Pricing page | §7 (Tier + refund display) |
| `export` | Export ready notification | §8 (Export disclaimer) |
| `landing` | Footer | §9 (Grievance Officer footer) |
| (root) | Cookie banner | §10 (V1 = no banner; V1.5 reservation) |
| (transactional email) | Email From-name, billing notices | §11 (Email From + billing copy) |

All strings are Transloco-keyed (per `docs/FRONTEND_ARCHITECTURE.md` §6 i18n) under namespace `legal.*`. V1 ships English only.

---

## 2. Consent UI (signup OTP screen)

Surface: `auth` feature → signup component, **below** the OTP input, **above** the "Verify" CTA.

### 2.1 Consent checkbox — explicit opt-in (NOT pre-ticked)

> **Component:** `<mat-checkbox>` with `[required]` form-control validation; submit disabled until checked.

```
[ ] I confirm that I am 18 years or older and that I have read and agree to the
    MeeSell Privacy Policy and Terms of Service.
```

**Links inside the checkbox label:**
- "Privacy Policy" → `https://www.meesell.in/legal/privacy-policy` (new tab)
- "Terms of Service" → `https://www.meesell.in/legal/terms-of-service` (new tab)

Transloco keys:
```json
{
  "legal.consent.checkbox_label": "I confirm that I am 18 years or older and that I have read and agree to the MeeSell {privacyLink} and {termsLink}.",
  "legal.consent.privacy_link_text": "Privacy Policy",
  "legal.consent.terms_link_text": "Terms of Service"
}
```

**DPDP requirement (DPDP §6):** consent must be free, specific, informed, unconditional, unambiguous. The pre-ticked checkbox or the implicit "by continuing you agree..." pattern is **not valid**. The checkbox MUST be explicit and MUST be the form gate.

### 2.2 Validation error if user tries to submit without ticking

```
Please review and accept the Privacy Policy and Terms of Service to continue.
```

Transloco key: `legal.consent.validation_required`

### 2.3 Consent receipt audit event

When the form submits, the backend (`iam` module per BEA §2.1) writes an `audit_events` row with:

```json
{
  "event_type": "auth.consent",
  "user_id": "<uuid>",
  "metadata_jsonb": {
    "privacy_policy_version": "v1.0",
    "tos_version": "v1.0",
    "consent_method": "explicit_checkbox",
    "ip": "<ip>",
    "user_agent": "<ua>",
    "timestamp": "<iso8601>"
  }
}
```

**Backend hand-off:** `auth.consent` is one of the 4 new event_types queued for `meesell-backend-coordinator` (per LEGAL_ARCHITECTURE §10). Wire after backend ships.

---

## 3. Profile collection notices (onboarding)

Surface: `onboarding` feature → seller-profile component, displayed as a one-time info-box at the top of the form on the first onboarding session.

### 3.1 Legal Metrology data collection notice

```
Why we collect this:
The manufacturer, packer, importer, and country-of-origin details below are
mandatory under the Legal Metrology (Packaged Commodities) Rules 2011 for every
product you sell on Meesho. We collect them once here and place them
automatically on every catalog you export, so you do not have to re-enter them
per product.
```

Transloco key: `legal.profile.legal_metrology_notice`

### 3.2 Statutory identifier notice (per super-category)

Shown when the seller picks a super-category that requires statutory data (Grocery → FSSAI, Kids & Toys → BIS, etc.).

```
Why we ask for {identifier_name}:
This identifier is mandatory under {statute_name} for products in
{super_category_name}. You are responsible for the accuracy and currency of the
number you enter. MeeSell does not verify it against the regulator's register.
```

Variables (filled at runtime):
- `{identifier_name}` — e.g., "FSSAI Licence Number"
- `{statute_name}` — e.g., "the Food Safety and Standards Act 2006"
- `{super_category_name}` — e.g., "Grocery"

Transloco key: `legal.profile.statutory_identifier_notice`

### 3.3 GSTIN collection notice (optional field)

```
GSTIN (optional):
Enter your GSTIN if you want GST-compliant invoices issued to your business
name for input credit. If you leave this blank, invoices are issued as B2C.
```

Transloco key: `legal.profile.gstin_optional_notice`

---

## 4. Data-subject rights surfaces (Account Settings)

Surface: `dashboard` feature → account-settings component, "Privacy & Rights" section.

> **V1 limitation:** Self-serve buttons for Access / Erasure / Withdrawal / Nomination are NOT wired. All actions route to the Grievance Officer email with a pre-filled subject. V1.5 wires the self-serve endpoints (`docs/LEGAL_ARCHITECTURE.md` §16).

### 4.1 Right to Access — "Download my data"

```
Right to Access (Download my data)

Email our Grievance Officer with the subject "Data access request". We will
send you a copy of all personal data we hold about you, in a structured
electronic format, within 7 calendar days.
```

**Button:** "Email Grievance Officer" → `mailto:grievance@meesell.in?subject=Data%20access%20request&body=...` (pre-filled body with user_id and request type).

Transloco key: `legal.rights.access_description`

### 4.2 Right to Correction — "Correct my data"

Most fields editable directly in the form. For fields that cannot be edited:

```
Right to Correction

You can edit most of your data directly above. For information you cannot
edit here, email our Grievance Officer with the subject "Correction request"
and we will action it within 7 calendar days.
```

Transloco key: `legal.rights.correction_description`

### 4.3 Right to Erasure — "Delete my account"

```
Right to Erasure (Delete my account)

When you delete your account:
  • Your profile and catalogs are deleted within 30 days (target 7 days).
  • Your invoices and audit logs are retained for legal compliance, with
    your personal identifiers removed.
  • Once deleted, your account cannot be restored. You will need to sign up
    fresh to use MeeSell again.

To delete your account, email our Grievance Officer with the subject
"Account deletion request". We will acknowledge within 72 hours and complete
the deletion within 30 days (target 7 days).
```

**Button:** "Email Grievance Officer" → `mailto:grievance@meesell.in?subject=Account%20deletion%20request&body=...`

Transloco key: `legal.rights.erasure_description`

### 4.4 Right to Withdraw Consent

```
Right to Withdraw Consent

You may withdraw your consent to the processing of your personal data at any
time. Note that withdrawal of consent will usually mean we can no longer
provide the MeeSell service to you — the service requires processing your
data to function. We will explain the consequence in our reply.

To withdraw consent, email our Grievance Officer with the subject
"Withdraw consent".
```

Transloco key: `legal.rights.withdraw_description`

### 4.5 Right to Nominate (V1 manual)

```
Right to Nominate

You may nominate a person to exercise your rights in the event of your death
or incapacity. We do not yet offer a self-service nomination form (planned
for V1.5). To register a nomination today, email our Grievance Officer with
the subject "Nominate".
```

Transloco key: `legal.rights.nominate_description`

### 4.6 Right to Portability

```
Right to Portability

You can download your catalog data at any time using our standard Export
feature (Meesho-format XLSX). For your personal data in a different format,
email our Grievance Officer with the subject "Portability request". We will
provide it within 7 calendar days.
```

Transloco key: `legal.rights.portability_description`

### 4.7 Right to Grievance Redress

```
Right to Grievance Redress

For any complaint about how we handle your personal data, contact our
Grievance Officer. We will acknowledge within 24 to 72 hours and resolve
within 7 calendar days. If you are not satisfied, you may approach the
Data Protection Board of India.
```

Transloco key: `legal.rights.grievance_description`

---

## 5. AI feature labels (catalog-form)

Surface: `catalog-form` feature → catalog-form component, on every AI Auto-fill suggestion + on every Smart Picker recommendation card.

### 5.1 AI suggestion banner (above any AI-generated text field)

```
AI suggestion — review before saving
This text was generated by Google Gemini. You retain all rights to it.
```

Transloco key: `legal.ai.suggestion_label`

### 5.2 Smart Picker disclaimer (below the 5-card suggestion list)

```
Suggestions are ranked by Google Gemini based on your description.
You make the final choice.
```

Transloco key: `legal.ai.picker_disclaimer`

### 5.3 Watermark detection notice (image upload)

```
Watermark detected (advisory).
We flagged a possible watermark on this image. Watermark detection is not
perfect — you decide whether the image is yours to use. Re-upload a clean
version if you want to remove this flag.
```

Transloco key: `legal.ai.watermark_advisory`

---

## 6. Image error wording (images feature)

Surface: `images` feature → image-upload component, error toast messages.

| Trigger | String | Transloco key |
|---|---|---|
| File not JPEG | "Please upload a JPEG image. We do not accept PNG, GIF, or other formats." | `legal.image.error_not_jpeg` |
| CMYK colour space | "This image uses CMYK colours. Meesho requires RGB. Please re-export as RGB and upload again." | `legal.image.error_cmyk` |
| Resolution below 1500×1500 | "This image is too small. Meesho requires at least 1500×1500 pixels." | `legal.image.error_resolution` |
| Background not white | "The product background is not white. Meesho requires a clean white background." | `legal.image.error_background` |
| File size over 10 MB | "This image is larger than 10 MB. Please compress it and try again." | `legal.image.error_filesize` |

None of these errors carry IP / liability copy — they are operational.

---

## 7. Pricing page display (pricing feature)

Surface: `pricing` feature → public landing pricing component (not the in-product calculator).

### 7.1 Tier prices

Display "₹499 / month incl. GST" — never "₹499 + GST" (per §15.7 ratified).

| Tier | Display |
|---|---|
| Free Forever | ₹0 — **Free Forever** |
| Pro | **₹499 / month** incl. GST |
| Business | **₹1,999 / month** incl. GST |
| Lifetime Deal | **₹4,999 one-time** incl. GST · capped at 1,000 spots |

### 7.2 Refund tile (below the tier cards)

```
Refunds

  • Monthly subscriptions: cancel any time; no partial-month refund.
  • Lifetime Deal: 7-day money-back guarantee from purchase confirmation.
  • Full details in our Refund Policy.
```

"Refund Policy" → `https://www.meesell.in/legal/refund-policy`.

Transloco key: `legal.pricing.refund_summary`

### 7.3 GST note (footer of pricing page)

```
All prices are in Indian Rupees and inclusive of 18% GST.
A GST tax invoice is issued for every paid transaction.
GSTIN: [will display Stellaxis's GSTIN once registered]
```

Transloco key: `legal.pricing.gst_footer`

---

## 8. Export disclaimer (export feature)

Surface: `export` feature → export-ready notification component (shown immediately after the XLSX file is generated).

```
Your catalog XLSX is ready.

  • You upload this file to Meesho yourself. MeeSell does not upload on your
    behalf.
  • Statutory identifiers (FSSAI, BIS, etc.) are taken directly from your
    profile — you are responsible for their accuracy.
  • Your catalog data may also have been processed by Google Gemini if you
    used AI features. See our Privacy Policy.

[Download XLSX]   [Open in Meesho seller panel ↗]
```

Transloco key: `legal.export.disclaimer`

---

## 9. Grievance Officer footer (every page)

Surface: `landing` feature → footer component (shared across the entire application).

```
Grievance Officer

  [FOUNDER: Name on PAN]
  Email: grievance@meesell.in
  Response: within 7 calendar days
  Address: [FOUNDER: Stellaxis registered business address]
```

Transloco key: `legal.footer.grievance_officer`

**Layout:** small block, bottom-right of the footer; visible on every page including the landing page. **Pre-incorporation: the `[FOUNDER:` placeholders display literally — that is acceptable on `dev.mesell.xyz` and `staging.mesell.xyz` but MUST be resolved before `www.mesell.in` goes public.**

---

## 10. Cookie banner (V1 = none; V1.5 reservation)

Per `docs/legal/cookie-policy.md` §4: V1 uses strictly-necessary cookies only, no banner needed.

**Forward reservation:** when V1.5 adds analytics / marketing cookies, the FE component spec is:

```
[Cookie Banner — V1.5 only — to be implemented when analytics lands]

Layout: sticky bottom-left of viewport
Buttons: "Accept all"  |  "Reject all"  |  "Preferences"  →  per-category opt-in
Default state: all non-essential cookies blocked until user clicks "Accept"
```

No V1 work for the FE specialist — but reserve `legal.cookie_banner.*` Transloco namespace.

---

## 11. Transactional email From + billing copy

Surface: `meesell-services-builder` (backend) issues transactional email; `meesell-angular-component-builder` does not own this. **Listed here for source-of-truth completeness; coordination required with backend.**

### 11.1 From-name and From-email

```
From: "MeeSell" <support@meesell.in>
Reply-To: support@meesell.in
```

The product brand "MeeSell" goes in the visible From-name for customer recognition. The legal operator Stellaxis is named in the email **body** footer.

### 11.2 Email body footer (every transactional email)

```
─────────────────────────────────────────
MeeSell is a service operated by Stellaxis [ENTITY SUFFIX]
[FOUNDER: Stellaxis registered business address]
GSTIN: [FOUNDER: Stellaxis GSTIN]

Privacy Policy: https://www.meesell.in/legal/privacy-policy
Terms of Service: https://www.meesell.in/legal/terms-of-service
Refund Policy: https://www.meesell.in/legal/refund-policy
Grievance: grievance@meesell.in

This is a transactional email. You are receiving it because you have an
active MeeSell account. We do not send marketing emails.
─────────────────────────────────────────
```

### 11.3 Billing email copy — payment success (Pro / Business monthly)

```
Subject: MeeSell — Payment received (₹{amount} incl. GST)

Hi [FirstName],

Thank you for your payment. Your MeeSell {tier_name} subscription is active
until {next_billing_date}.

Invoice: {invoice_number}     Amount: ₹{amount} incl. GST
Download invoice: {invoice_url}

To cancel, visit Account Settings → Subscription. Cancellation takes effect
at the end of the current billing cycle.

— MeeSell

[standard footer §11.2]
```

### 11.4 Billing email copy — payment success (LTD)

```
Subject: MeeSell — Lifetime Deal confirmed (₹4,999 incl. GST)

Hi [FirstName],

Welcome to MeeSell Lifetime. Your LTD purchase is confirmed (spot #{ltd_spot}
of 1,000).

Invoice: {invoice_number}     Amount: ₹4,999.00 incl. GST
Download invoice: {invoice_url}

You have a 7-day money-back guarantee on the LTD. To request a refund within
that window, reply to grievance@meesell.in with the subject "LTD refund".

After 7 days from this confirmation ({refund_cutoff}), the LTD is
non-refundable and your spot is permanently allocated.

— MeeSell

[standard footer §11.2]
```

### 11.5 Billing email copy — payment failed

```
Subject: MeeSell — We could not process your payment

Hi [FirstName],

Your MeeSell {tier_name} renewal payment failed. We will retry on
{retry_date}. Please ensure your payment method has sufficient funds.

To update your payment method, visit Account Settings → Subscription.

If the retries fail, your account will be downgraded to Free Forever at
the end of your current cycle on {downgrade_date}. Your catalog data
remains safe.

— MeeSell

[standard footer §11.2]
```

### 11.6 Billing email copy — downgrade to Free

```
Subject: MeeSell — Account downgraded to Free Forever

Hi [FirstName],

After repeated payment failures, your MeeSell {tier_name} subscription
ended on {downgrade_date}. Your account has been downgraded to Free
Forever.

Your catalog data is preserved. Sign in any time to view it.

To re-activate {tier_name}, visit Account Settings → Subscription and
update your payment method.

— MeeSell

[standard footer §11.2]
```

### 11.7 OTP email copy (fallback — V1 uses SMS only via MSG91; email OTP is V1.5)

(Not in V1 scope. Reserved namespace `legal.email.otp_*` for V1.5.)

---

## 12. String inventory summary (for the FE specialist)

| Section | Count | Component scope |
|---|---|---|
| Consent UI (§2) | 3 strings | `auth/signup` |
| Profile notices (§3) | 3 strings | `onboarding/profile` |
| Rights surfaces (§4) | 7 strings | `dashboard/account-settings` |
| AI labels (§5) | 3 strings | `catalog-form`, `smart-picker`, `images` |
| Image errors (§6) | 5 strings | `images/upload` |
| Pricing display (§7) | 3 strings | `pricing/landing` |
| Export disclaimer (§8) | 1 string | `export/ready-notification` |
| Grievance footer (§9) | 1 block | `landing/footer` (shared) |
| Cookie banner (§10) | 0 strings (V1.5) | reserved |
| Email body (§11) | 6 templates | `meesell-services-builder` (backend) |

**Total V1 strings owned by FE component-builder:** 26 single strings + 1 footer block + 1 reserved namespace.

---

## 13. Document control

| Field | Value |
|---|---|
| Document | In-Product Compliance Strings v1.0 |
| Operator | Stellaxis `[ENTITY SUFFIX]` |
| Status | DRAFT — copy locked by legal-writer; FE wires per spec |
| Drafted by | `meesell-legal-writer` 2026-06-05 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §7, §10, §11, §13, §14; `docs/legal/privacy-policy.md` §10, §12; `docs/legal/refund-policy.md` §4; `docs/legal/terms-of-service.md` §7; `docs/legal/cookie-policy.md` §3 |
| Founder placeholders | `[ENTITY SUFFIX]`, `[FOUNDER: Name on PAN]`, `[FOUNDER: Stellaxis registered business address]`, `[FOUNDER: Stellaxis GSTIN]` |
| Hand-off | `meesell-angular-component-builder` for §2-§10 wiring; `meesell-services-builder` for §11 email templates |
| Paired docs | All 4 published artifacts + DPA template (for any V1.5 enterprise customer-self-serve panel) |
