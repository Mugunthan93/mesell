# UI-Kit Sakai-Gap Build Spec — P0 + P1 + P2

**Author:** meesell-frontend-coordinator (Frontend Lead)
**Date:** 2026-06-19
**Dispatch step:** HYBRID step 1 of 3 — SPEC ONLY. No code is written by the Lead.
**Inputs:** `docs/ui-review/sakai-upgrade-path.md` (deliverable 6.4) + as-built ui-kit audit (this session).
**Branch for all work:** `feat/ui-kit-sakai-gaps` (worktree off `develop`).
**Blast radius:** confined to `frontend/libs/ui-kit/` + `frontend/libs/design-tokens/` + `apps/shell/src/styles.css` + barrel `frontend/libs/ui-kit/index.ts` + `frontend/libs/ui-kit/aggregators.ts`.

---

## 0. Scope reconciliation (READ FIRST — divergence from the upgrade-path doc)

The dispatch task names **9 items**: 8 components + the focus-ring token group. This differs from `sakai-upgrade-path.md` in two places. The **dispatch list is authoritative for this build**; recording the deltas so nothing is silently lost:

| Item | upgrade-path.md priority | THIS spec | Resolution |
|---|---|---|---|
| `mee-scroll-panel` | **P3 DEFER** | **P2 — build it** | Build per dispatch. Upgrade-path said "no confirmed V1 use case"; the Lead's call here is to land the wrapper now as layout groundwork (cheap, sealed). Acceptable scope expansion. |
| `mee-chip` | P2 ALIGN | **NOT in this build** | Deferred to a later wave. `mee-badge` covers static tags today; removable chips have no live consumer yet. No action this build. |
| typography token group | P1 ALIGN | **NOT in this build** | Out of scope for this dispatch (focus-ring is the only token item requested). |
| card-shadow cleanup | P2 ALIGN | **NOT in this build** | Out of scope for this dispatch. |

Net build set: **8 components** (`mee-checkbox`, `mee-radio`, `mee-breadcrumb`, `mee-tabs`, `mee-message`, `mee-panel`, `mee-divider`, `mee-scroll-panel`) + **1 token group** (focus-ring).

---

## 1. As-built ground truth the specialists MUST honor

These are verified facts from the current worktree (`design-figma-ui-screens`), not assumptions:

1. **ui-kit lives at `frontend/libs/ui-kit/`** (NOT `src/app/ui/`). Each component is a folder `{name}/{name}.component.ts` (+ `.spec.ts`, + optional `.types.ts`).
2. **PrimeNG is the only allowed dep inside ui-kit.** PrimeNG v21 ships as fesm2022 — import primitives from subpath specifiers (e.g. `import { Checkbox } from 'primeng/checkbox'`). Verified available subpaths: `primeng/checkbox`, `primeng/radiobutton`, `primeng/breadcrumb`, `primeng/tabs`, `primeng/message`, `primeng/panel`, `primeng/divider`, `primeng/scrollpanel`. **`primeng/tabview` does NOT exist in v21** — the new Tabs API (`Tabs/TabList/Tab/TabPanels/TabPanel`) replaces it.
3. **Two CVA patterns exist in the kit:**
   - **Pattern A (classic) — use for checkbox + radio:** `NG_VALUE_ACCESSOR + forwardRef(() => Cmp)` provider, `innerValue` signal, `writeValue/registerOnChange/registerOnTouched/setDisabledState`. Reference: `frontend/libs/ui-kit/input/input.component.ts`.
   - **Pattern B (NgControl self-inject + auto error message):** for inputs that auto-surface validator messages. Reference: `frontend/libs/ui-kit/multiselect/multiselect.component.ts`. **Do NOT use Pattern B for checkbox/radio** — they don't need the auto-error machinery; keep them lean (Pattern A).
