---
name: session-2-turn-2-locks-and-drafts
description: Founder "go with recommendation" 2026-06-05 — locked 5 architecture sections, ratified 11 of 15 §15 decisions, drafted Privacy Policy v1 and Refund Policy 3-variant v1
metadata:
  type: project
---

# Session 2 Turn 2 — Architecture Locks + First Drafts

**Date:** 2026-06-05
**Founder directive:** "go with your recommendation" — proceed with the recommendation issued in Turn 1.

## Why
Turn 1 produced `docs/LEGAL_ARCHITECTURE.md` SKELETON v1 with a clear forward path: lock §3/§4/§7 (+ §9/§14 per the doc's own gating rule), adopt sensible defaults for 7 of the 8 LACI §10 decisions and all 7 new architectural decisions, then begin drafting the highest-priority artifacts. Founder ratified that recommendation in one phrase; this turn executes it.

## What changed
1. **5 sections flipped SKELETON → LOCKED in `docs/LEGAL_ARCHITECTURE.md`:**
   - §3 Regulatory Regime Map
   - §4 Sub-Processor Register
   - §7 Consent + Data-Subject Rights Lifecycle
   - §9 Retention Schedule
   - §14 Document Mapping
2. **§15 updated:** 11 of 15 founder decisions adopted with stated defaults; 4 remain OPEN.
3. **`docs/legal/` directory created** via first writes.
4. **`docs/legal/privacy-policy.md` v1 drafted** — India-DPDP-native, 16 sections, 8 [LAWYER REVIEW] markers, 5 [FOUNDER:] placeholders. NOT TermsFeed per §15.4 ratified decision.
5. **`docs/legal/refund-policy.md` v1 drafted as 3-variant pack** — founder picks one in next turn; recommendation = Variant B (7-day on LTD only).

## How to apply (drafting precedent for future turns)
- **"Go with recommendation" = bulk-ratify everything I explicitly recommended.** For items I deferred to founder, fall back to placeholders.
- **5 critical [LAWYER REVIEW] markers** in Privacy Policy: §3.3 (SPDI claim), §3.4 (sensitive data scope), §6 (cross-border), §7 (data residency assertion), §9 (TLS+token security claims), §11 (breach SLA), §13 (cookies), §15 (jurisdiction). All must clear Indian lawyer redline before publishing.
- **Drafting style locked:** plain Indian English, second-person ("you"), narrative tables for tier/lifetime/sub-processor lists, every clause cited to `LEGAL_ARCHITECTURE` section + `LACI` section in document control footer.

## Ratified §15 defaults (for quick recall)

| # | Decision | Adopted value |
|---|---|---|
| 3 | GST timing | Week 1 |
| 4 | Privacy Policy source | Custom India-DPDP-native + lawyer review (NOT TermsFeed) |
| 6 | Grievance Officer email | grievance@meesell.in routed to founder |
| 7 | GST display | Inclusive ("₹499/mo incl. GST") |
| 9 | Marketing email V1 | No (transactional only) |
| 10 | LangFuse V1 | Disable |
| 11 | product_drafts TTL | 30 days |
| 12 | Cross-border to Gemini | Accept and disclose |
| 13 | Soft-delete grace period | 30 days |
| 14 | Manual erasure SLA | 30 days max, 7-day target |
| 15 | Personal data export SLA | 7 days via Grievance Officer |

## Still OPEN (require explicit founder ruling)

| # | Decision | Blocks |
|---|---|---|
| 1 | Legal entity (Sole Prop / OPC / LLP / Pvt Ltd) | Razorpay KYC checklist + GST checklist |
| 2 | Incorporator (Vakilsearch / IndiaFilings / local CA) | Incorporation paperwork |
| 5 | Refund variant (A / B / C) | Refund Policy final + ToS Refund clause + billing email + cancellation UI |
| 8 | Legal business name | Every legal-doc header + Razorpay name-match |

## Next dispatch chain
After founder responds with refund pick + legal name:
1. Collapse refund-policy.md to picked variant
2. Draft ToS v1 (references picked Refund clause + Privacy Policy)
3. Draft Cookie Policy v1 (short — most surfaces closed by Privacy §13)
4. Draft DPA template v1 (V1.5 enterprise; ships as draft now)
5. After §15.1 entity ruling: KYC checklist + GST checklist Sole-Prop-path variants
6. Draft in-product strings pack → FE component-builder hand-off

## Links
- See [[session-2-legal-architecture]] for the SKELETON v1 architecture.
- See [[reference-surface-to-doc-mapping]] for which artifact closes which surface.
- See [[reference-section-15-ratified]] for the full ratified decision list.
- See [[project-fe-d5-token-model]] for the auth-security wording used in Privacy §9.
