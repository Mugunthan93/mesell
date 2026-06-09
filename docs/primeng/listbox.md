# Listbox

**Import:** `import { Listbox } from 'primeng/listbox'`
**Selector:** `p-listbox`, `p-listBox`, `p-list-box`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | `any[]` | undefined | Array of options |
| optionLabel | `string \| undefined` | undefined | Field name to use as label |
| optionValue | `string \| undefined` | undefined | Field name to use as value |
| multiple | `boolean \| undefined` | false | Allow multiple selection |
| filter | `boolean` | false | Show filter input |
| filterBy | `string` | — | Field to filter by |
| disabled | `boolean` | false | Disables the component |
| checkbox | `boolean` | false | Show checkboxes for each item |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| id | `string \| undefined` | undefined | Component ID |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<ListboxChangeEvent>` | Emitted on selection change |
| onFilter | `EventEmitter<ListboxFilterEvent>` | Emitted on filter input change |
| onClick | `EventEmitter<ListboxClickEvent>` | Emitted on item click |
| onDblClick | `EventEmitter<ListboxClickEvent>` | Emitted on item double-click |

## Usage Example (from Sakai-ng)

```html
<p-listbox
  [(ngModel)]="listboxValue"
  [options]="listboxValues"
  optionLabel="name"
  [filter]="true"
/>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- For multi-selection: `[multiple]="true"` — value becomes an array.
- For in-place list (not a dropdown overlay), use `Listbox` not `p-select`.