4. **Tokens:** `--mee-*` CSS custom properties in `frontend/libs/design-tokens/_tokens.css`. Components reference tokens via `var(--mee-*)`, never hard-coded hex. No `--mee-focus-ring-*` group exists yet.
5. **Theme preset:** `frontend/libs/ui-kit/theme.ts` exports `MeeSellPreset = definePreset(Aura, {...})`. Has `semantic.primary`, `semantic.colorScheme.light`, and a `components` block (card/button/inputtext/select/dialog/**panel**). `components.panel.root.borderRadius: '16px'` is ALREADY present — panel theming groundwork done. There is **no `semantic.focusRing` block yet**.
6. **Global stylesheet:** `frontend/apps/shell/src/styles.css` (relocated from src/ at SP07 D43). Declares `@layer theme, base, primeng, components, utilities;`, imports Tailwind + design-tokens. **No `:focus-visible` rule today.**
7. **Icons:** semantic `MeeIconName` keys in `frontend/libs/ui-kit/icon/icon.registry.ts`; resolve via `MEE_ICONS[name]` or `resolveIcon(name)`. The registry is the ONLY file allowed to hold raw `pi pi-*` strings (FE-2 allow-list). If a new component needs an icon not in the registry, the registry must be extended — see §A icon notes.
8. **MenuItem semantic type:** `MeeMenuItem` (`frontend/libs/ui-kit/menu/menu.types.ts`) is the established narrowed-PrimeNG-MenuItem pattern. Breadcrumb reuses this shape (label + icon + routerLink), do not import PrimeNG `MenuItem` onto the feature surface.
9. **Option shape:** `MeeSelectOption { label: string; value: unknown }` (`select/select.types.ts`).
10. **Aggregators:** `frontend/libs/ui-kit/aggregators.ts` groups component classes into `MEE_FORM / MEE_OVERLAY / MEE_FEEDBACK / MEE_DATA / MEE_COMMON / MEE_FILE` + `MEE_UI_ALL`. There is **no `MEE_LAYOUT`** here (the comment says layout lives in `@mesell/layout`). New components must be added to the right group **and** the group's coverage count comment + `MEE_UI_ALL` total updated.
11. **Test harness:** Angular 21 + Vitest 4 via `@angular/build:unit-test` builder. TestBed auto-init works (no setup file). Wrapper spec template = `select.component.spec.ts` (uses `NoopAnimationsModule` import for animations + `setInput` + create/default/behavior assertions). CVA specs may bind a `FormControl` and assert write/change propagation.
12. **No new dependency needed.** `primeng@^21.1.9`, `@primeuix/themes@^2.0.3`, `primeicons@7.0.0` are all already in root `package.json`. **Zero installs.**
13. **Standalone only. `ChangeDetectionStrategy.OnPush` mandatory. TS strict.** No NgModules. File naming `{name}/{name}.component.ts`.

---

# SECTION A — for `meesell-angular-component-builder` (8 components)

General rules for every component below:
- Standalone, `ChangeDetectionStrategy.OnPush`, signal `input()`/`output()` API.
- Folder: `frontend/libs/ui-kit/{name}/`. Files: `{name}.component.ts` + `{name}.component.spec.ts` (+ `{name}.types.ts` only where a semantic type is listed).
- Inline template using the `p-*` primitive. Tokens via `var(--mee-*)`, never raw hex.
- Add the class export to `frontend/libs/ui-kit/index.ts`, any semantic type to the Types section, and the class to the correct aggregator array in `aggregators.ts` (update the coverage comment + `MEE_UI_ALL` total).
- A11y: every interactive control needs an accessible label path; icons that are decorative get `aria-hidden`.

---

## A.1 `mee-checkbox` (P0)

- **Path:** `frontend/libs/ui-kit/checkbox/checkbox.component.ts`
- **Wraps:** `Checkbox` from `primeng/checkbox`
- **CVA:** YES — **Pattern A** (`NG_VALUE_ACCESSOR + forwardRef`). Reference `input.component.ts`.
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `label` | `string \| undefined` | `undefined` | rendered to the right of the box, `<label [for]>` wired |
| `disabled` | `boolean` | `false` | |
| `required` | `boolean` | `false` | renders `*` (aria-hidden) when label present |
| `binary` | `boolean` | `true` | single boolean checkbox (true) vs value-in-group |
| `value` | `unknown \| undefined` | `undefined` | only used when `binary=false` (group member value) |
| `error` | `string \| undefined` | `undefined` | inline error text |
| `hint` | `string \| undefined` | `undefined` | inline hint text |

- **Output:** `changed = output<boolean>()` (emit on toggle, alongside CVA propagation).
- **MeeIconName:** none.
- **Template sketch:**
```html
@if (false) {}
<div class="flex items-center gap-2">
  <p-checkbox
    [inputId]="cbId"
    [binary]="binary()"
    [value]="value()"
    [disabled]="disabled()"
    [invalid]="!!error()"
    [ngModel]="innerValue()"
    (ngModelChange)="onModelChange($event)"
    (onBlur)="onTouched()"
  />
  @if (label()) {
    <label [for]="cbId" class="text-sm select-none" style="color: var(--mee-color-on-surface)">
      {{ label() }}
      @if (required()) { <span aria-hidden="true" style="color: var(--mee-color-error)"> *</span> }
    </label>
  }
</div>
@if (error()) {
  <small role="alert" class="block mt-1 text-xs" style="color: var(--mee-color-error)">{{ error() }}</small>
} @else if (hint()) {
  <small class="block mt-1 text-xs" style="color: var(--mee-color-on-surface-muted)">{{ hint() }}</small>
}
```
- **imports:** `[Checkbox, FormsModule]`. `cbId` = `mee-checkbox-${random}` (mirror `inputId` pattern in `input.component.ts`).
- **Aggregator:** add to `MEE_FORM` (form input primitive). Bump `MEE_FORM` 6→7 and `MEE_UI_ALL` 21→ new total.
- **Test:** `checkbox/checkbox.component.spec.ts` — (1) creates with default `binary=true`, unchecked; (2) bound `FormControl` → toggling propagates `true/false` through CVA (`writeValue` + `registerOnChange`); (3) `[error]` set → renders `role="alert"` text and passes `invalid` to `p-checkbox`.

---

## A.2 `mee-radio` (P0)

- **Path:** `frontend/libs/ui-kit/radio/radio.component.ts`
- **Wraps:** `RadioButton` + `RadioButtonGroup` from `primeng/radiobutton`
- **CVA:** YES — **Pattern A** (`NG_VALUE_ACCESSOR + forwardRef`). The CVA lives on the GROUP component (single selected value), not the individual radio.
- **Design decision:** ship ONE component `mee-radio` that takes an `options` array and renders a PrimeNG `RadioButtonGroup` of `RadioButton`s — a group control, not a single dumb radio. This matches how forms actually consume radios and keeps a single CVA seam (one selected value).
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `options` | `MeeSelectOption[]` (required) | — | reuse `MeeSelectOption` from `../select/select.types` |
| `label` | `string \| undefined` | `undefined` | group legend |
| `disabled` | `boolean` | `false` | disables all options |
| `required` | `boolean` | `false` | `*` when label present |
| `direction` | `'row' \| 'column'` | `'column'` | layout of options |
| `error` | `string \| undefined` | `undefined` | inline error |
| `hint` | `string \| undefined` | `undefined` | inline hint |

- **Output:** `changed = output<unknown>()` (selected value on change).
- **MeeIconName:** none.
- **Template sketch:**
```html
@if (label()) {
  <span class="block text-sm font-medium mb-1" style="color: var(--mee-color-on-surface)">
    {{ label() }}
    @if (required()) { <span aria-hidden="true" style="color: var(--mee-color-error)"> *</span> }
  </span>
}
<p-radiobutton-group [ngModel]="innerValue()" (ngModelChange)="onModelChange($event)">
  <div [class]="direction() === 'row' ? 'flex gap-4' : 'flex flex-col gap-2'">
    @for (opt of options(); track opt.value) {
      <div class="flex items-center gap-2">
        <p-radiobutton
          [inputId]="rId + '-' + $index"
          [value]="opt.value"
          [disabled]="disabled()"
        />
        <label [for]="rId + '-' + $index" class="text-sm select-none" style="color: var(--mee-color-on-surface)">
          {{ opt.label }}
        </label>
      </div>
    }
  </div>
</p-radiobutton-group>
@if (error()) {
  <small role="alert" class="block mt-1 text-xs" style="color: var(--mee-color-error)">{{ error() }}</small>
} @else if (hint()) {
  <small class="block mt-1 text-xs" style="color: var(--mee-color-on-surface-muted)">{{ hint() }}</small>
}
```
- **imports:** `[RadioButton, RadioButtonGroup, FormsModule]`. **VERIFY at build time** the exact exported class names + group selector for `primeng/radiobutton` in v21 (`RadioButtonGroup` selector is `p-radiobutton-group`). If the group component is not exported in this v21 minor, fall back to a manual `[(ngModel)]` shared across individual `p-radiobutton`s bound to the same model — the CVA seam is unchanged. Flag in the PR which path was taken.
- **Aggregator:** add to `MEE_FORM`. Bump count + `MEE_UI_ALL`.
- **Test:** `radio/radio.component.spec.ts` — (1) renders one radio per option; (2) bound `FormControl` → selecting an option propagates that option's `value` via CVA; (3) `[disabled]=true` disables all rendered radios.

---

## A.3 `mee-breadcrumb` (P1)

- **Path:** `frontend/libs/ui-kit/breadcrumb/breadcrumb.component.ts`
- **Wraps:** `Breadcrumb` from `primeng/breadcrumb`
- **CVA:** NO.
- **Semantic type:** reuse **`MeeMenuItem`** from `../menu/menu.types` (label + optional `icon: MeeIconName` + `routerLink`). Do NOT introduce a new breadcrumb-item type and do NOT expose PrimeNG `MenuItem`.
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `items` | `MeeMenuItem[]` (required) | — | trail crumbs (excluding home) |
| `home` | `MeeMenuItem \| undefined` | `undefined` | optional home crumb (icon `dashboard` typical) |

- **Output:** none (navigation via `routerLink` inside items). If a `command`-style click is needed later, add `itemClick` then.
- **MeeIconName:** YES — each `MeeMenuItem.icon` is a `MeeIconName`; map to PrimeNG MenuItem `icon` via `MEE_ICONS[item.icon]` before handing the array to `p-breadcrumb`. Mirror the resolution `mee-menu` already does.
- **Template sketch:**
```html
<p-breadcrumb [model]="pgItems()" [home]="pgHome()" />
```
where `pgItems = computed(...)` maps each `MeeMenuItem` → PrimeNG `MenuItem` (`{ label, icon: item.icon ? MEE_ICONS[item.icon] : undefined, routerLink, command }`), and `pgHome` does the same for `home()`.
- **imports:** `[Breadcrumb]` (+ `RouterModule` only if routerLink binding requires it — PrimeNG breadcrumb handles routerLink via its MenuItem model; verify whether `RouterModule` import is needed for the link to activate).
- **Aggregator:** add a **new group `MEE_NAV`** OR place in `MEE_COMMON`. **Decision:** place in `MEE_COMMON` (general-purpose chrome, same as `mee-menu`). Bump `MEE_COMMON` 4→5 and `MEE_UI_ALL`. (Avoid proliferating groups; menu already lives in COMMON.)
- **Test:** `breadcrumb/breadcrumb.component.spec.ts` — (1) creates with `items` only; (2) `MeeMenuItem.icon` semantic name is resolved to the registry `pi pi-*` class in the model passed to `p-breadcrumb`; (3) `home` input renders the home crumb.

---

## A.4 `mee-tabs` (P1)

- **Path:** `frontend/libs/ui-kit/tabs/tabs.component.ts`
- **Wraps:** `Tabs, TabList, Tab, TabPanels, TabPanel` from `primeng/tabs` (the v18+ API; **`p-tabview` is removed in v21**).
- **CVA:** NO (controlled via `value` two-way model).
- **Semantic type:** new `MeeTab` in `frontend/libs/ui-kit/tabs/tabs.types.ts`:
```ts
export interface MeeTab {
  /** Stable value/key for this tab (drives the active model). */
  value: string | number;
  /** Visible header label. */
  label: string;
  /** Optional semantic icon for the tab header. */
  icon?: MeeIconName;
  /** Disable the tab header. */
  disabled?: boolean;
}
```
- **Design decision:** content projection via named slots is awkward for a dynamic tab list. Ship a **declarative-header + projected-body** model: header list comes from `tabs` input; body is projected with one `<ng-template>` per tab matched by value. To keep it simple and OnPush-friendly, the component renders the `TabList` from `tabs()` and a `TabPanels` whose `TabPanel`s the consumer supplies via content projection keyed by `[value]`. **Recommended concrete shape:** consumer writes `mee-tab-panel` children. To avoid building a second child component this wave, the simpler accepted shape is: consumer passes `tabs` (headers) and projects panel bodies using PrimeNG's own `p-tabpanel` inside `<mee-tabs>` via `ng-content`. Builder picks the cleaner of the two and documents it in the PR; the input/output surface below is fixed regardless.
- **`@Input()` / model surface:**

| member | type | default | notes |
|---|---|---|---|
| `tabs` | `MeeTab[]` (required) | — | header definitions |
| `value` | `model<string \| number>` | first tab value | two-way active-tab model |
| `scrollable` | `boolean` | `false` | passes to `p-tablist` |

- **Output:** `value` is a two-way `model()`; add `valueChange` is implicit via `model`. Optionally `tabChange = output<string|number>()`.
- **MeeIconName:** YES — `MeeTab.icon` resolved via `MEE_ICONS`.
- **Template sketch:**
```html
<p-tabs [(value)]="value()" [scrollable]="scrollable()">
  <p-tablist>
    @for (t of tabs(); track t.value) {
      <p-tab [value]="t.value" [disabled]="t.disabled ?? false">
        @if (t.icon) { <i [class]="resolveIcon(t.icon)" aria-hidden="true" class="mr-2"></i> }
        {{ t.label }}
      </p-tab>
    }
  </p-tablist>
  <p-tabpanels>
    <ng-content></ng-content>
  </p-tabpanels>
