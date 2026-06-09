# Checkbox

**Import:** `import { Checkbox } from 'primeng/checkbox'`
**Selector:** `p-checkbox`, `p-checkBox`, `p-check-box`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any` | undefined | Value of the checkbox |
| binary | `boolean \| undefined` | undefined | Allows binding to a boolean instead of an array |
| inputId | `string \| undefined` | undefined | ID of the inner input element (for label `for` association) |
| disabled | `boolean` | false | Disables the component |
| tabindex | `number \| undefined` | undefined | Tab index |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby IDs |
| inputStyle | `object \| null` | undefined | Inline style for input element |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<CheckboxChangeEvent>` | Emitted on value change |
| onFocus | `EventEmitter<Event>` | Emitted when focused |
| onBlur | `EventEmitter<Event>` | Emitted when blurred |

## Usage Example (from Sakai-ng)

```html
<!-- Boolean checkbox with ngModel -->
<p-checkbox [(ngModel)]="checked" id="rememberme1" binary class="mr-2"></p-checkbox>
<label for="rememberme1">Remember me</label>

<!-- Multi-value checkbox (array binding) -->
<p-checkbox [(ngModel)]="selectedValues" value="Angular" inputId="cb1"></p-checkbox>
<label for="cb1">Angular</label>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- Use `binary="true"` for boolean toggle behavior; omit for array-based multi-selection.
- Always pair with `<label [for]="inputId">` for accessibility.
