# Catalog Wizard — Step Grouping & Risk Audit

**Status:** reference doc for the multi-step catalog-form wizard build.
**Owner:** `meesell-data-engineer` (data lead).
**Source of truth:** the seeded `templates.schema_jsonb` + `app.i18n.step_assignment.STEP_ORDER`.
**Companion artifacts:**
- `scripts/build_wizard_step_grouping.py` — the deterministic, read-only generator.
- `docs/plans/catalog-wizard/step_grouping_manifest.json` — the machine-readable manifest the FE consumes.

This doc is the "won't-get-issues" reference: it states the grouping rule, proves coverage
for all 3,772 categories, and audits every edge case the wizard build will hit, with a
recommendation and an affected-category count for each.

> **Not a re-derivation.** Step assignment already happened at seed time (`step_assignment.py`
> → `field["step_id"]`). This doc and the script only *read* `step_id` and *group* by it. We do
> NOT re-classify fields, touch the seed, or modify any runtime code.

---

## 1. The grouping rule

A wizard for a category is built from exactly one template schema. The rule is three lines:

1. **Group** each schema field by its pre-assigned `step_id`.
2. **Render** only NON-EMPTY steps, in canonical `STEP_ORDER`.
3. **Order fields within a step** COMPULSORY-FIRST, then original schema order
   (`meesho_column_index` ascending; stable fallback = position in `fields[]`).

This is fully deterministic — same DB state always yields byte-identical grouping.

### Canonical step list (STEP_ORDER) with seller-facing labels

| Order | `step_id` | Friendly label | Kind |
|------:|-----------|----------------|------|
| 1 | `basics` | Product Basics | universal |
| 2 | `pricing` | Pricing | universal |
| 3 | `inventory` | Inventory & Packaging | universal |
| 4 | `sizing` | Size & Fit | conditional |
| 5 | `materials` | Material & Pattern | conditional |
| 6 | `food` | Food & Nutrition | conditional |
| 7 | `tech_specs` | Technical Specs | conditional |
| 8 | `safety` | Safety & Age | conditional |
| 9 | `warranty` | Warranty | conditional |
| 10 | `compliance` | Compliance | universal |
| 11 | `photos` | Photos | universal |
| 12 | `description` | Description | universal |
| 13 | `advanced` | Advanced (optional) | **unused** (0 templates) |

Labels are owned by this doc/script pair (plain English, never a generated code). The FE may
localise later; the `step_id` is the stable join key.

---

## 2. Coverage proof

| Metric | Value |
|---|---|
| Categories covered | **3,772 / 3,772** (`category_index` in the manifest) |
| Distinct template schemas | **3,566** |
| Categories with NULL `template_id` | **0** (every category resolves to a schema) |
| Fields lacking a `step_id` (ungrouped) | **0** |
| Min steps per category | **6** |
| Max steps per category | **11** |

### Step-usage table (how many of the 3,566 templates include each step)

| Step | Templates | % | Universal? |
|---|---:|---:|---|
| `basics` | 3,566 | 100% | yes |
| `pricing` | 3,566 | 100% | yes |
| `inventory` | 3,566 | 100% | yes |
| `compliance` | 3,566 | 100% | yes |
| `photos` | 3,566 | 100% | yes |
| `description` | 3,566 | 100% | yes |
| `materials` | 1,815 | 50.9% | conditional |
| `sizing` | 614 | 17.2% | conditional |
| `food` | 555 | 15.6% | conditional |
| `tech_specs` | 463 | 13.0% | conditional |
| `warranty` | 448 | 12.6% | conditional |
| `safety` | 197 | 5.5% | conditional |
| `advanced` | **0** | 0% | unused |

**6 universal steps** appear in every template. **6 conditional steps** appear only when a
category has matching fields. The 13th step (`advanced`) is defined in `STEP_ORDER` but used by
**zero** templates (see §4.7).

### Step-count distribution (distinct steps per category template)

| Steps | Templates | Share |
|---:|---:|---:|
| 6 | 917 | 25.7% |
| 7 | 1,507 | 42.3% |
| 8 | 891 | 25.0% |
| 9 | 205 | 5.7% |
| 10 | 42 | 1.2% |
| 11 | 4 | 0.1% |

The modal wizard is **7 steps**; the floor is the 6 universals; the ceiling is 11.

---

## 3. Archetype examples (actual step sets from the seeded data)

Each row is the literal grouped output for a representative leaf. Notation: `step(Rc/T)` =
R compulsory of T total fields in that step.

