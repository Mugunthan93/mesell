# Carousel

**Import:** `import { Carousel } from 'primeng/carousel'`
**Selector:** `p-carousel`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any[]` | null | Array of items to display |
| page | `number` | 0 | Index of the first item |
| numVisible | `number` | 1 | Number of items visible per page |
| numScroll | `number` | 1 | Number of items scrolled per interaction |
| responsiveOptions | `CarouselResponsiveOptions[]` | undefined | Options for responsive breakpoints |
| orientation | `'horizontal' \| 'vertical'` | `'horizontal'` | Layout direction |
| verticalViewPortHeight | `string` | — | Viewport height in vertical mode |
| circular | `boolean` | false | Whether scrolling is infinite/circular |
| showIndicators | `boolean` | true | Whether to display indicator dots |
| contentClass | `string` | — | CSS class for main content |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onPage | `EventEmitter<CarouselPageEvent>` | Emitted when page changes |

## Usage Example (from Sakai-ng)

```html
<p-carousel
  [value]="products()"
  [numVisible]="3"
  [numScroll]="3"
  [circular]="false"
  [responsiveOptions]="carouselResponsiveOptions"
>
  <ng-template pTemplate="item" let-product>
    <div class="p-3">
      <p-card [header]="product.name">
        <img [src]="product.image" [alt]="product.name" class="w-full" />
      </p-card>
    </div>
  </ng-template>
</p-carousel>
```

## Notes

- Use `pTemplate="item"` for the item template — `let-product` provides each item.
- `responsiveOptions` lets you change `numVisible`/`numScroll` at different viewport widths.
