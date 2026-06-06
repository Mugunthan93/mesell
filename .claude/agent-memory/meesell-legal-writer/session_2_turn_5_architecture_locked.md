---
name: session-2-turn-5-architecture-locked
description: Founder deferred entity registration; legal architecture locked across all 17 sections; placeholders tracker created as the pre-incorporation pause-point reference
metadata:
  type: project
---

# Session 2 Turn 5 — Architecture Fully LOCKED + Placeholders Tracker

**Date:** 2026-06-05
**Founder directive:** "actually we didn't legally registered the company so better use the placeholder in all place and mark it in the separate document to track the unfinished details related to it and we will complete the legal architecture first"

## Why
Two strategic decisions in one sentence:
1. Stellaxis incorporation is **deferred** — we draft with placeholders, do not guess.
2. **Architecture first, artifacts second.** The 11 SKELETON sections of `LEGAL_ARCHITECTURE.md` get LOCKED before more artifact drafting, so that the next 4 artifacts (DPA, KYC, GST, invoice, in-product strings) are authored against a stable contract.

This is sound legal-doc hygiene. Pre-incorporation drafts with placeholders are safer than rushing to incorporate and bake decisions in.

## What changed

### 1. `docs/legal/placeholders-tracker.md` created
Single source of truth for:
- §1 Placeholder taxonomy (5 tag types: `[ENTITY SUFFIX]`, `[FOUNDER: Name on PAN]`, `[FOUNDER: Stellaxis registered business address]`, `[FOUNDER: City of Stellaxis registered office]`, `[FOUNDER: publish date]`)
- §2 Per-file location map (audit-grade — regenerated whenever any draft is edited)
- §3 The 28 [LAWYER REVIEW] markers across the 4 drafts (Privacy 8, ToS 17, Refund 2, Cookie 1)
- §4 Two outstanding §15 founder decisions (both DEFERRED — entity + incorporator)
- §5 Stellaxis incorporation runbook (16 steps from incorporation to legal pack going live)
- §6 Cross-document consistency invariants
- §7 The 4 documents queued for next-turn drafting
- §8 Update protocol (legal-writer owns this file)

### 2. `LEGAL_ARCHITECTURE.md` fully LOCKED
All 17 sections (§0 through §16) now carry `STATUS: LOCKED (2026-06-05)`:
- §3, §4, §7, §9, §14 — already LOCKED before this turn
- §0, §1, §2, §5, §6, §8, §10, §11, §12, §13, §16 — flipped this turn
- §15 — flipped this turn at 13 RATIFIED + 2 DEFERRED

### 3. §6 polished
Added the "V1.5 RLS as roadmap representation, not binding warranty" clarification — protects founder if RLS slips on the V1.5 schedule. Also added the three-layer defence-in-depth narrative (scope_to_user helper + ContextVar + RLS) for the DPA TOMs.

### 4. §15 status semantics
Reframed #1 (entity) and #2 (incorporator) from "OPEN" (suggesting founder must rule before drafting can proceed) to "DEFERRED" (an active strategic pause). This matches the founder's stated posture and removes false urgency from STATUS_LEGAL.md.

## How to apply (pre-incorporation drafting mode)

**Drafts that come next (DPA, KYC, GST, invoice, in-product strings) follow these rules:**

- Every legal name reference: `**Stellaxis** [ENTITY SUFFIX]`
- Every Razorpay-name-match field: `Stellaxis [ENTITY SUFFIX]` (the merchant-of-record name, must match PAN/GST/bank when registered)
- Every founder identity reference: `[FOUNDER: Name on PAN]`
- Every address: `[FOUNDER: Stellaxis registered business address]`
- Every jurisdiction clause: `[FOUNDER: City of Stellaxis registered office]`
- Every effective/last-updated date: `[FOUNDER: publish date]`
- KYC + GST checklists: ship **both** Sole-Prop and OPC variants side-by-side; founder picks at incorporation
- DPA: V1.5 enterprise template; OK to ship as draft now — first Business-tier customer can request and sign once Stellaxis registers

**No founder-input needed to proceed.** The architecture is closed; drafting resumes on next "continue" signal.

## What's NOT changed this turn
- The 4 existing drafts (Privacy, ToS, Refund, Cookie) — content is untouched. Their placeholders are inventoried in the new tracker.
- §15 decisions #3-#15 — all stay RATIFIED.
- The 4 audit event_types queued for `meesell-backend-coordinator` — still queued.

## Links
- See [[reference-brand-vs-legal-name]] for Stellaxis/MeeSell split.
- See [[reference-section-15-ratified]] for the full ratification list.
- See [[session-2-turn-4-brand-split-and-tos]] for prior turn context.
- See `docs/legal/placeholders-tracker.md` for the canonical placeholder inventory.