| Archetype | Leaf (super) | Steps | Step set |
|---|---|---:|---|
| Apparel / Kurti | `Feeding Kurtis & Kurta Sets` (Women Fashion) | 8 | basics(10c/21), pricing(2c/3), inventory(2c/2), **sizing(4c/6)**, **materials(3c/4)**, compliance(9c/9), photos(1c/4), description(0c/1) |
| Grocery / food | `Chaat Masala` (Grocery) | 7 | basics(5c/11), pricing(2c/3), inventory(3c/3), **food(3c/3)**, compliance(9c/9), photos(1c/4), description(0c/1) |
| Grocery / food | `Basmati Rice` (Grocery) | 7 | basics(5c/11), pricing(2c/3), inventory(3c/3), **food(3c/3)**, compliance(9c/9), photos(1c/4), description(0c/1) |
| Electronics / accessory | `Car Mobile Chargers` (Automotive) | 8 | basics(10c/20), pricing(2c/3), inventory(3c/3), **tech_specs(4c/7)**, **warranty(1c/1)**, compliance(9c/11), photos(1c/4), description(0c/1) |
| Books | `Account Books & Journals` (Office Supplies) | 6 | basics(12c/17), pricing(2c/3), inventory(3c/3), compliance(9c/9), photos(1c/4), description(0c/1) |

Books are the canonical **6-step minimum** (universals only). Apparel adds Size & Fit + Material;
Grocery adds Food & Nutrition; Electronics adds Technical Specs + Warranty.

---

## 4. Edge-case / risk audit

Each risk is quantified by affected-category count and carries a wizard-build recommendation.

### 4.1 Steps with ZERO compulsory fields (can a step be skippable?)

A step can be present yet have no required field. Occurrences (templates where the step is
present but all its fields are optional):

| Step | Templates all-optional | Notable |
|---|---:|---|
| `description` | **3,554 of 3,566** | nearly ALWAYS all-optional |
| `materials` | 234 | |
| `sizing` | 210 | |
| `safety` | 87 | |
| `tech_specs` | 54 | |
| `warranty` | 13 | |
| `food` | 6 | |

By category exposure, **3,760 of 3,772 categories** have an all-optional Description step.

- **Recommendation:** the wizard MUST treat "step has 0 compulsory fields" as a first-class case.
  Such a step should be enterable and freely skippable — never block "Next" on it. Description in
  particular should be skip-friendly (it is the AI-autofill target, so most sellers will leave it
  for the autofill pass). Drive "is this step required to advance" off `required_count > 0`, NOT
  off the step existing.
- **Note:** `basics`, `pricing`, `inventory`, `compliance`, `photos` ALWAYS have ≥1 compulsory
  field (0 templates have an all-optional version), so those gate progression in every category.

### 4.2 Unusually LARGE steps (the worst offenders)

`basics` is the catch-all and the only step that grows large.

| Templates with basics ≥ 15 fields | ≥ 20 | ≥ 25 |
|---:|---:|---:|
| 1,551 | 402 | 46 |

- **Max field-count in any single step across the catalog: 42** (`basics` of `Couple watches`,
  Women Fashion — manifest `max_fields_in_a_step`).
- Worst Basics offenders: Couple watches (42), Chronograph Watches (35, Women & Men), Sports
  Watches (34), Analog Watches (34), Motorcycle Headlights (33). Watches dominate the tail.
- **425 categories** sit behind a basics step of ≥ 20 fields.
- **Recommendation:** Product Basics needs in-step sub-grouping or progressive disclosure when
  `field_count` is high (e.g. a "core" cluster always visible + a "more details" expander for the
  optional remainder). The compulsory-first ordering already puts the must-fill fields at the top,
  so a simple cut line after `required_count` is a safe default. Do NOT split `basics` into multiple
  wizard steps — the `step_id` contract is one step per id; sub-group *within* the step instead.

### 4.3 Categories with RARE step combinations

There are **40 distinct step combinations** across the catalog. The long tail is thin:

- **21 combinations cover ≤ 10 categories each**, accounting for **77 categories total**.
- **12 combinations are held by ≤ 3 templates** (e.g. `basics+pricing+inventory+sizing+materials+food+warranty+compliance+photos+description`, `…+food+safety+compliance+…` — one template each).
- **Recommendation:** because the wizard is fully data-driven (renders whatever non-empty steps
  the schema declares), rare combinations need NO special-casing — they render mechanically. The
  risk is only in *test coverage*: the FE golden tests should include at least one of the rare
  9–11-step combos (the 4 eleven-step templates) so an off-by-one in step navigation surfaces.
  Pull a sample from `step_count_distribution` buckets 9/10/11 in the manifest.

### 4.4 PHOTOS / image fields — in-wizard vs separate page (OPEN)

- `photos` is universal (3,566 templates) and ALWAYS has exactly 1 compulsory field; the standard
  shape is 4 image slots with slot 1 compulsory. All 14,264 image fields use `primitive=image_upload`.
- The current form behaviour (per project memory) excludes `image_upload` fields from the field form
  and handles images on a separate `/images` page.
- **This decision is OPEN and I do NOT decide it here.** The manifest faithfully includes the
  `photos` step and its `image_upload` fields so the wizard CAN render them inline if chosen.
- **Flag for the lead/founder:** decide whether the Photos step renders inside the wizard (slot UI)
  or links out to the existing `/images` page. Either way the `photos` step exists in 100% of
  schemas — the wizard must account for it as a navigation node even if it delegates the actual
  upload UI elsewhere. **Affected: all 3,772 categories.**