</p-tabs>
```
Consumer supplies `<p-tabpanel [value]="...">` bodies via projection (documented usage). **VERIFY** `[(value)]` works on a signal `model()` binding in the template; if not, bind `[value]` + `(valueChange)`.
- **imports:** `[Tabs, TabList, Tab, TabPanels, TabPanel]`.
- **Aggregator:** add to `MEE_DATA` (presentation/navigation primitive — same group as `steps`). Bump `MEE_DATA` 2→3 and `MEE_UI_ALL`.
- **Test:** `tabs/tabs.component.spec.ts` — (1) renders one `p-tab` per `tabs` entry; (2) default `value` is the first tab's value; (3) `MeeTab.icon` resolves to a registry `pi pi-*` class in the rendered header.

---

## A.5 `mee-message` (P1) — INLINE message, NOT toast

- **Path:** `frontend/libs/ui-kit/message/message.component.ts`
- **Wraps:** `Message` from `primeng/message`
- **CVA:** NO.
- **Purpose:** field/section-level inline messaging. Distinct from `mee-toast` (transient overlay) and the page-level `alert-banner` composite. Pairs with the `validation.*.missing` i18n fallback work.
- **Semantic type:** new `MeeMessageSeverity = 'success' | 'info' | 'warn' | 'error'` in `frontend/libs/ui-kit/message/message.types.ts`. Map `'error' → 'error'`, `'warn' → 'warn'`, etc. to PrimeNG's `severity` (PrimeNG Message uses `'success'|'info'|'warn'|'error'|'secondary'|'contrast'`). Keep MeeSell surface to the 4 semantic values.
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `severity` | `MeeMessageSeverity` | `'info'` | maps to PrimeNG `severity` |
| `text` | `string \| undefined` | `undefined` | message body (also accept projected content via `ng-content`) |
| `icon` | `MeeIconName \| undefined` | `undefined` | optional leading icon override |
| `closable` | `boolean` | `false` | show dismiss control |
| `variant` | `'outlined' \| 'simple' \| undefined` | `undefined` | passthrough to PrimeNG `variant` |

- **Output:** `closed = output<void>()` (emit on dismiss).
- **MeeIconName:** optional via `icon` input → `MEE_ICONS`.
- **Template sketch:**
```html
<p-message
  [severity]="pgSeverity()"
  [closable]="closable()"
  [icon]="icon() ? resolveIcon(icon()!) : undefined"
  [variant]="variant()"
  (onClose)="closed.emit()"
