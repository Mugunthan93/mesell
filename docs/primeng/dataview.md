# DataView

**Import:** `import { DataView } from 'primeng/dataview'`
**Selector:** `p-dataview`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any[]` | undefined | Array of items to display |
| layout | `'list' \| 'grid'` | `'list'` | Display layout |
| paginator | `boolean \| undefined` | undefined | Enable pagination |
| rows | `number \| undefined` | undefined | Rows per page |
| totalRecords | `number \| undefined` | undefined | Total records count (for server-side pagination) |
| pageLinks | `number` | 5 | Number of page links in paginator |
| rowsPerPageOptions | `number[]` | undefined | Options for rows-per-page dropdown |
| paginatorPosition | `'top' \| 'bottom' \| 'both'` | `'bottom'` | Paginator position |
| alwaysShowPaginator | `boolean` | true | Show paginator even with single page |
| emptyMessage | `string \| undefined` | undefined | Message when no data |
| first | `number` | 0 | Index of the first record |
| sortField | `string \| undefined` | undefined | Field name for default sort |
| sortOrder | `number \| undefined` | undefined | Sort order (1 asc, -1 desc) |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onPage | `EventEmitter<DataViewPageEvent>` | Emitted on page change |
| onSort | `EventEmitter<DataViewSortEvent>` | Emitted on sort change |
| onLayoutChange | `EventEmitter<string>` | Emitted when layout changes |

## Usage Example

```html
<p-dataview [value]="products" layout="grid" [paginator]="true" [rows]="12">
  <ng-template pTemplate="list" let-items>
    @for (item of items; track item.id) {
      <div>{{ item.name }}</div>
    }
  </ng-template>
  <ng-template pTemplate="grid" let-items>
    <div class="grid">
      @for (item of items; track item.id) {
        <div class="col-4">{{ item.name }}</div>
      }
    </div>
  </ng-template>
</p-dataview>
```

## Notes

- Supports both list and grid layouts with separate `pTemplate` slots.
- For tabular data, prefer `p-table`. DataView is for card/list layouts.