### 4.5 DROPDOWN fields with `enum_resolver = "category"` (empty-options risk)

- **ALL 47,492 dropdown fields** in the catalog have `data_type="dropdown"` with **no inline
  `enum_codes_map`** (it is `null` at template level for every dropdown). Per the runtime
  derivation in `category.service._map_field_to_dto`, every one resolves to
  `enum_resolver = "category"` — i.e. the FE lazy-loads options via `GET .../field-enum/{field}`
  and the validator hits `get_field_enum`. **There are ZERO `"static"` resolvers in V1.**
- **Risk:** if a `(category_id, canonical_name)` pair has no seeded `field_enum_values` rows, the
  dropdown renders with empty options and the seller is stuck. This is the single highest-frequency
  surface in the wizard (47,492 fields).
- **Recommendation:** the wizard must (a) show a loading state while options fetch, (b) degrade
  gracefully on an empty option list (message + "request to add" escape hatch per the Brand-picker
  pattern, not a dead control), and (c) the FE/BE integration tests should assert non-empty
  field-enum for a sample of category dropdowns. The seed already populates `field_enum_values`
  (49,259 rows verified); the wizard build should treat empty-options as an alarming-but-handled
  state, not an impossible one. The manifest surfaces `enum_resolver_derived` per field so the FE
  knows which controls are lazy-loaded.

### 4.6 The `group_id` / advanced placement

- `group_id` (and any other `is_advanced=true` field) is NOT routed to an `advanced` step. It
  receives a normal `step_id` of `basics` and carries `is_advanced=true`. **All 3,566 templates**
  have their advanced field(s) sitting in `basics`.
- **Recommendation:** the FE renders the "Advanced fields" toggle *within* the Basics step (or as a
  global filter), keying off `is_advanced`, NOT off `step_id == "advanced"`. The `advanced` step in
  `STEP_ORDER` is a vestigial bucket — never instantiate a wizard step for it (it would always be
  empty; see §4.7). The manifest carries `is_advanced` per field for exactly this.

### 4.7 The unused `advanced` step

- `advanced` is in `STEP_ORDER` but used by **0 templates** (`unused_steps: ["advanced"]`).
- **Recommendation:** the wizard's "render non-empty steps" rule already drops it for free — no
  action needed. Documented here so a future reader doesn't mistake its presence in `STEP_ORDER`
  for a missing-data bug.

### 4.8 Determinism of ordering

- In-step ordering is `(marker rank, schema_index)` where schema_index = `meesho_column_index`
  (or a stable `fields[]` fallback). This is total and stable — re-runs produce identical output.
- **Recommendation:** the FE should render fields in the manifest's given order verbatim and NOT
  re-sort. Any client-side re-sort would desync from the export adapter, which relies on Meesho
  column order.

### 4.9 All-optional steps / min & max steps (summary of bounds)

- **Min steps:** 6 (the universals; e.g. Books). **Max steps:** 11 (4 templates).
- **All-optional whole steps:** see §4.1 — Description is all-optional in 3,760 categories; the 5
  truly-gating steps (basics, pricing, inventory, compliance, photos) are never all-optional.
- **Recommendation:** the progress/stepper UI must handle 6–11 nodes without layout breakage, and
  a "skip" affordance on any step whose `required_count == 0`.

---

## 5. Wizard build implications (short)

1. **The flat DTO drops `step_id`.** `category.service._map_field_to_dto` emits a 9-key DTO
   (`name, canonical_name, marker, data_type, primitive, help_text, is_advanced, enum_resolver,
   validation_message_ids`) and does **not** include `step_id`. Today the FE cannot group by step
   from the wire payload. **The wizard build requires surfacing `step_id` in the DTO** (add it to
   `_map_field_to_dto` + the §5A.C contract), so the FE groups exactly as this manifest does. This
   is a coordinated backend (DTO/contract) change — open a data → backend memo when the wizard
   build starts. Until then, this manifest is the FE's grouping reference.
2. **Group by `step_id`, render non-empty steps in `STEP_ORDER`** (the manifest gives the ready
   order per schema in `steps[]`).
3. **Gate "Next" on `required_count > 0`**, not on step existence (§4.1).
4. **Sub-group, don't split, large Basics** (§4.2). **Advanced toggle keys off `is_advanced`**, not
   a step (§4.6). **All dropdowns are lazy `category`-resolved** — handle empty options (§4.5).
5. **Photos in-wizard vs `/images` page is an OPEN founder decision** (§4.4).

---

## 6. Regenerating this manifest

Read-only; not in CI. After a re-seed / quarterly refresh:

```sh
set -a; . backend/.env; set +a
PYTHONPATH="$PWD/backend" <venv>/bin/python scripts/build_wizard_step_grouping.py
```

The script logs per-chunk progress and overwrites
`docs/plans/catalog-wizard/step_grouping_manifest.json`. Re-run this doc's numbers against the new
`summary` block if step usage shifts.
