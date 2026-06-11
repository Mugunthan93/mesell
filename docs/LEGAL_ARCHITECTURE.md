# MeeSell — Legal Architecture (Construction Contract)

**Owner:** `meesell-legal-writer`
**Last verified live:** 2026-06-05
**Status:** SKELETON v1 — founder + lawyer review required before any LOCKED markings
**Drives:** every artifact under `docs/legal/` and every in-product compliance string surface
**Peers:** `docs/FRONTEND_ARCHITECTURE.md` (auth UI, consent UI), `docs/BACKEND_ARCHITECTURE.md` (data flow, audit, AI ops), `docs/DATABASE_ARCHITECTURE.md` (PII inventory), `docs/INFRASTRUCTURE_ARCHITECTURE.md` (sub-processor + jurisdiction)
**Source:** `docs/LEGAL_AND_COMPLIANCE_INFO.md` is the authoritative regulatory research; every claim below cites a `LACI §N` anchor or returns "needs lawyer review"

> **This document is informational, NOT legal advice.** Outputs are templates / drafts for founder + qualified-lawyer review. Every artifact under `docs/legal/` MUST be signed off by an Indian lawyer before publishing. Quoted statute and procedural claims are verified against `LEGAL_AND_COMPLIANCE_INFO.md` (henceforth `LACI`); anything else carries a `[FOUNDER VERIFY]` marker.

---

## Table of Contents

