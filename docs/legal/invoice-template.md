# GST Tax Invoice Template

**Operator:** **Stellaxis** `[ENTITY SUFFIX]` operating the **MeeSell** service
**Purpose:** Single template for the GST-compliant tax invoice issued to every paying customer per **Rule 46 of the CGST Rules 2017**. Razorpay generates these automatically when configured with Stellaxis's GSTIN; this template is the field-by-field spec the Razorpay configuration must match.
**Status:** DRAFT — operational template; CA review required on SAC + place-of-supply rules
**Drafted by:** `meesell-legal-writer` 2026-06-05
**Source:** `docs/LEGAL_ARCHITECTURE.md` §12.4; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §7; `docs/PRICING_LOCKED.md` §5

> **Why this template exists:**
> Razorpay's invoice auto-generation is configurable — but the founder must enter the right values once during Razorpay setup. This template is the canonical source for those values. It also serves as the manual-issuance template if Razorpay's auto-generation is unavailable (e.g., LTD refunds where the original was a one-time payment).

---

## 1. Mandatory invoice fields (CGST Rule 46)

Every invoice MUST include all 16 fields below. Razorpay auto-fills most; the founder configures the static fields once.

| # | Field | Source | Static or per-invoice |
|---|---|---|---|
| 1 | **Supplier name** | "Stellaxis `[ENTITY SUFFIX]`" | Static |
| 2 | **Supplier address** | `[FOUNDER: Stellaxis registered business address]` | Static |
| 3 | **Supplier GSTIN** | `[FOUNDER: Stellaxis GSTIN]` | Static |
| 4 | **Invoice number** | Sequential, financial-year prefixed: `MEE/[YY-YY+1]/[6-digit sequence]` — e.g., `MEE/2026-27/000001`. Reset at financial-year boundary (1 April). | Per-invoice |
| 5 | **Invoice date** | Date of payment confirmation | Per-invoice |
| 6 | **Customer name** | Customer's legal name as provided at sign-up | Per-invoice |
| 7 | **Customer GSTIN** (if B2B) | Customer's GSTIN if provided; blank for B2C | Per-invoice |
| 8 | **Customer address** | Customer's billing address as provided | Per-invoice |
| 9 | **Place of supply** | Customer's state (2-digit GST state code + name) — determines CGST+SGST vs IGST split | Per-invoice |
| 10 | **HSN / SAC code** | `998314` (founder-ratified per `gst-registration-checklist.md` §5) | Static |
| 11 | **Description of service** | "MeeSell SaaS Subscription — Pro Tier" / "MeeSell SaaS Subscription — Business Tier" / "MeeSell Lifetime Deal" | Per-invoice (tier varies) |
| 12 | **Taxable value (base before GST)** | See §3 math | Per-invoice |
| 13 | **GST rate** | `18%` | Static |
| 14 | **CGST + SGST (intra-state) or IGST (inter-state)** | See §3 math | Per-invoice |
| 15 | **Total invoice value** | Gross amount the customer paid | Per-invoice |
| 16 | **Amount in words** | English words (e.g., "Four Hundred Ninety-Nine Rupees Only") | Per-invoice |

Plus:

| Field | Source |
|---|---|
| **Signature / digital signature** | Razorpay digital signature on auto-generated; manual issuance requires founder's scanned signature |
| **Reverse charge applicability** | "Not applicable" — SAC 998314 SaaS is forward-charge |

---

## 2. Place-of-supply rules — intra-state vs inter-state

Per CGST §10 + §12 (services delivered electronically):

| Customer state | Stellaxis state (`[FOUNDER: State]`) | Tax type | Math |
|---|---|---|---|
| Same as Stellaxis | Same | **CGST 9% + SGST 9%** = 18% intra-state | Split on invoice |
| Different from Stellaxis | Different | **IGST 18%** inter-state | Single line on invoice |

`[CA VERIFY]` Customer-without-GSTIN (B2C) is taxed at the place where the customer is *located at the time of supply* — for SaaS, this is the customer's address on file. Configure Razorpay to use the customer's billing-state field for this determination.

---

## 3. GST math — by tier (inclusive pricing per §15.7 ratified)

