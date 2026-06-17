# @mesell/layout

MeeSell layout-primitive library — page containers, section wrappers, toolbars, grid/stack, form columns. All primitives are standalone Angular 18 components (`OnPush`, signal inputs, content projection). Zero PrimeNG dependency.

Import path: `@mesell/layout` (barrel root only — never a subpath).

---

## Primitives

Phase 3 ships six page primitives. Chrome primitives (`mee-app-bar`, `mee-side-nav`, etc.) land in Phase 4.

| Component | Selector | Purpose |
|-----------|----------|---------|
| `MeePageComponent` | `mee-page` | Top-level routed-page container (max-width, padding, vertical gap) |
| `MeeSectionComponent` | `mee-section` | Titled content section (`<h2>` + description + body) |
| `MeeToolbarComponent` | `mee-toolbar` | Horizontal action bar with start + end slots |
| `MeeGridComponent` | `mee-grid` | Responsive 2-D card/tile grid (auto-fill or fixed cols) |
| `MeeStackComponent` | `mee-stack` | 1-D flex line with token-driven gap |
| `MeeFormLayoutComponent` | `mee-form-layout` | Vertical form field column (full-width children, reading-width cap) |

---

## `MEE_LAYOUT` spread pattern

Import the aggregator and spread it into any standalone component's `imports` array:

```ts
import { Component } from '@angular/core';
import { MEE_LAYOUT }  from '@mesell/layout';
import { MEE_FORM }    from '@mesell/ui-kit';

@Component({
  selector: 'app-catalog-form',
  standalone: true,
  imports: [...MEE_LAYOUT, ...MEE_FORM],
  template: `
    <mee-page maxWidth="lg" gap="lg">
      <mee-section heading="Catalog details">
        <mee-form-layout gap="lg" maxWidth="md">
          <mee-input label="Product name" formControlName="name" />
          <mee-select label="Category"    formControlName="category" />
        </mee-form-layout>
      </mee-section>
    </mee-page>
  `,
})
export class CatalogFormComponent {}
```

---

## `MeeLayoutGap` scale

All layout primitives share the same gap scale backed by design tokens:

| `MeeLayoutGap` | Token | Computed value |
|----------------|-------|---------------|
| `'none'` | — | `0` |
| `'xs'`   | `--mee-space-1` | `4px` |
| `'sm'`   | `--mee-space-2` | `8px` |
| `'md'`   | `--mee-space-4` | `16px` |
| `'lg'`   | `--mee-space-6` | `24px` |
| `'xl'`   | `--mee-space-8` | `32px` |

Gap values are applied via `[style.gap]` bound to `var(--mee-space-N)` — no hard-coded `px` values.

---

## Usage snippets

### `mee-page` — page container

```html
<!-- Default: lg max-width, padding on, lg vertical gap between sections -->
<mee-page maxWidth="lg" [padding]="true" gap="lg">
  <mee-section heading="Dashboard">
    ...
  </mee-section>
</mee-page>

<!-- Full-width, no padding (e.g. hero or image canvas) -->
<mee-page maxWidth="full" [padding]="false" gap="md">
  ...
</mee-page>
```

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `maxWidth` | `'sm'\|'md'\|'lg'\|'xl'\|'full'` | `'lg'` | Max readable width of the page column |
| `padding` | `boolean` | `true` | Responsive horizontal + vertical padding (`px-4 py-6 sm:px-6 lg:px-8`) |
| `gap` | `MeeLayoutGap` | `'lg'` | Vertical gap between projected child blocks |

---

### `mee-section` — titled content section

```html
<!-- With heading and description -->
<mee-section heading="Recent catalogs" description="Your last 20 listings" gap="md">
  <mee-grid [cols]="3" gap="md">
    ...
  </mee-grid>
</mee-section>

<!-- Body-only (no heading) — heading and description are conditional -->
<mee-section gap="sm">
  <p>Some content</p>
</mee-section>
```

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `heading` | `string \| undefined` | `undefined` | Section heading; renders `<h2>` only when set |
| `description` | `string \| undefined` | `undefined` | Optional paragraph under the heading |
| `gap` | `MeeLayoutGap` | `'md'` | Gap between header block and projected body |

---

### `mee-toolbar` — horizontal action bar

Default `<ng-content />` = start (leading) region. Elements with `[mee-toolbar-end]` = end (trailing) region, pushed right. Wraps on small screens (mobile-first).

```html
<mee-toolbar gap="sm" align="center">
  <!-- Start slot (default) -->
  <h2 class="text-lg font-semibold">Catalog list</h2>

  <!-- End slot -->
  <div mee-toolbar-end class="flex gap-2">
    <mee-button label="Filter"      variant="ghost" />
    <mee-button label="New catalog" variant="primary" />
  </div>
</mee-toolbar>
```

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `gap` | `MeeLayoutGap` | `'sm'` | Gap between toolbar items |
| `align` | `'start'\|'center'\|'end'` | `'center'` | Cross-axis alignment (`items-*`) |

