# MeeSell Core Philosophy

**Locked by founder 2026-06-04 evening.**

This is the rulebook. Every architectural choice, every backend schema, every UI label, every AI prompt must satisfy these rules. When in doubt, return here.

---

## The two anchors

> **Internal flexibility — UI and data model are shaped around the seller's understanding.**
> **External faithfulness — what we export to Meesho is byte-for-byte compatible with Meesho's upload template.**

The two anchors interact this way: **we can deviate from Meesho everywhere except at the export boundary.**

That creates one structural pattern that drives everything:

```
  Seller ←── flexible UI ──→ Internal model ──→ Export Adapter ──→ Meesho XLSX
              (any shape)      (any shape)        (sole point of           (Meesho's
              we want          we want            Meesho-format           wire format,
                                                  knowledge)               exact)
```

The **Export Adapter** is the only place in the system that knows about Meesho's wire format. Everywhere else is free.

---

## MANDATES (every architecture choice must satisfy these)

**M1. Every field has two names.**
Each field carries both:
- `meesho_column_header` — verbatim from Meesho's XLSX (used ONLY by Export Adapter)
- `display_label` — user-friendly UI label, may differ entirely

**M2. Help text is ours.**
UI shows help text WE wrote — plain language, optionally translated. Meesho's original help text is stored as `meesho_help_text` for reference but never shown to the seller.

**M3. Validation messages are ours.**
When a field fails validation, the seller sees plain language ("Please enter a valid pincode") — never Meesho's terse error codes.

**M4. Dropdowns are bilingual at the seam.**
Every dropdown value stores BOTH the Meesho code (for export) AND a friendly label (for UI). Frontend renders labels; Export Adapter writes codes.

**M5. The wizard layout follows seller intuition, not Meesho's column order.**
Steps are named in plain language ("Tell us about your product", "Set your price"). Export Adapter reorders fields to match Meesho's expected column order.

**M6. Round-trip is sacred.**
Every catalog created in MeeSell must export to an XLSX that passes Meesho's validator. A round-trip test per super-category is part of CI.

**M7. AI works in canonical space.**
Gemini auto-fill suggests values using canonical names. Validation checks against the Meesho enum codes. Export Adapter translates. **AI never produces values that wouldn't survive export.**

**M8. The presentation layer is first-class.**
Display labels, friendly help text, validation messages, and dropdown labels are part of the data model — not afterthoughts in component code. Templates carry both Meesho-side and seller-side metadata.

**M9. Localization is structural, not retrofit.**
Display labels, help text, and validation messages are stored as `{locale: string}` maps. V1 ships English. V1.5 adds Tamil/Hindi without schema migration.

**M10. The Export Adapter is the single source of Meesho-format knowledge.**
No other component in the system knows about Meesho's column headers, typos, or order. If the answer to "where does this Meesho rule live?" is more than one place, it's wrong.

---

## FORBIDS (no architecture choice may violate these)

**F1. Never show Meesho's raw column header to the seller.**
"Net Quantity (N)" / "Wrong/Defective Returns Price" / "Primiary Cameras" never appear in any UI. Either renamed or hidden.

**F2. Never invent column headers Meesho doesn't expect.**
XLSX export columns match Meesho's templates exactly, including typos and odd capitalization. No "fixing" Meesho.

**F3. Never send invalid enum values to Meesho.**
AI auto-fill, frontend validation, and backend validators must all enforce that exported enum values are in Meesho's allowed list for that category. Three layers, same constraint.

**F4. Never collect or store data we don't need for export OR for UI.**
If a field isn't shown to the seller AND isn't exported to Meesho, it has no business being in the system. Remove it.

**F5. Never show a field without an explanation.**
Every field rendered in the UI has a clear `display_label` AND a `display_help`. If we don't understand a field well enough to explain it, we either hide it (sensible default on export) or defer it to V1.5.

**F6. Never sacrifice export compatibility for UI cleverness.**
If a UI choice would break Meesho's accepted format, the UI yields — not the Export Adapter. We rename in display, never in export.

**F7. Never break round-trip.**
Catalog → XLSX → Meesho upload → re-parse must yield the same product. Round-trip test per super-category in CI.

