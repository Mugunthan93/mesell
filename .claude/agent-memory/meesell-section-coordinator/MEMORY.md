# meesell-section-coordinator — shared memory INDEX (append-only, unique session headers)

> 9 section-coordinators share this dir. This file is an INDEX ONLY. Real working memory lives in per-section topic files `section-{N}.md`. Never in-place-edit another session's block; append correction blocks.

## Session mesell-section-7-coordinator-session-1 — 2026-06-19
- Section 7 (price-calculator). AUTHORED the Price Calculator REWORK wave plan (correcting the wrong #285/#287 settlement model → confirmed `transfer_price = price − commission_fees − gst_on_shipping − tds − tcs`).
- Plan: `docs/plans/features/price-calculator-rework/WAVE_PLAN.md` (6 waves; critical path W1 data → W2 engine → W3 FE).
- Topic file: `section-7.md`. Status: at check-in gate, awaiting Tier-0 sign-off, NO dispatch yet.