>
  @if (text()) { {{ text() }} } @else { <ng-content></ng-content> }
</p-message>
```
- **imports:** `[Message]`. `pgSeverity = computed()` maps the 4 semantic values to PrimeNG's (`'error'` stays `'error'`, `'warn'` stays `'warn'`).
- **Aggregator:** add to `MEE_FEEDBACK` (notification/status indicators — same group as `toast`/`badge`). Bump `MEE_FEEDBACK` 5→6 and `MEE_UI_ALL`.
- **Test:** `message/message.component.spec.ts` — (1) renders with default `severity='info'`; (2) `severity='error'` maps to PrimeNG `'error'`; (3) `closable=true` + dismiss emits `closed`.

---

## A.6 `mee-panel` (P2) — theming already done

- **Path:** `frontend/libs/ui-kit/panel/panel.component.ts`
- **Wraps:** `Panel` from `primeng/panel`
- **CVA:** NO.
- **Note:** `components.panel.root.borderRadius: '16px'` is ALREADY in `MeeSellPreset` — no theme work needed, just the component.
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `header` | `string \| undefined` | `undefined` | panel header text |
| `toggleable` | `boolean` | `false` | collapsible |
| `collapsed` | `model<boolean>` | `false` | two-way collapse state |
| `icon` | `MeeIconName \| undefined` | `undefined` | optional header icon |

- **Output:** `collapsed` two-way model covers state. Optionally `toggled = output<boolean>()`.
- **MeeIconName:** optional header icon via `MEE_ICONS`.
- **Template sketch:**
```html
<p-panel [header]="header()" [toggleable]="toggleable()" [(collapsed)]="collapsed()">
  @if (icon()) {
    <ng-template #header>
      <span class="flex items-center gap-2">
        <i [class]="resolveIcon(icon()!)" aria-hidden="true"></i>{{ header() }}
      </span>
    </ng-template>
  }
  <ng-content></ng-content>
