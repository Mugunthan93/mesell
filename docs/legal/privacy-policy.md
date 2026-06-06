# Privacy Policy

**For:** **Stellaxis** `[ENTITY SUFFIX — fills in once §15.1 ruled]` operating the **MeeSell** service at `https://www.meesell.in`
**Effective date:** `[FOUNDER: publish date]`
**Last updated:** `[FOUNDER: publish date]`
**Version:** v1.0
**Status:** DRAFT for founder + Indian lawyer review — NOT YET PUBLISHED
**Drafted by:** `meesell-legal-writer` per `docs/LEGAL_ARCHITECTURE.md`

> **Founder action required before publishing:**
> 1. Confirm Legal Business Name (LEGAL_ARCHITECTURE §15 decision #8)
> 2. Confirm domain (default `www.meesell.in`)
> 3. ₹5,000-15,000 Indian lawyer review per LACI §3.4 step 3
> 4. Live HTTPS URL on the website footer
> 5. Linked from signup consent checkbox + footer of every page
>
> **[LAWYER REVIEW]** markers in this document flag clauses where Indian counsel should confirm wording before publication.

---

## 1. Who we are

**Stellaxis** `[ENTITY SUFFIX — fills in once §15.1 ruled]` (referred to in this policy as **"we"**, **"us"**, **"our"**, or by its product brand **"MeeSell"**) operates the MeeSell software-as-a-service platform (the **"Service"**) accessible at `https://meesell.in`. "Stellaxis" is our legal business name; "MeeSell" is the trade name under which we offer the Service.

MeeSell helps Indian sellers prepare product catalogs for upload to the Meesho marketplace. We are not Meesho. We are not affiliated with Meesho. We are an independent third-party service for sellers.

Under the **Digital Personal Data Protection Act 2023** (the **"DPDP Act"**), MeeSell is a **Data Fiduciary** for the personal data of the sellers who use our Service.

**Contact:** `support@meesell.in`
**Grievance Officer:** see Section 12.

---

## 2. What this policy covers

This policy explains:
- What personal data we collect from you
- Why we collect it and how we use it
- Who we share it with
- Where we store it
- How long we keep it
- How we protect it
- Your rights and how to exercise them
- How we notify you of changes

It applies to your use of our website, our application, and any communication you have with us by email, SMS, or in-product messaging.

---

## 3. What personal data we collect

We collect only what we need to provide the Service. We do not buy personal data from data brokers. We do not collect data from your device beyond what is needed to operate the Service.

### 3.1 Data you give us directly

| Category | Examples | Why we collect it |
|---|---|---|
| **Identity** | Your phone number (in international E.164 format such as +919876543210), and optionally your email address | To create your account, to send you one-time passwords (OTP) so you can log in, and to send transactional service notifications |
| **Business profile** | Your business name, manufacturer name and address, packer name and address, importer name and address (where applicable), 6-digit pincodes, country of origin | These are mandatory disclosures under the **Legal Metrology (Packaged Commodities) Rules 2011** for any product you sell on Meesho. We collect them so we can place them correctly on your Meesho catalog. |
| **Statutory identifiers** | FSSAI licence number, BIS / ISI certification number, R / IS / CM-L number, drug or cosmetic licence registration number, ISBN — depending on the categories you sell in | These are mandatory under category-specific Indian laws. We collect only the identifiers required for the super-categories you mark as active. |
| **Product content** | Product titles, descriptions, attributes (size, colour, fabric, etc.), images you upload | To build the catalog you want to upload to Meesho |
| **Pricing data** | Your cost, expected margin, MRP, your selling price | To compute Meesho commission and GST automatically |
| **Account preferences** | Your subscription plan, language preference (V1 ships English; Tamil and Hindi planned), notification settings | To deliver the Service correctly |

### 3.2 Data we collect automatically when you use the Service

| Category | Examples | Why we collect it |
|---|---|---|
| **Session data** | A short-lived access token (held only in your browser's memory, valid for at most 15 minutes), a separate longer-lived refresh token (held only in a secure browser-only cookie, never visible to JavaScript), and a server-side allowlist record that lets us revoke your session instantly | To keep you signed in safely; see Section 9 |
| **Security log data** | IP address, browser user agent, request ID, timestamp of significant actions (login, profile update, catalog export, account deletion request) | To detect unauthorised access, to investigate complaints, and to satisfy DPDP record-keeping obligations |
| **Image content metadata** | Image dimensions, colour space (RGB or CMYK), file format, presence of watermark (advisory) | To pre-check your images against Meesho's upload rules and reduce catalog rejection |

### 3.3 Data we **do not** collect

- We do **not** collect your card number, UPI ID, or bank account number. All payments are processed by Razorpay; we receive only a confirmation that you paid. **[LAWYER REVIEW]**
- We do **not** collect location data, contacts, calendar, or any other data from your device beyond the browser session.
- We do **not** collect data about your customers' end-consumers.
- We do **not** knowingly collect data from children. The Service is intended only for sellers aged 18 and above. If you become aware that a person under 18 has used the Service, please contact our Grievance Officer (Section 12) so we can delete the account.

### 3.4 Sensitive personal data

Under the **Information Technology (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules 2011**, we are aware that financial, biometric, sexual orientation, and similar categories qualify as **Sensitive Personal Data or Information ("SPDI")**. **The Service does not collect any SPDI.** Phone numbers are personal data under the DPDP Act but are not SPDI under the 2011 Rules. **[LAWYER REVIEW]**

---

## 4. Why we use your personal data

We use your personal data only for the purposes set out below. Each purpose has a lawful basis under the DPDP Act — primarily your **consent** given at signup (DPDP §6) and our **legitimate interest** in operating a secure service (DPDP §7).

| Purpose | Lawful basis | Data used |
|---|---|---|
| Authenticate you and keep your session secure | Consent + legitimate interest | Phone, OTP, session tokens, IP, user agent |
| Build, validate, and export your product catalog | Consent (the core service you signed up for) | Business profile, statutory identifiers, product content, images, pricing data |
| Pre-check your images and generate AI-suggested catalog text | Consent (you opted into AI features by using them) | Product titles, descriptions, image content — see Section 6 for cross-border note |
| Generate GST-compliant invoices and process subscription payments | Legal obligation (CGST Act + Razorpay merchant terms) + consent | Business name, GSTIN if applicable, plan tier |
| Detect and prevent fraud, unauthorised access, and abuse | Legitimate interest (DPDP §7) | Security log data, audit log entries |
| Respond to your support requests or grievances | Consent + legal obligation (DPDP §13) | Whatever you choose to send us with your request |
| Comply with Indian law, including DPDP Act, IT Act, GST law, and tax law | Legal obligation | Whichever data the specific obligation requires |

We do **not** use your personal data:
- To send you marketing email or SMS (Service v1.0 does not run marketing communications). If we add a marketing channel in a future version, we will ask you separately for opt-in consent and let you withdraw it at any time.
- To train artificial intelligence models. Your product text and images are passed to Google's Gemini API to generate suggestions for **your** catalog, not to train a model. Google's commitments on input/output handling apply; see Section 5 and Section 6.
- For automated decision-making that produces legal effects on you. Our suggestions are advisory; you decide what goes on your catalog.

---

## 5. Who we share your personal data with

We share your personal data only with the third-party service providers ("**sub-processors**") listed below. Each sub-processor receives only the data needed to perform their function, and each is contractually bound to handle that data securely.

| # | Sub-processor | What they do for us | What we share with them | Where they operate |
|---|---|---|---|---|
| 1 | **Razorpay Software Private Limited** (Bengaluru, India) | Process subscription payments and KYC. Razorpay is a Reserve Bank of India-licensed Payment Aggregator (PA-O) under the September 2025 RBI Master Directions. | Your business name, plan tier, payment instrument metadata (Razorpay holds the actual card / UPI details — we do not). | India |
| 2 | **Walkover Web Solutions Pvt Ltd (MSG91)** (Indore, India) | Send the one-time password (OTP) to your phone so you can log in | Your phone number + the OTP we issue | India |
| 3 | **Google Cloud India Pvt Ltd / Google LLC** — Google Cloud Platform (compute, networking, secret storage) | Host the servers that run the Service | All operational data at the platform layer | India (Mumbai region — primary), with control-plane support from Google globally |
| 4 | **Google Cloud India Pvt Ltd / Google LLC** — Google Cloud Storage | Store the images you upload, your generated XLSX exports, and archived audit logs | Image binaries, XLSX exports (which contain the data you put in your catalog), audit log archives (with personal data scrubbed before archival) | India (Mumbai region) |
| 5 | **Google LLC** — Gemini 2.5 Flash API | Generate AI-suggested catalog text and check uploaded images for watermarks | Product titles, descriptions, and image bytes you submit to the AI features | Google's multi-region infrastructure — see Section 6 |
| 6 | **Let's Encrypt (Internet Security Research Group)** | Issue and renew the TLS certificates that protect the connection between your browser and our servers | Our domain name only — no personal data of yours | United States — domain metadata only, no personal data transit |
| 7 | **Namecheap, Inc.** | Register and serve DNS for our domain | Domain name only — no personal data of yours | United States — DNS only, no personal data transit |
| 8 | **GitLab Inc.** | Host our source code and run our build/deployment automation | No personal data of sellers in V1.0; source code and operational metadata only | European Union / United States — source code, not seller data |

**We do not share your personal data with any other third party** except where required by Indian law (for example, a binding court order or a written direction from a competent authority). If we ever receive such a demand, we will, where lawfully permissible, notify you before disclosure.

**Sub-processor list may change.** When we add a sub-processor, we will update this list and the effective date at the top of the policy at least 30 days before the new sub-processor starts processing your data.

---

## 6. Cross-border transfer of your personal data

Some of our sub-processors process data outside India. Under **DPDP Act §16**, transfers outside India are permitted unless the Central Government restricts a specific country by notification; no restrictive list has been published at the time this policy was drafted. **[LAWYER REVIEW]**

| Sub-processor | Where the transfer goes | Why |
|---|---|---|
| Google Gemini API (sub-processor #5) | Google's multi-region infrastructure, which may include data centres outside India | The Gemini AI service routes inference workloads globally for capacity. The product text and image content you submit to AI features may briefly transit and be processed outside India. Google handles this data under its enterprise data-protection commitments. |

All other sub-processors store and process your data inside India (specifically, Google's `asia-south1` Mumbai region for compute and storage).

If you do not want your product text and image content to be transferred to Google's global infrastructure for AI processing, do not use the AI Auto-fill, Smart Category Picker, or AI Watermark Check features. The rest of the Service (manual catalog entry, image upload without AI vision check, manual category browse, export, billing) does not transmit your data outside India.

---

## 7. Where we store your personal data

Your personal data is stored in **Google Cloud's `asia-south1` Mumbai region** for all primary storage:
- The PostgreSQL database that holds your account, profile, catalog, and audit log records
- The Valkey cache that holds your session tokens and rate-limit counters
- The Google Cloud Storage bucket that holds your uploaded images, generated XLSX exports, and archived audit logs

Backups are stored in the same `asia-south1` region. We do not transfer backups outside India.

Only data submitted to the AI features (Section 6) leaves India during processing, and is not stored by Google outside India after processing completes per Google's API terms. **[LAWYER REVIEW]**

---

## 8. How long we keep your personal data

We follow the principle of **data minimisation** under DPDP §10: we keep personal data only as long as we need it for the purpose for which we collected it, plus any retention period required by law.

| Data | Retention |
|---|---|
| Your account record (phone, email, plan) | For as long as your account is open. On account deletion, anonymised within 30 days (target 7 days) — see Section 10. |
| Your seller profile (business name, manufacturer / packer / importer details, statutory identifiers) | Same as above. Deleted automatically when your account is deleted. |
| Your catalogs, products, and product images | Same as above for active records. Soft-deleted records (those you mark for deletion) are permanently purged 30 days after soft-deletion. |
| Your draft catalog entries (in-progress wizard state) | 30 days from your last edit, then automatically deleted. |
| Your generated XLSX exports | 1 year, then archived. Exports are retained even after account deletion to support refund and dispute resolution. The personal data identifying you in archived exports is unlinked from your account. |
| Audit log entries | 90 days in active database, then archived to Google Cloud Storage for 1 additional year. Personal data such as your phone number is hashed before any log entry is written; statutory identifiers are stripped. Audit logs are retained even after account deletion to satisfy DPDP §8(5) record-keeping obligations. |
| Session tokens (access JWT and refresh token) | Access JWT: maximum 15 minutes from issuance. Refresh token: maximum 7 days from issuance, deleted immediately on logout or session revocation. |
| Backups | Hot backups retained for 30 days; cold backups retained for 1 year. |
| Payment-related records held by Razorpay | Razorpay handles these per its own privacy policy at https://razorpay.com/privacy . MeeSell does not retain card or bank account numbers. |

Retention may be extended beyond the periods above when (a) we are subject to a legal hold or government order, or (b) data is needed to resolve an open dispute, claim, or investigation.

---

## 9. How we protect your personal data

We follow what we believe are **reasonable security practices and procedures** under **Information Technology Act 2000 §43A** and IT Rules 2011, scaled to the size and risk of our operation. Specific measures include: **[LAWYER REVIEW]**

**Transport security**
- All connections between your browser and our servers use TLS 1.2 or higher. We do not accept unencrypted HTTP traffic.
- TLS certificates are issued by Let's Encrypt and automatically renewed.

**Authentication and session security**
- We log you in via a one-time password (OTP) sent to your phone — no passwords to leak or be reused across services.
- Once you log in, your session is protected by a short-lived access token (15 minutes maximum) held only in your browser's memory.
- A separate refresh credential is delivered as a strict, secure, browser-only cookie (`HttpOnly`, `Secure`, `SameSite=Strict`) scoped narrowly to our authentication endpoints. JavaScript cannot read it.
- We keep a server-side allowlist of valid refresh credentials. When you log out, we revoke the allowlist entry immediately — even if someone has copied your refresh credential, it stops working at logout.
- Your tokens are never stored in browser local storage, session storage, or IndexedDB.
- Our token derivation uses HMAC-SHA256 with a private key held only on the server, so a server-cache breach alone cannot allow an attacker to validate stolen tokens.

**Data-at-rest security**
- Personal data in our database, cache, and object storage is encrypted at rest by Google Cloud Platform.
- Secrets (database passwords, API keys, signing keys) are held in Google Secret Manager with access restricted to our application's identity. No secrets are written into source code, container images, or configuration files.

**Tenant isolation**
- Every database query that reads or writes data you own is scoped by your account identifier. We use a single, centralised tenancy enforcement layer in our codebase, exercised by automated tests, to prevent any request from returning another seller's data.
- We are migrating to database-enforced row-level security (PostgreSQL RLS) in version 1.5. The application-layer scoping in version 1.0 is verified by integration tests in our continuous-integration pipeline.

**Audit and monitoring**
- We keep an append-only audit log of significant actions on every account.
- We scrub personal data (phone numbers are hashed; statutory identifiers are stripped) from the audit log before any entry is written.

**Personnel**
- Access to production data is limited to the founder. We will document additional access controls before our first employee or contractor joins.

**No security is absolute.** We cannot guarantee that our measures will defeat every possible attack. If a breach occurs that is likely to affect your personal data, we will follow Section 11.

---

## 10. Your rights

The DPDP Act gives you several rights over your personal data. Section 7 of `docs/LEGAL_ARCHITECTURE.md` describes how each right is wired into the Service. In summary:

### 10.1 Right to access — what data do we hold about you?
Email our Grievance Officer (Section 12) with the subject **"Data access request"**. We will send you a copy of the personal data we hold about you, in a structured electronic format, **within 7 calendar days**.

### 10.2 Right to correction
You can correct most of your data yourself in the Account Settings page. For data you cannot edit there, email our Grievance Officer with the subject **"Correction request"** and explain what needs to change. We will action it **within 7 calendar days**.

### 10.3 Right to erasure ("delete my account")
Email our Grievance Officer with the subject **"Account deletion request"**. We will:
1. Acknowledge your request within 72 hours, with a tracking reference.
2. Anonymise or delete the personal data we hold about you **within 30 calendar days (target 7 days)**.
3. Retain certain records as listed in Section 8 — specifically your XLSX export records and audit log entries — where the law requires it. The retained records are unlinked from your account so you cannot be identified from them in our active systems.

Account deletion via a self-service Account Settings button is planned for version 1.5. Until then, the Grievance Officer route is the deletion channel.

### 10.4 Right to withdraw consent
You may withdraw your consent to the processing of your personal data at any time by emailing our Grievance Officer with the subject **"Withdraw consent"**. Withdrawal of consent will, in most cases, mean we can no longer provide the Service to you — the Service requires processing your data to function. We will explain the consequence in our reply.

### 10.5 Right to grievance redress
You may raise a grievance with our Grievance Officer (Section 12). We will:
1. Acknowledge within 24 to 72 hours with a tracking reference.
2. Resolve **within 7 calendar days** of receipt.

If you are not satisfied with our response, you may approach the **Data Protection Board of India** under DPDP Act §27.

### 10.6 Right to nominate
You may nominate a person to exercise your rights in the event of your death or incapacity. We do not yet offer a self-service nomination form — please email our Grievance Officer with the subject **"Nominate"** and we will record the nomination manually. A self-service form is planned for version 1.5.

### 10.7 Right to portability
You can download your catalog data at any time using our standard export feature (Meesho-compatible XLSX). If you want your personal data in a different format, email our Grievance Officer with the subject **"Portability request"** and we will provide it **within 7 calendar days**.

---

## 11. Personal data breach notification

If we detect a breach of your personal data, we will:
1. Contain the breach (revoke tokens, rotate secrets, isolate the affected system).
2. Investigate the scope and impact.
3. Notify the **Data Protection Board of India** within the time prescribed by the DPDP Rules (currently within 72 hours of becoming aware of the breach). **[LAWYER REVIEW]**
4. Notify you, the affected user, of the nature of the breach, the data affected, the measures we have taken, and what you can do to protect yourself.
5. Publish a post-incident summary for transparency.

---

## 12. Grievance Officer

In compliance with DPDP §13 and IT Rules 2011 §5(9), our Grievance Officer is:

> **Name:** `[FOUNDER: Name on PAN — same person who is the Sole Proprietor / Director]`
> **Designation:** Founder and Grievance Officer
> **Email:** `grievance@meesell.in`
> **Postal address:** `[FOUNDER: Stellaxis registered business address — same as on PAN/GST]`
> **Response timeline:** Acknowledgement within 72 hours; resolution within 7 calendar days

All emails to the Grievance Officer must include a subject line drawn from Sections 10.1 to 10.7 so we can route them correctly.

---

## 13. Cookies and similar technologies

We use a small number of **functional** cookies and browser-storage items only. We do not use third-party tracking cookies, analytics cookies, advertising cookies, or social-media cookies in version 1.0.

| Item | Purpose | Storage | Lifetime | Set by |
|---|---|---|---|---|
| `refresh_token` | Authentication — lets us refresh your session without making you log in repeatedly. Marked `HttpOnly`, `Secure`, `SameSite=Strict`, scoped to `/api/v1/auth` on the MeeSell domain. | Browser cookie (JavaScript cannot read it) | Up to 7 days, deleted on logout | MeeSell server |
| Service worker cache | Offline-friendly delivery of the application shell (HTML, CSS, JavaScript) so the site loads instantly on subsequent visits. Does not store your personal data. | Browser cache | Cleared on browser cache clearance | MeeSell client |

If we add analytics or marketing cookies in a future version, we will update this section, refresh the effective date, and obtain your consent through a cookie banner. **[LAWYER REVIEW]**

For more details, see our `Cookie Policy` at `https://meesell.in/legal/cookie-policy`.

---

## 14. Changes to this policy

If we change this policy in a way that materially affects your rights or how we handle your data, we will:
- Update the **Effective date** at the top of this policy.
- Email you (if you have a registered email address) at least **30 days before** the change takes effect.
- Show a notice in the application when you next sign in.

If you continue to use the Service after the new policy takes effect, the new policy applies to you. If you do not agree with the change, you may exercise your right to delete your account under Section 10.3.

---

## 15. Disputes and governing law

This policy is governed by the laws of India. Any dispute arising from this policy or from your use of the Service shall be subject to the exclusive jurisdiction of the courts at **`[FOUNDER: City of Stellaxis registered office — same city as on PAN/GST]`**. **[LAWYER REVIEW]**

Before bringing any dispute to court, we ask you to first raise it with our Grievance Officer (Section 12) and give us 30 days to resolve it.

---

## 16. Contact us

For privacy-related questions, including any of the rights in Section 10:

> **Grievance Officer**
> Email: `grievance@meesell.in`
> Postal address: `[FOUNDER: Stellaxis registered business address]`

For other questions about the Service:

> Email: `support@meesell.in`

---

## Document control

| Field | Value |
|---|---|
| Document | MeeSell Privacy Policy v1.0 |
| Status | DRAFT — founder + lawyer review required |
| Drafted by | `meesell-legal-writer` 2026-06-05 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §1, §2, §3, §4, §5, §6, §7, §8, §9, §10, §13; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §3, §5, §6 |
| Next review | After Indian lawyer redline, before publishing on website |
| Lawyer review markers | 8 — search this document for `[LAWYER REVIEW]` |
| Founder placeholders | search this document for `[FOUNDER:` |
