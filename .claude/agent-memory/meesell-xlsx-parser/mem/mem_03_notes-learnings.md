## Notes & Learnings

### 2026-06-04 — Batch 1 results (Women Fashion + Women, 179 leaves)

- 179/179 parsed cleanly (100% coverage, 0 failures, 0 anomalies)
- Output: `data/parsed/batch_01_women_fashion.json` (~2-3 MB after enum truncation)
- Draft findings: `data/parsed/batch_01_summary.md` (for founder discussion → manual SSoT integration)
- Field count distribution: min 29 / median 42 / max 71 total fields. Compulsory: min 19 / median 28 / max 47.
- 26 universal fields (in all 179 leaves); 359 unique field names total
- **Critical: ZERO "Recommended" fields anywhere in this batch.** May appear in other batches — keep parser logic that detects them.
- Image rules: 100% uniform across batch (4 slots, slot 1 compulsory). Don't recompute for Women categories.

### 2026-06-04 — Key MVP-level findings from Batch 1 data

1. **Brand dropdowns are 1,500–3,998 values per category.** Same field name across categories has wildly different enum sources. UI MUST be autocomplete-with-API, never native `<select>`.
2. **15+ dropdowns have 100+ values** even excluding Brand (apparel sizes, packaging dims, etc.). Reusable searchable-picker component is non-negotiable.
3. **9-field Manufacturer/Packer/Importer block is universal compulsory.** Big auto-fill-from-profile opportunity (Theme 2 time savings).
4. **169 distinct templates serve 179 leaves** — leaf taxonomy is finer than template taxonomy. When storing `categories.attributes_jsonb`, dedupe by template, not by leaf.

### Guidance for Batches 2-12

- **Validate the binary marker assumption.** Batch 1 had only Compulsory/Optional. Batches 2-12 may include `Recommended Field`. Parser already handles it via `RECOMMENDED_PAT` regex — but watch if `recommended_count` stays 0 across all batches. **Update 2026-06-04: Batch 2 also had 0 Recommended fields. 285/285 leaves now confirm binary scheme.**
- **Inspect 3 diverse samples per batch before running.** Sheet structure was uniform in Batch 1, but Grocery / Mobiles / Books may diverge. **Update: Batch 2 (Men Fashion) also fit the same 5-sheet structure — no parser changes needed.**
- **Watch for sheet-name patterns ending in something other than `-Fill this`**. Parser's `find_main_sheet` falls back to checking for `Fill this` suffix — if a batch breaks, add more patterns.
- **Always run with `--super-ids` filter, write to `data/parsed/batch_NN_<name>.json`**. Don't touch `backend/app/data/category_attributes.json` until ALL 12 batches done AND MVP design locked.
- **Produce a draft summary in `data/parsed/batch_NN_summary.md` after each batch.** Do not write to `docs/MEESHO_CATEGORY_INTELLIGENCE.md` — the coordinator + founder integrate that manually.
- **Cross-batch analysis is now mandatory per batch** — compare against all prior batches' parsed JSONs. Required sections: true universals (intersection), new fields introduced, same-name-different-enum tracking (Brand pattern), Onboarding vs Catalog classification, primitive type mapping.

### 2026-06-04 — Batch 2 results (Men Fashion, 106 leaves)

- 106/106 parsed cleanly (0 failures, 0 anomalies)
- Output: `data/parsed/batch_02_men_fashion.json`
- Draft findings: `data/parsed/batch_02_summary.md`
- 28 universals in Batch 2 alone; 26 TRUE universals when intersected with Batch 1
- Compulsory range 21-43 (median 27, mean 27.1). Very close to B1 (median 28).
- Zero Recommended fields again. 285/285 leaves consistent — strong evidence Meesho's bulk-template marker scheme is binary.
- 49 NEW fields not in B1: menswear-specific (Chest Size, Waterproof, Number of Pockets, Toe Shape, etc.)
- 174 fields shared between B1 and B2 (out of 408 cumulative unique)
- **82 fields show variable enum size across categories** (the Brand pattern, but much wider). Top: Brand (1-3998), Variation (1-205), Group ID (30-200), Color (17-178), Length Size (25-321).
- Image rules uniform: 4 slots, slot 1 compulsory, 100% of 106 leaves. Pattern holds 285/285 cumulative.
- 105 distinct templates for 106 leaves (1 dedup, ~1%). B1 had 169 for 179 (10 dedup, ~6%). Dedup rate is real but small.

### 2026-06-04 — Coordinator-implements pattern still in force

The Agent tool reports `Agent type 'meesell-xlsx-parser' not found` — not just "blocked by hook." The spec file at `.claude/agents/meesell-xlsx-parser.md` exists but the agent was never wired into Claude Code's subagent discovery list. Founder's 7 PM hook-fix needs to do REGISTRATION, not just a settings tweak. Until then, coordinator (meesell-data-engineer) runs the parser script directly. All learnings still land here for continuity.