</p-panel>
```
(If `icon` is set, use the header template; else the plain `[header]` text. Builder simplifies if `[(collapsed)]` on a `model()` needs `[collapsed]`+`(collapsedChange)`.)
- **imports:** `[Panel]`.
- **Aggregator:** **create new `MEE_LAYOUT`** array in `aggregators.ts` for layout-surface primitives (panel, divider, scroll-panel). Per the existing aggregators.ts comment, `MEE_LAYOUT` was reserved for `@mesell/layout` page primitives — but those are a SEPARATE library. To avoid confusion, name this ui-kit group **`MEE_SURFACE`** (panel, divider, scroll-panel) and add a header comment clarifying it is the ui-kit surface/layout-utility group, distinct from `@mesell/layout`'s `MEE_LAYOUT`. Add `MEE_SURFACE` to `MEE_UI_ALL` and bump the total.
- **Test:** `panel/panel.component.spec.ts` — (1) renders with `header`; (2) projected content shows inside the panel body; (3) `toggleable=true` + toggle flips `collapsed` model.

---

## A.7 `mee-divider` (P2)

- **Path:** `frontend/libs/ui-kit/divider/divider.component.ts`
- **Wraps:** `Divider` from `primeng/divider`
- **CVA:** NO.
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `layout` | `'horizontal' \| 'vertical'` | `'horizontal'` | passthrough |
| `align` | `'left' \| 'center' \| 'right' \| 'top' \| 'bottom' \| undefined` | `undefined` | content alignment |
| `type` | `'solid' \| 'dashed' \| 'dotted'` | `'solid'` | line style |

- **Output:** none.
- **MeeIconName:** none.
- **Template sketch:**
```html
<p-divider [layout]="layout()" [align]="align()" [type]="type()">
  <ng-content></ng-content>
