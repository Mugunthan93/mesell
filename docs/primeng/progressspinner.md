# ProgressSpinner

**Import:** `import { ProgressSpinner } from 'primeng/progressspinner'`
**Selector:** `p-progressSpinner`, `p-progress-spinner`, `p-progressspinner`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| strokeWidth | `string` | `'2'` | Width of the circle stroke |
| fill | `string` | `'none'` | Background fill color of the circle |
| animationDuration | `string` | `'2s'` | Duration of the rotate animation |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` instead |
| ariaLabel | `string \| undefined` | undefined | ARIA label for accessibility |

## @Output() Events

None.

## Usage Example

```html
<!-- Basic spinner -->
<p-progressspinner></p-progressspinner>

<!-- Custom size via style -->
<p-progressspinner [style]="{ width: '50px', height: '50px' }"></p-progressspinner>

<!-- In a loading overlay -->
@if (loading()) {
  <div class="flex justify-center items-center h-full">
    <p-progressspinner strokeWidth="4" animationDuration=".5s"></p-progressspinner>
  </div>
}
```

## Notes

- No `value` prop — always shows indeterminate spinning animation.
- Resize via `style` (width/height) or Tailwind `w-*` / `h-*` classes on the host.
