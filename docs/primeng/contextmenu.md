# ContextMenu

**Import:** `import { ContextMenu } from 'primeng/contextmenu'`
**Selector:** `p-contextmenu`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[] \| undefined` | undefined | Array of menu items |
| triggerEvent | `string` | `'contextmenu'` | Browser event to trigger the menu |
| target | `HTMLElement \| string \| null` | undefined | Element to attach context menu to |
| global | `boolean` | false | When true, attaches to document (right-click anywhere) |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when menu shows |
| onHide | `EventEmitter<any>` | Emitted when menu hides |

## Usage Example

```html
<p-contextmenu #contextMenu [model]="menuItems"></p-contextmenu>
<div (contextmenu)="contextMenu.show($event)">Right-click me</div>
```

## Notes

- Use `#ref` to call `show($event)` and `hide()` methods programmatically.
- `MenuItem` from `'primeng/api'`.