**F8. Never let Meesho's representation leak past the Export Adapter.**
Components outside the adapter (backend services, frontend renderer, AI prompts) operate on canonical names + display labels. They do not know "Net Weight (gms)" exists. They know `net_weight_grams` + "Weight per package (grams)".

---

## Structural patterns that emerge

These are direct consequences of the rulebook. Implementation can refine them; the patterns themselves are non-negotiable.

### Pattern 1: Three layers per field

Every field is described by three concentric layers:

```
┌───────────────────────────────────────┐
│  DISPLAY (seller-facing)              │
│   display_label, display_help,        │
│   validation_message, dropdown_labels │
├───────────────────────────────────────┤
│  CANONICAL (internal)                 │
│   canonical_name, data_type,          │
│   primitive, enum_codes, marker       │
├───────────────────────────────────────┤
│  EXPORT (Meesho wire)                 │
│   meesho_column_header,               │
│   meesho_enum_value, column_order     │
└───────────────────────────────────────┘
```

### Pattern 2: Hidden fields with default-on-export

For fields whose purpose is unclear (e.g. Group ID), the pattern is:
- `hidden_in_ui = true` → field never rendered
- `export_default = ""` or `export_default = "<sensible value>"` → Export Adapter writes this on every catalog
- Documented in canonical schema as "hidden field, hidden reason"

Better than guessing; preserves export compatibility; respects seller's attention.

### Pattern 3: Constrained-but-escape-hatched dropdowns

For enum fields where the seller's value might not be in Meesho's list (e.g. Brand):
- UI shows search + a clearly marked "request to add" workflow
- Export uses one of Meesho's allowed values, or omits if Meesho allows blank
- "Request to add" generates a manual review queue for V1.5 brand-master-builder

### Pattern 5: Advanced fields (opt-in for power users)

For optional fields whose purpose is unclear OR whose seller-value is uncertain (e.g. Group ID), the pattern is:
- `is_advanced = true` on the field metadata
- UI hides them by default; an "Advanced fields" expandable section at the bottom of relevant wizard steps reveals them
- Seller's choice to expand is itself an acknowledgement of opacity — relaxes F5 (no field without explanation)
- Export Adapter writes whatever the seller chose; if they didn't expand, sends blank (Meesho accepts blank for optional fields)
- Documented as "advanced field, V1.5 investigation" when purpose is genuinely unknown to us

This sits between Pattern 2 (fully hidden) and a regular visible field. It respects seller's attention without removing their option.

### Pattern 4: Versioned templates

Meesho changes their XLSX templates over time. The system:
- Stores `parsed_from_xlsx_at` + `parser_version` on every template
- Quarterly refresh re-parses; diff report flags changes
- Schema migration only fires if a STRICT universal field changes type
- Other changes are version-tagged and serve old catalogs the old version until exported

---

## Quick self-check (for any new architectural decision)

Hold the decision up against this list:

1. Does this decision affect what the seller sees? → Apply MANDATES M1–M5, M8–M9. Apply FORBIDS F1, F4–F5.
2. Does this decision affect what we export? → Apply MANDATES M2–M3, M6, M10. Apply FORBIDS F2–F3, F6–F7.
3. Does this decision affect the boundary between the two? → It's an Export Adapter concern. Apply MANDATE M10 and FORBID F8.
4. Does this decision affect AI? → Apply MANDATE M7 and FORBID F3.

If a decision touches multiple boxes, the seller's clarity wins inside the system; Meesho's contract wins at the export.

---

## What this philosophy explicitly REJECTS

- **"Just mirror Meesho's template in the UI."** Rejected by M1, F1.
- **"The XLSX is the source of truth, render it directly."** Rejected by M2, F1.
- **"Show all fields; let the seller decide."** Rejected by F5.
- **"AI can suggest free-text values."** Rejected by M7, F3.
- **"Fix Meesho's typos in our export."** Rejected by F2.
- **"Translate Meesho enum codes on export."** Rejected by F3 — translations are at display time only.
- **"One representation of compliance fits all categories."** Rejected by need to support both 9-field and Eye-Serum collapsed templates via Export Adapter.

---

## Status

**Locked.** No further architectural decision is made without passing the checks above.

Next step (per Step 2 of the re-examination plan): re-examine all 14 prior locked decisions against this rulebook — mark each ALIGNED, NEEDS REVISION, or NEEDS NEW ANSWER.