</p-divider>
```
- **imports:** `[Divider]`.
- **Aggregator:** add to `MEE_SURFACE` (created in A.6).
- **Test:** `divider/divider.component.spec.ts` — (1) renders horizontal by default; (2) `layout='vertical'` passes through; (3) projected label content renders between the rules.

---

## A.8 `mee-scroll-panel` (P2)

- **Path:** `frontend/libs/ui-kit/scroll-panel/scroll-panel.component.ts`
- **Wraps:** `ScrollPanel` from `primeng/scrollpanel`
- **CVA:** NO.
- **`@Input()` surface:**

| input | type | default | notes |
|---|---|---|---|
| `maxHeight` | `string` | `'100%'` | applied as inline `style` height/max-height on the panel |
| `styleClass` | `string \| undefined` | `undefined` | passthrough |

- **Output:** none.
- **MeeIconName:** none.
- **Template sketch:**
```html
<p-scrollpanel [style]="{ height: maxHeight(), width: '100%' }" [styleClass]="styleClass()">
  <ng-content></ng-content>
</p-scrollpanel>
```
- **imports:** `[ScrollPanel]`.
- **Aggregator:** add to `MEE_SURFACE` (created in A.6).
- **Test:** `scroll-panel/scroll-panel.component.spec.ts` — (1) renders with default `maxHeight='100%'`; (2) `maxHeight='300px'` applies to the inline style; (3) projected content renders inside the scroll region.

---

## A.9 Barrel + aggregator updates (do once, after all components exist)

In `frontend/libs/ui-kit/index.ts`:
- Add 8 `export { MeeXxxComponent } from './xxx/xxx.component';` lines.
- Add type exports: `MeeTab` (tabs.types), `MeeMessageSeverity` (message.types). Breadcrumb reuses `MeeMenuItem` (already exported).
- Keep the existing comment-section grouping (Components / Types / Aggregators).

In `frontend/libs/ui-kit/aggregators.ts`:
- `MEE_FORM`: + `MeeCheckboxComponent`, `MeeRadioComponent` (6→8).
- `MEE_COMMON`: + `MeeBreadcrumbComponent` (4→5).
- `MEE_DATA`: + `MeeTabsComponent` (2→3).
- `MEE_FEEDBACK`: + `MeeMessageComponent` (5→6).
- **NEW `MEE_SURFACE`**: `MeePanelComponent`, `MeeDividerComponent`, `MeeScrollPanelComponent` (3).
- `MEE_UI_ALL`: spread MEE_SURFACE in; update total **21 → 29** (21 + 8 new) and the coverage comment math (6+3+5+2+4+1 → 8+3+6+3+5+1+3).
- Update the file's header doc COVERAGE block and the "21 component classes" prose to 29.
- `aggregators.spec.ts` exists — update any hard-coded counts/assertions there to 29 / new group.

---

# SECTION B — for `meesell-angular-ui-styler` (focus-ring token group, P0)

This is a TOKEN + THEME + GLOBAL CSS change. No component, no spec file (verify visually).

## B.1 Add tokens to `frontend/libs/design-tokens/_tokens.css`

Add a new block inside `:root` (group with a `/* Focus ring */` comment near the Border block):
```css
  /* Focus ring (a11y — brand-orange, explicit, swap-proof) */
  --mee-focus-ring-width:  2px;
  --mee-focus-ring-style:  solid;
  --mee-focus-ring-color:  rgba(242, 107, 35, 0.5);  /* primary #F26B23 at 50% */
  --mee-focus-ring-offset: 2px;
