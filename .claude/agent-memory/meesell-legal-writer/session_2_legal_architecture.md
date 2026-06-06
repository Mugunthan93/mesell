---
name: session-2-legal-architecture
description: Authored docs/LEGAL_ARCHITECTURE.md SKELETON v1 as peer to FE/BE/DB/Infra architecture docs; mapped legal surfaces, surfaced 7 new founder decisions on top of LACI §10's 8
metadata:
  type: project
---

# Session 2 — Legal Architecture SKELETON v1

**Date:** 2026-06-05
**Founder ask:** Compose legal architecture mirroring existing FE/BE/DB/Infra architecture files; analyse what legal entities (= legal-handling surfaces) the system must handle.
**Output:** `docs/LEGAL_ARCHITECTURE.md` (16 sections, SKELETON status), plus `docs/status/STATUS_LEGAL.md` update.

## Why
Before any `docs/legal/` artifact (Privacy Policy, ToS, Refund Policy, etc.) can be drafted, MeeSell needs a single source of truth that enumerates every legal surface in the as-built system and maps each surface to (a) the regulator who cares, (b) the artifact that closes it, (c) the founder decision blocking it. Without this map, drafting individual policies risks gaps and inconsistency across documents.

## How to apply
This file is the **construction contract** for every future `docs/legal/` artifact. The drafting order in §14 is the order in which Privacy/ToS/etc. should be authored. The §15 founder-decision list is the gating dependency map — no artifact ships until its blocking decisions are LOCKED.

## Structure of the document (16 sections)
0. Purpose, Audience, Cross-References
1. Legal Topology — ASCII map of regulators per request-path step
2. Regulated Data Inventory — per-table (mirrors DBA §2)
3. Regulatory Regime Map — 8 regimes (DPDP, IT Act, Consumer Protection, GST, RBI PA-O, Legal Metrology, Companies Act, per-super-category)
4. Sub-Processor Register — 10 vendors (8 in V1, +1 V1.5)
5. Cross-Border Data Transfer Map — Gemini, LangFuse, Mailgun
6. Tenant Isolation as Legal Control — V1 app-layer scoping, V1.5 RLS forward-promise
7. Consent + Data-Subject Rights Lifecycle — 8 rows, 5 V1 gaps with manual workarounds
8. Breach Response + Grievance Officer Runbook — DPB 72 h notification, GO 7 d SLA
9. Retention Schedule — per-table; cascade RESTRICT rule for exports/audit_events
10. Audit Log as Compliance Evidence — DPDP §8(5); 4 new event_types proposed
11. Intellectual Property — seller content, AI output, dataset moat, takedown procedure
12. Payment Compliance — Razorpay KYC, GST, invoice template, name-match rule
13. Per-Super-Category Statutory Touchpoints — FSSAI, BIS, DCA, WPC, AICTE
14. Document Mapping — Surface → Privacy/ToS/Refund/Cookie/DPA clause
15. Founder Decisions Blocking Legal Surfaces — 8 LACI + 7 new = 15 total
16. Deferred to V1.5

## 7 new founder decisions surfaced (beyond LACI §10)
- #9: Marketing email in V1 (recommend: no, transactional only)
- #10: LangFuse in V1 (recommend: disable until vendor jurisdiction confirmed)
- #11: product_drafts TTL (recommend: 30 d)
- #12: Cross-border to Gemini (recommend: accept and disclose)
- #13: Soft-delete grace period (recommend: 30 d)
- #14: Manual erasure workflow SLA (recommend: 30 d max, 7 d target)
- #15: Personal data export workflow SLA (recommend: 7 d via Grievance Officer)

## 4 new audit event_types proposed (backend hand-off)
- `auth.consent`
- `auth.logout`
- `user.deletion_request`
- `user.data_export_request`
Hand-off target: `meesell-backend-coordinator` to extend BEA §4.G audit catalogue after §10 LOCKED.

## 5 V1 data-subject-rights gaps (per §7)
- Right to access — manual via Grievance Officer, 7 d SLA
- Right to erasure — manual workflow, 30 d max
- Right to grievance ticket — manual, email-based, 7 d SLA
- Right to nomination — V1 SKIP
- Right to withdraw marketing consent — depends on §15.9 (recommend: no marketing email in V1 → no withdrawal surface)

## Drafting order (locked by §14 table)
1. Privacy Policy — closes 12 surface rows
2. Terms of Service — closes 9 rows
3. Refund Policy — closes 4 rows
4. Cookie Policy — closes 1 row
5. DPA template — closes 9 rows (V1.5 enterprise)
6. Razorpay KYC checklist
7. GST registration checklist
8. Invoice template

Plus `in-product-strings.md` for FE hand-off.

## Links
- See [[reference-surface-to-doc-mapping]] for the traceability matrix.
- See [[project-fe-d5-token-model]] for the auth security narrative used in Privacy "How we protect" + DPA Annex 2.
