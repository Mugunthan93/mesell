# MeeSell — Legal, GST & Privacy Compliance Info

**Last updated:** 2026-06-04
**Status:** Info gathering — founder review required
**Audience:** Solo founder, no prior legal/compliance knowledge
**Scope:** Bootstrap B2B SaaS, Indian sellers, Razorpay payments (₹499/mo Pro, ₹4,999 LTD)

> This document presents options with cited rates. It does NOT make decisions for the founder. Section 10 lists the choices you need to make. Verify all rupee figures with a CA before paying — vendor pricing changes frequently.

---

## Section 1: Legal Entity Options for Indian SaaS

A "legal entity" is the business name and structure under which you operate. It decides who is liable for debts, how you pay tax, and whether you can later raise investment. Below are five options ranked from cheapest/fastest to most scalable.

### 1.1 Sole Proprietorship

- **What it is:** You operate as yourself. The business is legally indistinguishable from you personally.
- **Cost to set up:** Effectively ₹0 — no government registration required. You may want a Shop & Establishment certificate (₹500–₹2,000 depending on state) and a GST registration if turnover crosses the threshold.
- **Compliance burden:** Lowest. File personal income tax (ITR-3 or ITR-4). No annual ROC filings.
- **Personal liability:** Unlimited. If MeeSell is sued or owes money, your personal assets (house, savings) are at risk.
- **Bank account:** Open a Current Account in a business name ("MeeSell") with GST certificate + Shop Act + PAN.
- **Fundraising:** Cannot issue equity. Hard to raise institutional money.
- **Best for:** Pre-revenue or sub-₹10L revenue founders testing an idea.

### 1.2 Partnership Firm

Not relevant — MeeSell is a solo founder. Skip.

### 1.3 Limited Liability Partnership (LLP)

