# Batch 8 — DRAFT findings (Office Supplies, super_id=76)

**Coverage:** 312 / 312 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed

### 1. SHORTEST median compulsory yet — 21
| Batch | Median compulsory |
|---|---|
| B5 Home & Kitchen | 33 |
| B1 Women Fashion | 28 |
| B8 Office Supplies | **21** |

→ Office supplies (pens, paper, files) have the simplest schemas. Wizard step structure can collapse to ~3-4 steps for these categories.

### 2. Paper-specific fields surface (130 new fields total)
| Field | In N | Compulsory |
|---|---|---|
| No. of Sheets | 27 | 27 (compulsory) |
| GSM | 7 | 7 (compulsory) — paper weight |
| Ruled | 6 | 5 (compulsory) — Y/N flag |
| Number of Sheets | 2 | 2 (compulsory) — **synonym alert** |
| Paper Finish | 3 | 1 |
| Ink Colour | 3 | 2 |

→ Industrial dimensions. The "No. of Sheets" / "Number of Sheets" pair is another canonical-name alias.

### 3. No new compliance/regulatory fields
Office Supplies adds NO onboarding extensions. Standard Manufacturer/Packer/Importer block covers it. No FSSAI/BIS/ISBN/AYUSH needed.

→ A seller dealing only in Office Supplies has the lightest onboarding (no super-category extensions).

### 4. Brand list scoped tight
Brand max enum = 393 in B8 — much smaller than Fashion (3,998). Most office brands are niche.

## Cross-batch impact

| | Before B8 | After B8 |
|---|---|---|
| TRUE universals | 26 | 26 (held) |
| Cumulative leaves | 1,993 | 2,305 (61.1%) |
| Recommended fields | 0 | 0 |
| Image rule 4/1 | 100% | 100% |
| Min median compulsory seen | 23 (Grocery) | **21 (Office Supplies)** |
| Onboarding extensions confirmed | Kids+BIS, Electronics+R/IS, Grocery+FSSAI | unchanged |

→ B8 is uneventful but reassuring: confirms the wizard scales DOWN as well as up. No surprises.
