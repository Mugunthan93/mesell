# OrderList

**Import:** `import { OrderList } from 'primeng/orderlist'`
**Selector:** `p-orderList`, `p-orderlist`, `p-order-list`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any[]` | undefined | Array of items to display and reorder |
| header | `string \| undefined` | undefined | Header title text |
| filterBy | `string \| undefined` | undefined | Field to filter on |
| filterPlaceholder | `string \| undefined` | undefined | Filter input placeholder |
| filter | `boolean` | false | Show filter input |
| disabled | `boolean` | false | Disables reordering |
| dataKey | `string \| undefined` | undefined | Unique identifier field for tracking |
| breakpoint | `string` | `'960px'` | Responsive breakpoint |
| styleClass | `string \| undefined` | undefined | CSS class |
| metaKeySelection | `boolean` | true | Toggle multiple selection with meta key |
| dragdrop | `boolean` | false | Enable drag-and-drop reorder |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onReorder | `EventEmitter<OrderListFilterEvent>` | Emitted after reorder |
| onSelectionChange | `EventEmitter<OrderListSelectionChangeEvent>` | Emitted on selection change |
| onFilterEvent | `EventEmitter<OrderListFilterEvent>` | Emitted on filter change |

## Usage Example (from Sakai-ng)

```html
<p-orderlist [value]="orderCities" dataKey="id" breakpoint="575px">
  <ng-template pTemplate="item" let-city>
    <div>{{ city.name }}</div>
  </ng-template>
</p-orderlist>
```

## Notes

- Use `pTemplate="item"` for custom item rendering.
- The `value` array is mutated in place on reorder — use `(onReorder)` to persist changes.
