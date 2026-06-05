# Batch 12 — DRAFT findings (Long tail: 11 small super-categories, super_ids=77+131+15+17+66+39+25)

**Coverage:** 122 / 122 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed

The long tail — 11 small super-categories totalling 122 leaves:
- Industrial & Scientific Products (89)
- Eye Utility (10)
- Appliances (8)
- Craft & Office Supplies (6)
- Men's Grooming (4)
- Kids (3)
- Mobiles & Tablets (2)

### 1. Median compulsory tied LOWEST — 19
Same as B9 (Sports + Musical). Niche / specialty super-categories have the simplest forms.

### 2. **Mobile/Tablet tech-spec fields surface** (28 new fields)
| Field | In N | Compulsory |
|---|---|---|
| RAM | 2 | 2 (100%) |
| Operating System (OS) | 2 | 2 (100%) |
| Battery Capacity | 2 | 0 |
| Dual Camera | 2 | 0 |
| Expandable Storage | 2 | 0 |
| Headphone Jack | 2 | 0 |
| No. of Primiary Cameras | 2 | 0 | **typo in Meesho's source** |
| No. of Seconadry Cameras | 2 | 0 | **typo in Meesho's source** |
| Calling Function | 2 | 0 |

→ **NEW data-quality finding: typos in Meesho's templates** (`Primiary`, `Seconadry`). Canonical-name layer must handle typo variants too.

### 3. BIS/ISI surfaces again (Appliances)
- BIS/ISI Certification Number in 5/122 leaves (Appliances category)
- Same field as in Kids and Electronics — confirms BIS is for any product needing Indian safety certification.

### 4. No new onboarding compliance extensions
Long tail uses combinations of already-discovered extensions (BIS for Appliances, none for the rest).

### 5. Industrial & Scientific — niche specs
Industrial products bring small-volume tech specs: Operating Temperature, Output Voltage variants, hardware interfaces. Auto-classified primitives handle them.

## Cross-batch impact (FINAL)

| | Before B12 | After B12 (FINAL) |
|---|---|---|
| TRUE universals (strict) | 15 | **15** |
| Practical universals (≥99%) | 28 | **28** |
| Cumulative leaves | 3,650 | **3,772 (100%!) ✅** |
| Recommended fields | 0 | **0 across full corpus** |
| Image rule 4/1 | 100% | **100% across 3,772 leaves** |
| Total unique field names | — | **1,831** |
| Brand-pattern fields | — | **291** |
| Onboarding extensions | 5 confirmed | unchanged |

---

## FULL CORPUS COVERAGE COMPLETE — 3,772 / 3,772 leaves parsed cleanly, 12 batches, parser v0.2.

See `data/parsed/FULL_CORPUS_ANALYSIS.md` (next deliverable) for the comprehensive corpus-wide synthesis that drives the MVP architecture.
