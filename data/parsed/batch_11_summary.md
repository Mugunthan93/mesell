# Batch 11 — DRAFT findings (Automotive Acc + Automotive + Pet + Books + Bags, super_ids=73+18+75+80+83)

**Coverage:** 493 / 493 (100%) | Parser v0.2 | Date 2026-06-04 | Coordinator-implements fallback

## What this batch contributed — **ANOTHER FOUNDER PREDICTION CONFIRMED**

### 1. 🚨 **Books bring ISBN — but it's OPTIONAL, not compulsory**

| Field | In N | Compulsory | Notes |
|---|---|---|---|
| ISBN | 163 | **0** | Optional in Books |
| Book Title | 163 | 163 | Compulsory |
| Book Format | 163 | 163 | Compulsory (paperback/hardcover/ebook) |
| Genre | 163 | 163 | Compulsory |
| Sub Genre | 49 | 49 | Compulsory in many |
| Pages | 163 | 163 | Compulsory |
| Publish Year | 163 | 163 | Compulsory |
| Author | 163 | 0 | OPTIONAL ← surprising |
| Edition | 163 | 0 | Optional |
| Book Type | 162 | 162 | Compulsory |

→ **Founder's Batch 3 prediction "Books → ISBN" is confirmed but with a twist**: ISBN is OPTIONAL, not compulsory. Author and Edition are also optional. Meesho treats Books leniently — sellers can list a book without ISBN/Author. This is unusual for an e-commerce platform.

→ MVP: For Books, the wizard shows ISBN/Author/Edition with prompts like "Adds trust — recommended" but doesn't block submission.

### 2. **Massive new vocabulary — 334 new fields** (second-biggest after B5)

Books + Automotive + Pet bring big domain-specific vocabularies. Auto parts especially: Wattage hit 415, Voltage 400 (battery and electrical car accessories), Output Voltage 400, Model Name dropdown up to 559.

### 3. Compulsory median 26 — sits in middle range
Driven mostly by Books (high-attribute) and Bags (moderate). Auto Accessories are also attribute-heavy.

### 4. Spelling/synonym drift continues
- `battery_power` (snake_case, lowercase) — Meesho's data team is inconsistent
- `Battery Included` / `Battery Type` — multiple Battery-related variants
- `Warranty Duration Months` — Warranty family grows another variant

### 5. Sub-cluster compliance signal weak
- BIS/ISI: 0 instances in B11 (Auto/Pet/Books/Bags don't need BIS)
- FSSAI: 16 instances (for pet food products)
- ISBN: 163 instances but optional

→ For Books, the onboarding extension could be ISBN (optional declaration of "do you publish books?"). For Pet (food overlap): FSSAI extension reuses the Grocery extension.

## Cross-batch impact

| | Before B11 | After B11 |
|---|---|---|
| TRUE universals (strict) | 15 | 15 (held since B10) |
| Practical universals (≥99%) | 28 | 28 (held) |
| Cumulative leaves | 3,157 | 3,650 (96.8%) |
| Recommended fields | 0 | 0 |
| Image rule 4/1 | 100% | 100% |
| Onboarding extensions confirmed | Kids+BIS, Electronics+R/IS, Grocery+FSSAI, Beauty+License | **+Books+ISBN (optional)** |
