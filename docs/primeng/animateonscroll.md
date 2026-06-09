# AnimateOnScroll

**Import:** `import { AnimateOnScroll } from 'primeng/animateonscroll'`
**Selector:** `[pAnimateOnScroll]` (DIRECTIVE on any host element)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> `AnimateOnScroll` is a DIRECTIVE that triggers CSS animation classes when the element enters/leaves the viewport (IntersectionObserver API).

## @Input() Props

| Prop | Attribute alias | Type | Default | Description |
|------|----------------|------|---------|-------------|
| enterClass | `enterClass` | `string \| undefined` | undefined | CSS animation class applied when element enters viewport |
| leaveClass | `leaveClass` | `string \| undefined` | undefined | CSS animation class applied when element leaves viewport |
| threshold | `threshold` | `number \| undefined` | undefined | IntersectionObserver threshold (0–1, fraction visible) |
| root | `root` | `any` | undefined | IntersectionObserver root element |
| rootMargin | `rootMargin` | `string` | undefined | IntersectionObserver root margin |
| once | `once` | `boolean` | false | When true, animation only fires once (not on scroll back) |

## @Output() Events

None.

## Usage Example

```html
<!-- Fade in on scroll using PrimeNG animation class -->
<div pAnimateOnScroll enterClass="animate-fadein" leaveClass="animate-fadeout">
  Content that animates on scroll
</div>

<!-- Slide in once -->
<div pAnimateOnScroll enterClass="animate-slidedown" [once]="true">
  Slide in when first visible
</div>
```

## Notes

- PrimeNG provides built-in animation utility classes: `animate-fadein`, `animate-fadeout`, `animate-slidedown`, `animate-slideup`, `animate-scalein`, etc.
- `once="true"` prevents re-triggering animation each time the element scrolls in/out — use for hero sections.
- Relies on the browser's IntersectionObserver API (supported in all modern browsers).
