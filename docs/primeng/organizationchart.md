# OrganizationChart

**Import:** `import { OrganizationChart } from 'primeng/organizationchart'`
**Selector:** `p-organizationChart`, `p-organization-chart`, `p-organizationchart`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `TreeNode[]` | undefined | Hierarchical tree data |
| selection | `TreeNode \| TreeNode[]` | undefined | Selected node(s) |
| selectionMode | `'single' \| 'multiple'` | undefined | Selection mode |
| collapsible | `boolean` | false | Whether nodes are collapsible |
| preserveSpace | `boolean` | true | Preserve space for collapsed nodes |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onNodeSelect | `EventEmitter<OrganizationChartNodeSelectEvent>` | Emitted on node selection |
| onNodeUnselect | `EventEmitter<OrganizationChartNodeUnSelectEvent>` | Emitted on node deselection |
| onNodeCollapse | `EventEmitter<OrganizationChartNodeCollapseEvent>` | Emitted on node collapse |
| onNodeExpand | `EventEmitter<OrganizationChartNodeExpandEvent>` | Emitted on node expand |

## Usage Example

```html
<p-organizationchart [value]="orgData">
  <ng-template pTemplate="person" let-node>
    <div class="text-center">
      <p-avatar [image]="node.data.image" shape="circle"></p-avatar>
      <p>{{ node.data.name }}</p>
      <p class="text-sm">{{ node.data.title }}</p>
    </div>
  </ng-template>
</p-organizationchart>
```

## Notes

- `value` is a single root `TreeNode` (from `'primeng/api'`).
- Use `pTemplate="typename"` where `typename` matches the `type` property on `TreeNode`.
