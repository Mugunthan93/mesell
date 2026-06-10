# Dock

**Import:** `import { Dock } from 'primeng/dock'`
**Selector:** `p-dock`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[]` | undefined | Array of menu items |
| position | `'bottom' \| 'top' \| 'left' \| 'right'` | `'bottom'` | Position of the dock |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| tooltipOptions | `DockTooltipOptions` | undefined | Options for tooltip display |
| magnification | `boolean` | true | Whether to magnify items on hover |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onClick | `EventEmitter<any>` | Emitted when an item is clicked |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |

## Usage Example

```html
<p-dock [model]="dockItems" position="bottom">
  <ng-template pTemplate="item" let-item>
    <img [src]="item.icon" [alt]="item.label" width="100%" />
  </ng-template>
</p-dock>
```

## Notes

- macOS dock-style component with hover magnification.
- `model` uses `MenuItem[]` from `'primeng/api'`.
- Use `pTemplate="item"` for custom item rendering.
