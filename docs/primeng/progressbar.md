# ProgressBar

**Import:** `import { ProgressBar } from 'primeng/progressbar'`
**Selector:** `p-progressBar`, `p-progressbar`, `p-progress-bar`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `number \| undefined` | undefined | Current value (0–100) |
| showValue | `boolean` | true | Display the percentage text |
| mode | `'determinate' \| 'indeterminate'` | `'determinate'` | Progress mode |
| unit | `string` | `'%'` | Unit sign appended to the value |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` instead |
| valueStyleClass | `string \| undefined` | undefined | CSS class for the value bar |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| valueChange | `EventEmitter<number>` | Emitted when value changes |

## Usage Example (from Sakai-ng)

```html
<!-- Determinate with value display -->
<p-progressbar [value]="value" [showValue]="true"></p-progressbar>

<!-- Without value display -->
<p-progressbar [value]="50" [showValue]="false"></p-progressbar>

<!-- Inline in a table cell -->
<p-progressbar [value]="customer.activity" [showValue]="false" [style]="{ height: '0.5rem' }"></p-progressbar>

<!-- Indeterminate loading indicator -->
<p-progressbar mode="indeterminate" [style]="{ height: '4px' }"></p-progressbar>
```

## Notes

- `mode="indeterminate"` shows an animated bar without a specific value (for unknown duration operations).
- Use `[style]="{ height: '4px' }"` to create a thin line progress indicator.
