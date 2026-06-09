# Skeleton

**Import:** `import { Skeleton } from 'primeng/skeleton'`
**Selector:** `p-skeleton`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| shape | `'rectangle' \| 'circle'` | `'rectangle'` | Shape of the placeholder |
| animation | `'wave' \| 'none'` | `'wave'` | Animation type |
| width | `string` | `'100%'` | Width (CSS value) |
| height | `string` | `'1rem'` | Height (CSS value) |
| size | `string \| undefined` | undefined | Equal width and height (overrides width/height for circles) |
| borderRadius | `string \| undefined` | undefined | CSS border radius |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Usage Example

```html
<!-- Text line placeholder -->
<p-skeleton width="10rem" height="1rem"></p-skeleton>

<!-- Circle avatar placeholder -->
<p-skeleton shape="circle" size="4rem"></p-skeleton>

<!-- Card skeleton -->
<div class="flex gap-4 items-center">
  <p-skeleton shape="circle" size="4rem"></p-skeleton>
  <div class="flex flex-col gap-2 flex-1">
    <p-skeleton width="100%" height="1rem"></p-skeleton>
    <p-skeleton width="75%"  height="1rem"></p-skeleton>
  </div>
</div>

<!-- No animation (static) -->
<p-skeleton animation="none" width="100%" height="2rem"></p-skeleton>
```

## Notes

- Use skeletons instead of spinners for list/card loading states — they reduce perceived latency.
- `size` sets both width and height to the same value (ideal for circle avatars).
- Wrap multiple skeletons in a `@if (loading())` block and swap with actual content.
