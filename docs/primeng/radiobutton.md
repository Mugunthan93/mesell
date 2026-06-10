# RadioButton

**Import:** `import { RadioButton } from 'primeng/radiobutton'`
**Selector:** `p-radioButton`, `p-radiobutton`, `p-radio-button`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any` | undefined | The value this radio button represents |
| name | `string \| undefined` | undefined | Name attribute for radio group |
| inputId | `string \| undefined` | undefined | Input element ID (for `<label for>`) |
| disabled | `boolean` | false | Disables the component |
| tabindex | `number \| undefined` | undefined | Tab index |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onClick | `EventEmitter<RadioButtonClickEvent>` | Emitted when radio is clicked |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |

## Usage Example (from Sakai-ng)

```html
<!-- Radio button group -->
<div class="flex flex-col gap-2">
  <div class="flex items-center">
    <p-radiobutton id="option1" name="option" value="Chicago" [(ngModel)]="radioValue" />
    <label for="option1" class="ml-2">Chicago</label>
  </div>
  <div class="flex items-center">
    <p-radiobutton id="option2" name="option" value="Los Angeles" [(ngModel)]="radioValue" />
    <label for="option2" class="ml-2">Los Angeles</label>
  </div>
</div>

<!-- Reactive form -->
<p-radiobutton inputId="opt1" value="monthly" formControlName="billingCycle" />
<label for="opt1">Monthly</label>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- All radio buttons in a group should share the same `name` attribute (for ngModel groups) or the same `formControlName`.
- Always pair with `<label [for]="inputId">` for accessibility.
