# SplitButton

**Import:** `import { SplitButton } from 'primeng/splitbutton'`
**Selector:** `p-splitbutton`, `p-splitButton`, `p-split-button`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[]` | undefined | Array of dropdown menu items |
| label | `string \| undefined` | undefined | Text on the main button |
| icon | `string \| undefined` | undefined | Icon class for the main button |
| iconPos | `SplitButtonIconPosition` | `'left'` | Icon position (`'left'`, `'right'`) |
| severity | `string \| undefined` | undefined | Visual severity (`'success'`, `'info'`, `'warn'`, `'danger'`, etc.) |
| raised | `boolean` | false | Raised appearance |
| rounded | `boolean` | false | Rounded corners |
| text | `boolean` | false | Text-only style |
| outlined | `boolean` | false | Outlined style |
| size | `string \| undefined` | undefined | `'small'` or `'large'` |
| plain | `boolean` | false | Plain (unstyled) button |
| disabled | `boolean` | false | Disables both buttons |
| buttonDisabled | `boolean` | false | Disables only the main button |
| menuButtonDisabled | `boolean` | false | Disables only the dropdown button |
| tabindex | `number \| undefined` | undefined | Tab index |
| dropdownIcon | `string \| undefined` | undefined | Custom dropdown chevron icon |
| appendTo | (signal) `any` | undefined | Target for overlay attachment |
| autofocus | `boolean \| undefined` | undefined | Auto-focus main button on init |
| buttonProps | `ButtonProps` | — | Props forwarded to the main button |
| menuButtonProps | `MenuButtonProps` | — | Props forwarded to the dropdown button |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onClick | `EventEmitter<MouseEvent>` | Emitted when main button is clicked |
| onMenuHide | `EventEmitter<any>` | Emitted when dropdown closes |
| onMenuShow | `EventEmitter<any>` | Emitted when dropdown opens |
| onDropdownClick | `EventEmitter<MouseEvent>` | Emitted when dropdown arrow is clicked |

## Usage Example

```html
<p-splitbutton
  label="Save"
  icon="pi pi-save"
  [model]="exportItems"
  severity="primary"
  (onClick)="save()"
/>

<!-- In component -->
exportItems: MenuItem[] = [
  { label: 'Save as Draft', command: () => this.saveDraft() },
  { label: 'Export XLSX', command: () => this.export() },
  { separator: true },
  { label: 'Delete', command: () => this.delete(), styleClass: 'text-red-500' }
];
```

## Notes

- `model` uses the standard `MenuItem` interface from `primeng/api`.
- The main button's click (`onClick`) is separate from the dropdown items' `command` callbacks.
- Use `menuButtonDisabled` to prevent opening the dropdown without disabling the main action.
