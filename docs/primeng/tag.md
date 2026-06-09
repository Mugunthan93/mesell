# Tag

**Import:** `import { Tag } from 'primeng/tag'`
**Selector:** `p-tag`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `string \| undefined` | undefined | Text to display inside the tag |
| severity | `'success'\|'secondary'\|'info'\|'warn'\|'danger'\|'contrast'\|null` | undefined | Color variant |
| icon | `string \| undefined` | undefined | PrimeIcon class to display before the text |
| rounded | `boolean` | false | Rounded pill shape |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Templates

| pTemplate | Purpose |
|-----------|---------|
| icon | Custom icon element |

## Usage Example (from Sakai-ng)

```html
<!-- Status badge -->
<p-tag severity="success" value="In Stock" />
<p-tag severity="danger" value="Out of Stock" />
<p-tag severity="warn" value="Pending Review" />
<p-tag severity="info" value="New" />
<p-tag severity="secondary" value="Draft" />

<!-- With icon -->
<p-tag icon="pi pi-check" severity="success" value="Approved" />

<!-- Rounded pill style -->
<p-tag [rounded]="true" severity="info" value="AI Generated" />

<!-- In a table body cell -->
<p-tag [value]="product.inventoryStatus" [severity]="getSeverity(product)" />
```

## Notes

- `severity` maps to the PrimeNG color palette: `success`=green, `info`=blue, `warn`=orange, `danger`=red, `secondary`=grey, `contrast`=inverted.
- For dynamic severity: `[severity]="product.active ? 'success' : 'danger'"`.
- `p-badge` is the numeric badge (attaches to other elements); `p-tag` is the standalone label chip.
