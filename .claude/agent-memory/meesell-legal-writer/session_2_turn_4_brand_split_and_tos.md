---
name: session-2-turn-4-brand-split-and-tos
description: Founder ratified §15.8 with the brand-vs-legal split (Stellaxis legal, MeeSell product). Drafted ToS v1 and Cookie Policy v1; patched existing Privacy + Refund placeholders.
metadata:
  type: project
---

# Session 2 Turn 4 — Brand-vs-Legal Split + ToS + Cookie Policy

**Date:** 2026-06-05
**Founder directive:** "MeeSell is the product name only. Business name is different. 'Stellaxis' this is the business name."

## Why
§15.8 was the last hard publish-blocker. Founder's response settled it AND introduced a useful structural distinction: legal documents say "Stellaxis", product surfaces say "MeeSell". This split is non-negotiable and is now codified in `reference_brand_vs_legal_name.md`.

## How to apply
- Every NEW legal document opens with the §1 pattern: "**Stellaxis** `[ENTITY SUFFIX]` (referred to as ... and trading under the product brand "**MeeSell**") operates the MeeSell Service at https://www.meesell.in".
- Razorpay merchant name, PAN, GST, bank account = **Stellaxis** + entity suffix. Anything that deviates from this triggers LACI §5.2 name-match KYC rejection.
- Email "From" header on transactional email may say "MeeSell" for customer recognition; the email body still names Stellaxis as the legal operator.
- All Stellaxis-related operational artifacts (Razorpay onboarding, GST registration, bank account, domain WHOIS) freeze once §15.1 entity ruling lands. **No rename after that point is cheap.**

## What was produced this turn
1. **Privacy Policy v1 patched** — `[FOUNDER: Legal Business Name]` → "Stellaxis [ENTITY SUFFIX]"; domain frozen to meesell.in; 3 founder placeholders remain (name, address, city of registered office).
2. **Refund Policy v1 patched** — same.
3. **`docs/legal/terms-of-service.md` v1 drafted** — 18 sections, 17 [LAWYER REVIEW] markers.
   - Highest-liability document in the legal pack.
   - Sections covering acceptable use, seller representations (statutory accuracy = seller's risk), IP (your content vs AI suggestions vs MeeSell catalog dataset), takedown procedure (IT Act §79), limitation of liability (3-month-fees cap or ₹10K min), indemnity, governing law (jurisdiction = `[FOUNDER: city]`).
   - Class-action waiver flagged for special lawyer attention (enforceability under Indian law is contested).
4. **`docs/legal/cookie-policy.md` v1 drafted** — short, ~110 lines.
   - Only one cookie + one cache item. No analytics, no advertising, no third-party tracking in V1.
   - Strictly-necessary classification means no banner needed in V1.
   - Forward-compatible: if non-essential cookies are added in V1.5, the policy commits to a consent banner at that point.

## Outstanding placeholders (3) — needed before lawyer review
- `[FOUNDER: Name on PAN]` — appears in Privacy §12, Refund §6, ToS §15 + §18, Cookie §7
- `[FOUNDER: Stellaxis registered business address]` — appears in Privacy §12 + §16, Refund §6, ToS §15 + §18, Cookie §7
- `[FOUNDER: City of Stellaxis registered office]` — appears in Privacy §15, Refund §10, ToS §16.2 — drives the exclusive-jurisdiction clause
- `[ENTITY SUFFIX]` — appears 14+ times across the 4 documents; resolved by §15.1 ruling (Sole Prop = blank; OPC = "(OPC) Private Limited"; etc.)
- `[FOUNDER: publish date]` — appears twice per doc (effective + last-updated). Set on the day of publication.

## Next turns
- **Turn 5 (queued):** DPA template v1 + Razorpay KYC checklist (Sole-Prop variant + OPC variant) + GST registration checklist + invoice template v1.
- **Turn 6 (queued):** In-product strings pack (consent UI, Grievance footer, cancellation copy) → hand-off to `meesell-angular-component-builder`.

## Links
- See [[reference-brand-vs-legal-name]] for the definitive lookup.
- See [[reference-section-15-ratified]] for the full ratification list (13/15).
- See [[session-2-turn-2-locks-and-drafts]] for prior turn context.
