# ScrollPanel

**Import:** `import { ScrollPanel } from 'primeng/scrollpanel'`
**Selector:** `p-scroll-panel`, `p-scrollPanel`, `p-scrollpanel`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| styleClass | `string \| undefined` | undefined | CSS class for the container |
| step | `number` | 5 | Step size for keyboard navigation (px) |

## @Output() Events

None.

## Usage Example

```html
<!-- Fixed-height scrollable panel with custom scrollbar -->
<p-scrollpanel [style]="{ width: '100%', height: '300px' }">
  <div class="p-4">
    <p>Long content here...</p>
    <!-- ... more content ... -->
  </div>
</p-scrollpanel>
```

## Notes

- Renders custom-styled scrollbars consistent with the PrimeNG theme.
- Size is controlled via `[style]` (width/height) or `class` — the panel itself does not auto-size.
- Use when native scrollbar styling is inconsistent across browsers/OS.