0. [Purpose, Audience, Cross-References](#section-0--purpose-audience-cross-references)
1. [The Legal Topology — Where Law Touches the System](#section-1--the-legal-topology--where-law-touches-the-system)
2. [Regulated Data Inventory (per-table)](#section-2--regulated-data-inventory-per-table)
3. [Regulatory Regime Map](#section-3--regulatory-regime-map)
4. [Sub-Processor Register](#section-4--sub-processor-register)
5. [Cross-Border Data Transfer Map](#section-5--cross-border-data-transfer-map)
6. [Tenant Isolation as a Legal Control](#section-6--tenant-isolation-as-a-legal-control)
7. [Consent + Data-Subject Rights Lifecycle](#section-7--consent--data-subject-rights-lifecycle)
8. [Breach Response + Grievance Officer Runbook](#section-8--breach-response--grievance-officer-runbook)
9. [Retention Schedule](#section-9--retention-schedule)
10. [Audit Log as Compliance Evidence](#section-10--audit-log-as-compliance-evidence)
11. [Intellectual Property — AI Output, Seller Content, Brand/Image Rights](#section-11--intellectual-property--ai-output-seller-content-brandimage-rights)
12. [Payment Compliance — Razorpay, GST, Invoicing, KYC](#section-12--payment-compliance--razorpay-gst-invoicing-kyc)
13. [Per-Super-Category Statutory Touchpoints](#section-13--per-super-category-statutory-touchpoints)
14. [Document Mapping — Surface → Privacy / ToS / DPA Clause](#section-14--document-mapping--surface--privacy--tos--dpa-clause)
15. [Founder Decisions Blocking Legal Surfaces](#section-15--founder-decisions-blocking-legal-surfaces)
16. [Deferred to V1.5](#section-16--deferred-to-v15)

---

## Section 0 — Purpose, Audience, Cross-References

STATUS: LOCKED (2026-06-05)

### A. What this document is

This document is the **construction contract** for `meesell-legal-writer`. It enumerates every legal surface in the as-built MeeSell system, maps each surface to the regulatory regime that governs it, identifies the artifact (policy, runbook, in-product string, founder decision) that closes the surface, and locks the order in which artifacts must be drafted so dependencies do not retro-block downstream work.

It is NOT legal advice. It is NOT a substitute for an Indian lawyer's review. It IS the engineering-level inventory a lawyer needs in order to draft (or sign off on) Privacy Policy, Terms of Service, Refund Policy, DPA, and the Razorpay / GST onboarding packs.

It mirrors the structure of `FRONTEND_ARCHITECTURE.md`, `BACKEND_ARCHITECTURE.md`, `DATABASE_ARCHITECTURE.md`, and `INFRASTRUCTURE_ARCHITECTURE.md` so reviewers can pattern-match the document shape they already know. Each section answers a single legal question; the section is locked only when the founder rules and (where required) a lawyer signs off.

### B. Audience

- **Founder (Muguntha)** — owns every `[FOUNDER:` and `[FOUNDER VERIFY]` decision; signs off section status flips.
- **Indian lawyer (TBD)** — must review and sign off Privacy / ToS / Refund / DPA before publishing.
- **CA (TBD)** — must confirm GST SAC code, invoice format, GST inclusive-vs-exclusive display.
- **Razorpay onboarding officer** — consumes the KYC pack derived from §12.
- **Other MeeSell agents** — consume the in-product copy + grievance footer + consent strings via hand-off (per `meesell-legal-writer.md` Hand-off Protocol).

### C. Cross-references

This document peers with — and does NOT duplicate — the following:

| Source | What it owns | What this doc uses it for |
|---|---|---|
| `LEGAL_AND_COMPLIANCE_INFO.md` (`LACI`) | Indian statutory research, vendor pricing, founder decision list §10 | Single citation source for every regulatory claim. If a claim is not in `LACI`, it carries `[FOUNDER VERIFY]` or "needs lawyer review". |
| `BUSINESS_STRATEGY.md` | Wedge, target persona, distribution channels | Source for "intended use" disclosures in Privacy + ToS (e.g., AI catalog generation, image processing). |
| `PRICING_LOCKED.md` | Tier prices, LTD scarcity rule, GST inclusive/exclusive design | Source for invoice template fields, refund clause numbers, sub-processor cost-share statements. |
| `DATABASE_ARCHITECTURE.md` (`DBA`) | 13-table schema, JSONB shapes, cascade chain, tenant scope | Source for §2 PII inventory and §9 retention schedule. |
| `BACKEND_ARCHITECTURE.md` (`BEA`) | Modules, middleware, AI Ops layer, audit pipeline, JWT contract | Source for §1 topology, §6 tenant control, §10 audit, §11 AI IP, §7 consent flow. |
| `FRONTEND_ARCHITECTURE.md` (`FEA`) | Routes, consent UI, token storage (FE-D5), service worker | Source for in-product copy hand-off targets and §7 consent UI surface. |
| `INFRASTRUCTURE_ARCHITECTURE.md` (`IA`) | GCP region, sub-processors, Secret Manager, backup posture | Source for §4 sub-processor list, §5 cross-border map, §8 breach runbook. |
| `V1_FEATURE_SPEC.md` | The 9 V1 features | Source for "what the service does" in ToS service-description clause. |

### D. Status discipline

Every later section carries `STATUS: SKELETON | DRAFT | LOCKED`. SKELETON = first cut, no founder review. DRAFT = in founder review. LOCKED = founder + (where applicable) lawyer + (where applicable) CA have signed off. **No `docs/legal/` artifact may be drafted against a SKELETON section.** Drafts may be drafted against DRAFT or LOCKED sections; published artifacts (publicly live on the website) require LOCKED.

---

## Section 1 — The Legal Topology — Where Law Touches the System

STATUS: LOCKED (2026-06-05)

### A. What this section answers

"Walk the request path from a seller's browser through the system, and at every step name the regulator who cares about that step." This is the **legal mirror of `BEA §1` and `FEA §1`** — same topology, same arrows, but annotated with statute and policy obligation.

### B. ASCII legal topology

```
Seller's browser
   │
   │ [DPDP §6 — consent UI MUST display privacy notice + consent checkbox at OTP step]
   │ [Refresh cookie (HttpOnly+Secure+SameSite=Strict, per FEA §1.F + FE-D5) = functional cookie, disclose in Cookie Policy]
   │ [Access JWT in memory only — IT Act §43A "reasonable security practices" defensible]
   ▼
Traefik ingress (TLS via Let's Encrypt)
   │ [IT Act §66E + DPDP §8(4) — transport encryption is a baseline reasonable security practice]
   ▼
FastAPI pod  (BEA §1, BEA §2)
   ├── iam module — OTP send / verify, JWT issue, refresh allowlist, Razorpay webhook
   │     [DPDP §6 — consent capture at OTP-verify is the legal moment of consent]
   │     [DPDP §11 — phone is "personal data"; OTP itself is "sensitive" in spirit (not explicit), treat as such]
   │     [TRAI / DoT — MSG91 carries the SMS; MeeSell is sender of record for transactional content]
   │     [RBI PA-O Master Directions Sept 2025 — Razorpay webhook capture inherits PA-O onboarding obligations]
   ├── customer module — seller profile, Legal Metrology fields, conditional compliance extensions
   │     [Legal Metrology (Packaged Commodities) Rules 2011 — manufacturer/packer/importer mandatory]
   │     [DPDP §6 — business contact information is still personal data; same consent applies]
   │     [FSSAI / BIS / DCA / WPC — depending on super-category, additional registers apply (§13)]
   ├── category module — Smart Picker + browse + schema fetch
   │     [Database Right (no Indian statute; ToS protects via contract) — the 3,772-category dataset is MeeSell's moat asset]
   │     [Meesho ToS — quarterly scrape sits on a gray legal line; BUSINESS_STRATEGY §11.1 risk register acknowledges]
   ├── catalog module — product CRUD, AI Auto-fill, draft autosave
   │     [Copyright Act 1957 — seller-supplied product text + AI-modified text; ownership clause in ToS]
   │     [Consumer Protection Act 2019 — MeeSell is an "intermediary" assisting product listing; IT Act §79 safe-harbour]
   ├── image module — upload, GCS write, precheck Celery task, signed URL issuance
   │     [Copyright Act — image IP is seller-asserted at upload; MeeSell carries no verification duty in V1]
   │     [IT Act §79 — safe-harbour requires takedown procedure for infringing content]
   │     [Trademark Act — watermark presence is *advisory*, not enforcement; ToS Acceptable Use covers]
   ├── pricing module — P&L calc, GST snapshot
   │     [CGST Act 2017 + Rule 46 (Tax invoice) — pricing surface displays inclusive vs exclusive per §12]
   ├── dashboard module — read-only listing
   │     [DPDP §10(2) — data minimisation: dashboard MUST NOT show fields not strictly needed]
   ├── export module — XLSX generation, signed-URL delivery, round-trip validation
   │     [Legal Metrology + Meesho compliance — XLSX restores typos for Meesho parser; MeeSell is conduit]
   │     [DPDP §11 — XLSX is a data extract containing all seller data; right-to-portability surface]
   └── core/audit_mw — append-only audit_events writes (BEA §4.G, DBA §2.12)
         [DPDP §8(5) — keep records of processing; audit_events is the record-of-processing log]
         [IT (Reasonable Security Practices) Rules 2011 §4 — written security policy expected for sensitive data handlers]
   │
   ▼ Egress (all routed through `adapters/` and `ai_ops/` per BEA §3.F/§3.G):
   │
   ├── MSG91 (asia-south1 region, India SaaS) ─── transactional SMS only
   │     [TRAI Telecom Commercial Communications Customer Preference Regulations 2018 — opt-in OTP exempt as service message]
   ├── Gemini 2.5 Flash (Google, multi-region routing) ─── product text + image vision
   │     [DPDP §16 — cross-border transfer (when Google routes outside India); whitelist not yet published Q2-2026]
   │     [Copyright — input text + image IP retained by seller; output AI suggestions; clarify in ToS]
   │     [Google Gemini API Terms — customer (MeeSell) is responsible for input/output IP rights]
   ├── GCS asia-south1 (Google) ─── image binary + XLSX exports + audit archive
   │     [DPDP — data residency satisfied (Mumbai region)]
   │     [Public-access prevention enabled per IA §3.2 — "reasonable security practices" defensible]
   ├── Razorpay (RBI-regulated PA-O, India) ─── inbound webhook, future subscription billing
   │     [RBI PA-O Master Directions Sept 2025 — Razorpay's licence; MeeSell inherits via merchant agreement (LACI §5.4)]
   │     [PCI-DSS — card data NEVER touches MeeSell; Razorpay-hosted checkout]
   ├── LangFuse (vendor TBD — likely US/EU) ─── async AI trace egress, fire-and-forget
   │     [DPDP §16 — cross-border transfer concern; sub-processor disclosure required (§4)]
   │     [Should be opt-in or disabled in V1 until vendor jurisdiction confirmed — see §15 founder decision]
   └── Let's Encrypt + Namecheap ─── TLS + DNS, no PII processing
         [No PII transit; minimal exposure; treat as utility, disclose in sub-processor list for completeness]

Inbound from Razorpay (webhook):
   [Signature verification only in V1 per BEA §1.E and IA §3.2 secret razorpay-key-secret]

Operational identities (NOT customer data — but inside the legal perimeter):
   [GCP project owner vaishnaviramoorthy@gmail.com (IA §3.1) — entity of record for GCP processing agreement]
   [ADC actor mugunthanks93@gmail.com (IA §3.1) — operational founder identity]
   [Founder IP /32 in firewall — exposes founder location metadata in audit logs]
   [MSG91 IP whitelist — same exposure]
```

### C. Per-surface obligation density

The 4 surfaces with the heaviest obligation density (= most distinct statutes touching the same code path) are:

1. **OTP / consent capture (`iam`)** — DPDP §6 + IT Act §79 + TRAI service-message exemption + DoT (MSG91 routing). Closes via Privacy Policy + in-product consent checkbox + Grievance Officer footer.
2. **Seller profile (`customer`)** — DPDP §6/§11 + Legal Metrology Rules 2011 + (per super-category) FSSAI / BIS / DCA / WPC / Trade License. Closes via Privacy Policy + ToS Acceptable Use + per-super-category data-collection notice.
3. **AI Auto-fill (`catalog`)** — DPDP §6 + Copyright Act + Google Gemini API Terms + DPDP §16 (cross-border). Closes via Privacy Policy disclosure + ToS IP clause + DPA AI-processing addendum.
4. **Export (`export`)** — DPDP §11 (portability) + Legal Metrology + Meesho merchant ToS + Consumer Protection Act §94 (e-commerce intermediary). Closes via ToS service-description + Privacy Policy export disclosure.

These four are the **highest-priority drafting order** — they unlock the largest fraction of total obligation surface.

### D. What §1 does NOT cover

Per-clause text is in §14 (document mapping). Per-statute language is in §3 (regime map). Per-vendor jurisdiction is in §4 + §5. §1 only enumerates where law touches the wire; what to write at each point is the later sections' job.

---

## Section 2 — Regulated Data Inventory (per-table)

STATUS: LOCKED (2026-06-05)

Mirrors `DBA §2` table-by-table — same row order — annotating each column with the regulator + the artifact that must disclose / govern it. Where DBA says "what shape," this section says "who governs."

### 2.1 `users` (DBA §2.1)

| Column | Regulator | Treatment |
|---|---|---|
| `id` | — | Internal opaque UUID; no PII. |
| `phone` (E.164) | DPDP §6 personal data; TRAI for SMS routing | Disclose in Privacy Policy §"What we collect"; OTP send capped 3/h (BEA §4.E); hashed in audit_events (BEA §4.G PII-scrub). |
| `email` (nullable) | DPDP §6 personal data | Disclose; used for transactional only per CAN-SPAM-equivalent IT Rules; marketing requires separate opt-in toggle (§7). |
| `plan` | — | Not PII; internal tier flag. |
| `created_at`, `last_login_at` | DPDP §8(5) (record of processing) | Security log; legitimate interest; retained per §9. |

### 2.2 `seller_profile` (DBA §2.2)

| Column | Regulator | Treatment |
|---|---|---|
| `manufacturer_name/address/pincode` | Legal Metrology (Packaged Commodities) Rules 2011 §6 | Mandatory for any packaged commodity sold; surfaced verbatim on Meesho XLSX export. Disclose in Privacy "What we collect" as business-compliance data. |
| `packer_name/address/pincode` | Legal Metrology Rules 2011 §6 | Same. |
| `importer_name/address/pincode` | Legal Metrology Rules 2011 §6 + Customs Act for IGCR registration | Optional for domestic sellers; required for imported goods. |
| `country_of_origin` | Consumer Protection (E-Commerce) Rules 2020 §6(5)(g) | Mandatory disclosure for all marketplace listings. |
| `compliance_extensions` JSONB | Per super-category statute (§13) | Variable; each key carries its own regulator (FSSAI, BIS, DCA, WPC, AICTE for books, etc.). |
| `active_super_categories` | — | Internal scoping; not PII. |
| `onboarding_complete` | — | Internal flag. |

**Note (DBA §2.2 phase note 1):** the Eye-Serum "collapsed" shape is derived at export time only — no `*_details` columns stored. Philosophy F4 ("never collect data we don't need") is also a DPDP §10(2) data-minimisation control.

### 2.3-2.6 `templates`, `categories`, `field_enum_values`, `field_aliases`

**Global reference data, no PII.** But: the dataset itself is MeeSell's moat (per `BUSINESS_STRATEGY §3`). ToS §"Intellectual Property" must claim MeeSell ownership of the compiled dataset as a Database Right by contract (India has no statutory database right). Scrape source (Meesho) carries a separate Meesho-ToS risk — `BUSINESS_STRATEGY §11.1` already flags as an existential risk; ToS must include an internal acknowledgement clause for forward-looking pivot to Meesho Tech Partner programme.

### 2.7 `catalogs` (DBA §2.7)

| Column | Regulator | Treatment |
|---|---|---|
| `user_id` (FK) | DPDP §6 (link to identity) | Tenant scope. |
| `name` | DPDP §6 (likely contains business name) | Personal data when inferable; treat as seller-PII. |
| `status` | — | Internal. |

### 2.8 `products` (DBA §2.8)

| Column | Regulator | Treatment |
|---|---|---|
| `user_id` (FK) | DPDP §6 | Tenant scope. |
| `name`, `description` | Copyright Act 1957; Consumer Protection Act §2(28) "misleading advertisement" | Seller-asserted IP; MeeSell is intermediary (IT Act §79 safe-harbour available); ToS Acceptable Use prohibits false claims. |
| `fields_jsonb` | Per-category statute (§13) — varies | Schema-validated against category template; legal liability for inaccurate compliance numbers rests with the seller (ToS §"Seller Representations"). |
| `ai_suggestions_jsonb` | Copyright (derivative-work question) + Google Gemini API Terms | AI output ownership: seller owns the input + adopted suggestions per ToS §"AI Output"; MeeSell makes no IP claim on AI text. |
| `status`, `deleted_at` | DPDP §13 (right to erasure) | Soft-delete in V1; hard-delete via deletion workflow (§7). |

### 2.9 `product_images` (DBA §2.9)

| Column | Regulator | Treatment |
|---|---|---|
| `gcs_path` | — | Path itself is not PII; the image bytes ARE potentially PII (faces, IDs, branded content). |
| `precheck_jsonb` (incl. watermark detection) | Trademark Act; Copyright Act | Watermark flag is *advisory*; MeeSell does not arbitrate IP claims. |

Image binary residency: `gs://meesell-prod-assets/{user_id}/{product_id}/{idx}.jpg` in `asia-south1` (IA §3.2) — DPDP data residency satisfied.

### 2.10 `pricing_calcs` (DBA §2.10)

| Column | Regulator | Treatment |
|---|---|---|
| `user_id` (FK), all `pricing_calcs.*` | DPDP §6 + CGST Act (calculation snapshot retained for invoice reconciliation) | Tenant-scoped; retained per §9. |

### 2.11 `exports` (DBA §2.11)

XLSX file generated from the export pipeline contains **all** seller-supplied data including PII (manufacturer addresses, business names, possibly seller phone if it leaks into a free-text field). The `exports.user_id` FK is `ON DELETE RESTRICT` (DBA §2.11 + §3 cascade chain) — exports survive user deletion; user erasure must therefore null the user_id or anonymise in place per §7 erasure workflow.

### 2.12 `audit_events` (DBA §2.12)

| Column | Regulator | Treatment |
|---|---|---|
| `id` (BIGINT) | — | Append-only monotonic; supports DPDP §8(5) record-of-processing. |
| `user_id` (FK ON DELETE RESTRICT) | DPDP §11 right-to-erasure conflict | Audit must survive deletion; erasure workflow (§7) anonymises the user-side data without destroying the audit row. |
| `event_type`, `entity_type`, `entity_id` | DPDP §8(5) | Forensic value preserved. |
| `diff_jsonb` (PII scrubbed at insert via `AUDIT_PII_SALT` per IA §4 + BEA §4.G) | DPDP §8(4) reasonable security | Phone hashed SHA-256(phone+salt); FSSAI/GST stripped. **Confirm with lawyer that this scrubbing level still satisfies DPDP investigative cooperation duties.** |
| `metadata_jsonb` (IP, user-agent, request_id) | IT Act §43A | Security log; legitimate interest. |
| `occurred_at` | — | Timestamp. |

Retention: 90 days hot in Postgres + 1 year archived to GCS (per DBA §10.1). §9 below confirms.

### 2.13 `product_drafts` (DBA §2.13)

Ephemeral autosave; `draft_jsonb` may contain PII mid-keystroke. TTL value (proposed 30 days, pending founder ruling per DBA §13) is itself a DPDP §10(2) data-minimisation decision — **earlier expiry = lower legal exposure**. Recommendation: lock TTL at 30 days; founder ruling needed (see §15).

---

## Section 3 — Regulatory Regime Map

STATUS: LOCKED (2026-06-05)

The eight regimes that govern MeeSell V1, each with its scope, its primary obligation, the artifact that closes it, and the LACI citation:

| # | Regime | Scope | Primary obligation on MeeSell | Closing artifact | LACI ref |
|---|---|---|---|---|---|
| 1 | **DPDP Act 2023 + Rules 2025** | All seller PII (phone, email, profile, image content, audit logs) | Consent, notice, data-subject rights, Grievance Officer, breach notification, sub-processor list | Privacy Policy + In-product consent + Grievance Officer footer + Breach runbook + DPA | LACI §3 + §6 |
| 2 | **IT Act 2000 + IT Rules 2011** | Information intermediary status (catalog generation); reasonable security practices | §79 safe-harbour requires takedown procedure; §43A "reasonable security practices" baseline | ToS §Acceptable Use + Takedown procedure + DPA technical safeguards | LACI §3 (implicit) |
| 3 | **Consumer Protection Act 2019 + E-Commerce Rules 2020** | MeeSell helps sellers prepare listings sold downstream on Meesho | Marketplace intermediary disclosures (§5 of E-Commerce Rules); country-of-origin (§6(5)(g)) | ToS Service Description + product schema country-of-origin (DBA §2.2) | LACI §3 + §4 |
| 4 | **CGST Act 2017 + GST regime** | SaaS subscription billing | GST registration (above ₹20L or first B2B request); 18% SAC 998314 or 998361; tax invoice per Rule 46 | GST registration checklist + Invoice template + Pricing page disclosure | LACI §2 + §7 |
| 5 | **RBI PA-O Master Directions Sept 2025** | Inbound webhook from Razorpay (PA-O); future subscription billing | Inherited via Razorpay merchant agreement — no direct registration | Razorpay KYC pack (§12) | LACI §5.4 |
| 6 | **Legal Metrology (Packaged Commodities) Rules 2011** | All packaged-good listings | Mandatory manufacturer/packer/importer/country-of-origin (collected in seller_profile) | seller_profile schema (DBA §2.2) + ToS Seller Representations + Export Adapter (BEA §2.8 + §0.G §12.6) | LACI implicit (verify) |
| 7 | **Companies Act 2013** | Choice of entity (Sole Prop / OPC / LLP / Pvt Ltd) | Founder decision per LACI §10.1; OPC = no AGMs, single shareholder; Pvt Ltd required if VC raise within 12 months | Founder decision §15 + Incorporation paperwork (out of scope for this doc) | LACI §1 |
| 8 | **Per-super-category statutes** (FSSAI, BIS, DCA, WPC, AICTE, etc.) | Sub-set of sellers per super-category | Collect the certificate number in `seller_profile.compliance_extensions` (DBA §4.1); verification responsibility rests with seller | seller_profile schema + ToS Seller Representations + per-super-category data-collection notice | §13 of this doc |

**LACI §10 founder decisions** (the 8 outstanding) — each blocks one or more rows above. The dependency map is in §15.

---

## Section 4 — Sub-Processor Register

STATUS: LOCKED (2026-06-05)

Every external vendor that processes seller personal data MUST be enumerated in the Privacy Policy (DPDP §6 notice obligation) and in the DPA Annex (if MeeSell signs DPAs with enterprise customers in V1.5). This section is the source of truth for both.

Mirrors `IA §3.2`, `IA §4`, and `BEA §1.E` egress map:

| # | Vendor | Service | Data processed | Region | Cross-border? | Required disclosures | Action item |
|---|---|---|---|---|---|---|---|
| 1 | **Razorpay** | Inbound webhook (V1); subscription billing (V1.5) | Payment metadata, KYC documents (§12), card data NEVER touches MeeSell | India (RBI-licenced) | No | Privacy Policy "Who we share with"; ToS Payment Terms; Razorpay merchant agreement (signed during KYC) | Founder must complete KYC pack §12. |
| 2 | **MSG91** | Transactional SMS (OTP only — `iam` module per BEA §2.1) | Phone number, OTP timestamp, IP (for whitelist) | India | No | Privacy Policy "Who we share with"; MSG91 commercial agreement | MSG91 IP whitelist must be refreshed on every founder-IP rotation per IA §12.1. |
| 3 | **Google Cloud (GCP — VM + Artifact Registry + Secret Manager)** | Compute, image registry, secret storage | All data at rest + in transit at the platform layer | `asia-south1` (Mumbai) | No (in-region) | Privacy Policy "Where data is stored"; GCP Customer Agreement (already in force) | Confirm GCP Data Processing Addendum is enabled for the project. |
| 4 | **Google Cloud Storage** | Object storage for images + XLSX + audit archive | Image binaries, XLSX exports (PII), 1-year audit archive (PII-scrubbed) | `asia-south1` | No | Privacy Policy "Where data is stored"; same GCP DPA | Public-access prevention is ON (IA §3.2) — verify on every IaC apply. |
| 5 | **Gemini 2.5 Flash API (Google)** | AI text + vision (Smart Picker, Auto-fill, watermark detect) | Product titles, descriptions, image binaries (vision) | Multi-region (Google routes globally) | **Yes** (transfer outside India during inference) | Privacy Policy "AI processing" + DPDP §16 disclosure; Google Gemini API Terms | §15 founder decision: is cross-border AI inference acceptable for V1? (Default: yes, disclose.) |
| 6 | **LangFuse** | Async AI trace egress (fire-and-forget) — sees prompt + response | Same data as Gemini (mirrored for observability) | Vendor jurisdiction **TBD** — likely US or EU | **Likely yes** | Privacy Policy disclosure or remove from V1 | §15 founder decision: disable LangFuse for V1 until jurisdiction confirmed, OR self-host. |
| 7 | **Let's Encrypt** | TLS certificate issuance via HTTP-01 | Domain name only; no PII | Internet Security Research Group (US) | Domain-only (no PII transit) | Cookie Policy / Cookie Banner — no, this is TLS infra; minor disclosure in "Vendors" footnote | None. |
| 8 | **Namecheap** | DNS + domain registrar | Domain registration metadata (founder name/address — WHOIS) | US | Domain-only | Founder's WHOIS data, NOT seller data; out of Privacy Policy scope but on founder's personal compliance | Consider WHOIS privacy on the registrar dashboard. |
| 9 | **GitLab** (CI/CD via WIF) | Source code hosting + CI runners | Source code only; no seller PII flows through CI in V1 | EU/US (GitLab.com) | Source-only | DPA-internal note: CI does not process seller PII | WIF means no keys leave Google (IA §10) — defensible "reasonable security practice". |
| 10 | **Mailgun** (V1.5+, deferred per IA §13) | Transactional email | Email address + content (e.g., welcome, payment receipt) | US (Atlanta primary) | **Yes** | Privacy Policy update at V1.5 launch | Not in V1 scope; flag for V1.5 legal re-review. |

**Total V1 sub-processors disclosed in Privacy Policy: 8** (rows 1-8). Mailgun (#10) joins on V1.5 launch.

---

## Section 5 — Cross-Border Data Transfer Map

STATUS: LOCKED (2026-06-05)

DPDP §16 governs transfer of personal data outside India. The DPDP Rules 2025 anticipate a "negative list" of restricted countries published by the Central Government; **the list is not yet published as of Q2-2026** (LACI implicit). Until publication, prudent posture is: transfer is allowed, but MUST be disclosed in the privacy notice, and MUST be on a contract that imposes "equivalent" data-protection obligations.

Per-vendor cross-border posture:

| Vendor | Transfer happens? | Defensible basis | Disclosure language for Privacy Policy |
|---|---|---|---|
| Gemini (Google) | Yes — inference may route to US / EU / global Google data centers | Google Gemini API Terms imposes Google's enterprise data-protection terms | "When you use AI features, your product text and image content may be transferred to and processed by Google Cloud in multiple regions including outside India. Google handles this data under its enterprise data-protection commitments." |
| LangFuse | Likely yes | **Undetermined until vendor confirmed.** §15 founder decision recommends DISABLING LangFuse in V1 until confirmed. | Either omit (if disabled) or "AI trace data may be processed by LangFuse in [jurisdiction]." |
| Mailgun (V1.5) | Yes — US | Mailgun DPA + standard contractual safeguards | "Transactional email is sent via Mailgun in the United States." |
| All others | No | In-region or non-PII | None required. |

**Conservative recommendation:** include a single "Cross-border transfers" section in the Privacy Policy that lists Gemini and Mailgun (when launched) and references DPDP §16. Lawyer review required.

---

## Section 6 — Tenant Isolation as a Legal Control

STATUS: LOCKED (2026-06-05)

V1 isolation strategy: **app-level `user_id` scoping** (DBA §9.1). RLS deferred to V1.5 per DBA §9. The legal narrative:

- **In Privacy Policy ("How we protect your data"):** "Every seller's data is isolated by a per-account identifier. Our software is engineered so that no request can return another seller's data. We enforce this through code reviews and automated tests." (Wired in `privacy-policy.md` §9.)
- **In DPA Annex 2 ("Technical and Organisational Measures"):** cite BEA §4.C `core/tenancy.py.scope_to_user` + the CI linter rule (BEA §4.C "Forward reference") + the cross-module matrix (BEA §2.D) as the structural controls.

**V1.5 RLS migration is a forward-promise** in the DPA — enterprise customers will ask "do you support row-level security?" and the honest answer in V1 is "app-layer scoping today; database-layer RLS landing V1.5 (committed)". This must NOT be over-promised. The DPA template (to be drafted) will phrase the V1.5 RLS commitment as a **roadmap representation**, not a binding warranty, so a slipped RLS timeline does not become a contract breach. Indian lawyer reviews the exact wording.

**Cross-tenant data leak is automatically a DPDP §17 breach.** Breach runbook (§8) lists cross-tenant leak as the first detection trigger. The 72-hour Data Protection Board notification clock starts at the moment cross-tenant return is confirmed in audit traces, not at the moment a customer reports it.

**Operational reinforcement.** The BEA §4.C ContextVar defence-in-depth (G15 gap item in DBA §13) becomes mandatory in V1.5 alongside RLS. Each layer (`scope_to_user` helper + ContextVar enforcement + RLS) catches a different class of bug: forgetting to filter (helper), bypassing the helper (ContextVar), accidentally setting the wrong tenant in middleware (RLS). All three are cited collectively in the DPA TOMs.

---

## Section 7 — Consent + Data-Subject Rights Lifecycle

STATUS: LOCKED (2026-06-05)

DPDP §6 + §11 enumerate the lifecycle MeeSell MUST implement. Mapping each onto the as-built system:

| DPDP duty | UI surface | Backend surface | Status |
|---|---|---|---|
| **Notice at collection** | Signup form below OTP field | `iam` module emits standard 201 response on first OTP-verify | Not yet wired. Founder approves copy; FE wires per `meesell-angular-component-builder` hand-off. |
| **Consent capture** | Explicit checkbox (NOT pre-ticked), linked to live Privacy + ToS | `iam` module persists timestamp + consent version in `audit_events` (event_type `auth.consent`) | Not yet wired. New event_type to add to BEA §4.G audit catalogue. |
| **Right to access** | Account settings page → "Download my data" button | New endpoint: `GET /api/v1/seller-profile/export-personal-data` (out of 27-endpoint V1 contract — V1.5 addition) | **V1 GAP.** Workaround: respond manually via Grievance Officer email within 7 days. Document in Privacy Policy. |
| **Right to correction** | Already exists — Account settings → seller profile edit | `customer` module `PATCH /seller-profile` (BEA §2.2) | Wired. |
| **Right to erasure** | New page: Account settings → "Delete my account" | New endpoint: `DELETE /api/v1/users/me`. Workflow: (1) anonymise `users.phone` to SHA-256; (2) NULL `email`; (3) CASCADE seller_profile/catalogs/products/product_drafts; (4) leave `exports`, `audit_events` (ON DELETE RESTRICT per DBA §2.11/§2.12 — but anonymise user_id-keyed PII in those rows) | **V1 GAP** (the endpoint and workflow are not in the 27-endpoint contract per BEA §0.C). Workaround for V1: manual erasure via Grievance Officer ticket, completed within 30 days. Document in Privacy Policy. |
| **Right to withdraw consent** | Account settings → marketing email toggle | Add `users.marketing_consent_at` column? OR persist in `seller_profile.compliance_extensions`? → DECISION pending | **V1 GAP.** Recommendation: skip marketing email in V1 entirely (transactional only) → no withdrawal surface needed. Lock in §15. |
| **Right to nomination** | Account settings → "Nominate a successor" field | New columns on `users` (V1.5) | **V1 SKIP** — disclose in Privacy Policy that nomination is a V1.5 feature; manual via Grievance Officer in interim. |
| **Right to grievance** | Footer Grievance Officer block on every page + dedicated `/grievance` form | New endpoint: `POST /api/v1/grievance` writes to a `grievance_tickets` table (V1.5) | **V1 GAP.** Workaround: published email address + 7-day SLA, manual ticketing. Lock email in §15 founder decision #6. |
| **Right to data portability** | Same as Export feature (Feature 9) | `export` module already produces XLSX | Wired — but disclose that the seller can request a separate "personal data" extract (different from Meesho catalog XLSX) via Grievance Officer. |

**V1 gap summary:** rights to access, erasure, and grievance ticket are handled MANUALLY in V1 via the Grievance Officer email, within the DPDP-required 7-day timeline. This is a defensible posture for a pre-PMF SaaS provided the Grievance Officer is reachable and responsive. Privacy Policy MUST set this expectation explicitly.

---

## Section 8 — Breach Response + Grievance Officer Runbook

STATUS: LOCKED (2026-06-05)

DPDP §17(2) requires notification to the Data Protection Board "in such form and manner and within such time as may be prescribed". The Rules 2025 prescribe 72 hours (LACI §6.1 — verify with lawyer). The runbook below codifies the steps; it lives at `docs/legal/breach-response-runbook.md` once locked.

### 8.1 Detection triggers

- Cross-tenant data return in any test or production trace (`audit_events` shows `user_id` mismatch on a payload).
- Unauthorized GCS object access (audit via GCS access logs — IA §13 deferred but log retention IS on).
- JWT secret leak / Secret Manager unauthorized access.
- Backup data on founder laptop seized / compromised (IA §12.4 + §13 deferred).
- Sub-processor (Razorpay / Gemini / MSG91 / LangFuse) reports a breach affecting MeeSell tenants.

### 8.2 Response sequence (T+ in hours from detection)

| T+ | Step | Owner | Output |
|---|---|---|---|
| 0 | Confirm breach. Capture `request_id`, `user_id`s affected, timestamp range. | Founder + on-call | Incident log entry. |
| 0-2 | Stop the bleed (revoke compromised tokens via Valkey allowlist DEL — BEA §4.B Lua atomic; rotate secrets via IA §12.4 if applicable). | Founder | Code/config change deployed. |
| 2-6 | Estimate impact — number of users, data categories, jurisdictions. | Founder | Internal memo. |
| 6-24 | Draft notification to Data Protection Board AND affected sellers. | Founder + legal-writer (templates) | Notification drafts. |
| 24-72 | Send notifications. Notify Razorpay if payments are implicated. | Founder | Notifications sent. |
| 72-168 | Post-mortem; control gap; remediation plan. | Founder | Post-mortem doc + JIRA-equivalent issue. |

### 8.3 Grievance officer SLA

- Acknowledge within 24-72 hours with a tracking ID (LACI §6.2).
- Resolve within 7 days (LACI §6.2 — confirmed citation).
- Escalation: if unresolved, founder is the final escalation point; document the unresolved state for the Data Protection Board if needed.

### 8.4 Template responses (drafts in `docs/legal/breach-templates.md`)

- Tenant data leak — affected sellers
- Sub-processor breach — affected sellers
- Routine grievance acknowledgement
- Routine grievance resolution
- Routine grievance escalation

(Drafts deferred to later session; this section locks the topology.)

---

## Section 9 — Retention Schedule

STATUS: LOCKED (2026-06-05)

Per-table retention, derived from `DBA §10`, `BEA §4.G`, and DPDP §10(3) (data minimisation — no retention beyond purpose). The schedule is the source of truth for:

- Privacy Policy "How long we keep your data" section.
- DPA Annex 3 "Retention".
- The Celery beat task that purges aged data (operational; deferred per DBA §13 + IA §13).

| Table | Hot retention | Archive retention | Trigger to purge | Legal basis |
|---|---|---|---|---|
| `users` | Lifetime of account | Anonymised survivors in `audit_events` / `exports` | Account deletion request (manual V1) | DPDP §10(3) |
| `seller_profile` | Lifetime of account | None — purged on user erasure (CASCADE) | Account deletion | DPDP §10(3) |
| `catalogs`, `products`, `product_images`, `pricing_calcs` | Lifetime + 30 days grace after `deleted_at` | None | Soft-delete + Celery purge after 30 d | DPDP §10(3) + dispute window |
| `product_drafts` | 30 days from `saved_at` (proposed — §15) | None | Celery beat (DBA §13 — pending founder ruling) | DPDP §10(3) |
| `exports` | 1 year | 1 year archived in GCS | Manual archive workflow | Consumer dispute window + Razorpay chargeback windows |
| `audit_events` | 90 days hot in Postgres | 1 year archived in GCS | Celery beat (deferred per DBA §13) | DPDP §8(5) record-of-processing + IT Act audit duty |
| `templates`, `categories`, `field_enum_values`, `field_aliases` | Lifetime (refreshed quarterly) | None | Quarterly re-seed (IA refresh) | Operational; no PII |

**Cross-cascade rule:** because `exports.user_id` and `audit_events.user_id` are `ON DELETE RESTRICT` (DBA §3 cascade chain), user deletion CANNOT hard-delete those rows. Erasure workflow (§7) MUST anonymise the FK-linked data:
- `audit_events.diff_jsonb` is PII-scrubbed at write (BEA §4.G) — already compliant.
- `exports.gcs_path` retains the user_id in the path — must be moved or renamed on erasure.
- This is a non-trivial workflow; document as a V1 manual procedure under §7.

---

## Section 10 — Audit Log as Compliance Evidence

STATUS: LOCKED (2026-06-05)

`audit_events` is the system's compliance evidence layer (BEA §2.10, §4.G, DBA §2.12, §10.1). The legal posture:

- **DPDP §8(5):** every Data Fiduciary must "maintain records of personal data processing". `audit_events` IS that record.
- **Append-only invariant:** "no UPDATE, no DELETE in application code" (DBA §2.12 operational rules) — enforces the integrity needed for evidentiary value.
- **PII scrubbing at write:** phone hashed via `AUDIT_PII_SALT` (IA §4); FSSAI / GST stripped (BEA §4.G) — satisfies DPDP §10(2) data-minimisation even on the audit path.
- **5-minute coalescing:** reduces volume from ~3K/day to ~300 rows/day (DBA §2.12 + BEA §4.G). Non-autosave events (export, profile update, login) are NEVER coalesced — preserves per-event evidentiary granularity.
- **Coverage of legal events** the audit catalogue MUST include (extending BEA §4.G event_type list):
  - `auth.login` ✓ (BEA §4.G)
  - `auth.consent` (NEW — see §7 above)
  - `auth.logout` (NEW — supports right-to-revocation evidence)
  - `seller_profile.update` ✓
  - `product.patch` ✓
  - `product.export` ✓
  - `user.deletion_request` (NEW — supports §7 erasure-workflow evidence)
  - `user.data_export_request` (NEW — supports §7 portability-workflow evidence)
  - `grievance.opened` (V1.5 — when `grievance_tickets` table lands)
  - `breach.detected` (operational — not seller-facing)

**The 4 new event_types** are a backend change request that this document files against `BEA §4.G`. Coordinator hand-off goes to `meesell-backend-coordinator` once §10 is LOCKED.

---

## Section 11 — Intellectual Property — AI Output, Seller Content, Brand/Image Rights

STATUS: LOCKED (2026-06-05)

Four IP surfaces, each governed by a different clause:

### 11.1 Seller's input content (product text + images)

- Seller retains all rights to text and images they upload.
- MeeSell licence (granted by seller via ToS acceptance) is "non-exclusive, royalty-free, worldwide, sub-licensable to sub-processors (Google Gemini, GCS) for the purpose of providing the service".
- Standard SaaS clause; lawyer review.

### 11.2 AI-suggested output

- `products.ai_suggestions_jsonb` stores Gemini-generated text.
- Per Google Gemini API Terms (cite verbatim from Google's published Terms after lawyer review), the customer (MeeSell, on behalf of the seller) is responsible for input/output IP rights.
- MeeSell makes NO IP claim on AI-generated text; seller may use, modify, or discard.
- Once seller "adopts" an AI suggestion into `products.fields_jsonb`, it becomes seller content under §11.1.

### 11.3 MeeSell's compiled dataset (the moat)

- `templates`, `categories`, `field_enum_values`, `field_aliases` — collectively the "MeeSell Catalog Schema Library".
- India has no statutory database right; MeeSell's protection is contractual via ToS §"Intellectual Property" and via the "no scraping" clause.
- The Meesho-scrape source carries a separate risk (BUSINESS_STRATEGY §11.1 + §11.2). ToS must acknowledge MeeSell's quarterly refresh process — NOT a clause that creates a duty to Meesho.

### 11.4 Third-party brand / watermark presence in images

- Watermark detection is *advisory* (image module + AI track per BEA §2.5).
- MeeSell does NOT verify image provenance; if a seller uploads a competitor's image with watermark, MeeSell flags but does NOT block.
- ToS §"Acceptable Use" prohibits IP infringement; takedown procedure per IT Act §79 safe-harbour.

### 11.5 Required takedown procedure (IT Act §79)

- Public email: `takedown@meesell.in` (or chosen domain — see §15 founder decision #8 for legal name).
- Procedure: rights-holder sends notice → MeeSell acknowledges in 24 h → investigates in 7 d → removes if substantiated.
- Failure to maintain procedure = loss of §79 safe-harbour.

---

## Section 12 — Payment Compliance — Razorpay, GST, Invoicing, KYC

STATUS: LOCKED (2026-06-05)

### 12.1 Razorpay KYC pack (`docs/legal/razorpay-kyc-checklist.md`)

Document set FORKS by legal entity (LACI §5.1):

**Sole Proprietorship (recommended per LACI §11):**
- Proprietor PAN (= business PAN)
- Government ID (Aadhaar / Passport / Voter ID)
- GST certificate (strongly recommended)
- Cancelled cheque in business name
- Business address proof
- Live website with HTTPS ✓ (IA §7 — `dev.mesell.xyz`, `www.mesell.xyz` deferred to Week 2)
- Live Privacy Policy URL ← THIS doc's §3 disclosure
- Live ToS URL
- Live Refund Policy URL
- Contact Us page with email + phone

**OPC / Pvt Ltd (alternate, recommended at Month 3 per LACI §11):**
- Company PAN
- Certificate of Incorporation
- MOA + AOA
- Director PAN + Aadhaar
- GST certificate
- Cancelled cheque in company name
- All website pages above

### 12.2 Name match (the #1 KYC rejection cause)

**Bank account name = PAN name = GST legal name = Razorpay merchant name** — letter-for-letter (LACI §5.2). Founder decision #8 (§15) locks the legal business name.

### 12.3 GST registration (`docs/legal/gst-registration-checklist.md`)

Per LACI §2.3:
- Portal: `gst.gov.in` (₹0)
- CA/vendor: ₹2,500–5,000
- Documents: PAN, Aadhaar, address proof, bank details, photograph, incorporation cert if entity
- Timeline: 7-10 working days
- SAC: 998314 ("IT design and development services") or 998361 — confirm with CA before first invoice (LACI §7).
- Rate: 18%.

### 12.4 Invoice template (`docs/legal/invoice-template.md`)

Per CGST Rule 46 + LACI §7:
- GSTIN (MeeSell's, post-registration)
- Customer name + GSTIN (B2B)
- Invoice number (sequential, financial-year prefixed, e.g., `MEE/2026-27/0001`)
- SAC code
- Taxable value
- CGST + SGST OR IGST split (depends on customer state — Razorpay handles automatically when configured)
- Total
- Place of supply
- Digital signature (Razorpay-generated)

### 12.5 Pricing display (LACI §10 decision 7)

V1 default per PRICING_LOCKED §5: **inclusive of GST** ("₹499/mo incl. GST"). Inclusive math: base ₹422.88 + GST ₹76.12 = ₹499 (LACI §2.4). Founder confirms in §15 decision #7.

### 12.6 Refund policy hooks (`docs/legal/refund-policy.md` — see §14)

Per LACI §10 decision #5. 4 variants — founder picks one in §15.

---

## Section 13 — Per-Super-Category Statutory Touchpoints

STATUS: LOCKED (2026-06-05)

`seller_profile.compliance_extensions` JSONB (DBA §4.1) is the structural surface; per-super-category statutes govern the *content* of each key. Each statute has its own register / regulator / penalty regime — MeeSell's role is collection-only; the seller is the registrant of record.

| Super-cat | super_id | Statute | Identifier collected | Verification posture | ToS clause |
|---|---|---|---|---|---|
| Grocery | 26 | Food Safety and Standards Act 2006 + Packaging & Labelling Regulations | FSSAI license number + expiry | Seller-asserted; no FSSAI database lookup in V1 | Seller Representations + Liability cap |
| Kids & Toys | 13 | BIS Act 2016 + Toys (Quality Control) Order 2020 | BIS / ISI certification number | Seller-asserted | Same |
| Consumer Electronics | 16 | BIS Act + WPC / DoT registration for wireless devices | BIS-ISI, R-number, IS-number, CM-L number | Seller-asserted | Same |
| Beauty & Health | 19, 36, 37, 14, 88, 34 | Drugs and Cosmetics Act 1940 + Drugs and Cosmetics Rules 1945 + Cosmetic Rules 2020 | License registration number + type + expiry | Seller-asserted | Same |
| Home & Kitchen appliances | 30 | BIS Act + (state-level) Trade License | License number + expiry | Seller-asserted | Same |
| Books | 80 | RTI / AICTE (no central registry for ISBN; ISBN-International via Raja Rammohun Roy National Agency for ISBN) | ISBN / publisher ID (optional per LACI §10 decision #1) | Optional field (LACI §12.1 ruling) | Same |

**Universal ToS language:** "Seller represents and warrants that all statutory licence numbers entered are current, valid, and lawfully held. MeeSell does not verify the validity of any licence number entered. Liability for statutory non-compliance arising from inaccurate or expired licence data rests solely with the seller."

This is the safe-harbour stance that keeps MeeSell as a passive collection layer and not a co-regulator. Lawyer review essential.

---

## Section 14 — Document Mapping — Surface → Privacy / ToS / DPA Clause

STATUS: LOCKED (2026-06-05)

This section is the **traceability matrix** from system surface to legal document clause. Every legal-document section below is in scope per `meesell-legal-writer.md`.

| System surface | Privacy Policy clause | ToS clause | Refund Policy clause | Cookie Policy clause | DPA clause |
|---|---|---|---|---|---|
| OTP / consent capture (§1) | §"What we collect" — phone, IP, timestamp | §"Account & Eligibility" | — | — | Annex 2 — auth flow |
| Seller profile (§2.2) | §"What we collect" — business-compliance fields | §"Seller Representations" | — | — | Annex 3 — categories of data |
| Compliance extensions (§13) | §"What we collect" — statutory identifiers | §"Seller Representations" + per-statute disclaimer | — | — | Annex 3 — categories of data |
| Catalog / product (§2.7-§2.8) | §"What we collect" — product data | §"Acceptable Use" + §"Intellectual Property" | — | — | Annex 2 — data flow |
| AI Auto-fill / Smart Picker (§1, §11.2) | §"AI processing" + §"Cross-border transfer" | §"AI Output IP" | — | — | Annex 2 — sub-processor (Gemini) |
| Image upload (§2.9) | §"What we collect" — image content | §"Acceptable Use" + §"Takedown" | — | — | Annex 3 |
| Pricing / GST (§12) | — | §"Payment Terms" + §"Pricing" | §"Refund eligibility" | — | — |
| Export XLSX (§2.11) | §"How we use" — data delivery | §"Service Description" + §"Data Portability" | — | — | Annex 3 |
| Audit log (§10) | §"How long we keep" + §"How we protect" | — | — | — | Annex 2 — TOMs |
| Auth tokens (FE-D5; §1.B) | §"How we protect" (15-min access TTL, server-side revocation) | — | — | §"Functional cookies" (refresh_token cookie disclosure) | Annex 2 — TOMs |
| Razorpay webhook (§12.1) | §"Who we share with" — Razorpay | §"Payment Terms" | §"Refund process" | — | Annex 1 — sub-processor |
| Sub-processors (§4) | §"Who we share with" — full list | — | — | — | Annex 1 — sub-processor list |
| Cross-border (§5) | §"Cross-border transfers" | — | — | — | Annex 1 |
| Tenant isolation (§6) | §"How we protect" | — | — | — | Annex 2 — TOMs |
| Data-subject rights (§7) | §"Your rights" — entire section | §"Termination" (links to erasure) | — | — | Annex 4 — data-subject request procedure |
| Breach response (§8) | §"Breach notification" | — | — | — | Annex 5 — breach notification SLA |
| Retention (§9) | §"How long we keep" | — | — | — | Annex 3 — retention |
| Grievance Officer (§7, §8.3) | §"Grievance Officer" footer block | §"Notices" | §"Refund disputes" | — | Annex 4 |
| Takedown (§11.5) | — | §"Takedown procedure" | — | — | — |

**8 legal documents to produce** (per `meesell-legal-writer.md` Scope IN):
1. `docs/legal/privacy-policy.md` — closes 12 surface rows above
2. `docs/legal/terms-of-service.md` — closes 9 rows
3. `docs/legal/refund-policy.md` — closes 4 rows
4. `docs/legal/cookie-policy.md` — closes 1 row (refresh-token functional-cookie disclosure)
5. `docs/legal/dpa-template.md` — closes 9 rows (V1.5 enterprise; V1 = template only)
6. `docs/legal/razorpay-kyc-checklist.md` — closes §12.1
7. `docs/legal/gst-registration-checklist.md` — closes §12.3
8. `docs/legal/invoice-template.md` — closes §12.4

Plus in-product strings (`docs/legal/in-product-strings.md`) for the consent UI + Grievance footer + cancellation copy (hand-off to `meesell-angular-component-builder`).

---

## Section 15 — Founder Decisions Blocking Legal Surfaces

STATUS: LOCKED (2026-06-05 — 13 of 15 ratified; 2 explicitly DEFERRED to Stellaxis incorporation; status is now closed for V1 pre-incorporation drafting)

The 8 original LACI §10 decisions PLUS 7 new decisions surfaced by this architecture analysis. Per founder direction 2026-06-05 ("go with your recommendation"), the items below marked **RATIFIED** adopt the recommended value; the items marked **OPEN** still require an explicit founder ruling before downstream artifacts can ship.

### Original (LACI §10)

| # | Decision | Status | Adopted value / blocker |
|---|---|---|---|
| 1 | Legal entity (Sole Prop / OPC / LLP / Pvt Ltd) | **RATIFIED — OPC** | Founder ruling 2026-06-11. Entity: **Stellaxis (OPC) Private Limited**. All drafts: replace `[ENTITY SUFFIX]` with "(OPC) Private Limited". Razorpay KYC + GST checklists: use OPC/Pvt Ltd path only. |
| 2 | Incorporator (Vakilsearch / IndiaFilings / local CA) | **DEFERRED — bundled with #1** | Resolves alongside #1. Off V1 critical path. |
| 3 | GST timing (Week 1 / first customer / ₹20L) | **RATIFIED — Week 1** | Per LACI §11 founder-skip-ahead recommendation: register immediately for Razorpay credibility + clean invoicing. CA fee ₹2.5K-5K (LACI §2.3). |
| 4 | Privacy Policy source | **RATIFIED — Custom India-DPDP-native draft + lawyer review** | Authored by `meesell-legal-writer` from scratch per LACI §3.4 step 1+2; ₹5K-10K lawyer review before publishing (LACI §3.4 step 3). NOT TermsFeed (US-centric per LACI §12). |
| 5 | Refund policy variant | **RATIFIED — Variant B (7-day money-back on LTD only; no refunds on monthly)** | Founder ruling 2026-06-05. `docs/legal/refund-policy.md` collapsed to single-variant final. |
| 6 | Grievance Officer contact | **RATIFIED — `grievance@meesell.in`, routed to founder** | Per LACI §10.6 recommendation (founder personally for V1 = fastest response). Alias creates a stable contact across founder identity changes. |
| 7 | GST inclusive vs exclusive | **RATIFIED — Inclusive ("₹499/mo incl. GST")** | Per LACI §2.5 + PRICING_LOCKED §5 industry norm. Inclusive math: base ₹422.88 + GST ₹76.12 = ₹499. |
| 8 | Legal business name (PAN = GST = bank = Razorpay) | **RATIFIED — "Stellaxis"** | Founder ruling 2026-06-05. MeeSell is the product / trade name; **Stellaxis** is the legal business name (matches founder's GitLab org). Drafts now ship with `**Stellaxis** [ENTITY SUFFIX]` — the suffix (e.g., "Private Limited", "(OPC) Private Limited", or blank for Sole Prop) collapses once §15.1 is ruled. |

### New (surfaced by this architecture analysis)

| # | Decision | Status | Adopted value / blocker |
|---|---|---|---|
| 9 | Marketing email in V1 | **RATIFIED — No, transactional only** | Eliminates withdrawal-UI surface entirely. Per architectural recommendation 2026-06-05. |
| 10 | LangFuse in V1 | **RATIFIED — Disable** | Re-enable when vendor jurisdiction confirmed OR self-hosted lands (`MVP_ARCH §9.6` defers). §4 sub-processor row 6 marked "disabled in V1". |
| 11 | `product_drafts` TTL | **RATIFIED — 30 days** | Matches DPDP §10(3) data-minimisation posture. DBA §13 ruling resolved. |
| 12 | Cross-border transfer to Gemini | **RATIFIED — Accept and disclose** | Vertex AI India-only route deferred to V1.5. Privacy Policy §"Cross-border" closes. |
| 13 | Soft-delete grace period for products | **RATIFIED — 30 days after `deleted_at`** | Matches LTD refund window + dispute window. Celery purge task hand-off pending. |
| 14 | Manual erasure workflow SLA | **RATIFIED — 30 days max, 7-day target** | Privacy Policy §"Your rights" sets this expectation. Lawyer review on final language. |
| 15 | Personal data export (right-to-access) SLA | **RATIFIED — Manual via Grievance Officer, 7 days** | Self-serve endpoint deferred to V1.5. Privacy Policy §"Your rights" sets this expectation. |

**Status summary:** **14 ratified, 1 explicitly DEFERRED (§15.2 incorporator — founder decides when filing)** as of 2026-06-11. Founder ruled 2026-06-05 that Stellaxis is not yet legally registered; #1 and #2 collapse on incorporation. Until incorporation, every draft carries the 5 placeholder tags inventoried in `docs/legal/placeholders-tracker.md`. The placeholders block **publishing**, not drafting — the full V1 legal pack can be authored, lawyer-reviewed, and pre-staged before Stellaxis is registered, then go live in a single placeholder-collapse-and-publish pass once incorporation completes.

---

## Section 16 — Deferred to V1.5

STATUS: LOCKED (2026-06-05)

| Item | Why deferred | Legal-doc impact |
|---|---|---|
| Self-serve "Download my data" endpoint | Not in 27-endpoint V1 contract (BEA §0.C) | Privacy Policy DISCLOSES manual workflow with 7-day SLA in V1; switches to "self-serve via Account Settings" in V1.5 |
| Self-serve "Delete my account" endpoint | Same | Same |
| Marketing email + withdrawal toggle | §15 decision #9 deferral | Privacy Policy omits marketing section in V1 |
| `grievance_tickets` table + endpoint | V1 uses email + manual ticketing | Privacy Policy lists Grievance Officer email; switches to in-app form in V1.5 |
| Row-Level Security (DBA §9 + §6 above) | DBA §13 deferred | DPA Annex 2 says "app-layer scoping today; RLS V1.5 (committed)" |
| Self-hosted LangFuse | Per §15 decision #10 if disabled in V1 | Privacy Policy + Sub-processor list omits in V1; re-added in V1.5 |
| Off-VM backup storage (IA §13) | Operational deferral | Pre-launch blocker per IA §13; "Pre-launch" implies before public launch — coordinate timing with Privacy Policy publication |
| Wildcard TLS cert (IA §13) | DNS-01 challenge work deferred | None on docs |
| Subscription billing business logic (Razorpay) | BEA §1.E V1 = webhook capture only | Refund Policy + ToS Payment Terms must describe MANUAL refund workflow for V1; V1.5 wires automated |
| Mailgun integration (V1.5+) | IA §13 deferred | Sub-processor disclosure added at launch |
| Significant Data Fiduciary classification | LACI §6.3 — not applicable at V1 scale | None on V1 docs; monitor as user count grows |

---

**End of document.** This is the SKELETON v1. Founder review opens with §15. No artifact under `docs/legal/` is authored until at least §3, §4, §7, §9, and §14 are LOCKED.

**Memory hand-off:** `meesell-legal-writer` memory is updated post-review. STATUS_LEGAL.md is updated on every section flip.

**Next session:** founder picks 1-2 sections to drive to LOCKED, then drafting begins on the artifacts unlocked by those sections.
