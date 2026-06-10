# OverlayBadge

**Import:** `import { OverlayBadge } from 'primeng/overlaybadge'`
**Selector:** `p-overlayBadge`, `p-overlay-badge`, `p-overlaybadge`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `string \| number \| null` | undefined | Badge value to display |
| severity | `'secondary' \| 'info' \| 'success' \| 'warn' \| 'danger' \| 'contrast' \| null` | undefined | Badge color severity |
| badgeSize | `'small' \| 'large' \| 'xlarge' \| null` | undefined | Badge size |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Usage Example

```html
<!-- Avatar with notification badge overlay -->
<p-overlaybadge value="3" severity="danger">
  <p-avatar image="https://example.com/user.png" shape="circle" size="large"></p-avatar>
</p-overlaybadge>

<!-- Button with badge overlay -->
<p-overlaybadge value="5" severity="info">
  <p-button icon="pi pi-bell" [rounded]="true" [outlined]="true"></p-button>
</p-overlaybadge>
```

## Notes

- Wraps any content and overlays a badge in the top-right corner.
- Unlike the `[pBadge]` directive, `OverlayBadge` works with any content via content projection.
