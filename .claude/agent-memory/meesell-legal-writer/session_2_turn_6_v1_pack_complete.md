---
name: session-2-turn-6-v1-pack-complete
description: All 8 V1 legal artifacts + tracker drafted (Privacy, ToS, Refund, Cookie, DPA, Razorpay KYC, GST, Invoice, In-product strings). V1 legal pack complete.
metadata:
  type: project
---

# Session 2 Turn 6 — V1 Legal Pack COMPLETE

**Date:** 2026-06-05
**Founder directive:** "continue" — draft the remaining 5 V1 documents in one pass.

## Why
Architecture had been LOCKED in Turn 5 and the founder ratified all draftable §15 decisions. Only the 5 remaining artifacts stood between the V1 legal pack and lawyer-redline readiness. The founder's "continue" was a green light to ship them all in one turn.

## What landed

5 new artifacts under `docs/legal/`:

| File | Length | Status | Key feature |
|---|---|---|---|
| `dpa-template.md` | ~430 lines | DRAFT TEMPLATE v1 | 14 sections + 5 annexes (Sub-processors, TOMs, Categories of data, Data-subject rights procedure, Breach notification SLA). 6 [LAWYER REVIEW] markers. Pre-staged for the first enterprise customer DPA request. |
| `razorpay-kyc-checklist.md` | ~210 lines | DRAFT runbook v1 | Sole-Prop + OPC paths side-by-side. Includes the LACI §5.2 name-match pre-flight check (#1 KYC rejection cause). Merchant form field-by-field. TEST→LIVE secret rotation procedure cross-linked to IA §4. |
| `gst-registration-checklist.md` | ~190 lines | DRAFT runbook v1 | Dual-path. SAC 998314 ratified. Portal application field-by-field. Inclusive pricing math per tier. Ongoing GSTR-1 + GSTR-3B returns calendar. |
| `invoice-template.md` | ~225 lines | DRAFT spec v1 | CGST Rule 46 field-by-field. Per-tier GST math for intra-state (CGST 9% + SGST 9%) and inter-state (IGST 18%). Two example invoices (Pro intra-state, LTD inter-state). Credit-note flow per CGST Rule 53. Razorpay Invoices product config checklist. |
| `in-product-strings.md` | ~360 lines | DRAFT spec v1 | 10 UI surfaces × 26 single strings + 1 Grievance footer block + 6 transactional email templates. Transloco-keyed under `legal.*` namespace. Hand-off to `meesell-angular-component-builder` (FE) + `meesell-services-builder` (email). |

Plus `placeholders-tracker.md` updated to include all new placeholders + `[LAWYER REVIEW]` + `[CA VERIFY]` markers + final 9-artifact status summary.

## How to apply

The V1 legal pack is **complete in draft**. No further drafting work is queued for `meesell-legal-writer` in this session. The next phase is:

1. **Lawyer redline** of the 5 customer-facing/DPA documents (Privacy, ToS, Refund, Cookie, DPA) — 34 [LAWYER REVIEW] markers form the worklist
2. **CA review** of GST checklist + Invoice template — 3 [CA VERIFY] markers (SAC 998314 confirmation, place-of-supply for B2C, invoice number length cap)
3. **Stellaxis incorporation** (founder + CA / Vakilsearch) — collapses `[ENTITY SUFFIX]`, `[FOUNDER: Name on PAN]`, `[FOUNDER: address]`, `[FOUNDER: City]`, `[FOUNDER: State / District]`, `[FOUNDER: GSTIN]`
4. **Apply redlines + collapse placeholders + publish** per `placeholders-tracker.md` §5 runbook (16 steps)

`meesell-legal-writer` re-enters scope on amendments only:
- Lawyer suggests changes → integrate
- Architecture changes (new sub-processor, new feature, new statute) → cascade through Privacy + ToS + DPA Annex 1
- Stellaxis incorporation changes the legal name → propagate
- Quarterly review (lock at the architecture level)

## Hand-offs fire-able now

| Recipient | Deliverable |
|---|---|
| `meesell-backend-coordinator` | 4 new audit `event_type`s per LEGAL_ARCHITECTURE §10 + In-product strings §2.3: `auth.consent`, `auth.logout`, `user.deletion_request`, `user.data_export_request` |
| `meesell-angular-component-builder` | 26 strings + 1 footer block per In-product strings §12; Transloco namespace `legal.*` |
| `meesell-services-builder` | 6 email templates per In-product strings §11 (payment success Pro/Business, payment success LTD, payment failed, downgrade, plus the standard footer) |

## Quality notes for future amendment turns

- **DPA template** — §11.2 liability cap may be negotiated with each enterprise customer. Default keeps Stellaxis aligned with ToS §11.1. Be ready to bump to 12-month cap on customer request.
- **DPA §5.7 48-hour customer notification** — tighter than the 72-hour DPDP regulator window. Founder may want to relax to 72 hours per LACI norm; flagged for lawyer review.
- **Invoice number format** — `MEE2627/000001` (14 chars) stays under the 16-char CGST cap. If the CA prefers a different format (e.g., FY-prefixed with slashes), update both the template and the Razorpay Invoices config.
- **GST SAC 998314** — strong default for SaaS but the CA may suggest 998361 (custom software development) if Stellaxis offers per-customer customisation. Wait for CA verdict.
- **In-product strings — V1.5 cookie banner** — reserved namespace `legal.cookie_banner.*` so the FE spec can land later without renumbering.

## What did NOT change

- LEGAL_ARCHITECTURE.md — fully LOCKED in Turn 5; no edits in this turn
- §15 ratification — still 13/15 RATIFIED + 2 DEFERRED
- The 4 prior drafts (Privacy, ToS, Refund, Cookie) — content untouched; only tracker references updated

## Links
- See [[session-2-turn-5-architecture-locked]] for the architecture LOCK turn.
- See [[reference-brand-vs-legal-name]] for the Stellaxis/MeeSell split.
- See [[reference-section-15-ratified]] for the founder-decision matrix.
- See `docs/legal/placeholders-tracker.md` for the canonical artifact + placeholder inventory.