Display price is **gross (incl. GST)**. The invoice splits the gross into base + GST.

### 3.1 Pro tier — ₹499 / month

| Line | Intra-state | Inter-state |
|---|---|---|
| Base (taxable value) | ₹422.88 | ₹422.88 |
| CGST 9% | ₹38.06 | — |
| SGST 9% | ₹38.06 | — |
| IGST 18% | — | ₹76.12 |
| **Total** | **₹499.00** | **₹499.00** |

### 3.2 Business tier — ₹1,999 / month

| Line | Intra-state | Inter-state |
|---|---|---|
| Base | ₹1,693.22 | ₹1,693.22 |
| CGST 9% | ₹152.89 | — |
| SGST 9% | ₹152.89 | — |
| IGST 18% | — | ₹305.78 |
| **Total** | **₹1,999.00** | **₹1,999.00** |

### 3.3 Lifetime Deal — ₹4,999 one-time

| Line | Intra-state | Inter-state |
|---|---|---|
| Base | ₹4,236.44 | ₹4,236.44 |
| CGST 9% | ₹381.28 | — |
| SGST 9% | ₹381.28 | — |
| IGST 18% | — | ₹762.56 |
| **Total** | **₹4,999.00** | **₹4,999.00** |

Round half-up to 2 decimal places on each line; rounding differences (typically ≤ ₹0.02) are absorbed in the base column. Razorpay's invoice engine handles this correctly when configured for **inclusive pricing**.

---

## 4. Example invoice — Pro tier, intra-state (Tamil Nadu seller)

```
═══════════════════════════════════════════════════════════════════
  STELLAXIS [ENTITY SUFFIX]                          TAX INVOICE
  [FOUNDER: Stellaxis registered business address]
  Tamil Nadu, India - [PIN]
  GSTIN: [FOUNDER: Stellaxis GSTIN]
  Email: support@meesell.in    Web: www.meesell.in
═══════════════════════════════════════════════════════════════════

  Invoice No.:  MEE/2026-27/000001
  Invoice Date: 15 April 2026
  Due Date:     Paid

  Bill To:
    [Customer legal name]
    [Customer billing address]
    Tamil Nadu, India - [Customer PIN]
    GSTIN: [Customer GSTIN, if B2B]

  Place of Supply: 33 - Tamil Nadu  (intra-state)

───────────────────────────────────────────────────────────────────
  Description                           SAC      Qty   Amount (₹)
───────────────────────────────────────────────────────────────────
  MeeSell SaaS Subscription             998314   1     422.88
    Pro Tier - Monthly
    Billing period: 15 Apr - 14 May 2026
───────────────────────────────────────────────────────────────────
  Sub-total (taxable value)                            422.88
  CGST  @  9%                                           38.06
  SGST  @  9%                                           38.06
───────────────────────────────────────────────────────────────────
  Grand Total                                          499.00
═══════════════════════════════════════════════════════════════════

  Amount in words: Four Hundred Ninety-Nine Rupees Only

  Payment received via: Razorpay (txn id rzp_xxxxxxxxxxxxxx)
  Reverse charge: Not applicable

  This is a system-generated invoice issued under
  Rule 46 of the CGST Rules 2017.
  Digital signature: [Razorpay-generated]

═══════════════════════════════════════════════════════════════════
```

---

## 5. Example invoice — LTD, inter-state (Maharashtra seller)

```
═══════════════════════════════════════════════════════════════════
  STELLAXIS [ENTITY SUFFIX]                          TAX INVOICE
  [Same supplier block as §4]
═══════════════════════════════════════════════════════════════════

  Invoice No.:  MEE/2026-27/000042
  Invoice Date: 20 May 2026
  Due Date:     Paid

  Bill To:
    [Customer legal name]
    [Customer billing address]
    Maharashtra, India - [Customer PIN]
    GSTIN: [Customer GSTIN]

  Place of Supply: 27 - Maharashtra  (inter-state)

───────────────────────────────────────────────────────────────────
  Description                           SAC      Qty   Amount (₹)
───────────────────────────────────────────────────────────────────
  MeeSell Lifetime Deal                 998314   1     4,236.44
    One-time purchase; permanent Pro
    tier access; LTD spot #042/1000
───────────────────────────────────────────────────────────────────
  Sub-total (taxable value)                            4,236.44
  IGST  @ 18%                                            762.56
───────────────────────────────────────────────────────────────────
  Grand Total                                          4,999.00
═══════════════════════════════════════════════════════════════════

  Amount in words: Four Thousand Nine Hundred Ninety-Nine Rupees Only

  Payment received via: Razorpay
  Reverse charge: Not applicable

═══════════════════════════════════════════════════════════════════
```