### 2026-06-04 — Batch 3 results (Kids & Toys, 284 leaves)

- 284/284 parsed cleanly (0 failures, 0 anomalies)
- Output: `data/parsed/batch_03_kids_toys.json`
- Draft findings: `data/parsed/batch_03_summary.md`
- 26 TRUE universals locked across B1∩B2∩B3 — zero attrition.
- Compulsory range 20-42 (median 24, mean 24.8). **Lower than Fashion** (B1=28, B2=27). Wizard can't have fixed step count.
- 0 Recommended fields again. **569/569 cumulative confirms binary marker scheme.**
- 149 NEW fields not in B1+B2 — biggest batch expansion yet.
- Safety-critical compliance fields surface for the first time: Product Dimensions (compulsory in 133/284), Recommended Age (107/284, 95 comp), Kids Weight, BIS/ISI Certification Number, Assembling Required, Battery Required, Material Type.
- Brand-pattern field set: 82 → 106 fields (cumulative).
- Image rules uniform: 100% of 284 leaves (4 slots, 1 compulsory). 569/569 cumulative.
- Template dedup: 247 distinct templates for 284 leaves (13%). MUCH higher than Fashion (1-6%). Schema-by-template strategy reinforced.

### 2026-06-04 — Data-quality issues SURFACED at source

Kids & Toys revealed multiple data-quality issues that originate in Meesho's XLSX templates, not the parser:

- **Spelling drift**: "Colour" (British) vs "Color" (American) — both used. Same semantic field, different names.
- **Synonym fields**: "Assembly Required" vs "Assembling Required" — same concept, two names.
- **Concept fragmentation**: "Battery" / "Battery Required" / "Battery Available" — three variants in different categories.

These require a `canonical_field_name` normalisation layer maintained alongside `category_attributes.json`. Recommend the data-engineer coordinator owns the alias map; backend consumes it when serving schema.

### 2026-06-04 — Onboarding bucket grows per super-category (NEW PATTERN)

Batch 3 surfaces a pattern that didn't exist in B1+B2: **super-category-specific compliance fields**.

- B1+B2: Onboarding = 10 universal fields (Manufacturer/Packer/Importer x3, Country of Origin)
- B3: Kids & Toys introduces optional BIS/ISI Certification Number (28 leaves), Recommended Age (compulsory in 95/107), etc.

→ A Tirupur seller dealing ONLY in Kids products benefits from being asked at onboarding: "BIS certification number?" and having it auto-fill on every toy.

→ Seller profile schema needs `compliance_extensions: jsonb` keyed by super-category. Onboarding wizard adds conditional steps per super-category the seller declares.

**Watch in subsequent batches:** Grocery (FSSAI), Books (ISBN), Electronics (BIS/IEC), Health & Wellness (AYUSH license). Each likely adds its own onboarding extension.

### 2026-06-04 — Batch 4 results (Consumer Electronics, 248 leaves)

