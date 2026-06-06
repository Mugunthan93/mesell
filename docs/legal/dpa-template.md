# Data Processing Addendum (Template)

**For:** **Stellaxis** `[ENTITY SUFFIX — fills in once §15.1 ruled]` operating the **MeeSell** service
**Version:** v1.0
**Status:** DRAFT TEMPLATE — pre-staged for first Business-tier customer DPA request; founder + Indian lawyer review required before signature with any customer
**Drafted by:** `meesell-legal-writer` per `docs/LEGAL_ARCHITECTURE.md` §6, §7, §9, §11, §14

> **When to use this template:**
> A Data Processing Addendum (DPA) is signed between MeeSell (as **data processor**) and a paying Business-tier customer (as **data controller / Data Fiduciary** for the personal data of its own end-customers or employees that they may incidentally enter into the MeeSell Service).
>
> For seller-only data (the seller's own phone, business profile, statutory identifiers), MeeSell is the Data Fiduciary; that relationship is governed by the [Privacy Policy](./privacy-policy.md) and [Terms of Service](./terms-of-service.md). No DPA is needed for seller-only data.
>
> **A DPA becomes useful when:**
> - A Business-tier customer is a registered enterprise (LLP, Pvt Ltd, OPC, partnership)
> - The customer's compliance team has asked for one
> - The customer expects to enter personal data of THIRD parties (their end-customers, suppliers, or employees) into MeeSell (e.g., in a free-text catalog field or via a custom integration)

> **Founder action required before this template can be signed:**
> 1. Resolve `[ENTITY SUFFIX]` per §15.1 (Stellaxis must be incorporated)
> 2. Confirm Stellaxis registered business address (Annex 1 + signature block)
> 3. Indian lawyer redline pass (₹5,000-15,000 — particular focus on §11 Liability cap and §9.2 Audit rights)
> 4. Negotiate any customer-specific changes (most customers accept the standard template; large enterprises may request changes)

---

## 1. Parties

This Data Processing Addendum (this **"DPA"**) is entered into between:

**(A) Stellaxis `[ENTITY SUFFIX]`**, having its registered office at `[FOUNDER: Stellaxis registered business address]`, operating the MeeSell service at `https://www.meesell.in` (the **"Processor"** or **"Stellaxis"**); and

**(B) `[CUSTOMER: Customer legal name]`**, having its registered office at `[CUSTOMER: registered office address]` (the **"Controller"** or **"Customer"**).

each individually a **"Party"** and together the **"Parties"**.

This DPA supplements the [Terms of Service](./terms-of-service.md) accepted by the Customer (the **"Principal Agreement"**) and is incorporated into it by reference. Where this DPA conflicts with the Principal Agreement on any matter relating to the processing of personal data, this DPA prevails.

---

## 2. Definitions

For purposes of this DPA, the following terms apply (capitalised terms not defined here have the meaning given in the Principal Agreement or in the **Digital Personal Data Protection Act 2023** (the **"DPDP Act"**)):

- **"Personal Data"** — any data about an identified or identifiable individual processed by Stellaxis on the Customer's instructions, as further described in Annex 3.
- **"Data Principal"** — the individual to whom Personal Data relates, per DPDP §2(j).
- **"Processing"** — any operation on Personal Data, including collection, storage, retrieval, use, disclosure, alignment, restriction, erasure, or destruction.
- **"Sub-processor"** — a third party engaged by Stellaxis to process Personal Data on Stellaxis's behalf, as listed in Annex 1.
- **"Personal Data Breach"** — any breach of security leading to accidental or unlawful destruction, loss, alteration, unauthorised disclosure of, or access to, Personal Data.
- **"Technical and Organisational Measures"** or **"TOMs"** — the security measures described in Annex 2.
- **"Applicable Law"** — the DPDP Act, the IT Act 2000, the IT Rules 2011, the DPDP Rules 2025, the Consumer Protection Act 2019, and any other Indian law that applies to the Processing.

---

## 3. Scope and roles

### 3.1 Processor and Controller roles

For Personal Data **of the Customer's own end-customers, suppliers, employees, or other third parties** that the Customer (or a person authorised by it) submits to the Service:
- The Customer is the **Data Fiduciary** under the DPDP Act and the **Controller** under this DPA.
- Stellaxis is the **Data Processor** under this DPA, processing such Personal Data **only on the Customer's documented instructions**.

For Personal Data **of the Customer itself** (the Customer's account-holder phone, email, business profile, statutory identifiers, payment metadata):
- Stellaxis is the **Data Fiduciary** under the DPDP Act for this data.
- The Customer's rights and obligations for this Stellaxis-held data are governed by the [Privacy Policy](./privacy-policy.md), not by this DPA.

### 3.2 Documented instructions

The Customer's documented instructions to Stellaxis comprise:
- The Principal Agreement
- This DPA (including its Annexes)
- The use of the Service features as published in the Service documentation
- Any written instructions the Customer issues from time to time via the Grievance Officer email (`grievance@meesell.in`) and that Stellaxis accepts in writing

Stellaxis will not process Personal Data for any other purpose without the Customer's prior written consent, except where required by Applicable Law.

---

## 4. Subject-matter, nature, purpose, and duration

| Item | Detail |
|---|---|
| **Subject-matter** | The processing of Personal Data necessary to provide the MeeSell Service to the Customer, as set out in the Principal Agreement and Annex 3. |
| **Nature of processing** | Storage, retrieval, transmission, AI-assisted suggestion generation, structured export, and ancillary security and audit logging. |
| **Purpose** | To enable the Customer to prepare product catalogs for upload to the Meesho marketplace, including ancillary support, billing, and compliance. |
| **Duration** | For the term of the Principal Agreement, plus any retention period stated in Annex 3 or required by Applicable Law. |
| **Type of Personal Data** | As described in Annex 3. |
| **Categories of Data Principals** | As described in Annex 3. |

---

## 5. Processor obligations

Stellaxis will:

### 5.1 Process only on instructions
Process Personal Data only on the Customer's documented instructions (§3.2), unless required by Applicable Law. If Applicable Law requires processing outside the Customer's instructions, Stellaxis will notify the Customer of that requirement before processing, unless the notification itself is prohibited by Applicable Law. **[LAWYER REVIEW]**

### 5.2 Confidentiality
Ensure that persons authorised to process Personal Data on Stellaxis's behalf (founder, future employees, contractors) are bound by confidentiality obligations no less strict than those in §8 of the Principal Agreement.

### 5.3 Security
Implement and maintain the Technical and Organisational Measures described in **Annex 2**, appropriate to the risk of the processing under DPDP §8(5) and IT Act §43A.

### 5.4 Sub-processor governance
Engage Sub-processors only in accordance with **§7** and Annex 1.

### 5.5 Assistance with Data Principal rights
Assist the Customer in responding to Data Principal requests (access, correction, erasure, withdrawal of consent, nomination, grievance, portability) under the procedure in **Annex 4**. Stellaxis will action assistance requests within **7 calendar days** of receipt.

### 5.6 Assistance with controller obligations
Assist the Customer in meeting its own DPDP obligations relating to security, breach notification, and (where applicable) data protection impact assessment, taking into account the nature of the processing and the information available to Stellaxis.

### 5.7 Breach notification
Notify the Customer of any Personal Data Breach affecting the Customer's data **without undue delay and in any event within 48 hours** of becoming aware of it, with the detail prescribed in **Annex 5**. **[LAWYER REVIEW — 48-hour customer-notification window is tighter than the 72-hour DPDP regulator window. Verify enforceability and operational feasibility.]**

### 5.8 Deletion or return on termination
On termination or expiry of the Principal Agreement, at the Customer's choice:
- Delete the Personal Data within 30 calendar days, or
- Return the Personal Data in a structured electronic format (XLSX or equivalent) within 30 calendar days,
and in either case delete all remaining copies, except where Applicable Law requires retention or where retained data is needed to defend an active legal claim. Stellaxis will certify deletion on request.

### 5.9 Records of processing
Maintain a written record of all categories of processing carried out on behalf of the Customer, as required by DPDP §8(5). This record is available on the Customer's reasonable written request (no more than once per calendar year, with at least 14 days' notice).

---

## 6. Customer obligations

The Customer:

### 6.1 Lawful basis
Warrants that it has a lawful basis under Applicable Law for all Personal Data that the Customer (or a person authorised by it) submits to the Service, and that it has obtained any consents or notices required for Stellaxis's processing under this DPA.

### 6.2 Instructions are lawful
Warrants that its instructions to Stellaxis under §3.2 are lawful under Applicable Law.

### 6.3 Cooperation in joint matters
Cooperates with Stellaxis in good faith to resolve Data Principal requests, breach response, and any other matter requiring joint action.

### 6.4 Customer-side TOMs
Implements appropriate security on its own systems (account credentials, access devices, custom integrations) such that the security boundary between the Customer's system and the Service is not the weakest link. Stellaxis is not responsible for breaches arising on the Customer's side of that boundary.

---

## 7. Sub-processors

### 7.1 General authorisation
The Customer authorises Stellaxis to engage the Sub-processors listed in **Annex 1** for the categories of processing described against each.

### 7.2 Notification of changes
Stellaxis will notify the Customer of any intended addition or replacement of Sub-processors at least **30 days before** the change takes effect, by email to the Customer's account-holder address and by updating the Privacy Policy and Annex 1. The Customer may object in writing within 14 days of notification.

### 7.3 Right to object
If the Customer reasonably objects to a new Sub-processor, the Parties will negotiate in good faith for 30 days. If the Parties cannot resolve the objection in that period, the Customer may terminate the Principal Agreement for cause, with refund of pre-paid fees pro-rated to the unused term. The Customer will not unreasonably withhold or delay consent to a Sub-processor that is necessary for the operation of the Service.

### 7.4 Sub-processor flow-down
Stellaxis will impose on each Sub-processor data-protection obligations no less strict than those in this DPA, by written contract.

### 7.5 Liability for Sub-processors
Stellaxis remains liable to the Customer for any Sub-processor's failure to meet its data-protection obligations under §7.4, subject to the limitation of liability in §11.

---

## 8. Cross-border data transfers

The Sub-processor list in Annex 1 indicates whether each Sub-processor transfers Personal Data outside India.

- Where transfer is to a country **not** restricted by notification under DPDP §16, the transfer is permitted under Indian law and disclosed in the Privacy Policy.
- Where the Central Government issues a notification under DPDP §16 restricting transfer to a specific country, Stellaxis will, within 30 days of the notification:
  - Suspend further transfer to that country, AND
  - Migrate processing to a compliant region, OR
  - Suspend the affected Sub-processor (Customer notified per §7.2).

**[LAWYER REVIEW — confirm the §8 mechanism stays aligned with the final DPDP Rules 2025 on cross-border restrictions.]**

---

## 9. Audit and cooperation

### 9.1 Information rights
On the Customer's reasonable written request (no more than once per calendar year, with at least 14 days' notice), Stellaxis will provide the Customer with:
- A summary of Stellaxis's TOMs (Annex 2), with any material changes since last reporting;
- The most recent annual independent security audit report (when commissioned — V1.5 / V2 timeline);
- A list of Sub-processors actively used in the past 12 months.

