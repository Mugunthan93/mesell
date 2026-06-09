# Fluid

**Import:** `import { Fluid } from 'primeng/fluid'`
**Selector:** `p-fluid`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

None (layout wrapper only).

## @Output() Events

None.

## Usage Example

```html
<!-- Makes all child PrimeNG inputs span full width -->
<p-fluid>
  <div class="flex flex-col gap-4">
    <input pInputText type="text" placeholder="Full width input" />
    <p-select [options]="options" placeholder="Full width select"></p-select>
    <p-button label="Full width button"></p-button>
  </div>
</p-fluid>
```

## Notes

- `Fluid` is a layout utility component that applies `fluid` behavior to all child PrimeNG form components.
- Equivalent to setting `[fluid]="true"` on each individual child component.
- Convenient wrapper when building forms where all fields should be 100% width.
