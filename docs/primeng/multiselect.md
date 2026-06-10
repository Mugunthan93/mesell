# MultiSelect

**Import:** `import { MultiSelect } from 'primeng/multiselect'`
**Selector:** `p-multiSelect`, `p-multiselect`, `p-multi-select`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | `any[]` | undefined | Array of options |
| optionLabel | `string \| undefined` | undefined | Field name for display label |
| optionValue | `string \| undefined` | undefined | Field name for value |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| filter | `boolean` | true | Show filter input |
| filterBy | `string` | — | Field to filter by |
| filterPlaceHolder | `string \| undefined` | undefined | Filter input placeholder |
| display | `'comma' \| 'chip'` | `'comma'` | Display style for selected values |
| selectedItemsLabel | `string` | `'{0} items selected'` | Label when many items selected |
| maxSelectedLabels | `number` | 3 | Max items to show before using `selectedItemsLabel` |
| disabled | `boolean` | false | Disables the component |
| readonly | `boolean \| undefined` | undefined | Read-only mode |
| showClear | `boolean` | false | Show clear button |
| showSelectAll | `boolean` | true | Show select all checkbox |
| overlayVisible | `boolean \| undefined` | undefined | Control overlay visibility |
| inputId | `string \| undefined` | undefined | Input element ID |
| styleClass | `string \| undefined` | undefined | CSS class |
| panelStyle | `any` | undefined | Inline style for overlay panel |
| group | `boolean \| undefined` | undefined | Whether to display grouped options |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<MultiSelectChangeEvent>` | Emitted on selection change |
| onFilter | `EventEmitter<MultiSelectFilterEvent>` | Emitted on filter input change |
| onFocus | `EventEmitter<MultiSelectFocusEvent>` | Emitted on focus |
| onBlur | `EventEmitter<MultiSelectBlurEvent>` | Emitted on blur |
| onClick | `EventEmitter<Event>` | Emitted on click |
| onClear | `EventEmitter<void>` | Emitted when selection cleared |
| onPanelShow | `EventEmitter<AnimationEvent>` | Emitted when panel opens |
| onPanelHide | `EventEmitter<AnimationEvent>` | Emitted when panel closes |

## Usage Example (from Sakai-ng)

```html
<p-multiselect
  [options]="multiselectCountries"
  [(ngModel)]="multiselectSelectedCountries"
  placeholder="Select Countries"
  optionLabel="name"
  display="chip"
  [filter]="true"
>
  <ng-template pTemplate="item" let-country>
    <div class="flex items-center gap-2">
      <span>{{ country.name }}</span>
    </div>
  </ng-template>
</p-multiselect>

<!-- In table filter -->
<p-multiselect
  [ngModel]="value"
  [options]="representatives"
  placeholder="Any"
  (onChange)="filter($event.value)"
  optionLabel="name"
  styleClass="w-full"
></p-multiselect>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- The model value is always an array of selected values.
- `display="chip"` shows selected items as removable chips.
