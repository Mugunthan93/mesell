# WAVE — PrimeNG 21 Component Reference Docs

| Field | Value |
|---|---|
| **Document type** | Dispatch notification (master → sub-session) |
| **Wave** | PrimeNG Docs (pre-Wave 2C tooling) |
| **Date authored** | 2026-06-09 |
| **Status** | 📤 READY TO DISPATCH |
| **Agent** | `meesell-angular-component-builder` (sonnet) |
| **Recipient** | Any available meesell sub-session |
| **Est. output** | ~90 markdown files in `docs/primeng/` |

---

## Why

Future agents building Angular components hallucinate wrong PrimeNG prop names and import paths. A local ground-truth reference eliminates retry cycles. Source material is already installed — no web scraping needed.

---

## Sources (all local — no network)

| Source | Path | What it contains |
|---|---|---|
| TypeScript type defs | `frontend/node_modules/primeng/types/primeng-{component}.d.ts` | `@Input()` props + `@Output()` events with JSDoc |
| Extended type interfaces | `frontend/node_modules/primeng/types/primeng-types-{component}.d.ts` | Event payload types, interfaces |
| Usage examples | `themes/sakai-ng/src/` | Real Angular template code (grep for `<p-{name}` or directive attr) |

---

## Output

**Location**: `docs/primeng/`

**One file per component** (`docs/primeng/{component}.md`) with this structure:

```markdown
# ComponentName

**Import:** `import { ClassName } from 'primeng/{component}'`
**Selector:** `p-{component}` (or directive attr where applicable)
**PrimeNG version:** 21.1.9

## @Input() Props
| Prop | Type | Default | Description |
|------|------|---------|-------------|
| ... | ... | ... | ... |

## @Output() Events
| Event | Type | Description |
|-------|------|-------------|
| ... | ... | ... |

## Key Types / Interfaces
(from primeng-types-{component}.d.ts)

## Usage Example
```html
<!-- From themes/sakai-ng/src/ or minimal example if not found -->
```

## Notes
Directive vs component distinction, deprecated props, gotchas.
```

**Plus `docs/primeng/INDEX.md`:**

```markdown
# PrimeNG 21 Component Reference — MeeSell
Generated from node_modules/primeng@21.1.9

## Wave Usage Map
| Wave | Components needed |
|------|------------------|
| 2B Shell | drawer, menu |
| 2C Auth | inputtext, inputotp, button, message, floatlabel, iconfield |
| 2D Dashboard | card, progressbar, progressspinner, badge, tag, chart |
| 2E Catalogs | table, paginator, dialog, stepper, steps, select, multiselect, inputnumber, datepicker, fileupload |

## Full Component List
(one row per component with file link)
```

---

## Component List (~90 total)

Process ALL of these. Do NOT skip any.

```
accordion, animateonscroll, autocomplete, autofocus, avatar, avatargroup,
badge, blockui, breadcrumb, button, buttongroup,
card, carousel, cascadeselect, chart, checkbox, chip, colorpicker,
confirmdialog, confirmpopup, contextmenu,
dataview, datepicker, dialog, divider, dock, drawer, dynamicdialog,
editor, fieldset, fileupload, floatlabel, fluid,
galleria,
iconfield, iftalabel, image, imagecompare, inplace, inputgroup,
inputgroupaddon, inputicon, inputmask, inputnumber, inputotp, inputtext,
knob,
listbox,
megamenu, menu, menubar, message, metergroup, multiselect,
orderlist, organizationchart, overlay, overlaybadge,
paginator, panel, panelmenu, password, picklist, popover,
progressbar, progressspinner,
radiobutton, rating,
scroller, scrollpanel, scrolltop, select, selectbutton, skeleton,
slider, speeddial, splitbutton, splitter, stepper, steps,
table, tabs, tag, terminal, textarea, tieredmenu, timeline, toast,
togglebutton, toggleswitch, toolbar, tooltip,
tree, treeselect, treetable
```

Skip: `icons-*`, `base*`, `bind`, `dom`, `ts-helpers`, `passthrough`, `usestyle`, `ripple`, `styleclass`, `dragdrop`, `focustrap`, `motion`

---

## Execution Order

