# Batch 5 — DRAFT findings (Home & Kitchen, super_id=30)

**Coverage:** 816 / 816 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed

### 1. HIGHEST median compulsory of any batch — 33
| Batch | Median compulsory | Note |
|---|---|---|
| B5 Home & Kitchen | **33** | new high-water mark |
| B1 Women Fashion | 28 | (prior high) |
| Others | 19-27 | |

→ Home & Kitchen has the longest forms in the entire corpus. Lehengas-level depth, distributed across 816 leaves. Wizard step count must accommodate this — auto-derive from schema.

### 2. **NEW pattern: unit-suffix companion fields** (381 new fields)
Home & Kitchen introduces explicit `_unit` companion fields paired with numeric values:

| Field | In N leaves | Compulsory |
|---|---|---|
| Packaging Weight unit | 181 | 179 |
| Weight Unit | 155 | 155 |
| Product Weight unit | 91 | 91 |

→ Confirms `number_with_unit` primitive design. The frontend renderer auto-pairs `{X}` (numeric) with `{X} unit` (dropdown of g/kg/oz) using name suffix matching. Number-with-unit isn't one component — it's a two-field PAIR.

### 3. Warranty fields surface (didn't appear in B1-B4)
| Field | In N |
|---|---|
| Warranty Period | 143 (compulsory 143) |
| Warranty | 62 |
| Warranty Type | 48 |

→ Three near-synonyms (canonical-name layer): "Warranty Period" / "Warranty" / "Warranty Type". Plus the Electronics-batch "Warranty Type" (149 leaves). Conditional "Warranty" wizard step now confirmed for appliances + electronics + cookware.

### 4. Brand spelling variants in same batch
- Brand (capitalized) — max enum 1,251, in most leaves
- "Brands" (plural) — max 343, in 2 leaves
- "brand" (lowercase) — max 330, in some leaves

→ Same field, 3 variants, all within ONE super-category. Canonical-name normalisation cannot wait — Backend must dedupe at seed time.

### 5. License compliance fields (appliance regulations)
- License Expiry Date (DD/MM/YYYY) — 6 leaves
- License Number — 6 leaves
- License/Registration No. — 1 leaf

→ Small, but suggests Onboarding extension for appliance dealers (kitchen/electrical safety licensing).

## Cross-batch impact

| | Before B5 | After B5 |
|---|---|---|
| TRUE universals (100% intersection) | 26 (B1∩B2∩B3∩B4) | 26 (held — Home & Kitchen has all of them) |
| Brand-pattern fields | 136 | ~190 |
| Recommended-field instances | 0 | 0 (816/816 = 0) |
| Image rule 4/1 | 100% | 100% |
| Cumulative leaves | 817 | 1,633 (43.3%) |
