## Parser Design — `scripts/parse_meesho_xlsx.py` v0.1

### XLSX schema discovered (uniform across Sarees / Mobile Covers / Spices probes — likely universal but verify per batch)

Every Meesho category XLSX has exactly 5 sheets:
1. **`Instructions`** — uniform 101 rows × 15 cols. General guidance + image rules. Currently NOT parsed (uniform across categories, so skip).
2. **`{CategoryName}-Fill this`** — THE MAIN UPLOAD SHEET. All variance lives here. `max_col` ranges 37–50+ across batch 1.
3. **`Example Sheet`** — sample row(s). Currently NOT parsed.
4. **`Validation Sheet`** — dropdown enum value source. Cells referenced by `data_validation` formula1 ranges. **Wildly variable size: 858 to 4,483+ rows in batch 1 (Brand list dominates).**
5. **`Return Reasons`** — uniform 18 rows × 3 cols. Skipped.

### Main upload sheet layout

- **Row 1**: Template title cell (e.g. `"Sarees Template (Women Fashion/Ethnic Wear/Sarees, Blouses & Petticoats/Sarees)"`). Currently skipped.
- **Row 2**: Per-column marker cell. Possible values:
  - `* Compulsory Field` → `compulsory` marker
  - `Recommended Field` → `recommended` marker (NEVER seen in Batch 1 — Women Fashion + Women is binary)
  - `Optional Field` → `optional` marker
  - `Do not fill these 2 columns. To be filled by Meesho only` → meta column, SKIP
  - `Field Names` (col 1) → label, SKIP
- **Row 3**: `\n\n{field_name}\n\n{help_text}\n` — multi-line cell. Parser splits on `\n+` and takes parts[0] as `field_name`, joins rest as `help_text`.
- **Row 4+**: Sample/formula rows. SKIPPED.
- **User-fillable fields START AT COLUMN 4.** Columns 1-3 are meta: "Field Names" label, "ERROR STATUS" (Meesho-only), "ERROR MESSAGE" (Meesho-only).

### Compulsory detection heuristic

`r"\*\s*compulsor"` (case-insensitive) on Row 2 cell value. This worked 100% on Batch 1 (no missed compulsory fields).

### Dropdown extraction

Per main sheet, openpyxl `ws.data_validations.dataValidation` gives the list of validations. For each:
- Build `col_dvs` map: column-index → list of validations affecting that column
- For each field column, check `col_dvs[col]` for a `list`-type validation
- `dv.formula1` is either:
  - A literal comma-separated list: `"value1,value2,value3"` (may be quote-wrapped)
  - A range reference: `'Validation Sheet'!$A$2:$A$100` — dereference to the Validation Sheet
- Regex for range parsing: `r"'?([^'!]+)'?!\$?([A-Z]+)\$?(\d+):\$?([A-Z]+)\$?(\d+)"`
- **Large enums (>50 values) are truncated to first 50 in the output JSON**, with `enum_count` storing the true size and `enum_truncated: true` flag. This keeps batch JSON files small (Brand alone has 3,998 values per category — without truncation the file would be 200MB+).

### Data-type inference

In priority order:
1. Field name contains "image" or "url" → `image_url`
2. Has enum_values → `dropdown`
3. Field name matches price/qty/quantity/weight/length/width/height/size in → `number`
4. Field name contains "date" or "expiry" → `date`
5. Default → `text`

⚠️ **Known imperfection:** `MRP` and `Inventory` are typed as `text` but semantically `number`. Improve heuristic by adding `mrp`, `inventory` to the number-pattern list when extending the parser.

### Compute-cost notes

- 179 files parsed in ~25 seconds (~7 files/sec). Brand-heavy categories take slightly longer due to Validation Sheet dereferencing.
- Memory: peaks ~100MB during a single file load. No streaming optimization needed.
- For full 3,772-file run: estimate ~9 minutes total.

---