### 9.2 Audit rights
The Customer may audit Stellaxis's compliance with this DPA, **once per calendar year**, on at least **30 days' written notice**, during normal business hours, conducted by the Customer or a mutually-agreed third-party auditor (subject to a confidentiality undertaking acceptable to Stellaxis). Audits will be limited in scope to the processing performed for the Customer.

The Customer will bear all audit costs unless the audit identifies a material breach of this DPA by Stellaxis, in which case Stellaxis will reimburse reasonable audit costs.

**[LAWYER REVIEW — broad audit rights can be very costly for a small SaaS. Negotiate specific scope and frequency caps with each enterprise customer.]**

### 9.3 Regulator cooperation
Stellaxis will cooperate, on the Customer's reasonable written request, with any audit or investigation by the Data Protection Board of India or another competent authority that affects the Personal Data processed under this DPA.

---

## 10. Data Principal rights — assistance procedure

The procedure in **Annex 4** governs how Stellaxis assists the Customer with Data Principal requests.

---

## 11. Liability

### 11.1 Allocation
Each Party is liable for its own breach of this DPA, subject to the limitations in the Principal Agreement (Terms of Service §11) and this Section 11.

### 11.2 Cap
Stellaxis's total aggregate liability under this DPA in any rolling 12-month period is **capped at the limit set out in Terms of Service §11.1** (the higher of 3 months of fees actually paid or ₹10,000), regardless of the legal basis for the claim. **[LAWYER REVIEW — enterprise customers may push for a higher cap (e.g., 12 months of fees) for DPA-specific claims. Negotiate per customer.]**

