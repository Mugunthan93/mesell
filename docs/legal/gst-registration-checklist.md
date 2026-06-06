# GST Registration Checklist

**Operator:** **Stellaxis** `[ENTITY SUFFIX]` operating the **MeeSell** service
**Purpose:** Single checklist for registering Stellaxis under the Indian Goods and Services Tax regime. **Forks by entity path** — both Sole Prop and OPC/Pvt Ltd variants below.
**Status:** DRAFT — founder runbook; CA review recommended on the SAC code line item
**Drafted by:** `meesell-legal-writer` 2026-06-05
**Source:** `docs/LEGAL_ARCHITECTURE.md` §3 row 4 + §12.3; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §2 + §7; `docs/PRICING_LOCKED.md` §5

> **When to register (founder-ratified per §15 decision #3):** Week 1, immediately upon Stellaxis incorporation — registering before crossing the ₹20 lakh threshold (LACI §2.1) is a credibility multiplier for Razorpay KYC and lets MeeSell issue GST-compliant invoices from day one for B2B input-credit recovery.

---

## 0. Prerequisites

- [ ] Stellaxis is **legally incorporated** with PAN in entity name issued
- [ ] **Business address** is firm (rent agreement signed if leased, or property document in hand if owned)
- [ ] **Founder's Aadhaar** is current and linked to mobile (for OTP-based portal verification)
- [ ] **Business email** `support@meesell.in` is operational (used as the GST account email)

---

## 1. Choose your path

| Path | Stellaxis form | Documents below | When to use |
|---|---|---|---|
| **A — Sole Proprietorship** | `[ENTITY SUFFIX]` is empty | §2 | Founder ruling per LACI §11 — recommended for V1; upgrade at Month 3 |
| **B — OPC / Private Limited / LLP** | `[ENTITY SUFFIX]` is `(OPC) Private Limited`, `Private Limited`, or `LLP` | §3 | When Stellaxis is incorporated as a registered company / LLP |

---

## 2. Documents — PATH A: Sole Proprietorship

### 2.1 Required documents (PDF, < 5 MB each, clearly legible)

| # | Document | Source | Notes |
|---|---|---|---|
| 1 | **Founder's PAN card** | Income Tax Department | Serves as business PAN |
| 2 | **Founder's Aadhaar** (both sides) | UIDAI | Required for portal OTP verification |
| 3 | **Business address proof** | See §2.2 below | Picks ONE |
| 4 | **Bank details** — cancelled cheque OR first page of passbook OR bank statement | Bank | Must show Stellaxis legal name |
| 5 | **Founder's photograph** | — | Passport size, JPEG / PNG |
| 6 | **Founder's signature** on white paper (scanned) | — | Used for digital signature step |
| 7 | **Shop & Establishment certificate** | State labour department | State-dependent — Tamil Nadu, Maharashtra, Delhi require; some states optional |

### 2.2 Business address proof — pick one

- [ ] **Rent agreement** (current, registered if > 11 months) + **electricity bill** (last 3 months) — leased premises
- [ ] **Property tax receipt** OR **municipal tax bill** — owned by founder
- [ ] **Sale deed** OR **property document** — owned by founder

---

## 3. Documents — PATH B: OPC / Private Limited / LLP

### 3.1 Required documents

| # | Document | Source |
|---|---|---|
| 1 | **Company PAN** | Income Tax Department, issued at incorporation |
| 2 | **Certificate of Incorporation** | Ministry of Corporate Affairs |
| 3 | **MOA + AOA** (Pvt Ltd / OPC) OR **LLP Agreement** (LLP) | MCA |
| 4 | **Director's PAN + Aadhaar** | Income Tax + UIDAI |
| 5 | **Director's photograph** | — |
| 6 | **Director's signature** scan | — |
| 7 | **Registered office address proof** | Same options as §2.2 |
| 8 | **Bank details** in Stellaxis legal name | Bank |
| 9 | **Board Resolution** authorising the director to file GST application | Stellaxis internal |

---

## 4. Application — choose your route

| Route | Cost | Speed | Best for |
|---|---|---|---|
| **A. Self-file at gst.gov.in** | ₹0 government fee | 7-10 working days | Founders comfortable with the portal |
| **B. Through a CA** | ₹2,500 – 5,000 service fee + ₹0 govt | Same 7-10 working days | First-time GST registration — strongly recommended |
| **C. Through Vakilsearch / IndiaFilings / ClearTax** | ₹2,500 – 5,000 service fee | Same 7-10 working days | If no relationship with a CA yet |

**Founder-ratified per §15 decision #3:** Route B (local CA) — same cost as online vendors, plus ongoing GST return-filing relationship (₹1,500-3,000 / month per LACI §9).

---

## 5. SAC code — the critical line item

> **SAC = Service Accounting Code.** The wrong SAC on an invoice triggers GST notices (LACI §12).

| SAC | Description | Best fit for MeeSell? |
|---|---|---|
| **998314** | IT design and development services | **PRIMARY** — recommended for SaaS subscriptions |
| **998361** | Custom software development services | Alternative if customer-specific work is offered |
| **998313** | IT consulting and support services | Closest fit only if MeeSell offers consulting (not currently) |

**`[CA VERIFY]`** Confirm SAC 998314 with your CA before issuing the first invoice. The CA may suggest a different code based on Stellaxis's specific service mix.

GST rate at SAC 998314: **18%** (CGST 9% + SGST 9% intra-state; IGST 18% inter-state).

---

## 6. Portal application — field-by-field

When self-filing at `https://gst.gov.in` → "Register Now" → "New Registration":

| Section | Field | Value |
|---|---|---|
| Part A — initial | I am a | Taxpayer |
| | State | `[FOUNDER: State of Stellaxis registered office]` |
| | District | `[FOUNDER: District]` |
| | Legal name of business | `Stellaxis [ENTITY SUFFIX]` — **MUST match PAN exactly** |
| | Trade name | "MeeSell" |
| | PAN | Stellaxis's PAN |
| | Email | `support@meesell.in` |
| | Mobile | Founder's mobile (Aadhaar-linked) |
| Part B — verification | Choose Aadhaar authentication | Yes (recommended — faster) |
| | Business constitution | "Proprietorship" (Path A) / "Private Limited Company" / "One Person Company" / "Limited Liability Partnership" (Path B) |
| | Business activities | "Service Provider" — and on the next screen select "Other services not elsewhere classified" → SAC 998314 |
| | Principal place of business | `[FOUNDER: Stellaxis registered business address]` |
| | Bank account | Stellaxis Current Account number + IFSC |
| | Authorised signatory | Founder details + DSC (if Pvt Ltd / OPC) OR EVC via Aadhaar OTP (Sole Prop) |

---

## 7. After GSTIN issuance — immediate actions

When the GSTIN allotment letter arrives (typically email within 7-10 working days):

- [ ] **Save the GSTIN** — format `[2-digit state code][10-digit PAN][1-digit entity code][1-digit check][Z][1-digit blank]`, total 15 chars
- [ ] **Update the legal documents** — replace any remaining GSTIN placeholders in the live Privacy + ToS + Refund + Cookie (none in V1 templates — GSTIN appears only on invoices)
- [ ] **Configure invoice template** (`docs/legal/invoice-template.md`) with the issued GSTIN
- [ ] **Configure Razorpay merchant profile** with the GSTIN — see `razorpay-kyc-checklist.md` §4
- [ ] **Notify the Stellaxis bank** to flag the account as GST-registered (some banks require this for input-credit on operational transactions)
- [ ] **Set up the GST returns calendar** with the CA — see §8 below

---

## 8. Ongoing GST compliance (post-registration)

Per LACI §9 + CGST Act:

| Return | Frequency | Deadline | CA fee (LACI estimate) |
|---|---|---|---|
| **GSTR-1** (outward supplies — invoices issued) | Monthly | 11th of following month | Bundled |
| **GSTR-3B** (summary return) | Monthly | 20th of following month | ₹1,500 – 3,000 / month bundled for GSTR-1 + 3B |
| **GSTR-9** (annual return) | Yearly | 31 December of following year (if turnover > ₹2 Cr) | ₹3,000 – 10,000 |
| **GSTR-9C** (audit reconciliation) | Yearly | Same as 9 (if turnover > ₹5 Cr) | Higher |

V1 Stellaxis at low volume: only GSTR-1 + GSTR-3B monthly. Bundle with CA for ~₹2K/month.

**Quarterly Composition Scheme NOT recommended for MeeSell** — composition scheme blocks B2B input-credit invoicing, which kills B2B credibility. Stick to the regular scheme.

---

## 9. GST inclusive / exclusive display — locked

Per founder ruling §15 decision #7 (RATIFIED): **inclusive of GST in all customer-facing pricing**:

| Tier | Display price | Base | GST 18% | Customer pays |
|---|---|---|---|---|
| Free Forever | ₹0 | ₹0 | ₹0 | ₹0 |
| Pro | "₹499 / month incl. GST" | ₹422.88 | ₹76.12 | ₹499.00 |
| Business | "₹1,999 / month incl. GST" | ₹1,693.22 | ₹305.78 | ₹1,999.00 |
| LTD | "₹4,999 one-time incl. GST" | ₹4,236.44 | ₹762.56 | ₹4,999.00 |

The invoice template (`invoice-template.md`) splits the gross figure into base + CGST + SGST (or IGST) on the invoice line items.

---

## 10. Common rejection causes — pre-empt these

| Rejection cause | How to pre-empt |
|---|---|
| Aadhaar OTP fails (mobile not linked) | Update Aadhaar mobile linking at the nearest enrolment centre BEFORE applying |
| Business address proof not clear | Use a recent (within 3 months) electricity bill — clearest evidence of address |
| Bank account name doesn't match PAN | Open the Current Account in Stellaxis's exact legal name BEFORE applying for GST |
| Wrong business constitution selected | "Service Provider" is the right macro-category; under that, SAC 998314 |
| Multiple addresses in different states | Register the principal place of business in Stellaxis's incorporation state; add other states as "Additional Place of Business" later if needed (V1.5+) |

---

## 11. Document control

| Field | Value |
|---|---|
| Document | GST Registration Checklist v1.0 |
| Operator | Stellaxis `[ENTITY SUFFIX]` |
| Status | DRAFT — operational runbook (CA verifies SAC; no lawyer review required) |
| Drafted by | `meesell-legal-writer` 2026-06-05 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §12.3; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §2 + §7 + §9; `docs/PRICING_LOCKED.md` §5 |
| CA review markers | 1 — search for `[CA VERIFY]` (SAC code confirmation) |
| Founder placeholders | `[ENTITY SUFFIX]`, `[FOUNDER: State / District / address]` |
| Paired docs | `razorpay-kyc-checklist.md` (consumes GSTIN), `invoice-template.md` (consumes GSTIN + SAC) |
