# TieredMenu

**Import:** `import { TieredMenu } from 'primeng/tieredmenu'`
**Selector:** `p-tieredmenu`, `p-tieredMenu`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[]` | undefined | Array of menu items (supports nested `items`) |
| popup | `boolean` | false | When true, renders as popup overlay |
| autoDisplay | `boolean` | true | Show submenus on hover (when false, requires click) |
| autoZIndex | `boolean` | true | Auto-manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| appendTo | `any` | undefined | Target for popup overlay attachment |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| tabindex | `number` | 0 | Tab index |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when menu opens (popup mode) |
| onHide | `EventEmitter<any>` | Emitted when menu closes (popup mode) |

## Usage Example

```html
<!-- Inline (static) -->
<p-tieredmenu [model]="items" />

<!-- Popup (triggered by button) -->
<p-tieredmenu #tm [model]="items" [popup]="true" />
<p-button label="Options" (onClick)="tm.toggle($event)" />

<!-- In component -->
items: MenuItem[] = [
  {
    label: 'File',
    items: [
      { label: 'New', icon: 'pi pi-plus', command: () => this.newFile() },
      { label: 'Open', icon: 'pi pi-folder-open', command: () => this.openFile() },
      {
        label: 'Export',
        items: [
          { label: 'PDF', command: () => this.exportPdf() },
          { label: 'CSV', command: () => this.exportCsv() }
        ]
      }
    ]
  }
];
```

## Notes

- Use `[popup]="true"` with `#tm` template reference and `tm.toggle($event)` for dropdown behavior.
- Supports unlimited nesting depth via `items` property on each `MenuItem`.
- `MenuItem` interface from `primeng/api` — use `label`, `icon`, `command`, `items`, `separator`, `disabled`, `visible`.