### 11.3 Exclusions
The exclusions in Terms of Service §11.2 apply to this DPA.

### 11.4 Exceptions
The cap and exclusions in §11.2 and §11.3 do not apply to liability that cannot be excluded under Applicable Law, including liability for fraud or wilful misconduct, and including statutory penalties under DPDP §33 where directly attributable to Stellaxis's breach of this DPA.

### 11.5 Indemnity
Each Party will indemnify the other against claims by Data Principals or by regulators to the extent caused by the indemnifying Party's breach of this DPA. **[LAWYER REVIEW — indemnity scope is often a heavily-negotiated DPA clause.]**

---

## 12. Term and termination

### 12.1 Term
This DPA takes effect on the date both Parties sign it and continues for the term of the Principal Agreement.

### 12.2 Survival
Sections that by their nature survive termination — including §5.7 (breach notification of pre-termination breaches), §5.8 (deletion or return), §5.9 (record retention), §9 (audit, in respect of the audit window), §11 (liability) — survive expiry or termination of this DPA.

### 12.3 Effect of termination
On termination, §5.8 governs the treatment of Personal Data.

---

## 13. Governing law, jurisdiction, and notices

### 13.1 Governing law and jurisdiction
This DPA is governed by the laws of **India** and is subject to the **exclusive jurisdiction of the courts at `[FOUNDER: City of Stellaxis registered office]`**, as in the Principal Agreement.

