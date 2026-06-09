# IftaLabel

**Import:** `import { IftaLabel } from 'primeng/iftalabel'`
**Selector:** `p-iftalabel`, `p-iftaLabel`, `p-ifta-label`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

None (layout wrapper only).

## @Output() Events

None.

## Usage Example

```html
<!-- In-field top-aligned label (label stays at top of input) -->
<p-iftalabel>
  <input pInputText id="username" type="text" formControlName="username" />
  <label for="username">Username</label>
</p-iftalabel>
```

## Notes

- Alternative to `p-floatlabel`. The label sits at the top-inside of the input at all times (not floating on focus).
- Wrap input and `<label>` inside `<p-iftalabel>`.
- The `for` attribute on `<label>` must match the `id` on the input.
- Works with `pInputText`, `p-select`, `p-datepicker`, etc.
