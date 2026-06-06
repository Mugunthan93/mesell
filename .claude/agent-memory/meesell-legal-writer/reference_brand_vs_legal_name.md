---
name: reference-brand-vs-legal-name
description: MeeSell is the product / trade name; Stellaxis is the legal business name. Always use the right one in the right place.
metadata:
  type: reference
---

# Brand vs Legal Name — Quick Lookup

**Ruled by founder 2026-06-05.** This split is non-negotiable: confusing them in a published document = Razorpay KYC rejection + potential trademark dispute.

## The names

- **Product / trade name:** MeeSell
- **Legal business name:** Stellaxis
- **Entity suffix (pending §15.1):** `[ENTITY SUFFIX]` — fills to:
  - `` (empty / blank) if Sole Proprietorship
  - `LLP` if Limited Liability Partnership
  - `(OPC) Private Limited` if One Person Company
  - `Private Limited` if Private Limited Company
- **Domain:** meesell.in (product domain — hosts product + legal docs)
- **Grievance email:** grievance@meesell.in (product domain — routes to founder)

## Where to use which

| Surface | Use this name |
|---|---|
| Page titles, product UI, customer-facing copy, social media | **MeeSell** |
| Marketing copy describing the service | **MeeSell** |
| Privacy Policy operator | **Stellaxis** `[ENTITY SUFFIX]` operating the MeeSell service |
| ToS operator / contracting party | **Stellaxis** `[ENTITY SUFFIX]` |
| Refund Policy issuer | **Stellaxis** `[ENTITY SUFFIX]` |
| DPA contracting party | **Stellaxis** `[ENTITY SUFFIX]` |
| Razorpay merchant name (must match exactly per LACI §5.2) | **Stellaxis** `[ENTITY SUFFIX]` |
| GST registration legal name | **Stellaxis** `[ENTITY SUFFIX]` |
| PAN name | **Stellaxis** `[ENTITY SUFFIX]` |
| Bank account name | **Stellaxis** `[ENTITY SUFFIX]` |
| GST invoice "From" line | **Stellaxis** `[ENTITY SUFFIX]` |
| Email "From" name for transactional email | MeeSell (product brand acceptable for customer recognition; the email body still cites Stellaxis as legal operator) |
| Domain WHOIS registrant | **Stellaxis** `[ENTITY SUFFIX]` |
| GitLab org | `stellaxis` (already established) |
| Internal product folder names | `mesell/` (legacy spelling — does not affect customer surfaces) |

## Drafting pattern (use exactly this)

First mention in any legal document:
> **Stellaxis** `[ENTITY SUFFIX]` (referred to in these terms as **"Stellaxis"**, **"we"**, **"us"**, or **"our"**, and trading under the product brand **"MeeSell"**) operates the MeeSell software-as-a-service platform (the **"Service"**) at `https://www.meesell.in`. "Stellaxis" is our legal business name; "MeeSell" is the trade name under which we offer the Service.

Subsequent mentions: "we", "us", "our", or "MeeSell" — depending on which reads naturally.

## Cross-link
- See [[reference-section-15-ratified]] for the full ratification list.
- See [[session-2-turn-2-locks-and-drafts]] for the day-of context.
