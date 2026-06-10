# ImageCompare

**Import:** `import { ImageCompare } from 'primeng/imagecompare'`
**Selector:** `p-imageCompare`, `p-imagecompare`, `p-image-compare`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| tabindex | `number \| undefined` | undefined | Tab index |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledby | `string \| undefined` | undefined | ARIA labelledby |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<ImageCompareChangeEvent>` | Emitted when slider position changes |

## Usage Example

```html
<p-imagecompare>
  <ng-template pTemplate="left">
    <img src="before.jpg" alt="Before" />
  </ng-template>
  <ng-template pTemplate="right">
    <img src="after.jpg" alt="After" />
  </ng-template>
</p-imagecompare>
```

## Notes

- Provides a draggable divider between two images for before/after comparison.
- Use `pTemplate="left"` and `pTemplate="right"` for the two image slots.