---

### `mee-grid` — responsive 2-D grid

```html
<!-- Auto-fill: browser fills as many columns as fit at ≥ 16rem each -->
<mee-grid cols="auto" minItemWidth="16rem" gap="md">
  @for (cat of categories; track cat.id) {
    <app-category-card [category]="cat" />
  }
</mee-grid>

<!-- Fixed 3 columns at md+, collapses to 1 on mobile -->
<mee-grid [cols]="3" gap="md">
  @for (c of catalogs; track c.id) {
    <mee-catalog-card [catalog]="c" />
  }
</mee-grid>
```

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `cols` | `'auto'\|1\|2\|3\|4` | `'auto'` | Column count; `'auto'` uses auto-fill |
| `minItemWidth` | `string` | `'16rem'` | Min item width for `cols='auto'` |
| `gap` | `MeeLayoutGap` | `'md'` | Grid gap (row + column) |

---

### `mee-stack` — 1-D flex line

```html
<!-- Vertical stack of form fields -->
<mee-stack direction="vertical" gap="md">
  <mee-input label="Name" />
  <mee-input label="Phone" />
</mee-stack>

<!-- Horizontal row of actions, spread apart -->
<mee-stack direction="horizontal" gap="sm" justify="between">
  <span class="text-sm text-muted">3 items selected</span>
  <mee-button label="Delete" variant="danger" />
</mee-stack>
```

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `direction` | `'vertical'\|'horizontal'` | `'vertical'` | Flex axis |
| `gap` | `MeeLayoutGap` | `'md'` | Gap between children |
| `align` | `'start'\|'center'\|'end'\|'stretch'` | `'stretch'` | Cross-axis alignment |
| `justify` | `'start'\|'center'\|'end'\|'between'` | `'start'` | Main-axis justification |
| `wrap` | `boolean` | `false` | Allow children to wrap |

---

### `mee-form-layout` — vertical form field column

Use instead of a bare `mee-stack` for forms: encodes form defaults (full-width children, reading-width cap, larger gap) so you do not re-derive them per form.

```html
<mee-form-layout gap="lg" maxWidth="md">
  <mee-input     label="Product name" formControlName="name" />
  <mee-input     label="MRP (₹)"      formControlName="mrp" />
  <mee-select    label="Category"     formControlName="category" [options]="cats" />
  <mee-textarea  label="Description"  formControlName="description" />
</mee-form-layout>
```

**Inputs:**

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `gap` | `MeeLayoutGap` | `'lg'` | Vertical gap between fields |
| `maxWidth` | `'sm'\|'md'\|'lg'\|'full'` | `'md'` | Max width of the form column (~640px) |

---

## Composing primitives

A full page from scratch:

```html
<mee-page maxWidth="lg" gap="lg">

  <!-- Toolbar at the top of the page -->
  <mee-toolbar gap="sm">
    <h1 class="text-xl font-bold">Edit catalog</h1>
    <div mee-toolbar-end>
      <mee-button label="Save" variant="primary" />
    </div>
  </mee-toolbar>

  <!-- Catalog details section -->
  <mee-section heading="Details" description="Basic product information" gap="md">
    <mee-form-layout gap="lg" maxWidth="md">
      <mee-input  label="Product name" formControlName="name" />
      <mee-select label="Category"     formControlName="category" [options]="cats" />
    </mee-form-layout>
  </mee-section>

  <!-- Image grid section -->
  <mee-section heading="Images" gap="md">
    <mee-grid cols="auto" minItemWidth="10rem" gap="sm">
      @for (img of images; track img.id) {
        <img [src]="img.url" alt="" class="rounded-md aspect-square object-cover" />
      }
    </mee-grid>
  </mee-section>

</mee-page>
```

---

## Styling notes

- All spacing is driven by `var(--mee-space-*)` design tokens from `libs/design-tokens/_tokens.css`.
- Layout is mobile-first: grids collapse to 1 column, toolbars wrap on small screens.
- No hard-coded `px` values for spacing — always a token.
- Zero PrimeNG dependency — primitives import only `@angular/core` + local types.

---

## What is NOT here

- **Chrome primitives** (`mee-app-bar`, `mee-side-nav`, `mee-nav-item`, `mee-user-menu`) — **Phase 4**.
- **MFE adoption** (changing any MFE `imports:` to use `MEE_LAYOUT`) — **Phase 6**. Primitives ship unused; Phase 6 wires real consumers.
- **Services / providers** — layout primitives are purely structural; no Angular providers.

See `docs/plans/architecture/UI_DESIGN_SYSTEM_DECOUPLING_PLAN.md` for the full phased plan.