### 13.2 Notices
Notices to Stellaxis under this DPA are sent to `grievance@meesell.in` AND, where the matter is contractual, to the postal address in the signature block.

Notices to the Customer are sent to the email and postal address in the signature block.

### 13.3 Order of precedence
In case of conflict between this DPA, the Principal Agreement, and the Privacy Policy: (a) this DPA prevails on Personal Data processing matters; (b) the Principal Agreement prevails on other matters; (c) the Privacy Policy prevails on Stellaxis-as-Data-Fiduciary matters for the Customer's own data.

---

## 14. Signature block

| Stellaxis `[ENTITY SUFFIX]` | `[CUSTOMER: Customer legal name]` |
|---|---|
| Name: `[FOUNDER: Name on PAN]` | Name: `[CUSTOMER: signatory name]` |
| Title: Founder & Grievance Officer | Title: `[CUSTOMER: signatory title]` |
| Date: `[FOUNDER: signature date]` | Date: `[CUSTOMER: signature date]` |
| Signature: ____________________ | Signature: ____________________ |

Address for notices: `[FOUNDER: Stellaxis registered business address]` | Address for notices: `[CUSTOMER: registered office address]`

---

# Annex 1 — Sub-processors

The current list of Sub-processors. Updated under §7.2 with at least 30 days' notice of changes.

| # | Sub-processor | Service | Personal Data accessed | Country of processing | Cross-border? |
|---|---|---|---|---|---|
| 1 | Razorpay Software Private Limited | Subscription payment processing and KYC | Customer business name, plan tier, payment metadata | India | No |
| 2 | Walkover Web Solutions Pvt Ltd (MSG91) | OTP SMS for account-holder authentication | Phone number, OTP, IP | India | No |
| 3 | Google Cloud India Pvt Ltd / Google LLC — GCP (compute) | Hosting | All operational data at platform layer | India (Mumbai region) | No |
| 4 | Google Cloud India Pvt Ltd / Google LLC — GCS | Object storage | Image binaries, XLSX exports, audit archives (PII-scrubbed) | India (Mumbai region) | No |
| 5 | Google LLC — Gemini 2.5 Flash API | AI text and vision | Product titles, descriptions, image bytes (only when AI features used) | Google multi-region | Yes |
| 6 | Let's Encrypt (Internet Security Research Group) | TLS certificate issuance | Domain name only — no Personal Data | US | Domain only |
| 7 | Namecheap, Inc. | DNS and domain registration | Domain name only — no Personal Data | US | Domain only |
| 8 | GitLab Inc. | Source code hosting and CI/CD | Source code only — no Personal Data in V1 | EU / US | Code only |

