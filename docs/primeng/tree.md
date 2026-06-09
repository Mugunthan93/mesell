# Tree

**Import:** `import { Tree } from 'primeng/tree'`
**Selector:** `p-tree`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `TreeNode[] \| any[]` | undefined | Array of `TreeNode` items to display |
| selectionMode | `'single'\|'multiple'\|'checkbox'\|null` | null | Selection behavior |
| selection | (signal) `any` | undefined | Selected node(s) — two-way signal |
| filter | `boolean` | false | Show filter input |
| filterBy | `string` | `'label'` | Field(s) to filter by |
| filterMode | `'lenient'\|'strict'` | `'lenient'` | Filter mode |
| filterPlaceholder | `string` | undefined | Filter input placeholder |
| loading | `boolean` | false | Show loading state |
| loadingIcon | `string` | undefined | Custom loading icon |
| lazy | `boolean` | false | Load children on expand |
| virtualScroll | `boolean` | false | Enable virtual scrolling |
| virtualScrollItemSize | `number` | undefined | Item height for virtual scroll |
| scrollHeight | `string` | undefined | Fixed scroll height |
| draggableNodes | `boolean` | false | Enable node drag |
| droppableNodes | `boolean` | false | Enable node drop |
| propagateSelectionUp | `boolean` | true | Propagate checkbox selection upward |
| propagateSelectionDown | `boolean` | true | Propagate checkbox selection downward |
| emptyMessage | `string` | `'No results found'` | Empty state text |
| indentation | `number` | 1.5 | Level indentation (rem) |
| highlightOnSelect | `boolean` | false | Highlight the selected node row |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onNodeSelect | `EventEmitter<TreeNodeSelectEvent>` | Emitted when a node is selected |
| onNodeUnselect | `EventEmitter<TreeNodeUnSelectEvent>` | Emitted when a node is deselected |
| onNodeExpand | `EventEmitter<TreeNodeExpandEvent>` | Emitted when a node expands |
| onNodeCollapse | `EventEmitter<TreeNodeCollapseEvent>` | Emitted when a node collapses |
| onLazyLoad | `EventEmitter<TreeLazyLoadEvent>` | Emitted for lazy child loading |
| onFilter | `EventEmitter<TreeFilterEvent>` | Emitted when filter changes |
| selectionChange | `EventEmitter<any>` | Two-way binding for selection |

## TreeNode Interface

```typescript
interface TreeNode {
  label?: string;
  data?: any;
  icon?: string;            // node icon class
  expandedIcon?: string;
  collapsedIcon?: string;
  children?: TreeNode[];
  leaf?: boolean;           // set true for lazy loading nodes with no known children
  expanded?: boolean;
  type?: string;            // for pTemplate="<type>" custom renderer
  styleClass?: string;
  selectable?: boolean;
  key?: string;
}
```

## Usage Example

```html
<p-tree
  [value]="categoryTree"
  selectionMode="single"
  [(selection)]="selectedCategory"
  [filter]="true"
  filterPlaceholder="Search categories..."
/>
```

## Notes

- Use `selectionMode="checkbox"` for multi-select with parent/child propagation.
- For lazy loading: set `leaf: false` on nodes, handle `onNodeExpand` to load children, update the `value` array.
- `selection` is a signal input — use `[(selection)]="selectedNode"` where `selectedNode` is a signal, or split to `[selection]="..."` + `(selectionChange)="..."`.
