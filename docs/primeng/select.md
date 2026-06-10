# Select (Dropdown)

**Import:** `import { Select } from 'primeng/select'`
**Selector:** `p-select`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Replaces the deprecated `p-dropdown` selector. Use `p-select` in all new code.

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | `any[]` | undefined | Array of items to display |
| optionLabel | `string` | `'label'` | Field to use as display label |
| optionValue | `string \| undefined` | undefined | Field to use as option value |
| optionDisabled | `string \| undefined` | undefined | Field to mark options as disabled |
| optionGroupLabel | `string \| undefined` | undefined | Field for group label |
| optionGroupChildren | `string \| undefined` | undefined | Field for group children |
| group | `boolean` | false | Enable grouped options |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| filter | `boolean` | false | Show filter input |
| filterBy | `string \| undefined` | undefined | Comma-separated field(s) to filter by |
| filterFields | `any[]` | undefined | Fields array to filter by |
| filterPlaceholder | `string \| undefined` | undefined | Filter input placeholder |
| filterMatchMode | `'contains'\|'startsWith'\|'endsWith'\|'equals'\|...` | `'contains'` | Filter algorithm |
| editable | `boolean` | false | Allow freeform text input |
| showClear | `boolean` | false | Show clear button |
| checkmark | `boolean` | false | Show checkmark on selected option |
| loading | `boolean` | false | Show loading indicator |
| loadingIcon | `string \| undefined` | undefined | Custom loading icon class |
| readonly | `boolean` | false | Disable editing but allow selection display |
| disabled | `boolean` | false | Disables the component |
| tabindex | `number \| undefined` | undefined | Tab index |
| inputId | `string \| undefined` | undefined | Input element ID |
| dataKey | `string \| undefined` | undefined | Key for option comparison |
| scrollHeight | `string` | `'200px'` | Max height of option list |
| virtualScroll | `boolean` | false | Enable virtual scrolling |
| virtualScrollItemSize | `number \| undefined` | undefined | Item height for virtual scroll |
| lazy | `boolean` | false | Enable lazy loading |
| appendTo | (signal) `any` | undefined | Target for overlay attachment |
| motionOptions | (signal) | — | Animation configuration |
| autofocus | `boolean` | false | Auto-focus on init |
| autofocusFilter | `boolean` | true | Auto-focus filter input when panel opens |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<SelectChangeEvent>` | Emitted when selected value changes |
| onFilter | `EventEmitter<SelectFilterEvent>` | Emitted when filter input changes |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |
| onClick | `EventEmitter<Event>` | Emitted on click |
| onShow | `EventEmitter<any>` | Emitted when panel opens |
| onHide | `EventEmitter<any>` | Emitted when panel closes |
| onClear | `EventEmitter<any>` | Emitted when clear button clicked |
| onLazyLoad | `EventEmitter<SelectLazyLoadEvent>` | Emitted for lazy loading |

## Templates

| pTemplate | Purpose |
|-----------|---------|
| selectedItem | Custom selected value display |
| item | Custom option item |
| group | Custom option group |
| header | Custom panel header |
| footer | Custom panel footer |
| emptyFilter | Shown when filter returns no results |
| empty | Shown when no options |
| dropdownicon | Custom dropdown chevron |

## Usage Example (from Sakai-ng)

```html
<!-- Basic select -->
<p-select
  [options]="categories"
  [(ngModel)]="selectedCategory"
  optionLabel="name"
  placeholder="Select a Category"
  class="w-full"
/>

<!-- With filter -->
<p-select
  [options]="products"
  [(ngModel)]="selectedProduct"
  optionLabel="name"
  [filter]="true"
  filterBy="name"
  placeholder="Search products"
  [showClear]="true"
/>

<!-- Reactive form -->
<p-select
  formControlName="category"
  [options]="categoryOptions"
  optionLabel="label"
  optionValue="value"
  placeholder="Select category"
  class="w-full"
/>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- When using objects as options, set `optionValue` to a string field; otherwise the entire object is bound.
- `dataKey` ensures object identity comparison works when the same option list is re-fetched.
- `p-dropdown` selector is deprecated — always use `p-select`.
