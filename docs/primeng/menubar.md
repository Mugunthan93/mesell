# Menubar

**Import:** `import { Menubar } from 'primeng/menubar'`
**Selector:** `p-menubar`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[]` | undefined | Array of menu items |
| styleClass | `string \| undefined` | undefined | CSS class |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| autoDisplay | `boolean` | — | Auto-show submenus on hover |
| autoHide | `boolean` | — | Auto-hide submenus on leave |
| autoHideDelay | `number` | — | Delay before auto-hide |
| breakpoint | `string` | — | Responsive breakpoint for hamburger menu |
| id | `string \| undefined` | undefined | Component ID |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |

## Usage Example (from Sakai-ng)

```html
<p-menubar [model]="nestedMenuItems">
  <ng-template pTemplate="start">
    <img src="assets/logo.png" alt="Logo" height="40" />
  </ng-template>
  <ng-template pTemplate="end">
    <p-button label="Login" icon="pi pi-user"></p-button>
  </ng-template>
</p-menubar>
```

## Notes

- Supports `pTemplate="start"` and `pTemplate="end"` slots for logo/actions.
- `MenuItem` supports nested `items` for dropdown submenus.
- At mobile breakpoints, renders a hamburger button.
