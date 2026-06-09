# SelectButton

**Import:** `import { SelectButton } from 'primeng/selectbutton'`
**Selector:** `p-selectButton`, `p-selectbutton`, `p-select-button`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | `any[]` | undefined | Array of option items |
| optionLabel | `string` | `'label'` | Field to use as button label |
| optionValue | `string \| undefined` | undefined | Field to use as the bound value |
| optionDisabled | `string \| undefined` | undefined | Field that marks an option disabled |
| multiple | `boolean` | false | Allow selecting multiple buttons |
| allowEmpty | `boolean` | true | When false, at least one option must remain selected |
| tabindex | `number \| undefined` | undefined | Tab index |
| unselectable | `boolean` | false | Click a selected option to deselect it |
| dataKey | `string \| undefined` | undefined | Field for object identity comparison |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| disabled | `boolean` | false | Disables all buttons |
| autofocus | `boolean \| undefined` | undefined | Auto-focus on init |
| size | (signal) `'small' \| 'large' \| undefined` | undefined | Button size |
| fluid | (signal) `boolean` | false | Full-width layout |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onOptionClick | `EventEmitter<SelectButtonOptionClickEvent>` | Emitted when a button is clicked |
| onChange | `EventEmitter<SelectButtonChangeEvent>` | Emitted when selected value changes |

## Templates

| pTemplate | Purpose |
|-----------|---------|
| item | Custom button content |

## Usage Example (from Sakai-ng)

```html
<!-- Single select -->
<p-selectbutton
  [options]="justifyOptions"
  [(ngModel)]="justifyValue"
  optionLabel="icon"
  optionValue="value"
/>

<!-- Multiple select -->
<p-selectbutton
  [options]="paymentOptions"
  [(ngModel)]="selectedPayments"
  optionLabel="name"
  [multiple]="true"
/>

<!-- Reactive form -->
<p-selectbutton
  formControlName="billingCycle"
  [options]="[{label:'Monthly',value:'monthly'},{label:'Annual',value:'annual'}]"
  optionLabel="label"
  optionValue="value"
/>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- Renders as a group of toggle buttons — good for small option sets (2–5 options).
- `allowEmpty="false"` forces radio-button semantics (exactly one selected always).
