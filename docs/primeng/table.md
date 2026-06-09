# Table (DataTable)

**Import:** `import { Table, TableModule } from 'primeng/table'`
**Selector:** `p-table`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Also import `TableModule` when using sub-directives like `pSortableColumn`, `pSelectableRow`, `pTableCheckbox`, etc.

## @Input() Props (core)

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any[]` | undefined | Data array to display |
| columns | `any[]` | undefined | Column definitions (optional — can define columns inline) |
| rows | `number` | undefined | Number of rows per page |
| first | `number` | 0 | Index of the first record |
| totalRecords | `number` | 0 | Total records (for server-side pagination) |
| paginator | `boolean` | false | Show built-in paginator |
| rowsPerPageOptions | `number[]` | undefined | Options for rows-per-page dropdown |
| paginatorPosition | `'top'\|'bottom'\|'both'` | `'bottom'` | Paginator placement |
| lazy | `boolean` | false | Load data on demand (server-side) |
| lazyLoadOnInit | `boolean` | true | Trigger onLazyLoad on component init |
| loading | `boolean` | false | Show loading overlay |
| sortField | `string` | undefined | Field for single-column sort |
| sortOrder | `number` | 1 | Sort direction (1 = ASC, -1 = DESC) |
| sortMode | `'single'\|'multiple'` | `'single'` | Sorting mode |
| customSort | `boolean` | false | Use custom sort via `sortFunction` output |
| selectionMode | `'single'\|'multiple'\|null` | null | Row selection mode |
| selection | `any` | undefined | Selected row(s) |
| dataKey | `string` | undefined | Field for row identity (required for selection) |
| scrollable | `boolean` | false | Enable scrolling |
| scrollHeight | `string` | undefined | Height of the scrollable area |
| virtualScroll | `boolean` | false | Enable virtual scrolling |
| virtualScrollItemSize | `number` | undefined | Row height for virtual scroll |
| resizableColumns | `boolean` | false | Enable column resizing |
| columnResizeMode | `'fit'\|'expand'` | `'fit'` | Column resize behavior |
| reorderableColumns | `boolean` | false | Enable column drag-and-drop reordering |
| rowHover | `boolean` | false | Apply hover highlight on rows |
| showGridlines | `boolean` | false | Show column gridlines |
| stripedRows | `boolean` | false | Alternate row shading |
| size | `string` | undefined | `'small'` or `'large'` density |
| filters | `object` | undefined | External filter state |
| globalFilterFields | `string[]` | undefined | Fields searched by global filter input |
| filterDelay | `number` | 300 | Debounce delay for filter (ms) |
| stateKey | `string` | undefined | Key to persist table state |
| stateStorage | `'local'\|'session'` | `'session'` | Storage type for state |
| editMode | `'cell'\|'row'` | undefined | Inline edit mode |
| groupRowsBy | `string` | undefined | Group rows by field |
| rowGroupMode | `'subheader'\|'rowspan'` | undefined | Row grouping display mode |
| expandedRowKeys | `object` | undefined | Map of expanded row keys |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onLazyLoad | `EventEmitter<TableLazyLoadEvent>` | Fired for server-side data load |
| onPage | `EventEmitter<TablePageEvent>` | Fired on page change |
| onSort | `EventEmitter<TableSortEvent>` | Fired on column sort |
| onFilter | `EventEmitter<TableFilterEvent>` | Fired on filter change |
| onRowSelect | `EventEmitter<TableRowSelectEvent>` | Fired when a row is selected |
| onRowUnselect | `EventEmitter<TableRowUnselectEvent>` | Fired when a row is deselected |
| onRowExpand | `EventEmitter<TableRowExpandEvent>` | Fired when a row expands |
| onRowCollapse | `EventEmitter<TableRowCollapseEvent>` | Fired when a row collapses |
| selectionChange | `EventEmitter<any>` | Two-way binding for selection |
| firstChange | `EventEmitter<number>` | Two-way binding for first |
| rowsChange | `EventEmitter<number>` | Two-way binding for rows |
| onEditInit | `EventEmitter<...>` | Fired when inline edit starts |
| onEditComplete | `EventEmitter<...>` | Fired when inline edit completes |
| sortFunction | `EventEmitter<SortEvent>` | Custom sort callback |

## Key Templates

| pTemplate | Purpose |
|-----------|---------|
| header | Column header row |
| body | Data row |
| footer | Footer row |
| caption | Table caption |
| summary | Summary row |
| emptymessage | Empty state |
| paginatorleft / paginatorright | Paginator slot content |
| loadingbody | Loading placeholder rows |
| expandedrow | Row expansion content |
| groupheader / groupfooter | Row group header/footer |

## Usage Example (from Sakai-ng)

```html
<p-table
  [value]="products"
  [rows]="5"
  [paginator]="true"
  [rowsPerPageOptions]="[5, 10, 25]"
  [loading]="loading"
  dataKey="id"
  [lazy]="true"
  (onLazyLoad)="loadProducts($event)"
  [totalRecords]="totalRecords"
  selectionMode="multiple"
  [(selection)]="selectedProducts"
  [scrollable]="true"
  scrollHeight="400px"
  [stripedRows]="true"
  [showGridlines]="true"
>
  <ng-template pTemplate="header">
    <tr>
      <th><p-tableHeaderCheckbox /></th>
      <th pSortableColumn="name">Name <p-sortIcon field="name" /></th>
      <th pSortableColumn="status">Status <p-sortIcon field="status" /></th>
      <th>Actions</th>
    </tr>
    <tr>
      <th></th>
      <th><p-columnFilter type="text" field="name" /></th>
      <th>
        <p-columnFilter field="status" matchMode="equals">
          <ng-template pTemplate="filter" let-value let-filter="filterCallback">
            <p-select [options]="statuses" (onChange)="filter($event.value)" [ngModel]="value" placeholder="Any" />
          </ng-template>
        </p-columnFilter>
      </th>
      <th></th>
    </tr>
  </ng-template>
  <ng-template pTemplate="body" let-product let-expanded="expanded">
    <tr [pSelectableRow]="product">
      <td><p-tableCheckbox [value]="product" /></td>
      <td>{{ product.name }}</td>
      <td><p-tag [value]="product.status" /></td>
      <td>
        <p-button icon="pi pi-pencil" severity="secondary" (onClick)="edit(product)" />
      </td>
    </tr>
  </ng-template>
  <ng-template pTemplate="emptymessage">
    <tr><td colspan="4">No products found.</td></tr>
  </ng-template>
</p-table>
```

## Notes

- For server-side use: set `[lazy]="true"`, `[totalRecords]`, handle `onLazyLoad` to fetch data with sort/filter/page params.
- `dataKey` is required for selection to work correctly — set it to the unique field (e.g., `"id"`).
- Column filters: use `p-columnFilter` with `type="text"`, `type="numeric"`, or `pTemplate="filter"` for custom filter UI.
- Import `TableModule` (not just `Table`) when using sub-directives like `pSortableColumn`, `pSelectableRow`, `p-tableCheckbox`.
