# Menu

**Import:** `import { Menu } from 'primeng/menu'`
**Selector:** `p-menu`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[] \| undefined` | undefined | Array of menu items |
| popup | `boolean \| undefined` | false | Display as a popup (trigger via `toggle($event)`) |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| appendTo | `any` | undefined | Target element for overlay attachment |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when popup shows |
| onHide | `EventEmitter<any>` | Emitted when popup hides |

## Usage Example (from Sakai-ng)

```html
<!-- Inline menu -->
<p-menu [model]="menuItems"></p-menu>

<!-- Popup menu triggered by button -->
<p-menu #menu [popup]="true" [model]="overlayMenuItems"></p-menu>
<p-button label="Options" icon="pi pi-angle-down" (onClick)="menu.toggle($event)"></p-button>
```

## Notes

- For popup mode: use `#menu` template reference and call `menu.toggle($event)` from a trigger.
- `MenuItem` from `'primeng/api'`.
- For grouped menus: use nested `items` arrays inside `MenuItem`.
