# Accordion

**Import:** `import { Accordion, AccordionPanel, AccordionHeader, AccordionContent } from 'primeng/accordion'`
**Selector:** `p-accordion` (container), `p-accordion-panel` / `p-accordionpanel`, `p-accordion-header` / `p-accordionheader`, `p-accordion-content` / `p-accordioncontent`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props — `<p-accordion>`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `string \| number \| string[] \| number[] \| null` | undefined | Value(s) of the active panel(s); two-way binding via `[(value)]` |
| multiple | `boolean` | false | When enabled, multiple panels can be active simultaneously |

## @Input() Props — `<p-accordion-panel>`

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `string \| number` | undefined | Unique value identifying this panel; two-way via `[(value)]` |
| disabled | `boolean` | false | Disables the panel when enabled |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| valueChange (on accordion) | `EventEmitter<...>` | Emitted when active value changes (two-way binding) |

## Usage Example (from Sakai-ng)

```html
<p-accordion value="0">
  <p-accordion-panel value="0">
    <p-accordion-header>Header I</p-accordion-header>
    <p-accordion-content>
      <p>Content for panel 1.</p>
    </p-accordion-content>
  </p-accordion-panel>
  <p-accordion-panel value="1">
    <p-accordion-header>Header II</p-accordion-header>
    <p-accordion-content>
      <p>Content for panel 2.</p>
    </p-accordion-content>
  </p-accordion-panel>
</p-accordion>
```

## Notes

- PrimeNG 21 uses a **composable** API: `Accordion` + `AccordionPanel` + `AccordionHeader` + `AccordionContent` (NOT the old `p-accordionTab` pattern).
- Import all four classes: `Accordion`, `AccordionPanel`, `AccordionHeader`, `AccordionContent` from `'primeng/accordion'`.
- `[(value)]` on `<p-accordion>` controls which panel is open.
- For multiple open panels, add `[multiple]="true"` and bind `[(value)]` to an array.