**Do FIRST (Wave 2C needs these immediately):**
1. `inputtext` — directive (`pInputText`) on `<input>`
2. `inputotp` — component `<p-inputotp>`
3. `button` — component `<p-button>`
4. `message` — component `<p-message>`
5. `floatlabel` — component `<p-floatlabel>`
6. `iconfield` — component `<p-iconfield>`

Then all remaining alphabetically.

---

## Key Extraction Rules

1. **Directive vs Component**: `InputText` is a **directive** applied to `<input pInputText>`, NOT `<p-inputtext>`. Note this distinction clearly in the doc.

2. **JSDoc extraction**: In `.d.ts` files, each `@Input()` prop has a JSDoc block above it with `@group Props` — extract the description text.

3. **Sakai-ng grep**: Find usage examples with:
   ```bash
   grep -r "p-inputotp\|InputOtp" /Users/mugunthansrinivasan/Project/mesell/themes/sakai-ng/src/ --include="*.html" -l 2>/dev/null
   ```
   Read the most representative file. If nothing found, write a minimal example.

4. **File size target**: 50–150 lines per component. Scannable, not exhaustive.

---

## Constraints

- **Read-only**: `frontend/node_modules/`, `themes/sakai-ng/`
- **Write-only**: `docs/primeng/`
- Do NOT touch `frontend/src/` or any other docs files
- Only `meesell-*` agents (CLAUDE.md rule)

---

## Paste-Ready Block

```
══════════════════════════════════════════════════════════════════
📨 MASTER → SUB-SESSION NOTIFICATION
Date: 2026-06-09
Task: Generate PrimeNG 21 Component Reference Docs
Agent: meesell-angular-component-builder (sonnet)
══════════════════════════════════════════════════════════════════

GOAL
────
Generate ~90 markdown API reference files for PrimeNG 21 components.
Each file = import path + @Input props + @Output events + usage example.
Future agents MUST read the relevant file before implementing any PrimeNG component.

SOURCES (all local — no internet needed)
────────────────────────────────────────
1. API defs:
   frontend/node_modules/primeng/types/primeng-{component}.d.ts

2. Type interfaces:
   frontend/node_modules/primeng/types/primeng-types-{component}.d.ts

3. Usage examples (grep):
   themes/sakai-ng/src/  →  grep -r "p-{component}" --include="*.html"

OUTPUT
──────
docs/primeng/INDEX.md  +  docs/primeng/{component}.md × ~90

FORMAT per file:
  # ComponentName
  Import / Selector / Version
  ## @Input() Props (table)
  ## @Output() Events (table)
  ## Key Types / Interfaces
  ## Usage Example (html codeblock from sakai-ng or minimal)
  ## Notes (directive vs component, gotchas)

PRIORITY ORDER
──────────────
Do Wave 2C components first:
  inputtext, inputotp, button, message, floatlabel, iconfield

Then alphabetical for the rest (~84 components).

COMPONENT LIST
──────────────
accordion, animateonscroll, autocomplete, autofocus, avatar, avatargroup,
badge, blockui, breadcrumb, button, buttongroup,
card, carousel, cascadeselect, chart, checkbox, chip, colorpicker,
confirmdialog, confirmpopup, contextmenu, dataview, datepicker,
dialog, divider, dock, drawer, dynamicdialog,
editor, fieldset, fileupload, floatlabel, fluid,
galleria, iconfield, iftalabel, image, imagecompare, inplace,
inputgroup, inputgroupaddon, inputicon, inputmask, inputnumber, inputotp, inputtext,
knob, listbox, megamenu, menu, menubar, message, metergroup, multiselect,
orderlist, organizationchart, overlay, overlaybadge,
paginator, panel, panelmenu, password, picklist, popover,
progressbar, progressspinner, radiobutton, rating,
scroller, scrollpanel, scrolltop, select, selectbutton, skeleton,
slider, speeddial, splitbutton, splitter, stepper, steps,
table, tabs, tag, terminal, textarea, tieredmenu, timeline, toast,
togglebutton, toggleswitch, toolbar, tooltip,
tree, treeselect, treetable

CONSTRAINTS
───────────
  Read-only:  frontend/node_modules/  +  themes/sakai-ng/
  Write-only: docs/primeng/
  DO NOT touch frontend/src/ or any other file

══════════════════════════════════════════════════════════════════
END NOTIFICATION
══════════════════════════════════════════════════════════════════
```