- 248/248 parsed cleanly (0 failures, 0 anomalies)
- Output: `data/parsed/batch_04_consumer_electronics.json`
- Draft findings: `data/parsed/batch_04_summary.md`
- 26 TRUE universals UNCHANGED — held across 4 batches now
- Compulsory range 19-39, median 24 (same as B3). Confirmed Fashion=~28 / non-Fashion=~24 pattern.
- 0 Recommended fields. 817/817 cumulative confirmed binary.
- 151 NEW fields introduced. Cumulative unique field names: 708.
- **Warranty Type** appears in 149/248 leaves all-compulsory — biggest single-batch field surprise. Conditional-on-Electronics wizard step needed.
- **Compatible Models** is the new largest dropdown: max 4,481 values (beats Brand's 3,998). Same primitive (API-backed search picker). Validates decision #6 auto-classification.
- Indian regulatory IDs surface: R Number (106 leaves), IS Number (112), CM/L Number (26), BIS/ISI (20). All optional. Strong onboarding-extension candidates.
- Tech-spec attributes introduced: Voltage, Wattage, Frequency, Capacity, USB Ports, Bluetooth Version. **NEW primitive needed: number_with_unit** (V, W, Hz, mAh, mm, cm, g, kg suffixes).

### 2026-06-04 — Parser v0.2 fix queued: image_url over-detection

`infer_data_type` heuristic over-classifies as `image_url`. False-positive surfaced in B4: Webcams template field "Still Image Sensor Resolution" is a tech-spec dropdown (camera megapixels), NOT an image upload. Parser mis-tagged it because name contains "Image".

**v0.2 fix:** restrict image_url detection to canonical patterns: `^Image \d+`, `^Front Image`, `^Back Image`, `^Side Image`, `^Image \d+ \(.+\)$`. Drop loose substring match. Add unit-suffix detection for number_with_unit primitive while we're in there.

### 2026-06-04 — Canonical field-name normalisation layer (DECISION DEFERRED)

Synonym/spelling drift growing across batches:
- B3: Colour/Color, Assembly/Assembling Required, Battery/Battery Required/Battery Available
- B4: Battery/Battery Required/Battery Available/Batteries Required/Batteries Included/Battery Type (6 variants!), Compatible Model/Models/Mobiles/Devices, Cable Length/Cable Length Size

**Proposal:** maintain `data/parsed/canonical_field_aliases.json` keyed by canonical name → list of variants. Built up per batch. Backend serves the canonical name to frontend; alias mapping happens at parse/seed time.

**Ownership:** unclear. Probably data-engineer coordinator builds it as part of cross-batch analysis. Awaiting founder decision.

### 2026-06-04 — FULL CORPUS PARSE COMPLETE (Batches 5-12, parallel execution)

**3,772 / 3,772 leaves parsed (100% coverage). 0 failures across the entire Meesho corpus.**

Parallel execution: 12 batches launched simultaneously via bash background jobs. Total wall time: 167 seconds. (Sequential would have taken ~10x longer.) Parser v0.2 used throughout.

**Per-batch results (B5-B12):**

| Batch | Super-categories | Leaves | Median Comp | Notable findings |
|---|---|---|---|---|
| B5 | Home & Kitchen (30) | 816 | **33 (HIGHEST)** | Unit-suffix companion fields, 381 new fields, Warranty Period universal-ish in 143 leaves |
| B6 | Home & Living + Utility (12+24) | 39 | 25 | Primary/Secondary Colour pattern, Pet Type |
| B7 | Grocery (26) | 321 | 23 | **🚨 FSSAI License COMPULSORY in 321/321 — onboarding extension locked** |
| B8 | Office Supplies (76) | 312 | 21 | Lowest at the time, no new compliance extensions |
| B9 | Sports + Musical (68+78) | 511 | **19 (LOWEST)** | Sport-specific niche fields |
| B10 | Beauty + Health cluster | 341 | 24 | **Eye-Serum breaks 26→15 universal claim** (collapsed compliance representation), License/Registration onboarding extension confirmed |
| B11 | Auto + Pet + Books + Bags | 493 | 26 | **ISBN universal in Books (but OPTIONAL — surprising)**, 334 new fields |
| B12 | Long tail (11 super-cats) | 122 | 19 | Mobile/Tablet tech specs, Meesho typos surfaced ("Primiary", "Seconadry") |

**CORPUS-WIDE INVARIANTS:**

1. **Strict TRUE universals: 15 fields** (7 always-compulsory + 8 always-optional). The 26 claimed in B1-B4 dropped to 15 once Eye-Serum's alternate compliance representation surfaced in B10.
2. **Practical universals (≥99% coverage): 28 fields.** Eye-Serum is the only outlier on the 9-field compliance block.
3. **0 Recommended-Field markers** in 3,772 leaves. V1 binary tier is permanently locked.
4. **Image rule (4 slots, slot 1 compulsory): 100% uniform** across all 3,772 leaves.
5. **Total unique field names: 1,831.** Cannot hand-code form components — data-driven primitive library is mandatory.
6. **Brand-pattern fields (same name, different enum source by category): 291.** The auto-classification by `enum_count` is the only viable approach.
7. **Template dedup: 3,557 distinct templates serve 3,772 leaves (5.7% dedup).** Schema-by-template strategy saves ~6% storage.
8. **Compulsory median range: 19 (Sports/Long-tail) to 33 (Home & Kitchen)**. Wizard step count must be data-driven.

**ONBOARDING COMPLIANCE EXTENSIONS — CONFIRMED:**

| Super-category | Extension fields |
|---|---|
| Grocery | Seller FSSAI License Number (COMPULSORY!) |
| Kids & Toys | BIS/ISI Certification Number (optional) |
| Consumer Electronics | BIS/ISI + R Number + IS Number + CM/L Number (all optional) |
| Beauty & Health | License/Registration Number + Type + Expiry (compulsory in subset) |
| Books | ISBN (optional, surprising) |
| Home & Kitchen (appliances subset) | License Number + Expiry |
| Pet (food overlap) | FSSAI (reuses Grocery's) |

### 2026-06-04 — DELIVERABLES INDEX

- `scripts/parse_meesho_xlsx.py` — Parser v0.2 (tightened image_url detection, expanded number keywords)
- `data/parsed/batch_01_*` through `batch_12_*` — Raw JSON + summary md (24 files total)
- `data/parsed/FULL_CORPUS_ANALYSIS.md` — Comprehensive synthesis driving MVP architecture
- (Pending) `data/parsed/canonical_field_aliases.json` — Variant-to-canonical map, ~16 alias families
- (Pending) `docs/MEESHO_CATEGORY_INTELLIGENCE.md` — SSoT, co-authored with founder at laptop
- (Pending) `docs/MVP_ARCHITECTURE.md` — Phase 3 deliverable
