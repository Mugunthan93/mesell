# ScrollTop

**Import:** `import { ScrollTop } from 'primeng/scrolltop'`
**Selector:** `p-scrollTop`, `p-scrolltop`, `p-scroll-top`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| threshold | `number` | 400 | Vertical scroll position (px) at which the button appears |
| target | `'window' \| 'parent'` | `'window'` | Target element to listen for scroll events |
| icon | `string \| undefined` | undefined | Icon class for the button |
| behavior | `'auto' \| 'smooth'` | `'smooth'` | Scroll animation behavior |
| buttonAriaLabel | `string \| undefined` | undefined | ARIA label for the scroll-to-top button |
| buttonProps | `object \| undefined` | undefined | Additional props for the inner p-button |
| motionOptions | `AnimationOptions` (signal) | — | Animation configuration (replaces transition strings) |

## @Output() Events

None.

## Usage Example

```html
<!-- Page-level scroll to top (appears after 400px scroll) -->
<p-scrolltop></p-scrolltop>

<!-- Container-level scroll to top -->
<div style="height: 400px; overflow: auto">
  <p-scrolltop target="parent" [threshold]="200" behavior="smooth"></p-scrolltop>
  <!-- long content -->
</div>
```

## Notes

- Place `<p-scrolltop>` at the page/app level for window-scroll behavior (default).
- Use `target="parent"` to attach to a scrollable container.
- `motionOptions` replaces the deprecated `showTransitionOptions` / `hideTransitionOptions` in v21.
