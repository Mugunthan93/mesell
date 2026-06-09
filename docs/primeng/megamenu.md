# MegaMenu

**Import:** `import { MegaMenu } from 'primeng/megamenu'`
**Selector:** `p-megaMenu`, `p-megamenu`, `p-mega-menu`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MegaMenuItem[]` | undefined | Array of menu items (with nested sub-columns) |
| orientation | `'horizontal' \| 'vertical'` | `'horizontal'` | Menu orientation |
| id | `string \| undefined` | undefined | Component ID |
| styleClass | `string \| undefined` | undefined | CSS class |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| breakpoint | `string` | — | Responsive breakpoint for vertical collapse |
| scrollHeight | `string` | — | Scroll height for overflow |
| disabled | `boolean` | false | Disables the component |
| tabindex | `number` | undefined | Tab index |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when sub-menu shows |
| onHide | `EventEmitter<any>` | Emitted when sub-menu hides |

## Usage Example (from Sakai-ng)

```html
<p-megamenu [model]="megaMenuItems" />

<p-megamenu [model]="megaMenuItems" orientation="vertical" />
```

## Notes

- `model` uses `MegaMenuItem[]` — items can have `items: MegaMenuItem[][]` for column sub-menus.
- For simple navigation, `p-menubar` is simpler. `p-megamenu` supports multi-column dropdowns.
