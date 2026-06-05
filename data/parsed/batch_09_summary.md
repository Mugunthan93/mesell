# Batch 9 — DRAFT findings (Sports & Fitness + Musical Instruments, super_ids=68+78)

**Coverage:** 511 / 511 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed

### 1. **NEW MINIMUM median compulsory — 19** (tied with B12 later)
| Batch | Median compulsory |
|---|---|
| B5 Home & Kitchen | 33 |
| B1 Women Fashion | 28 |
| B8 Office Supplies | 21 |
| **B9 Sports + Musical** | **19** |

→ Sports/Musical have the SHORTEST forms in the corpus. Wizard's lower-bound: ~3 steps × 6 fields each.

### 2. Sport-specific niche fields (115 new total)
| Field | In N | Notes |
|---|---|---|
| Best For | 9 | use-case (e.g. "cricket", "running") |
| Playing Level | 4 | Skill tier (beginner/intermediate/pro) |
| Skill Level | 2 | synonym alert |
| Head Shape | 3 | Cricket bat |
| Bat Grade | 2 | |
| Right Hand Or Left Hand | 2 | |
| Stitching Type | 2 | |
| Bladder Type | 2 | Footballs |
| Fingerless | 2 | Gloves |

→ All very niche. The data-driven primitive library handles them cleanly — no bespoke wizards needed.

### 3. No new compliance/regulatory fields
Sports/Musical add zero onboarding extensions. Standard 10-field block sufficient.

### 4. Brand list still meaningful
Brand max enum = 1,122 in B9. Reasonable scope for sports.

## Cross-batch impact

| | Before B9 | After B9 |
|---|---|---|
| TRUE universals | 26 | 26 (held) |
| Cumulative leaves | 2,305 | 2,816 (74.7%) |
| Recommended fields | 0 | 0 |
| Image rule 4/1 | 100% | 100% |
| Min median compulsory | 21 (Office) | **19 (Sports/Musical)** |
| Onboarding extensions confirmed | Kids+BIS, Electronics+R/IS, Grocery+FSSAI | unchanged |

→ B9 contributes range (lowest medians yet) and confirms niche-field handling without surprises.
