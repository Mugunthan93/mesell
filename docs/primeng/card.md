# Card

**Import:** `import { Card } from 'primeng/card'`
**Selector:** `p-card`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| header | `string \| undefined` | undefined | Header text of the card |
| subheader | `string \| undefined` | undefined | Subheader text below the header |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` attribute instead |

## @Output() Events

None.

## Key Templates

| Template | Description |
|----------|-------------|
| `#headerTemplate` or `ng-template pTemplate="header"` | Custom header slot |
| `#titleTemplate` | Custom title slot |
| `#subtitleTemplate` | Custom subtitle slot |
| `#contentTemplate` | Custom content slot |
| `#footerTemplate` | Custom footer slot |

## Usage Example (from Sakai-ng)

```html
<!-- Simple card with header and subheader props -->
<p-card [header]="event.status" [subheader]="event.date">
  <p>Card content goes here.</p>
</p-card>

<!-- Card with custom footer template -->
<p-card header="Product Details">
  <p>Main content area.</p>
  <ng-template pTemplate="footer">
    <p-button label="View Details"></p-button>
  </ng-template>
</p-card>
```

## Notes

- Content projection via `ng-content` (the default slot) is the simplest way to add body content.
- For rich header/footer, use `pTemplate` named slots.
- Implements `BlockableUI` — compatible with `p-blockui` overlay.