- **What it is:** A partnership with limited liability protection. Requires at least 2 designated partners (a relative or trusted nominee can be the second).
- **Cost to set up:** Vakilsearch advertises from ₹1,499 + government fees; total range typically ₹5,000–₹15,000 depending on capital contribution and state stamp duty. Source: [Vakilsearch LLP cost breakdown](https://vakilsearch.com/article/llp-registration-cost/), [RegisterKaro LLP fees 2026](https://www.registerkaro.in/post/llp-registration-fee).
- **Compliance burden:** Medium. Annual Form 8 + Form 11 filings. Statutory audit required only if turnover > ₹40L or contribution > ₹25L.
- **Personal liability:** Limited to your capital contribution.
- **Fundraising:** Hard. VCs and angels rarely invest in LLPs because they cannot hold shares.
- **Best for:** Solo founders who want liability protection, plan to stay bootstrapped, and never want VC money.

### 1.4 Private Limited Company (Pvt Ltd)

- **What it is:** A separate legal entity with shareholders and directors. Requires minimum 2 directors and 2 shareholders.
- **Cost to set up:** ₹8,000–₹25,000 typical range depending on state stamp duty, authorised capital, and service provider. Source: [RegisterKaro company registration cost guide](https://www.registerkaro.in/post/cost-of-company-registration-in-india-a-complete-breakdown).
- **Compliance burden:** High. Annual ROC filings (AOC-4, MGT-7), board meetings, statutory audit mandatory regardless of turnover, director KYC each year.
- **Personal liability:** Limited to your shareholding.
- **Fundraising:** Easiest. Clean cap table, standard for VC term sheets.
- **Best for:** Founders who plan to raise investment, add a team with ESOPs, or scale beyond ₹2 Cr revenue within 2 years.

### 1.5 One Person Company (OPC)

- **What it is:** A single-shareholder private limited company. Created specifically for solo founders by the Companies Act 2013.
- **Cost to set up:** ₹5,599 starter packages reported; total realistic range ₹8,000–₹18,000 including government fees, DSC, DIN, stamp duty. Vakilsearch advertises plans from ₹999 + government fees. Source: [Vakilsearch OPC registration](https://vakilsearch.com/one-person-company-registration), [Pricivo OPC cost comparison June 2026](https://www.pricivo.xyz/one-person-company-opc-registration-costs-india/), [IndiaFilings OPC](https://www.indiafilings.com/one-person-company).
- **Compliance burden:** Similar to Pvt Ltd but slightly relaxed — no requirement to hold AGMs, board resolutions can be signed by the single director.
- **Personal liability:** Limited.
- **Mandatory conversion threshold:** REMOVED. As of the Companies (Incorporation) Second Amendment Rules 2021, OPCs are NO LONGER forced to convert to Pvt Ltd when crossing ₹2 Cr turnover or ₹50L paid-up capital. Source: [RestTheCase OPC turnover limit 2026](https://restthecase.com/knowledge-bank/business-and-compliance/turnover-limit-for-one-person-company-in-india), [Razorpay Rize OPC threshold rules](https://razorpay.com/rize/blogs/opc-turnover-threshold-conversion-rules). This makes OPC significantly more attractive than older guides suggest.
- **Nominee requirement:** OPC requires a nominee (a relative or friend with PAN+Aadhaar) who would take over if you become incapacitated.
- **Fundraising:** Can be voluntarily converted to Pvt Ltd before a funding round (1–2 weeks process).
- **Best for:** Solo founders who want Pvt Ltd-level protection without bringing in a second shareholder/partner.

### 1.6 Recommendation Table

| If founder wants… | Choose |
|---|---|
| Lowest cost, fastest start, willing to accept personal liability | Sole Proprietorship |
| Limited liability, never raise VC, can find a second designated partner | LLP |
| Future-proof for VC/team, willing to pay higher compliance | Pvt Ltd |
| Pvt Ltd benefits with single shareholder, no nominee partner needed | OPC |

### 1.7 Specific Recommendation for MeeSell

Based on stated context (bootstrap, solo, no immediate VC plan, may scale):

- **Primary recommendation: OPC.** Reasoning:
  1. Limited liability protects personal assets when customers store sensitive catalog/business data with you (DPDP-related risk).
  2. The 2021 amendment removed the forced ₹2 Cr conversion trap — you can grow without forced restructuring.
  3. Cheaper than Pvt Ltd in compliance (no AGMs, simpler resolutions).
  4. Convertible to Pvt Ltd later if you raise money — clean transition.
- **Cheap fallback: Sole Proprietorship + upgrade later.** Reasoning:
  1. ₹0 vs ₹10K+ saves runway during the validation phase.
  2. Downside: you carry unlimited personal liability while the product is live.
- **Avoid for MeeSell V1:** Pvt Ltd (overkill until you raise), Partnership Firm (no second partner), LLP (harder to convert to Pvt Ltd later if VC arrives).

---

## Section 2: GST Registration

### 2.1 When GST Registration Is Required

GST registration becomes mandatory under any of these conditions:
- Aggregate turnover exceeds ₹20 lakh per financial year (₹10 lakh in special-category states: Manipur, Mizoram, Nagaland, Tripura).
- You make inter-state supply of services exceeding the threshold. Note: a 2017 notification exempts inter-state service suppliers from registration up to ₹20L turnover, BUT this is contested for SaaS — verify with CA.
- You are an e-commerce operator (TCS obligations).
- You voluntarily register (often useful for B2B credibility and to claim input tax credit).

Sources: [Taxwink inter-state supply rules](https://www.taxwink.com/blog/gst-on-inter-state-supply-of-services), [IndiaFilings compulsory GST registration](https://www.indiafilings.com/learn/compulsory-registration-under-gst), [RegisterKaro GST for software services 2026](https://www.registerkaro.in/post/gst-registration-for-software-it-services).

### 2.2 What Applies to MeeSell V1

- Subscription SaaS sold across India → inter-state supply.
- Customers are businesses (B2B) requiring GST invoices for input credit.
- Razorpay onboarding is smoother and more credible with GSTIN.
- Recommendation: register before crossing ₹20L turnover OR before first B2B customer requests GST invoice — whichever is earlier.

### 2.3 Registration Process

- Portal: gst.gov.in
- Documents needed:
  - PAN of business (founder PAN for sole prop, company PAN for OPC/LLP)
  - Aadhaar of founder/director
  - Business address proof (rent agreement + electricity bill, or property document)
  - Bank details (cancelled cheque or first page of passbook)
  - Photograph of founder
  - For OPC/LLP/Pvt Ltd: incorporation certificate, MOA/AOA or LLP Agreement
- Processing time: 7–10 working days
- Cost: ₹0 on the government portal. CA or service-provider fees ₹1,500–₹5,000 typical.

### 2.4 GST Rate for SaaS

- Rate: 18% (9% CGST + 9% SGST intra-state, or 18% IGST inter-state). Source: [RegisterKaro GST software services](https://www.registerkaro.in/post/gst-registration-for-software-it-services), [Ampuesto GST on SaaS](https://ampuesto.in/blog/gst-on-saas-digital-services-india/).
- On ₹499 Pro tier:
  - If pricing is GST-inclusive: base ₹422.88, GST ₹76.12, customer pays ₹499.
  - If pricing is GST-exclusive: base ₹499, GST ₹89.82, customer pays ₹588.82.
- Industry norm for Indian B2C/SMB SaaS: inclusive pricing (cleaner UX, no sticker shock).
- For LTD ₹4,999: inclusive — base ₹4,236.44, GST ₹762.56.

### 2.5 Recommendation

- Register GSTIN within Week 1, before first paying customer.
- Use a CA or a service provider (Vakilsearch, IndiaFilings, ClearTax) — estimated ₹2,500–₹5,000, verify with CA.
- Use inclusive pricing on the website ("₹499/mo incl. GST").

---

## Section 3: Privacy Policy

### 3.1 Why You Need One

- **Legal requirement** under the Digital Personal Data Protection Act (DPDP Act) 2023 — see Section 6.
- **Razorpay onboarding** requires a live Privacy Policy URL on your website.
- **App stores** (Play Store, App Store) reject submissions without one.
- **Customer trust** — B2B buyers check for it before signing up.

### 3.2 Mandatory Contents

Your Privacy Policy must clearly describe:
- **What data you collect:** phone, email, business name, GSTIN, catalog data (product images, descriptions, prices), payment metadata.
- **How you use it:** service delivery, customer support, billing, AI generation (Gemini), marketing communications.
- **Who you share it with:** Razorpay (payments), Gemini API / Google (AI processing), MSG91 or equivalent (SMS/OTP), GCP (hosting), email provider (transactional email).
- **Where data is stored:** GCP region(s).
- **Retention policy:** how long after account deletion.
- **User rights:** access, correction, deletion, data portability, consent withdrawal.
- **Grievance Officer contact:** name, email, response timeline (mandatory under DPDP).
- **Children's data:** state that the service is not intended for users under 18.
- **Cookies / trackers** if the website uses them.
- **Updates:** how you notify users of policy changes.

### 3.3 Generation Options

| Option | Cost | Notes |
|---|---|---|
| TermsFeed (free tier) | ₹0 base | Add-on clauses ~$10–$80 each for GDPR/CCPA/payment processor disclosure. One-time payment, not subscription. Source: [TermsFeed best generators](https://www.termsfeed.com/blog/best-privacy-policy-generators/) |
| iubenda Starter | ~$10/mo billed annually (~₹830/mo) | Includes Privacy Policy, ToS, Cookie Policy. Source: [iubenda comparison 2026](https://www.iubenda.com/en/blog/best-privacy-policy-generators/) |
| iubenda Pro+ | ~$15/mo billed annually (~₹1,250/mo) | All 10 generators, unlimited edits |
| Local lawyer (custom draft) | ₹5,000–₹15,000 one-time, estimated, verify | Best fit for India-specific DPDP language |
| Vakilsearch / IndiaFilings legal docs package | ₹2,000–₹5,000 estimated, verify | Includes Privacy + ToS + Refund |

### 3.4 Recommendation

1. Start with TermsFeed free template, customise for MeeSell specifics (Gemini AI mention, GSTIN collection, Indian jurisdiction).
2. Add a DPDP-specific addendum manually (Grievance Officer block, 7-day response commitment — see Section 6).
3. Get one lawyer review at ₹5,000–₹10,000 (estimated, verify) before scaling past 100 customers.

---

## Section 4: Terms of Service (ToS)

### 4.1 Why You Need One

- Limits founder liability (if a seller's catalog leak causes them damage, your ToS limits what they can claim).
- Defines acceptable use (no spamming customers, no illegal goods listed via your catalog).
- Required for any paid product.
- Sets subscription, cancellation, and refund rules.

### 4.2 Mandatory Contents

- **Service description:** what MeeSell does, what it does NOT do (e.g., "MeeSell is a tool; we do not guarantee sales outcomes").
- **Acceptable use policy:** no illegal goods, no scraping, no resale of access.
- **Account terms:** one account per seller, accuracy of info, password responsibility.
- **Payment terms:** subscription billing cycle, auto-renewal, failed-payment handling.
- **Refund / cancellation:** see Section 4.3 below.
- **Disclaimer of warranties:** "service provided as-is."
- **Limitation of liability:** typically capped at last 3 months of fees paid.
- **Termination clauses:** when MeeSell can terminate an account, what happens to data.
- **Intellectual property:** founder retains platform IP; sellers retain their catalog IP.
- **Governing law and jurisdiction:** India, [city of incorporation] jurisdiction.
- **Modification rights:** "we reserve the right to update these terms with 30-day notice."

### 4.3 Refund Policy Options

| Option | Description | Pro | Con |
|---|---|---|---|
| No refunds (strict) | All sales final | Maximises revenue retention | Hurts conversion; some payment gateways flag this |
| 7-day money-back | Refund within 7 days, no questions | Builds trust; legal-safe | Some abuse risk |
| Pro-rated cancellation | Monthly cancel anytime; LTD has 7-day window | Industry standard for SaaS | Slightly more billing complexity |

**Industry norm for Indian SaaS:** 7-day refund for first purchase + pro-rated cancellation for monthly. For LTD ₹4,999: 7-day refund window is standard.

### 4.4 Generation Options & Recommendation

Same vendors as Privacy Policy (Section 3.3). Recommended approach: TermsFeed template + manual customisation for MeeSell + ₹5K lawyer review before scaling.

---

## Section 5: Razorpay Compliance Requirements

### 5.1 What Razorpay Needs to Activate Live Payments

Documents required depend on entity type. Sources: [Razorpay KYC documents by business type](https://razorpay.com/docs/payments/business-types-kyc-documents/), [Razorpay payment gateway KYC onboarding guide 2026](https://razorpay.com/blog/payment-gateway-kyc-onboarding-india/).

**For Sole Proprietorship:**
- Proprietor's PAN (serves as business PAN)
- Government ID (Aadhaar, Passport, or Voter ID)
- GST certificate (if registered) — strongly recommended
- Bank account proof (cancelled cheque) in business name
- Business address proof
- Live website with HTTPS
- Live Privacy Policy URL
- Live Terms of Service URL
- Live Refund / Cancellation Policy URL
- Contact Us page with email + phone

**For OPC / Pvt Ltd:**
- Company PAN
- Certificate of Incorporation
- MOA + AOA (or LLP Agreement for LLP)
- Director's PAN + Aadhaar
- GST certificate
- Bank account proof in company name
- Address proof
- All website pages above

### 5.2 Critical Name Match Rule

**Bank account name, PAN name, and GST legal name MUST match EXACTLY.** Even "&" vs "and" causes rejection. Decide your legal business name once and use it everywhere. Source: [Razorpay payment gateway KYC onboarding guide 2026](https://razorpay.com/blog/payment-gateway-kyc-onboarding-india/).

### 5.3 Verification Timeline

1–3 working days from document submission to live activation.

### 5.4 RBI Master Directions

Razorpay operates under the September 2025 RBI Master Directions for Payment Aggregators (PA-O for online). MeeSell as a merchant is not directly regulated but inherits compliance obligations through Razorpay's onboarding. Source: [Razorpay payment gateway KYC onboarding guide 2026](https://razorpay.com/blog/payment-gateway-kyc-onboarding-india/).

---

## Section 6: DPDP Act 2023 Compliance

The Digital Personal Data Protection Act 2023 (DPDP Act) is India's primary data privacy law. The DPDP Rules 2025 added operational specifics. As a SaaS collecting seller PII (phone, email, business info), MeeSell is a "Data Fiduciary" and must comply.

### 6.1 Core Obligations

- **Get explicit consent** before collecting personal data. Implicit / pre-ticked boxes are NOT valid.
- **Provide a clear privacy notice** at the point of consent (what data, why, with whom shared).
- **Allow withdrawal of consent** as easily as it was given.
- **Allow data subject rights:** access, correction, erasure, grievance redressal, nomination.
- **Notify breaches** to the Data Protection Board within prescribed timelines.
- **Appoint a Grievance Officer** and publish contact details.

Sources: [DPDP Act compliance essentials](https://corridalegal.com/dpdp-act-compliance-essential-steps-for-businesses/), [Complydog SaaS DPDP guide](https://complydog.com/blog/india-dpdp-act-data-protection-privacy-compliance-saas), [DPDP grievance redressal duties](https://ksandk.com/data-protection-and-data-privacy/grievance-redressal-under-the-dpdp-act-2023/).

### 6.2 Grievance Officer Requirements

- **Must be appointed** — every Data Fiduciary including small SaaS.
- **Contact must be published** on the website / app.
- **Response timeline:** every complaint must be resolved within **7 days** of receipt; acknowledgement is expected within 24–72 hours, ideally with a tracking ID. Source: [DPDP grievance redressal](https://ksandk.com/data-protection-and-data-privacy/grievance-redressal-under-the-dpdp-act-2023/).
- **Internal escalation process** must be documented.
- **Who can be the GO:** anyone competent — for solo founder, founder themselves at the start, but ensure operational ability to respond within 7 days.

### 6.3 Significant Data Fiduciary (SDF) — Probably Not You Yet

Larger or higher-risk fiduciaries can be classified as Significant Data Fiduciaries by the government, triggering extra obligations (mandatory DPO based in India, DPIA, independent audit). MeeSell at V1 is unlikely to qualify, but monitor as you scale.

### 6.4 Practical Implementation for MeeSell V1

- **Signup flow:** explicit consent checkbox ("I have read and agree to the Privacy Policy and Terms"). Not pre-ticked. Link to both policies.
- **Account settings page:**
  - "Download my data" button → emails a JSON/CSV of stored data.
  - "Delete my account" button → triggers erasure workflow (within 30 days; retain only what is legally required).
  - "Withdraw consent for marketing" toggle.
- **Footer:** "Grievance Officer: [name], [email], response within 7 days."
- **Breach response runbook:** document who notifies the Data Protection Board, internal escalation, customer comms template.
- **Vendor list (sub-processors):** maintain and disclose in Privacy Policy — Razorpay, Gemini, GCP, MSG91, email vendor.

---

## Section 7: HSN / SAC Code for Invoicing

- **SAC code for SaaS subscription:** generally classified under heading 9983 (other professional/technical services) with specific 6-digit SACs depending on the activity. SAC 998314 covers "IT design and development services"; 998313 covers "IT consulting and support services". Many SaaS providers use 998314 or 998361 depending on classification. Source: [RegisterKaro GST software services](https://www.registerkaro.in/post/gst-registration-for-software-it-services).
- **Confirm exact SAC with your CA** — using the wrong SAC can trigger notices. Estimated, verify with CA.
- **GST rate:** 18%.
- **Invoice must include:** GSTIN, customer name + GSTIN (if B2B), invoice number (sequential, financial-year prefixed), SAC code, taxable value, CGST + SGST or IGST split, total, place of supply, signature/digital signature.

---

## Section 8: Recommended Order of Operations (Founder Action List)

### Week 0 (Now)
- [ ] Decide legal entity (recommendation: OPC; cheap fallback: Sole Prop)
- [ ] Confirm personal PAN and Aadhaar are valid; address proof in hand
- [ ] Reserve `.in` domain and business email
- [ ] Decide legal business name (used identically on PAN, GST, bank — see Razorpay name match rule)

### Week 1
- [ ] Apply for OPC or LLP via Vakilsearch / IndiaFilings / local CA (₹8K–₹18K estimated, verify)
- [ ] Open Current Account (HDFC / ICICI / Axis / Kotak — most have startup bundles)
- [ ] Apply for GSTIN via gst.gov.in or CA (₹0 govt; ₹2.5K–₹5K service)
- [ ] Draft Privacy Policy + ToS + Refund Policy from TermsFeed templates
- [ ] Appoint yourself as Grievance Officer; create founder@meesell.in (or chosen domain)

### Week 2
- [ ] Publish Privacy / ToS / Refund pages on the website with HTTPS
- [ ] Begin Razorpay merchant onboarding (1–3 working days for KYC)
- [ ] Receive GSTIN (7–10 working days from application)
- [ ] Optional: ₹5K–₹10K lawyer review of Privacy + ToS (estimated, verify)
- [ ] Wire signup flow consent checkbox + "delete my account" + "download my data" endpoints

### Week 3+
- [ ] Razorpay live → first paying customer
- [ ] First GST invoice issued (correct SAC code, sequential numbering)
- [ ] Monthly: GSTR-1 + GSTR-3B filings via CA (~₹1,500–₹3,000/month, estimated)

---

## Section 9: Estimated Total Setup Cost

All figures below are **estimated and require verification with a CA / service provider before payment**.

| Item | Cost Range | Source / Note |
|---|---|---|
| OPC incorporation (service provider) | ₹8,000 – ₹18,000 | [Pricivo OPC cost comparison](https://www.pricivo.xyz/one-person-company-opc-registration-costs-india/), [Vakilsearch](https://vakilsearch.com/one-person-company-registration) |
| LLP incorporation (alternative to OPC) | ₹5,000 – ₹15,000 | [Vakilsearch LLP cost](https://vakilsearch.com/article/llp-registration-cost/) |
| Sole Proprietorship (alternative) | ₹0 – ₹2,000 | Shop & Establishment fee varies by state |
| GST registration (service charge) | ₹2,500 – ₹5,000 | Government portal is free; this is CA / vendor fee, estimated |
| Bank Current Account opening | ₹0 | Most banks free; minimum balance ₹10K–₹25K |
| Privacy Policy (TermsFeed free + add-ons) | ₹0 – ₹6,500 | [TermsFeed](https://www.termsfeed.com/blog/best-privacy-policy-generators/); add-ons $10–$80 each |
| ToS + Refund Policy (TermsFeed) | ₹0 – ₹4,000 | Same as above |
| Lawyer review of legal docs | ₹5,000 – ₹15,000 | Estimated, verify with local lawyer |
| Stamp papers, notary, misc | ₹1,000 – ₹3,000 | Estimated, varies by state |
| **One-time total (OPC path)** | **₹16,500 – ₹51,500** | Realistic mid-point: ₹25K–₹30K |
| **One-time total (Sole Prop path)** | **₹2,500 – ₹15,500** | Realistic mid-point: ₹8K–₹10K |

### Recurring Annual Costs (Estimated)

| Item | Annual Cost | Note |
|---|---|---|
| ROC filings (OPC) — AOC-4, MGT-7, DIR-3 KYC | ₹3,000 – ₹8,000 | Via CA; estimated, verify |
| Statutory audit (OPC mandatory) | ₹8,000 – ₹20,000 | Mandatory regardless of turnover |
| LLP annual filings (Form 8 + 11) | ₹2,000 – ₹5,000 | Audit only > ₹40L turnover |
| GST monthly returns (GSTR-1 + 3B) | ₹18,000 – ₹36,000 (₹1.5K–₹3K × 12) | Via CA; estimated |
| GST annual return (GSTR-9) | ₹3,000 – ₹10,000 | If turnover > ₹2 Cr; estimated |
| Income tax filing | ₹3,000 – ₹8,000 | Estimated |
| **Annual recurring (OPC)** | **~₹35,000 – ₹82,000** | Realistic: ₹50K |
| **Annual recurring (Sole Prop)** | **~₹21,000 – ₹54,000** | Realistic: ₹30K |

Note: Sole Proprietorship saves ~₹20K/year in compliance vs OPC, at the cost of unlimited personal liability.

---

## Section 10: Decisions Founder Needs to Make

These are explicit decisions only the founder can make. Tick the chosen option.

1. **Legal entity for MeeSell V1**
   - [ ] Sole Proprietorship (cheapest, personal liability)
   - [ ] OPC (recommended — limited liability, solo)
   - [ ] LLP (limited liability, requires nominee partner)
   - [ ] Pvt Ltd (only if planning VC within 12 months)

2. **Who incorporates the entity**
   - [ ] Vakilsearch (online package)
   - [ ] IndiaFilings (online package)
   - [ ] Local CA in [city of incorporation] (relationship-based, often cheaper)

3. **GST registration timing**
   - [ ] Register immediately in Week 1 (recommended for B2B credibility)
   - [ ] Wait until first paying customer
   - [ ] Wait until ₹20L turnover (risky if interpreted as inter-state supply)

4. **Privacy Policy source**
   - [ ] TermsFeed free template + manual customisation (cheapest)
   - [ ] iubenda subscription (~₹10K/year, professional)
   - [ ] Custom lawyer draft (₹5K–₹15K, estimated)

5. **Refund policy for monthly Pro and LTD**
   - [ ] No refunds, all sales final
   - [ ] 7-day refund on first purchase, pro-rated cancellation thereafter
   - [ ] 7-day refund for LTD only; no refunds for monthly
   - [ ] 30-day refund (generous; aids early conversion)

6. **Grievance Officer**
   - [ ] Founder personally (recommended for V1 — fastest response)
   - [ ] Designated email alias (grievance@meesell.in) routing to founder
   - [ ] External CS hire (only after revenue justifies)

7. **Pricing display**
   - [ ] Inclusive of GST ("₹499/mo incl. GST") — industry norm
   - [ ] Exclusive of GST ("₹499 + 18% GST")

8. **Legal business name** (must match exactly across PAN, GST, bank, Razorpay)
   - [ ] _____________________________________

---

## Section 11: Founder Skip-Ahead — V1 Minimum Compliance to Launch Next Week

If the founder needs to ship V1 with absolute minimum legal overhead:

1. **Stay Sole Proprietorship** for the first 3–6 months.
   - Cost: ₹0 – ₹2,000 (Shop & Establishment if your state requires it)
   - Risk accepted: unlimited personal liability while validating product-market fit.

2. **GST registration immediately** via Vakilsearch / local CA.
   - Cost: ₹2,500 – ₹5,000 estimated, verify
   - Timeline: 7–10 working days
   - Required for Razorpay B2B credibility and proper invoicing.

3. **TermsFeed free templates** for Privacy Policy + ToS + Refund.
   - Cost: ₹0
   - Add DPDP Grievance Officer block manually (your email + 7-day SLA).

4. **Razorpay onboarding** in parallel.
   - Cost: ₹0 onboarding (2% + GST transaction fees)
   - Timeline: 1–3 working days after documents submitted.

5. **Convert to OPC** after ~100 paying customers (revenue ~₹50K/month) when the ~₹50K/year incremental compliance cost is comfortably affordable and the unlimited liability risk grows uncomfortable.

**Estimated V1 launch cost (Sole Prop path):** ₹2,500 – ₹7,000 total. Estimated, verify with CA.

---

## Section 12: Risks & Caveats

- **Unlimited personal liability under Sole Proprietorship** is real: a data breach lawsuit can target personal assets. The DPDP Act enables individual data subjects to file complaints with the Data Protection Board, and penalties for serious violations can reach ₹250 crore — though small operators with good-faith compliance are not the primary target.
- **Wrong SAC code** on invoices can trigger GST notices. Confirm with a CA before issuing the first invoice.
- **Name mismatch across PAN, GST, bank, Razorpay** is the #1 cause of Razorpay rejection. Decide the legal name once, use identically everywhere.
- **TermsFeed templates are US-centric.** Manual DPDP Act addendum is required — do not rely on auto-generated text for India-specific obligations.
- **Quoted prices change.** All rupee figures here are point-in-time estimates from public sources as of June 2026. Always confirm current price with the vendor or your CA before paying.
- **This document is informational, not legal advice.** Engage a qualified Indian company-secretary or CA before incorporation and a lawyer before publishing legal documents.

---

## Section 13: Sources

- [Vakilsearch — OPC Registration](https://vakilsearch.com/one-person-company-registration)
- [Pricivo — OPC Registration Costs Comparison June 2026](https://www.pricivo.xyz/one-person-company-opc-registration-costs-india/)
- [IndiaFilings — One Person Company](https://www.indiafilings.com/one-person-company)
- [Vakilsearch — LLP Registration Cost 2026](https://vakilsearch.com/article/llp-registration-cost/)
- [RegisterKaro — LLP Registration Fees 2026](https://www.registerkaro.in/post/llp-registration-fee)
- [RegisterKaro — Company Registration Cost Guide 2026](https://www.registerkaro.in/post/cost-of-company-registration-in-india-a-complete-breakdown)
- [RestTheCase — OPC Turnover Limit Latest Rules 2026](https://restthecase.com/knowledge-bank/business-and-compliance/turnover-limit-for-one-person-company-in-india)
- [Razorpay Rize — OPC Turnover Threshold & Conversion Rules](https://razorpay.com/rize/blogs/opc-turnover-threshold-conversion-rules)
- [RegisterKaro — GST Registration for Software & IT Services 2026](https://www.registerkaro.in/post/gst-registration-for-software-it-services)
- [Ampuesto — GST on SaaS & Digital Services in India](https://ampuesto.in/blog/gst-on-saas-digital-services-india/)
- [Taxwink — Inter-State Supply of Services](https://www.taxwink.com/blog/gst-on-inter-state-supply-of-services)
- [IndiaFilings — Compulsory Registration Under GST](https://www.indiafilings.com/learn/compulsory-registration-under-gst)
- [KSandK — Grievance Officers Under DPDP Act & 2025 Rules](https://ksandk.com/data-protection-and-data-privacy/grievance-officers-under-indias-dpdp-act-and-2025-rules/)
- [KSandK — Grievance Redressal Under DPDP Act 2023](https://ksandk.com/data-protection-and-data-privacy/grievance-redressal-under-the-dpdp-act-2023/)
- [Corridalegal — DPDP Act Compliance Essential Steps](https://corridalegal.com/dpdp-act-compliance-essential-steps-for-businesses/)
- [Complydog — India DPDP Act SaaS Compliance Guide](https://complydog.com/blog/india-dpdp-act-data-protection-privacy-compliance-saas)
- [Razorpay — KYC Documents for Business Types](https://razorpay.com/docs/payments/business-types-kyc-documents/)
- [Razorpay — Payment Gateway KYC Onboarding Guide 2026](https://razorpay.com/blog/payment-gateway-kyc-onboarding-india/)
- [TermsFeed — Best Privacy Policy Generators](https://www.termsfeed.com/blog/best-privacy-policy-generators/)
- [iubenda — Best Privacy Policy Generators 2026](https://www.iubenda.com/en/blog/best-privacy-policy-generators/)