---

# Annex 2 — Technical and Organisational Measures (TOMs)

Stellaxis maintains the following TOMs, scaled to the risk of the V1 Service. References are to internal architecture documents (`docs/INFRASTRUCTURE_ARCHITECTURE.md` = IA; `docs/BACKEND_ARCHITECTURE.md` = BEA; `docs/FRONTEND_ARCHITECTURE.md` = FEA; `docs/DATABASE_ARCHITECTURE.md` = DBA).

## A2.1 Transport security
- TLS 1.2 or higher on all customer connections
- Let's Encrypt certificates, auto-renewed (IA §7)

## A2.2 Authentication and session
- One-time-password login via MSG91 (BEA §2.1) — no passwords stored
- Access tokens (JWT) held in browser memory only, TTL ≤ 15 min (FEA §1.F)
- Refresh tokens stored in HttpOnly + Secure + SameSite=Strict cookies, scoped to `/api/v1/auth`, TTL ≤ 7 days (FEA §1.F)
- HMAC-SHA256 with private pepper for refresh-token allowlist (BEA §4.B + IA §4 secret)
- Atomic rotation via Valkey Lua EVAL (BEA §4.B)
- Server-side revocation on logout

## A2.3 Data at rest
- PostgreSQL, Valkey, and GCS encrypted at rest by Google Cloud (IA §3.2, §4)
- Secrets in Google Secret Manager (IA §4) — never in source, images, or config
- 7 production secrets actively managed (IA §4)

## A2.4 Tenant isolation
- V1: app-level `user_id` scoping enforced by `core/tenancy.py.scope_to_user` (BEA §4.C)
- Cross-module access matrix prevents cross-tenant joins (BEA §2.D)
- CI linter rejects un-scoped queries (BEA §4.C forward reference)
- **V1.5 roadmap: PostgreSQL Row-Level Security (RLS)** as an additional defence layer (DBA §9, §13)

## A2.5 Audit and monitoring
- Append-only `audit_events` log (DBA §2.12)
- PII scrubbed at write — phone hashed (SHA-256 + salt), FSSAI / GST / R-number stripped (BEA §4.G)
- 90-day hot retention + 1-year archive in GCS (DBA §10.1)

## A2.6 Personnel and access
- V1: founder is the only person with production data access
- Future personnel will be subject to confidentiality, background checks (V1.5+), and least-privilege access policies

## A2.7 Network security
- GCP firewall: HTTP 80 (all), HTTPS 443 (all), K3s API 6443 (founder IP /32 only) (IA §3.2)
- No direct database access from outside the cluster — connections via in-cluster service DNS only (IA §8)

## A2.8 Backup and recovery
- PostgreSQL and Valkey snapshots
- Backup off-VM to GCS (IA §13 — pre-launch hardening item; in scope before public launch)

## A2.9 Sub-processor security
- All Sub-processors in Annex 1 are bound by their own data-protection commitments
- Stellaxis flows down equivalent obligations per DPA §7.4

## A2.10 Update cadence
- TOMs reviewed at minimum once per calendar year and on any material architecture change
- Material changes notified to Customer per DPA §9.1

---

# Annex 3 — Categories of Personal Data, Data Subjects, and Retention

## A3.1 Categories of Personal Data processed

| Category | Examples | Source |
|---|---|---|
| Account credentials | Phone number, email (optional) | Customer's account-holder, entered at signup |
| Business identity | Business name, GSTIN | Customer, entered in seller profile |
| Legal Metrology data | Manufacturer / packer / importer name, address, pincode, country of origin | Customer, entered in seller profile |
| Statutory identifiers | FSSAI, BIS, ISI, R-number, IS-number, CM-L, drug or cosmetic licence number, ISBN | Customer, entered in seller profile |
| Product content | Catalog titles, descriptions, attributes | Customer, entered in catalog wizard |
| Pricing data | Cost, margin, MRP, selling price | Customer, entered in pricing module |
| Image content | Product images (may contain incidental Personal Data of third parties if uploaded) | Customer, uploaded to image module |
| Security log data | IP, user agent, request ID, action timestamps | Auto-collected from request headers |
| AI processing inputs/outputs | Product text, image bytes submitted to AI; AI suggestions returned | Generated when Customer uses AI features |

