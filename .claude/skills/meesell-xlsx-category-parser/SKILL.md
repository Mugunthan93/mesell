---
name: meesell-xlsx-category-parser
description: >-
  MeeSell's conventions for parsing the 3,772 Meesho category XLSX templates into normalized
  reference data (category_attributes.json + meesho_category_tree.json) and the brand whitelist.
  Use this skill WHENEVER you are creating or editing the XLSX→JSON parser, the category tree /
  attribute normalization, the brand whitelist extraction, or the schema versioning of those
  data files — even if the user only says "parse the category sheets", "update the category
  data", "the attributes are wrong", or "regenerate the tree". Do NOT use it for the live
  scraper that refreshes the source (defer to meesell-meesho-scraper) or the picker that
  consumes the tree (defer to meesell-category-picker-pipeline).
---

# MeeSell XLSX Category Parser Conventions

These are the locked rules for turning Meesho's category XLSX templates into the normalized
JSON the rest of MeeSell relies on. They exist so the category tree is consistent, versioned,
and the parse is reproducible and diffable across quarterly refreshes. They derive from
`CLAUDE.md` Feature 3 + the project data layout, which win.

## The non-negotiables (and why each matters)

- **Deterministic, reproducible parse.** Same input XLSX → byte-identical JSON (stable key
  order, sorted leaves). A non-deterministic parser makes every quarterly refresh look like a
  huge diff and hides the real changes. Sort and canonicalize on the way out.

- **Two outputs, clearly separated.** `meesho_category_tree.json` is the hierarchy
  (super → category → leaf with ids); `category_attributes.json` is the per-leaf attribute
  schema (field name, type, allowed enum values, required-ness). Don't merge them — the picker
  needs the tree, the catalog form needs the attributes.

- **Schema-versioned.** The output carries a `schema_version` (and a source snapshot date).
  When Meesho changes a template shape, bump the version so consumers can detect and adapt
  rather than silently misreading a moved column.

- **Normalize, don't pass through.** Trim whitespace, canonicalize casing for ids, dedupe enum
  values, and map Meesho's column quirks to a stable internal field shape. Downstream code
  should never have to know which column Meesho happened to use this quarter.

- **Fail loudly on structural surprises.** If a sheet is missing an expected header, has a new
  required column, or a leaf has zero attributes, raise with a precise message — don't emit a
  half-empty tree that breaks catalog creation at runtime.

- **Brand whitelist extracted inline (V1).** The brand whitelist is parsed inline here for V1
  (the dedicated brand-master builder is deferred to V1.5). Keep it a separate output list with
  its own normalization.

## Output shapes (illustrative)

```jsonc
// meesho_category_tree.json
{
  "schema_version": "2026.2",
  "source_snapshot": "2026-06-01",
  "tree": [
    { "id": "...", "name": "Women Ethnic", "children": [
        { "id": "...", "name": "Sarees", "leaf": true } ] }
  ]
}
```

```jsonc
// category_attributes.json
{
  "schema_version": "2026.2",
  "attributes": {
    "<leaf_id>": [
      { "field": "size_in_ltrs", "type": "enum", "required": true,
        "allowed": ["3.5", "5", "..."] }
    ]
  }
}
```

Note on enums: the picker/validator builds its allowed-set from exactly this `allowed` list —
if a valid value (e.g. `"3.5"`) is dropped here, downstream PATCH validation will false-reject
it. Completeness of the enum extraction is load-bearing.

## Parse workflow

1. Read every category XLSX (openpyxl), identify the header row per sheet defensively.
2. Build the tree (super/category/leaf with stable ids) and the per-leaf attribute schema.
3. Normalize + sort; extract the brand whitelist.
4. Validate structure (expected headers present, no empty leaves) — raise on surprise.
5. Emit JSON with `schema_version` + snapshot date; the diff vs the previous version is the
   changelog the data-engineer reviews.

## Quick checklist before you finish a parse/normalize task

- [ ] Deterministic output (stable key order, sorted) — diffable across refreshes
- [ ] Tree and attributes emitted as separate, clearly-shaped files
- [ ] `schema_version` + source snapshot date stamped on output
- [ ] Values normalized (trim/case/dedupe); enum `allowed` lists COMPLETE (no dropped values)
- [ ] Structural surprises raise a precise error, never a half-empty tree
- [ ] Brand whitelist extracted as its own normalized list (V1 inline)
