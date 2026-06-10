# TreeTable

**Import:** `import { TreeTable, TreeTableModule } from 'primeng/treetable'`
**Selector:** `p-treeTable`, `p-treetable`, `p-tree-table`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> TreeTable combines hierarchical `Tree` navigation with the column features of `Table`. Use when data has parent-child hierarchy AND tabular columns.

## @Input() Props (core)

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `TreeNode[]` | undefined | Root-level tree nodes |
| columns | `any[]` | undefined | Column definitions |
| selectionMode | `'single'\|'multiple'\|'checkbox'\|null` | null | Row selection mode |
| selection | `any` | undefined | Selected node(s) |
| selectionKeys | `object` | undefined | Checkbox selection key map |
| dataKey | `string` | undefined | Field for row identity |
| lazy | `boolean` | false | Lazy loading mode |
| lazyLoadOnInit | `boolean` | true | Fire onLazyLoad on init |
| paginator | `boolean` | false | Show paginator |
| rows | `number` | undefined | Rows per page |
| first | `number` | 0 | First record index |
| totalRecords | `number` | 0 | Total records (server-side) |
| rowsPerPageOptions | `number[]` | undefined | Page size options |
| loading | `boolean` | false | Show loading overlay |
| sortField | `string` | undefined | Sort field |
| sortOrder | `number` | 1 | Sort direction (1=ASC, -1=DESC) |
| sortMode | `'single'\|'multiple'` | `'single'` | Sort mode |
| scrollable | `boolean` | false | Enable scrolling |
| scrollHeight | `string` | undefined | Fixed scroll height |
| virtualScroll | `boolean` | false | Virtual scrolling |
| virtualScrollItemSize | `number` | undefined | Row height for virtual scroll |
| resizableColumns | `boolean` | false | Column resizing |
| reorderableColumns | `boolean` | false | Column reordering |
| rowHover | `boolean` | false | Hover highlight |
| showGridlines | `boolean` | false | Column gridlines |
| filters | `object` | undefined | Filter state |
| globalFilterFields | `string[]` | undefined | Global filter fields |
| filterMode | `'lenient'\|'strict'` | `'lenient'` | Filter mode |
| editMode | `string` | undefined | `'cell'` or `'row'` |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onNodeExpand | `EventEmitter<TreeTableNodeExpandEvent>` | Emitted on node expand |
| onNodeCollapse | `EventEmitter<TreeTableNodeCollapseEvent>` | Emitted on node collapse |
| onNodeSelect | `EventEmitter<TreeTableNodeSelectEvent>` | Emitted on node select |
| onNodeUnselect | `EventEmitter<TreeTableNodeUnselectEvent>` | Emitted on node deselect |
| onLazyLoad | `EventEmitter<TreeTableLazyLoadEvent>` | Emitted for lazy loading |
| onPage | `EventEmitter<TreeTablePageEvent>` | Emitted on page change |
| onSort | `EventEmitter<TreeTableSortEvent>` | Emitted on column sort |
| onFilter | `EventEmitter<TreeTableFilterEvent>` | Emitted on filter |
| selectionChange | `EventEmitter<any>` | Two-way for selection |
| sortFunction | `EventEmitter<SortEvent>` | Custom sort callback |

## Usage Example

```html
<p-treetable [value]="skuTree" [columns]="cols" [scrollable]="true" scrollHeight="400px">
  <ng-template pTemplate="header" let-columns>
    <tr>
      <th *ngFor="let col of columns">{{ col.header }}</th>
    </tr>
  </ng-template>
  <ng-template pTemplate="body" let-rowNode let-rowData="rowData" let-columns="columns">
    <tr [ttSelectableRow]="rowNode">
      <td *ngFor="let col of columns; let i = index">
        <p-treetableToggler [rowNode]="rowNode" *ngIf="i === 0" />
        {{ rowData[col.field] }}
      </td>
    </tr>
  </ng-template>
</p-treetable>
```

## Notes

- `value` takes `TreeNode[]` (same interface as `p-tree`) where each node can have `children`.
- Import `TreeTableModule` (not just `TreeTable`) to get access to sub-directives like `ttSelectableRow`, `p-treetableToggler`, `p-treeTableCheckbox`.
- For lazy expansion: handle `onNodeExpand`, load children, update the node's `children` array and set `leaf: false` initially.
- `selectionKeys` is used for checkbox mode — it's a key/boolean map tracking checked state.
