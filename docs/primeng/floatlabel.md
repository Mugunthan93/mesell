# FloatLabel

**Import:** `import { FloatLabel } from 'primeng/floatlabel'`
**Selector:** `p-floatlabel`, `p-floatLabel`, `p-float-label` (all three aliases)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| variant | `'in' \| 'over' \| 'on'` | `'over'` | Defines the positioning of the label relative to the input |

## @Output() Events

None.

## Key Interfaces / Types

None beyond the component itself.

## Usage Example (from Sakai-ng)

```html
<!-- Float label wrapping an input -->
<p-floatlabel>
  <input pInputText id="username" type="text" [(ngModel)]="username" />
  <label for="username">Username</label>
</p-floatlabel>

<!-- With variant -->
<p-floatlabel variant="in">
  <input pInputText id="email" type="email" formControlName="email" />
  <label for="email">Email</label>
</p-floatlabel>
```

## Notes

- Wrap the input and `<label>` together inside `<p-floatlabel>`.
- The `for` attribute on `<label>` must match the `id` on the `<input>` for correct label animation.
- Variants: `'over'` = label floats over the input on focus; `'on'` = label appears on top border; `'in'` = label inside field.
- Works with `pInputText`, `p-inputnumber`, `p-select`, `p-datepicker`, and other PrimeNG form inputs.
- Standalone component — import `FloatLabel` directly in component's `imports[]` array.
