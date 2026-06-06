# STATUS — LEGAL / MARKETING

**Owner:** LEGAL sub-session (`meesell-legal-writer`)
**Last update:** 2026-06-05

**Status:** Session 2 complete. **LEGAL_ARCHITECTURE.md fully LOCKED** (all 17 sections). §15 closed at 13/15 RATIFIED + 2 DEFERRED until Stellaxis incorporation. **V1 LEGAL PACK COMPLETE: all 8 artifacts + tracker drafted** (Privacy, ToS, Refund, Cookie, DPA template, Razorpay KYC, GST registration, Invoice template, In-product strings). 34 [LAWYER REVIEW] markers across the customer-facing/DPA docs flag the redline worklist. Pre-incorporation posture: lawyer redline → placeholder collapse → publish in one pass on Stellaxis registration.

## Current Phase
Architecture LOCKED. V1 legal pack DRAFTED in full (8 artifacts + tracker). Ready for Indian lawyer redline + (parallel) Stellaxis incorporation. Publishing waits on both.

## Done
- Session 1: Context loaded.
- Session 2 turn 1: Authored `docs/LEGAL_ARCHITECTURE.md` SKELETON v1 (16 sections).
- Session 2 turn 2 (this turn):
  - Flipped §3 (regime map), §4 (sub-processors), §7 (rights lifecycle), §9 (retention), §14 (doc mapping) from SKELETON → LOCKED
  - Ratified 11 of 15 §15 founder decisions (defaults adopted): #3, #4, #6, #7, #9, #10, #11, #12, #13, #14, #15
  - 4 §15 decisions remain OPEN: #1 entity, #2 incorporator, #5 refund variant, #8 legal business name
  - Drafted `docs/legal/privacy-policy.md` v1 — India-DPDP-native, 16 sections, 8 [LAWYER REVIEW] markers, 5 [FOUNDER:] placeholders
  - Drafted `docs/legal/refund-policy.md` v1 — 3 variants side-by-side, decision template included
  - Created `docs/legal/` directory (first writes)

## In Progress
- Awaiting founder:
  - Refund variant pick (A / B / C — recommendation B)
  - Legal business name confirmation (blocks publishing of all 8 docs)
- After founder responds, the 3-variant refund-policy.md collapses to single-variant LOCKED.

## Blockers (publishing only, not drafting)
- **PUBLISHING:** Stellaxis incorporation pending (§15.1 + §15.2 deferred per founder ruling 2026-06-05). Placeholders inventoried in `placeholders-tracker.md`.
- **OPERATIONAL:** 4 new audit `event_type`s — hand-off to `meesell-backend-coordinator` queued.

## Next (out of legal-writer's scope — these are founder actions, no committed timeline)
1. **Indian lawyer redline pass** on the 5 customer-facing/DPA drafts — **deferred to a later date** per founder ruling 2026-06-06. 34 [LAWYER REVIEW] markers form the worklist when review happens. Drafts are not marked as "no-review baseline" — review is a pending step, not a waived one.
2. **CA review** on 3 [CA VERIFY] markers in GST checklist + Invoice template — **deferred to the same later date** (typically alongside CA engagement for monthly GSTR-1/3B returns, which is non-deferrable once GST registered).
3. **Decide §15.1 entity path** (Sole Prop / OPC / LLP / Pvt Ltd).
4. **Incorporate Stellaxis** in chosen form; obtain PAN + GST + Current Account.
5. **Apply lawyer redlines + CA suggestions** to the drafts (when review happens).
6. **Resolve placeholders** per `placeholders-tracker.md` §5 runbook (16 steps).
7. **Publish** the 4 customer-facing docs at `meesell.in/legal/...` and complete Razorpay KYC.

## Hand-offs (queued, can fire in parallel)
- `meesell-backend-coordinator`: 4 new audit `event_type`s (`auth.consent`, `auth.logout`, `user.deletion_request`, `user.data_export_request`) per LEGAL_ARCHITECTURE §10 + In-product strings §2.3
- `meesell-angular-component-builder`: 26 single strings + 1 footer block + 1 reserved namespace per In-product strings §12
- `meesell-services-builder`: 6 transactional email templates per In-product strings §11
4. Draft `docs/legal/cookie-policy.md` v1 — short, mostly closed by Privacy §13
5. Draft `docs/legal/dpa-template.md` v1 — V1.5 enterprise template; can ship as draft now
6. Draft `docs/legal/razorpay-kyc-checklist.md` Sole-Prop-path variant (assumes §15.1 = Sole Prop interim)
7. Draft `docs/legal/gst-registration-checklist.md` Sole-Prop-path variant
8. Draft `docs/legal/invoice-template.md` — needs §15.1 + §15.7 + §15.8 all locked
9. Draft `docs/legal/in-product-strings.md` — FE hand-off pack (consent UI, Grievance footer, cancellation copy)

## Hand-offs (queued, fire after this session's docs are reviewed)
- `meesell-backend-coordinator`: 4 new audit `event_type`s (`auth.consent`, `auth.logout`, `user.deletion_request`, `user.data_export_request`) to extend BEA §4.G audit catalogue
- `meesell-backend-coordinator`: erasure workflow endpoint (Privacy §10.3 manual procedure; V1.5 → endpoint per LEGAL_ARCHITECTURE §16)
- `meesell-backend-coordinator`: data-export workflow endpoint (Privacy §10.7 manual procedure; V1.5 → endpoint)
- `meesell-services-builder`: Celery beat purge tasks per LEGAL_ARCHITECTURE §9 retention schedule (product_drafts 30d, soft-delete grace 30d, audit archive 90d→1y)
- `meesell-angular-component-builder`: in-product strings pack (consent UI, Grievance footer, cancellation copy) — pending §15.5 + in-product-strings.md draft
- `meesell-angular-component-builder`: footer Grievance Officer block on every page per Privacy §12

