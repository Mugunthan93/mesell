# Divider

**Import:** `import { Divider } from 'primeng/divider'`
**Selector:** `p-divider`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| layout | `'horizontal' \| 'vertical' \| undefined` | `'horizontal'` | Orientation of the divider |
| type | `'solid' \| 'dashed' \| 'dotted' \| undefined` | `'solid'` | Border style |
| align | `'left' \| 'center' \| 'right' \| 'top' \| 'bottom' \| undefined` | undefined | Alignment of content within the divider |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Usage Example

```html
<!-- Horizontal divider -->
<p-divider></p-divider>

<!-- Divider with text label centered -->
<p-divider align="center" type="dashed">
  <span class="font-semibold">OR</span>
</p-divider>

<!-- Vertical divider (inside flex row) -->
<div class="flex">
  <span>Left</span>
  <p-divider layout="vertical"></p-divider>
  <span>Right</span>
</div>
```

## Notes

- Content projection into `<p-divider>` renders as a label in the middle of the line.
- Use `layout="vertical"` inside flex containers to separate items horizontally.
