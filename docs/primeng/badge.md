# Badge

**Import:** `import { Badge } from 'primeng/badge'` (component) or `import { BadgeDirective } from 'primeng/badge'` (directive)
**Selector:** `p-badge` (component) or `[pBadge]` (directive on another element)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Two usages: `<p-badge>` standalone component, or `[pBadge]` directive on an icon/button.

## @Input() Props — `<p-badge>` component

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `string \| number \| null` | undefined | Value displayed inside the badge |
| severity | `'secondary' \| 'info' \| 'success' \| 'warn' \| 'danger' \| 'contrast' \| null` | undefined | Color severity of the badge |
| badgeSize | `'small' \| 'large' \| 'xlarge' \| null` | undefined | Size of the badge |
| size | `'small' \| 'large' \| 'xlarge' \| null` | undefined | **Deprecated.** Use `badgeSize` instead |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Input() Props — `[pBadge]` directive

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| pBadge | — | — | Applied as attribute selector |
| value | `string \| number` | — | Badge value |
| severity | see above | undefined | Severity color |
| badgeSize | see above | undefined | Size |
| disabled | `boolean` | false | Hides the badge when true |
| badgeStyle | `object` | — | Inline style |
| badgeStyleClass | `string` | — | CSS class for badge |

## @Output() Events

None.

## Usage Example (from Sakai-ng)

```html
<!-- Standalone badge component -->
<p-badge value="2"></p-badge>
<p-badge value="8" severity="success"></p-badge>
<p-badge value="4" severity="info"></p-badge>
<p-badge value="12" severity="warn"></p-badge>
<p-badge value="3" severity="danger"></p-badge>

<!-- Sized badges -->
<p-badge [value]="2"></p-badge>
<p-badge [value]="4" badgeSize="large" severity="warn"></p-badge>
<p-badge [value]="6" badgeSize="xlarge" severity="success"></p-badge>
```

## Notes

- Use standalone `<p-badge>` for inline display.
- Use `[pBadge]` directive on `<i>`, `<p-button>`, or icons to overlay a badge on them.
- The `BadgeModule` covers both `Badge` component and `BadgeDirective`.