## Updates Log

=== UPDATE: 2026-06-04 00:00 ===
File initialised by master session. Awaiting first LEGAL sub-session.
=========

=== UPDATE: 2026-06-04 SESSION-1-START ===
Task: Read all project context files and await founder task.
Status: Context loaded. Zero legal documents exist. docs/legal/ not yet created.
=========

=== UPDATE: 2026-06-05 SESSION-2-START ===
Task: Compose legal architecture peer to FE/BE/DB/Infra architecture docs; analyse legal-handling surfaces.
Done: Read 4 architecture docs; authored `docs/LEGAL_ARCHITECTURE.md` SKELETON v1 (16 sections).
=========

=== UPDATE: 2026-06-05 SESSION-2 TURN 2 ===
Task: Founder ratified "go with recommendation" — lock sections + adopt defaults + begin drafting.
Done:
  - Architecture: §3 + §4 + §7 + §9 + §14 LOCKED; §15 ratified 11/15 (4 open: #1 entity, #2 incorporator, #5 refund variant, #8 legal business name)
  - Drafted Privacy Policy v1 (16 sections, India-DPDP-native, custom — NOT TermsFeed per §15.4 ruling)
  - Drafted Refund Policy v1 3-variant pack — founder picks one (recommendation: Variant B = 7-day on LTD only)
=========

=== UPDATE: 2026-06-05 SESSION-2 TURN 3 ===
Task: Founder ruling on §15.5 refund variant.
Founder input: "2" → interpreted as Variant B.
Done: §15.5 RATIFIED — Variant B. Refund Policy collapsed to single-variant final.
=========

=== UPDATE: 2026-06-05 SESSION-2 TURN 4 ===
Task: §15.8 ruling.
Done: §15.8 RATIFIED (Stellaxis legal / MeeSell product); brand-vs-legal split codified; Privacy + Refund placeholders patched; ToS v1 + Cookie Policy v1 drafted.
=========

=== UPDATE: 2026-06-05 SESSION-2 TURN 5 ===
Task: Architecture LOCK + placeholders tracker.
Done: All 17 sections of LEGAL_ARCHITECTURE LOCKED; placeholders-tracker.md created; §15 closed 13/15+2-deferred.
=========

=== UPDATE: 2026-06-06 SESSION-2 TURN 7 ===
Task: Founder clarification — lawyer + CA review is deferred to a later date, not skipped. Don't mark drafts with a posture flag. Founder's question was for understanding the trade-off, not deciding to skip.
Done:
  - STATUS_LEGAL "Next" section reworded: review is "pending, not waived"; no committed timeline
  - No document-control footers modified — drafts remain at standard v1 DRAFT status
  - Memory updated with founder's clarification for future-agent recall
Blockers: Unchanged. Stellaxis incorporation still blocks publishing.
Next: Founder-driven. No legal-writer action queued.
=========

=== UPDATE: 2026-06-05 SESSION-2 TURN 6 ===
Task: Draft remaining 5 V1 legal artifacts per founder "continue".
Done:
  - `docs/legal/dpa-template.md` v1 — 14 sections + 5 annexes; 6 [LAWYER REVIEW] markers; pre-staged for first enterprise customer
  - `docs/legal/razorpay-kyc-checklist.md` v1 — Sole-Prop path + OPC path side-by-side; merchant form field-by-field; webhook config; TEST→LIVE rotation procedure
  - `docs/legal/gst-registration-checklist.md` v1 — dual-path; SAC 998314 ratified; portal field-by-field; ongoing returns calendar; pricing inclusive math
  - `docs/legal/invoice-template.md` v1 — CGST Rule 46 field-by-field; per-tier GST math (intra + inter-state); 2 example invoices; credit-note flow; Razorpay config checklist
  - `docs/legal/in-product-strings.md` v1 — 10 surfaces × 26 strings + 1 footer + 6 email templates; Transloco-keyed; FE specialist hand-off
  - `placeholders-tracker.md` updated: 9 artifacts inventoried; 34 [LAWYER REVIEW] + 3 [CA VERIFY] markers catalogued; final document list with status
In progress: NOTHING. V1 legal pack drafting COMPLETE.
Blockers: NONE on drafting. Only Stellaxis incorporation + lawyer redline block publishing.
Next: All next actions are founder/lawyer/CA scope. legal-writer is now in standby for amendments only.
Hand-offs (now actionable):
  - meesell-backend-coordinator: 4 new audit event_types
  - meesell-angular-component-builder: 26 single strings + 1 footer + 1 reserved namespace
  - meesell-services-builder: 6 transactional email templates
Founder action required:
  1. Review the 5 new drafts (60-90 min)
  2. Send 5 customer-facing/DPA docs to Indian lawyer (₹5K-15K)
  3. Send GST checklist + Invoice template to CA for SAC + numbering confirmation
  4. (Parallel) Decide §15.1 entity + start Stellaxis incorporation
=========
