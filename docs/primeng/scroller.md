# Scroller (Virtual Scroller)

**Import:** `import { Scroller } from 'primeng/scroller'`
**Selector:** `p-scroller`, `p-virtualscroller`, `p-virtual-scroller`, `p-virtualScroller`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| items | `any[] \| undefined` | undefined | The items to render |
| itemSize | `number \| number[]` | undefined | Height (or [width, height]) of each item in pixels |
| scrollHeight | `string \| undefined` | undefined | Height of the scrollable container |
| scrollWidth | `string \| undefined` | undefined | Width of the scrollable container |
| orientation | `'vertical' \| 'horizontal' \| 'both'` | `'vertical'` | Scroll orientation |
| step | `number` | 0 | Number of items beyond viewport to render |
| delay | `number` | 0 | Delay in ms before rendering after scroll |
| resizeDelay | `number` | 10 | Delay after resize before re-layout |
| lazy | `boolean` | false | When true, use lazy loading |
| loading | `boolean \| undefined` | undefined | External loading state |
| columns | `any[] \| undefined` | undefined | Columns for grid layout |
| showLoader | `boolean` | false | Show loading indicator |
| loaderDisabled | `boolean` | false | Disable built-in loader |
| inline | `boolean` | false | Inline (no fixed height) |
| autoSize | `boolean` | true | Auto-calculate item sizes |
| appendOnly | `boolean` | false | Only append items, never remove |
| trackBy | `Function` | undefined | TrackBy function |
| options | `ScrollerOptions \| undefined` | undefined | Programmatic options object |
| numToleratedItems | `number \| undefined` | undefined | Number of items to tolerate outside viewport |
| showSpacer | `boolean` | true | Show placeholder spacer elements |
| disabled | `boolean \| undefined` | undefined | Disables virtual scrolling |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onLazyLoad | `EventEmitter<ScrollerLazyLoadEvent>` | Emitted when lazy loading is triggered |
| onScroll | `EventEmitter<ScrollerScrollEvent>` | Emitted on scroll |
| onScrollIndexChange | `EventEmitter<ScrollerScrollIndexChangeEvent>` | Emitted when scroll index changes |

## Templates

| pTemplate | Purpose |
|-----------|---------|
| item | Custom item renderer |
| content | Custom content renderer |
| loader | Custom loading element |
| loadericon | Custom loader icon |

## Usage Example

```html
<!-- Virtual scrolling list -->
<p-scroller
  [items]="products"
  [itemSize]="80"
  scrollHeight="400px"
  [lazy]="true"
  (onLazyLoad)="loadMore($event)"
>
  <ng-template pTemplate="item" let-item let-options="options">
    <div class="flex items-center p-2" [style.height.px]="80">
      {{ item.name }}
    </div>
  </ng-template>
</p-scroller>
```

## Notes

- `itemSize` MUST be set for virtual scrolling to work correctly — it controls the DOM recycling calculation.
- `p-table` and `p-listbox` have built-in virtual scroll support via `[virtualScroll]="true"` — use `p-scroller` only when building custom virtualized lists.
- Use `lazy + onLazyLoad` for server-side pagination with virtual scroll.