---

## 6. Refund / credit-note flow — CGST Rule 53

When a refund is issued (per `refund-policy.md` — Variant B, 7-day LTD window):

1. Issue a **credit note** with sequential numbering `MEE-CN/[YY-YY+1]/[6-digit sequence]`
2. Reference the original invoice number on the credit note
3. Reverse the exact CGST/SGST or IGST split from the original
4. Razorpay handles the reverse fund transfer to the original payment method (Razorpay 7-10 business days)
5. The credit note line in GSTR-1 must be filed in the same month the refund is issued

### Example credit-note math (refund of the LTD in §5):

| Line | Amount |
|---|---|
| Base (taxable value reversed) | -₹4,236.44 |
| IGST 18% (reversed) | -₹762.56 |
| **Credit total** | **-₹4,999.00** |

---

## 7. Sequential numbering rules

Per CGST Rule 46 (b): invoice numbers must be **consecutive** within a financial year. Specific rules:

- **Format:** `MEE/[YY-YY+1]/[6-digit sequence]` — e.g., `MEE/2026-27/000001`
- **Length cap:** 16 characters maximum per CGST Rule 46 — `MEE/2026-27/000001` = 18 chars; **shorten to `MEE2627/000001` = 14 chars** to stay under the cap. **`[CA VERIFY]`** This abbreviation is widely used but confirm with your CA before issuing the first invoice.
- **No gaps:** if invoice 000005 is voided, the system records 000005 as voided and proceeds to 000006 — no re-use of numbers
- **Reset at financial-year boundary:** 1 April starts the new series at 000001
- **Credit notes:** separate series `MEE-CN/2627/000001`

Razorpay Invoices product handles this correctly when configured with the prefix and start number.

---

## 8. Configuration checklist (Razorpay Invoices)

On the Razorpay dashboard → Invoices → Settings:

- [ ] Prefix: `MEE/2627/` (or `MEE2627/` if Razorpay rejects the slash)
- [ ] Starting number: `000001`
- [ ] Company name: `Stellaxis [ENTITY SUFFIX]`
- [ ] Company address: `[FOUNDER: Stellaxis registered business address]`
- [ ] Company GSTIN: `[FOUNDER: Stellaxis GSTIN]`
- [ ] Default SAC: `998314`
- [ ] Default tax rate: `18%`
- [ ] GST behavior: **inclusive**
- [ ] Logo upload: MeeSell logo (per FE design system)
- [ ] Terms on invoice footer: "Powered by Razorpay. Reverse charge not applicable. Issued under CGST Rule 46."

---

## 9. Document control

| Field | Value |
|---|---|
| Document | GST Tax Invoice Template v1.0 |
| Operator | Stellaxis `[ENTITY SUFFIX]` |
| Status | DRAFT — operational template; CA verifies SAC + numbering format |
| Drafted by | `meesell-legal-writer` 2026-06-05 |
| Source citations | `docs/LEGAL_ARCHITECTURE.md` §12.4; `docs/LEGAL_AND_COMPLIANCE_INFO.md` §7; `docs/PRICING_LOCKED.md` §5; CGST Rule 46 + Rule 53 |
| CA review markers | 2 — search for `[CA VERIFY]` (place of supply for B2C; invoice number length cap) |
| Founder placeholders | `[ENTITY SUFFIX]`, `[FOUNDER: GSTIN]`, `[FOUNDER: address]`, `[FOUNDER: State]` |
| Paired docs | `gst-registration-checklist.md` (issues the GSTIN consumed here), `razorpay-kyc-checklist.md` (configures Razorpay before this template can be used) |