```

## B.2 Project into `MeeSellPreset` — `frontend/libs/ui-kit/theme.ts`

Add a `focusRing` block under `semantic` (sibling to `primary` / `colorScheme`). PrimeNG/Aura consumes `semantic.focusRing.{width,style,color,offset,shadow}` and emits `--p-focus-ring-*` design variables. Map the `--mee-*` tokens in so PrimeNG focus rings inherit MeeSell's:
```ts
  semantic: {
    primary: { /* …unchanged… */ },
    focusRing: {
      width:  'var(--mee-focus-ring-width)',
      style:  'var(--mee-focus-ring-style)',
      color:  'var(--mee-focus-ring-color)',
      offset: 'var(--mee-focus-ring-offset)',
      shadow: 'none',
    },
    colorScheme: { /* …unchanged… */ },
  },
```
**VERIFY** at build time that `@primeuix/themes` Aura accepts `semantic.focusRing` in this version (2.0.3). If the key path differs (e.g. nested under `colorScheme`), place it where Aura's schema expects and keep the `var(--mee-focus-ring-*)` mapping. Build must stay green; the goal is `--p-focus-ring-*` resolving to the `--mee-*` values.

## B.3 Wire a global `:focus-visible` for non-PrimeNG elements — `frontend/apps/shell/src/styles.css`

PrimeNG primitives get their ring from the preset (B.2). Native/non-PrimeNG focusable elements (raw `<a>`, custom clickable divs, skip-links) need a global rule. Add, inside the appropriate `@layer base` context (so utilities can still override):
```css
/* A11y: explicit brand focus ring for non-PrimeNG focusable elements.
   PrimeNG components inherit the ring via MeeSellPreset semantic.focusRing. */
