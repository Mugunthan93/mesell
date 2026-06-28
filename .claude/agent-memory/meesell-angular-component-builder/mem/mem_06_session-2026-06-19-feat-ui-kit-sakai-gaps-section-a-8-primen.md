## Session 2026-06-19 — feat/ui-kit-sakai-gaps Section A — 8 PrimeNG wrapper components {#sakai-gaps-section-a}

### Task
HYBRID step 2 (builder): Implement 8 ui-kit primitive wrappers for the Sakai-gap spec Section A.
Branch/worktree: `worktree-design-figma-ui-screens`

### Files Created (18 new files)
- `checkbox/checkbox.component.ts` + `.spec.ts`
- `radio/radio.component.ts` + `.spec.ts`
- `breadcrumb/breadcrumb.component.ts` + `.spec.ts`
- `tabs/tabs.types.ts` + `tabs/tabs.component.ts` + `.spec.ts`
- `message/message.types.ts` + `message/message.component.ts` + `.spec.ts`
- `panel/panel.component.ts` + `.spec.ts`
- `divider/divider.component.ts` + `.spec.ts`
- `scroll-panel/scroll-panel.component.ts` + `.spec.ts`

### Files Modified
- `aggregators.ts` — MEE_FORM 6→8, MEE_FEEDBACK 5→6, MEE_DATA 2→3, MEE_COMMON 4→5, NEW MEE_SURFACE[3], MEE_UI_ALL 21→29
- `aggregators.spec.ts` — count assertions updated, MEE_SURFACE test block added
- `index.ts` — 8 new component exports, MeeTab + MeeMessageSeverity type exports, MEE_SURFACE in aggregator re-export line

### PrimeNG v21 API Findings (CRITICAL — save for future builders)

**RadioButtonGroup does NOT exist in primeng/radiobutton v21:**
- Only `RadioButton` and `RadioControlRegistry` are exported
- Fallback taken: shared `[ngModel]`+`[name]`+`[value]` on individual `p-radiobutton` elements
- The group CVA seam is on the wrapper component (`mee-radio`); all radios share the same `[name]` and `[ngModel]`

**Tabs API in PrimeNG v21 (p-tabview is GONE):**
- Import: `{ Tabs, TabList, Tab, TabPanels, TabPanel }` from `primeng/tabs`
- `p-tabs` = host; `p-tablist` = header bar; `p-tab [value]` = individual tab header
- `p-tabpanels` = panel container; `p-tabpanel [value]` = content area matched by value
- `Tabs.value` is a SIGNAL input (not classic @Input) → emit via `valueChange` output
- Two-way binding in template: use `[value]="value()" (valueChange)="onTabChange($event)"`
- `TabPanel` in the wrapper's imports[] triggers NG8113 warning (not used in wrapper template but used by consumers via projection) — remove from imports[], document that consumers import it from primeng/tabs directly

**Panel.collapsedChange emits `boolean | undefined` (not just `boolean`):**
- Handler must accept `boolean | undefined` and normalise: `const next = value ?? false`

**ScrollPanel has NO `[style]` input in v21:**
- Apply max-height via a host wrapper `<div [style]="hostStyle()">` around `<p-scrollpanel>`
- `p-scrollpanel` only accepts `styleClass`; sizing must be done externally

**Panel ng-template naming trap:**
- `<ng-template #header>` inside a panel template conflicts with a component `header = input<...>()` because the template variable `header` shadows the signal in Angular's template scope
- Fix: rename the signal input with an alias: `readonly panelHeader = input<...>(undefined, { alias: 'header' })` so the template uses `panelHeader()` (no clash) and the ng-template uses `#header` (what PrimeNG's `predicate: ["header"]` query needs)

**Checkbox CVA pattern — ALWAYS use Pattern A (not Pattern B) for checkbox/radio:**
- Pattern A = `NG_VALUE_ACCESSOR + forwardRef(() => Cmp)` provider + `innerValue` signal
- No NgControl self-inject needed (these components don't need auto-error-message machinery)
- `[binary]="true"` default → CVA emits `boolean`; `[binary]="false"` → emits in-group value

### CVA Pattern A vs existing p-checkbox API
- `p-checkbox` emits `onChange: { checked: boolean, originalEvent: Event }` (EventEmitter)
- Better: use `[ngModel]="innerValue()" (ngModelChange)="onModelChange($event)"` — cleaner CVA seam
- `(onBlur)="onTouched()"` fires the CVA `registerOnTouched` callback

### mee-breadcrumb design
- Reuses `MeeMenuItem` from `menu/menu.types.ts` (no new type needed)
- `pgItems` computed maps `MeeMenuItem[]` → PrimeNG `MenuItem[]` with `MEE_ICONS[item.icon]` resolution
- `RouterModule` import needed because `p-breadcrumb` uses `routerLink` internally

### Aggregator MEE_SURFACE naming decision
- `MEE_LAYOUT` is reserved for `@mesell/layout` library (page-level primitives)
- New ui-kit surface group named `MEE_SURFACE` (panel, divider, scroll-panel) — different level of abstraction
- Added `MEE_SURFACE` to `MEE_UI_ALL` spread; total = 29

### Build result
- `tsc --noEmit -p tsconfig.json`: 0 errors from new files
- `tsc --noEmit -p tsconfig.spec.json`: 0 errors from new files
- Pre-existing errors in `mfe-auth` (errorMessage) and `mfe-catalog` (ApiClient) block `ng test` run — NOT introduced by this PR
- 24 new test cases across 8 spec files; aggregators.spec.ts: 15 assertions updated

---
