---
name: meesell-legal-compliance-copy
description: >-
  MeeSell's conventions for drafting legal and compliance copy — Privacy Policy, Terms of
  Service, Refund/Cancellation, Cookie Policy, DPA, the Razorpay KYC pack, the GST pack, plus
  transactional email templates and landing/marketing copy. Use this skill WHENEVER you are
  writing or editing any legal document, policy, consent text, compliance pack, email template,
  or marketing/landing copy for MeeSell — even if the user only says "write the privacy
  policy", "we need refund terms", "draft the KYC docs", "the consent wording", or "landing
  page copy". Do NOT use it for application code or API behavior (defer to the relevant builder
  skills) — this is doc authoring only.
---

# MeeSell Legal & Compliance Copy Conventions

These are the locked rules for MeeSell's legal, compliance, and marketing copy. They exist so
every document is India-law-correct (DPDP, GST, consumer protection), consistent in voice, and
honest about what the product does. They derive from `docs/LEGAL_AND_COMPLIANCE_INFO.md`, which
is the single source of truth and WINS over anything written here or from general knowledge.

## The non-negotiables (and why each matters)

- **`docs/LEGAL_AND_COMPLIANCE_INFO.md` is authoritative — read it first, every time.** Company
  entity name, registered address, GSTIN, grievance officer, data-retention periods, governing
  law/jurisdiction, and contact emails come from that file, never from assumption. A policy with
  a guessed entity name or wrong jurisdiction is worse than no policy.

- **India-first legal framing.** MeeSell serves Indian Meesho sellers. Policies follow the
  **DPDP Act 2023** (consent, purpose limitation, data-principal rights, grievance redressal),
  the **IT Act / SPDI Rules**, **Consumer Protection (E-Commerce) Rules**, and **GST** law. Don't
  template GDPR/CCPA boilerplate as if it were the governing regime — reference them only where
  genuinely applicable.

- **Consent is explicit, specific, and logged.** DPDP requires informed, unambiguous consent for
  each purpose (account, OTP/SMS, payments, analytics). The copy must state WHAT is collected,
  WHY, how long it's kept, and how to withdraw — matching the consent the app actually records.
  Copy and code must agree; never promise a control the product doesn't implement.

- **Never overstate or guarantee.** No "100% secure", no "guaranteed Meesho approval", no implied
  earnings promises. Claims about AI quality, pricing, or listing success must be honest and
  hedged. Misleading copy is both a legal risk and a trust risk with sellers.

- **Payments copy matches Razorpay + the real billing model.** Subscription terms, the ₹499–1,999
  tiers, the renewal/cancellation/refund mechanics, and the Razorpay KYC pack must reflect what
  Razorpay Subscriptions actually does and what the backend enforces. Refund terms can't promise
  something the plan-guard / billing flow won't honor.

- **Plain, seller-friendly voice.** The audience is small Meesho sellers (often Tirupur/Tamil
  Nadu, mobile-first, not lawyers). Lead with plain-language summaries, then the formal clause.
  Short sentences. Define jargon. Marketing copy is confident but never deceptive.

- **No secrets, no real PII in templates.** Email templates and examples use placeholders
  (`{{seller_name}}`, `{{plan}}`), never real keys, tokens, or a real person's data.

## Document set and what each must contain

- **Privacy Policy** — data collected (phone, email, catalog content, images, payment metadata),
  purposes, retention, third parties (MSG91, Razorpay, Google/Gemini, GCS), data-principal rights,
  grievance officer, withdrawal of consent.
- **Terms of Service** — eligibility, acceptable use, the catalog/CSV-export nature of the service
  (no Meesho affiliation/endorsement), subscription terms, limitation of liability, governing law.
- **Refund & Cancellation** — subscription cancellation flow, refund eligibility window, proration
  stance — aligned to Razorpay + billing reality.
- **Cookie Policy** — what's stored client-side; note the auth model keeps no tokens in
  localStorage (refresh token is an HttpOnly cookie).
- **DPA** — for processors; sub-processor list; data-transfer basis.
- **Razorpay KYC pack / GST pack** — entity, GSTIN, bank, authorized-signatory docs per Razorpay
  and GST requirements; pull specifics from the source-of-truth doc.
- **Email templates** — OTP, welcome, subscription receipts/renewal/failure, grievance
  acknowledgement; transactional tone, required unsubscribe/contact footer.
- **Landing / marketing copy** — value prop, honest feature claims, pricing clarity.

## Workflow for any legal/compliance doc

1. Read `docs/LEGAL_AND_COMPLIANCE_INFO.md` and lift the authoritative facts (entity, GSTIN,
   addresses, officer, retention, jurisdiction).
2. Draft with a plain-language summary up top, formal clauses below.
3. Cross-check every promise against what the product/code actually does (consent, refunds, data).
4. Flag any gap where the doc requires a fact not in the source file — escalate, don't invent it.
5. Keep a consistent defined-terms vocabulary across all documents.

## Quick checklist before you finish a copy task

- [ ] Read `docs/LEGAL_AND_COMPLIANCE_INFO.md`; all entity/GST/officer/jurisdiction facts sourced from it (none invented)
- [ ] India-first framing (DPDP, GST, Consumer Protection E-Commerce Rules) — not GDPR/CCPA boilerplate
- [ ] Consent text is explicit, purpose-specific, and matches what the app records
- [ ] No overstatement, no guarantees, no implied earnings/approval promises
- [ ] Payments/refund copy matches Razorpay Subscriptions + the real billing model
- [ ] Plain seller-friendly voice; jargon defined; summary-then-clause structure
- [ ] Placeholders only — no real PII, keys, or tokens in templates
- [ ] Defined terms consistent across the document set
