# Slider

**Import:** `import { Slider } from 'primeng/slider'`
**Selector:** `p-slider`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| min | `number` | 0 | Minimum value |
| max | `number` | 100 | Maximum value |
| step | `number` | 1 | Increment step size |
| range | `boolean` | false | Enable range selection (two handles) |
| orientation | `'horizontal' \| 'vertical'` | `'horizontal'` | Slider orientation |
| animate | `boolean` | false | Animate handle on click |
| disabled | `boolean` | false | Disables the component |
| tabindex | `number \| undefined` | undefined | Tab index |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| autofocus | `boolean \| undefined` | undefined | Auto-focus on init |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<SliderChangeEvent>` | Emitted continuously while sliding |
| onSlideEnd | `EventEmitter<SliderSlideEndEvent>` | Emitted when handle is released |

## Usage Example (from Sakai-ng / PricingComponent)

```html
<!-- Basic slider -->
<p-slider [(ngModel)]="priceValue" [min]="100" [max]="5000" [step]="50" />

<!-- Range slider -->
<p-slider [(ngModel)]="priceRange" [range]="true" [min]="0" [max]="10000" />
<span>{{ priceRange[0] }} – {{ priceRange[1] }}</span>

<!-- Reactive form slider -->
<p-slider formControlName="marginPercent" [min]="0" [max]="100" />

<!-- Vertical slider -->
<p-slider [(ngModel)]="val" orientation="vertical" [style]="{ height: '200px' }" />
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- When `range="true"`, the bound value is an array `[start, end]`.
- Use `onSlideEnd` for expensive operations (API calls) — `onChange` fires on every pixel movement.
