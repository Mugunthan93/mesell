---
name: reference-section-15-ratified
description: Quick lookup — the 11 of 15 LEGAL_ARCHITECTURE §15 decisions ratified 2026-06-05 via founder "go with recommendation" + the 4 still open
metadata:
  type: reference
---

# §15 Decisions — Ratified vs Open (snapshot 2026-06-05)

Source: `docs/LEGAL_ARCHITECTURE.md` §15. Updated when founder rules on any OPEN item.

## Ratified — adopt these in every draft

| # | Topic | Use this value |
|---|---|---|
| 3 | GST registration timing | Register in Week 1 (immediately) |
| 5 | Refund policy variant | Variant B — 7-day money-back on Lifetime Deal only; no refunds on monthly. (Founder ruling 2026-06-05.) |
| 8 | Legal business name | **Stellaxis** is the legal business name. **MeeSell** is the product / trade name. The entity suffix (e.g., "Private Limited", "(OPC) Private Limited", or blank for Sole Prop) collapses once §15.1 is ruled. Use `Stellaxis [ENTITY SUFFIX]` in every draft until then. (Founder ruling 2026-06-05.) |
| 4 | Privacy Policy authoring | Custom India-DPDP-native, drafted in-house, ₹5K-15K lawyer review pre-publish. NOT TermsFeed (US-centric). |
| 6 | Grievance Officer contact | `grievance@meesell.in` routed to founder personally (V1) |
| 7 | GST display in pricing | Inclusive — "₹499/mo incl. GST" everywhere customer-facing |
| 9 | Marketing email in V1 | No — transactional only. No marketing-consent toggle in V1. |
| 10 | LangFuse in V1 | Disabled. Re-add at V1.5 if self-hosted or vendor jurisdiction confirmed. |
| 11 | `product_drafts` TTL | 30 days from last `saved_at`. Celery beat purge per LEGAL_ARCHITECTURE §9. |
| 12 | Cross-border to Gemini | Accept and disclose. Vertex AI India-only deferred V1.5. |
| 13 | Soft-delete grace period | 30 days after `deleted_at` then purge. |
| 14 | Manual erasure SLA | 30 days max, 7-day target. State both in Privacy §10.3. |
| 15 | Personal-data export SLA | 7 days, manual via Grievance Officer. Self-serve endpoint V1.5. |

## Deferred — Stellaxis not yet legally registered (founder ruling 2026-06-05)

Pre-incorporation: use placeholders in drafts. Both items collapse on incorporation.

| # | Topic | Resolution path |
|---|---|---|
| 1 | Legal entity (Sole Prop / OPC / LLP / Pvt Ltd) | Founder picks at incorporation. Draft KYC + GST checklists with both Sole Prop and OPC variants side-by-side. Recommendation per LACI §11: Sole Prop V1, OPC at Month 3. |
| 2 | Incorporator (Vakilsearch / IndiaFilings / local CA) | Founder picks alongside #1. |

## How to use this reference
On every drafting turn:
1. Read this file
2. Use the ratified value verbatim for the 11 closed decisions
3. Stop and ask if a draft requires one of the 4 open decisions to make sense
4. When founder closes an open item, edit this file to move it to the Ratified table