:focus-visible {
  outline: var(--mee-focus-ring-width) var(--mee-focus-ring-style) var(--mee-focus-ring-color);
  outline-offset: var(--mee-focus-ring-offset);
}
```
Place it after the Tailwind/`@layer` declarations so it lands in (or after) `base` but does not get stripped. **VERIFY** it does not double-ring PrimeNG components (which may also paint `:focus-visible`); if doubling occurs, scope the global rule to exclude PrimeNG roots or rely on PrimeNG's own outline reset — document the resolution in the PR.

## B.4 Test / verification

- **No unit test** (token + global CSS change).
- Verify via: (1) `pnpm build` green; (2) keyboard-tab through a P0 route (`/login`, `/dashboard`, `/catalogs/new`) and confirm a visible brand-orange 2px ring on inputs, buttons, links, checkboxes, radios; (3) screenshots at 360px + 1280px with a focused control visible; (4) contrast check — `rgba(242,107,35,0.5)` ring against white + light-grey surfaces meets the non-text 3:1 WCAG 1.4.11 threshold (note the composited color in the PR).

---

## C. Merge-gate evidence the Lead requires (HYBRID step 3)

The specialist PR (`feat/ui-kit-sakai-gaps` → integration) must carry, in `.github/PULL_REQUEST_TEMPLATE/frontend.md`:
- All template sections filled, no `<placeholder>` left.
- `pnpm build` evidence < 90s + bundle delta (these are lazy ui-kit additions — initial bundle should NOT grow; confirm the new wrappers do not leak into the initial chunk via a barrel-at-root import, per the known 1MB-budget landmine).
- Test count delta: baseline + ~24 new tests (8 components × 3 cases) all green; **no DROP** in discovered specs (the `../apps`/`../libs` discovery-glob gotcha).
- Screenshots at 360px AND 1280px for each new visible component + a focused-control shot for the ring.
- A11y confirmation: keyboard nav reaches checkbox/radio/tabs/breadcrumb; the focus ring is visible; `aria-hidden` on decorative icons; checkbox/radio labels are clickable (`for`/`id`).
- Boundary check: `grep -rn "from 'primeng" frontend/libs | grep -v libs/ui-kit/` returns ZERO (PrimeNG stays sealed in ui-kit).
- Aggregator/barrel counts updated to 29 and `aggregators.spec.ts` green.

---

## D. Ambiguities / blockers flagged BEFORE the specialists start

1. **No dependency blocker.** `primeng@^21.1.9`, `@primeuix/themes@^2.0.3`, `primeicons@7.0.0` already in root `package.json`. Zero installs. All 8 PrimeNG subpaths verified present in `node_modules/primeng` exports.
2. **`p-tabview` is GONE in v21** — `mee-tabs` MUST use the new `Tabs/TabList/Tab/TabPanels/TabPanel` API from `primeng/tabs`. The upgrade-path doc's "p-tabs/p-tabview" wording is stale; build against `p-tabs`.
3. **`RadioButtonGroup` export uncertainty** — verify `primeng/radiobutton` exports `RadioButtonGroup` (selector `p-radiobutton-group`) in 21.1.9; fallback (shared ngModel across individual radios) documented in A.2. Not a blocker, a build-time verify.
4. **`semantic.focusRing` schema location** in `@primeuix/themes` 2.0.3 — verify the exact key path Aura expects (B.2). Not a blocker; the `--mee-*` mapping is the fixed requirement, placement is build-time-verified.
5. **`MEE_SURFACE` vs `MEE_LAYOUT` naming** — the existing `aggregators.ts` reserves `MEE_LAYOUT` for the separate `@mesell/layout` library. To avoid a name collision, this spec names the new ui-kit surface group **`MEE_SURFACE`**. Lead's decision; if the founder/styler prefers a different name, it is cosmetic — confirm before merge.
6. **`mee-tabs` content-projection shape** is the one genuinely open design call (declarative headers + projected `p-tabpanel` bodies). The input/output surface is fixed; the builder picks the cleaner projection mechanism and documents it. If the builder finds a child `mee-tab-panel` component is unavoidable for OnPush correctness, that is an acceptable +1 component — flag it in the PR (it would NOT be a barrel/aggregator surprise; add it to `MEE_DATA`).
7. **Scope note:** `mee-scroll-panel` is built here despite being P3-DEFER in the upgrade-path doc (§0). If the founder prefers to honor the original DEFER, drop A.8 — it is fully self-contained and removable without affecting the other 7.
