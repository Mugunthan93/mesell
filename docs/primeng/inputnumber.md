# InputNumber

**Import:** `import { InputNumber } from 'primeng/inputnumber'`
**Selector:** `p-inputNumber`, `p-inputnumber`, `p-input-number`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| inputId | `string \| undefined` | undefined | ID of the inner input element |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| mode | `'decimal' \| 'currency'` | `'decimal'` | Formatting mode |
| format | `boolean` | true | Whether to format the value |
| showButtons | `boolean` | false | Display increment/decrement spinner buttons |
| buttonLayout | `string` | `'stacked'` | Button layout: `'stacked'`, `'horizontal'`, `'vertical'` |
| min | `number \| undefined` | undefined | Minimum allowed value |
| max | `number \| undefined` | undefined | Maximum allowed value |
| step | `number` | 1 | Increment/decrement step |
| minFractionDigits | `number \| undefined` | undefined | Minimum fraction digits |
| maxFractionDigits | `number \| undefined` | undefined | Maximum fraction digits |
| locale | `string \| undefined` | undefined | Locale for formatting (e.g. `'en-IN'`) |
| currency | `string \| undefined` | undefined | Currency code for mode=currency (e.g. `'INR'`) |
| prefix | `string \| undefined` | undefined | Text to display before the value |
| suffix | `string \| undefined` | undefined | Text to display after the value |
| disabled | `boolean` | false | Disables the component |
| readonly | `boolean \| undefined` | undefined | Read-only mode |
| inputStyle | `any` | undefined | Inline style for the inner input |
| styleClass | `string \| undefined` | undefined | CSS class |
| ariaLabel | `string \| undefined` | undefined | ARIA label |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onInput | `EventEmitter<InputNumberInputEvent>` | Emitted on each keystroke |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |
| onKeyDown | `EventEmitter<KeyboardEvent>` | Emitted on key press |

## Usage Example (from Sakai-ng)

```html
<!-- Decimal input with spinner buttons -->
<p-inputnumber [(ngModel)]="inputNumberValue" showButtons mode="decimal"></p-inputnumber>

<!-- Currency formatted -->
<p-inputnumber [(ngModel)]="price" mode="currency" currency="INR" locale="en-IN"></p-inputnumber>

<!-- Reactive form with min/max -->
<p-inputnumber formControlName="mrp" [min]="0" [max]="99999" [minFractionDigits]="0"></p-inputnumber>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- The model value is always a `number` (not a formatted string).
- For Indian currency: `mode="currency" currency="INR" locale="en-IN"`.
