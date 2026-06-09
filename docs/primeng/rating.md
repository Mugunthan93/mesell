# Rating

**Import:** `import { Rating } from 'primeng/rating'`
**Selector:** `p-rating`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| stars | `number` | 5 | Number of stars |
| readonly | `boolean` | false | When true, rating is not interactive |
| iconOnClass | `string \| undefined` | undefined | CSS class for filled star icon |
| iconOnStyle | `object \| undefined` | undefined | Inline style for filled star |
| iconOffClass | `string \| undefined` | undefined | CSS class for empty star icon |
| iconOffStyle | `object \| undefined` | undefined | Inline style for empty star |
| autofocus | `boolean \| undefined` | undefined | Auto-focus on mount |
| disabled | `boolean` | false | Disables the component |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onRate | `EventEmitter<RatingRateEvent>` | Emitted when a star is selected |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |

## Templates

| pTemplate | Purpose |
|-----------|---------|
| onicon | Custom filled star icon |
| officon | Custom empty star icon |

## Usage Example (from Sakai-ng)

```html
<!-- Basic rating with ngModel -->
<p-rating [(ngModel)]="productRating" />

<!-- Read-only display -->
<p-rating [ngModel]="product.rating" [readonly]="true" />

<!-- Reactive form -->
<p-rating formControlName="quality" [stars]="5" />

<!-- Custom star count -->
<p-rating [(ngModel)]="val" [stars]="10" />
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- Use `[readonly]="true"` for display-only rating indicators.
- Use `pTemplate="onicon"` / `pTemplate="officon"` for custom star icons.
