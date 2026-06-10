# Tabs

**Import:** `import { Tabs, TabList, Tab, TabPanels, TabPanel } from 'primeng/tabs'`
**Selector:** `p-tabs` (root), `p-tablist`, `p-tab`, `p-tabpanels`, `p-tabpanel`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Composable API (introduced in PrimeNG v18+). Replaces the deprecated `p-tabView` / `p-tabPanel` pattern.

## Tabs @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | (signal) `string \| number \| undefined` | undefined | Active tab value — two-way model signal |
| scrollable | (signal) `boolean` | false | Enable scroll navigation for many tabs |
| lazy | (signal) `boolean` | false | Lazy-load tab panel content |
| selectOnFocus | (signal) `boolean` | true | Auto-select tab when focused via keyboard |
| showNavigators | (signal) `boolean` | true | Show scroll navigation arrows when scrollable |
| tabindex | (signal) `number` | 0 | Tab index |

## Tab @Input() Props

| Prop | Type | Description |
|------|------|-------------|
| value | (signal) `string \| number \| undefined` | This tab's identifier value |
| disabled | (signal) `boolean` | Disables this tab |

## TabPanel @Input() Props

| Prop | Type | Description |
|------|------|-------------|
| value | (signal) `string \| number \| undefined` | Matches corresponding `Tab` value |
| lazy | (signal) `boolean` | Lazy render panel content |

## Usage Example (from Sakai-ng)

```html
<p-tabs [(value)]="activeTab">
  <p-tablist>
    <p-tab value="overview">Overview</p-tab>
    <p-tab value="images">Images</p-tab>
    <p-tab value="pricing" [disabled]="!catalogReady()">Pricing</p-tab>
  </p-tablist>
  <p-tabpanels>
    <p-tabpanel value="overview">
      <div class="p-4">Overview content</div>
    </p-tabpanel>
    <p-tabpanel value="images">
      <div class="p-4">Images content</div>
    </p-tabpanel>
    <p-tabpanel value="pricing">
      <div class="p-4">Pricing content</div>
    </p-tabpanel>
  </p-tabpanels>
</p-tabs>

<!-- In component -->
activeTab = signal<string>('overview');
```

## Notes

- All `Tab` values and their corresponding `TabPanel` values must match.
- Signal two-way binding: `[(value)]="activeTab"` where `activeTab` is a `signal<string|number>`.
- If using a plain variable: split to `[value]="activeTab()"` + `(valueChange)="activeTab.set($event)"`.
- `lazy="true"` on a `TabPanel` renders its content only when first activated — use for heavy panels.
- Do not use the old `p-tabView` / `p-tabPanel` pattern — these are deprecated.