## A3.2 Categories of Data Principals

- The Customer's account holder
- Authorised users acting on behalf of the Customer
- (Incidental, where Customer chooses to enter such data): the Customer's end-customers, suppliers, employees, or other third parties whose Personal Data appears in product content or image uploads. The Customer warrants under §6.1 that it has lawful basis for any such data.

## A3.3 Retention periods

| Data | Hot retention (active DB) | Archive | Trigger to delete |
|---|---|---|---|
| Account record (users) | Lifetime of account | None | Account deletion |
| Seller profile | Lifetime | None | Account deletion |
| Catalogs, products, images, pricing calcs | Lifetime active | 30 days grace after `deleted_at` | Soft-delete + grace |
| Draft autosave (`product_drafts`) | 30 days from last edit | None | TTL Celery beat |
| Exports (`exports`) | 1 year | 1 year archived in GCS | Manual review |
| Audit events (`audit_events`) | 90 days | 1 year archived in GCS | Celery beat archive |
| Session tokens | Access ≤ 15 min; Refresh ≤ 7 days | None | On logout |

---

# Annex 4 — Data Principal Request Handling

## A4.1 Receipt
Data Principal requests received directly by Stellaxis (via `grievance@meesell.in`) are routed to the Customer if the request concerns the Customer's controlled Personal Data; routed to Stellaxis's internal flow if the request concerns Stellaxis-as-Data-Fiduciary data.

## A4.2 SLA
- Acknowledgement to Customer: **within 24 hours** of receipt
- Action of assistance: **within 7 calendar days** of Customer's confirmed instruction
- Source: DPDP §13 grievance redress timeline + LACI §6.2

## A4.3 Request types
| Type | Action |
|---|---|
| Access | Stellaxis extracts the data and provides to Customer in structured electronic format |
| Correction | Customer instructs the correction; Stellaxis applies via service or admin path |
| Erasure | Stellaxis anonymises or deletes within 30 days; retains `exports` and `audit_events` per DBA §3 cascade chain (anonymised at user_id level) |
| Withdrawal of consent | Stellaxis logs and notifies Customer; consequences explained to Data Principal |
| Nomination | V1 manual; recorded against the user record |
| Grievance redress | Joint resolution within 7 days |

## A4.4 Documentation
Every Data Principal request triggers an `audit_events` entry of type `user.data_export_request`, `user.deletion_request`, or `grievance.opened` (new event_types pending in `meesell-backend-coordinator` hand-off per LEGAL_ARCHITECTURE §10).

---

# Annex 5 — Personal Data Breach Notification

## A5.1 Notification SLA
- Customer notification: **within 48 hours** of Stellaxis becoming aware of a breach affecting Customer-controlled data
- Data Protection Board notification: **within 72 hours** (per DPDP Rules 2025) by the Customer (as Data Fiduciary) or by Stellaxis (where Stellaxis is jointly responsible)

## A5.2 Notification content
- Nature of the breach
- Categories and approximate number of Data Principals affected
- Categories and approximate number of records affected
- Likely consequences
- Measures Stellaxis has taken to contain and mitigate
- Recommended actions for Customer and Data Principals
- Stellaxis's point of contact for follow-up

## A5.3 Coordination
Stellaxis and the Customer will coordinate breach communications to Data Principals, regulators, and the public to avoid inconsistent statements.

---

## Document control

| Field | Value |
|---|---|
| Document | MeeSell DPA Template v1.0 |
| Operator | Stellaxis `[ENTITY SUFFIX]` |
| Status | DRAFT TEMPLATE — pre-staged for first enterprise DPA request |
| Drafted by | `meesell-legal-writer` 2026-06-05 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §3, §4, §5, §6, §7, §8, §9, §11, §14; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §3, §6 |
| Lawyer review markers | 6 — search for `[LAWYER REVIEW]` (§5.1, §5.7, §8, §9.2, §11.2, §11.5) |
| Founder placeholders | search for `[FOUNDER:` or `[ENTITY SUFFIX]` |
| Customer placeholders | search for `[CUSTOMER:` |
| Pairs with | `privacy-policy.md`, `terms-of-service.md` (Principal Agreement), `refund-policy.md`, `cookie-policy.md` |
