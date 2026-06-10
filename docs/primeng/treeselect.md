# TreeSelect

**Import:** `import { TreeSelect } from 'primeng/treeselect'`
**Selector:** `p-treeSelect`, `p-treeselect`, `p-tree-select`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | `TreeNode[]` | undefined | Hierarchical tree data |
| selectionMode | `'single'\|'multiple'\|'checkbox'` | `'single'` | Selection mode |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| display | `'comma'\|'chip'` | `'comma'` | Display style for selected items |
| filter | `boolean` | false | Show filter input |
| filterBy | `string` | `'label'` | Field to filter by |
| filterMode | `'lenient'\|'strict'` | `'lenient'` | Filter algorithm |
| filterPlaceholder | `string` | undefined | Filter input placeholder |
| showClear | `boolean` | false | Show clear button |
| scrollHeight | `string` | `'400px'` | Dropdown panel max height |
| propagateSelectionUp | `boolean` | true | Propagate checkbox selection upward |
| propagateSelectionDown | `boolean` | true | Propagate checkbox selection downward |
| loading | `boolean` | false | Show loading indicator |
| emptyMessage | `string` | `'No results found'` | Empty state text |
| inputId | `string` | undefined | Input element ID |
| tabindex | `number` | undefined | Tab index |
| ariaLabel | `string` | undefined | ARIA label |
| autofocus | `boolean` | false | Auto-focus on init |
| variant | (signal) `'filled'\|'outlined'` | undefined | Visual variant |
| fluid | (signal) `boolean` | false | Full-width |
| size | (signal) `string` | undefined | `'small'` or `'large'` |
| appendTo | (signal) `any` | undefined | Overlay target |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onNodeSelect | `EventEmitter<TreeSelectNodeSelectEvent>` | Emitted when a node is selected |
| onNodeUnselect | `EventEmitter<TreeSelectNodeUnselectEvent>` | Emitted when a node is deselected |
| onNodeExpand | `EventEmitter<TreeSelectNodeExpandEvent>` | Emitted when a node expands |
| onNodeCollapse | `EventEmitter<TreeSelectNodeCollapseEvent>` | Emitted when a node collapses |
| onShow | `EventEmitter<any>` | Emitted when panel opens |
| onHide | `EventEmitter<any>` | Emitted when panel closes |
| onClear | `EventEmitter<any>` | Emitted when cleared |
| onFilter | `EventEmitter<any>` | Emitted on filter |
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |

## Usage Example

```html
<p-treeselect
  [options]="categoryTree"
  [(ngModel)]="selectedCategory"
  selectionMode="single"
  placeholder="Select category"
  [filter]="true"
  class="w-full"
/>

<!-- Checkbox mode with reactive form -->
<p-treeselect
  formControlName="categories"
  [options]="categoryTree"
  selectionMode="checkbox"
  display="chip"
  [propagateSelectionDown]="true"
  class="w-full"
/>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- Accepts the same `TreeNode[]` interface as `p-tree`.
- `display="chip"` shows selected items as removable chips (better for multi-select).
- `selectionMode="checkbox"` enables parent/child propagation for hierarchical selection.
