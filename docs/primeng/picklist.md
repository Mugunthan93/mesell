# PickList

**Import:** `import { PickList } from 'primeng/picklist'`
**Selector:** `p-pickList`, `p-picklist`, `p-pick-list`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| source | `any[]` | undefined | Source list items |
| target | `any[]` | undefined | Target list items |
| sourceHeader | `string \| undefined` | undefined | Source list header |
| targetHeader | `string \| undefined` | undefined | Target list header |
| sourceFilterPlaceholder | `string \| undefined` | undefined | Source filter placeholder |
| targetFilterPlaceholder | `string \| undefined` | undefined | Target filter placeholder |
| filterBy | `string \| undefined` | undefined | Field to filter by |
| filter | `boolean` | false | Show filter inputs |
| disabled | `boolean` | false | Disables the component |
| dataKey | `string \| undefined` | undefined | Unique field for tracking |
| metaKeySelection | `boolean` | true | Toggle multiple selection with meta key |
| breakpoint | `string` | `'960px'` | Responsive breakpoint |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onMoveToTarget | `EventEmitter<PickListMoveToTargetEvent>` | Emitted when items move to target |
| onMoveAllToTarget | `EventEmitter<PickListMoveAllToTargetEvent>` | Emitted when all items move to target |
| onMoveToSource | `EventEmitter<PickListMoveToSourceEvent>` | Emitted when items move to source |
| onMoveAllToSource | `EventEmitter<PickListMoveAllToSourceEvent>` | Emitted when all items move to source |
| onSourceReorder | `EventEmitter<PickListSourceReorderEvent>` | Emitted on source reorder |
| onTargetReorder | `EventEmitter<PickListTargetReorderEvent>` | Emitted on target reorder |
| onSourceSelect | `EventEmitter<PickListSourceSelectEvent>` | Emitted on source selection |
| onTargetSelect | `EventEmitter<PickListTargetSelectEvent>` | Emitted on target selection |
| sourceChange | `EventEmitter<any[]>` | Two-way binding for source |
| targetChange | `EventEmitter<any[]>` | Two-way binding for target |

## Usage Example

```html
<p-picklist
  [(source)]="availableProducts"
  [(target)]="selectedProducts"
  sourceHeader="Available"
  targetHeader="Selected"
  [dragdrop]="true"
  [responsive]="true"
  filterBy="name"
>
  <ng-template pTemplate="item" let-item>
    <div>{{ item.name }}</div>
  </ng-template>
</p-picklist>
```

## Notes

- Two-list transfer component — use `[(source)]` and `[(target)]` for two-way binding.
- Use `pTemplate="item"` for custom item rendering in both lists.
