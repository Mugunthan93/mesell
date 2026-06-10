# CascadeSelect

**Import:** `import { CascadeSelect } from 'primeng/cascadeselect'`
**Selector:** `p-cascadeselect`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| options | `any[]` | undefined | Hierarchical data array |
| optionLabel | `string \| undefined` | undefined | Field name to use as label |
| optionValue | `string \| undefined` | undefined | Field name to use as value (defaults to full object) |
| optionDisabled | `any` | undefined | Field name for disabled state |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| disabled | `boolean` | false | Disables the component |
| inputId | `string \| undefined` | undefined | Input element ID |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` instead |
| emptyMessage | `string \| undefined` | undefined | Text when no options |
| selectOnFocus | `boolean` | false | Select option on focus |
| autoOptionFocus | `boolean` | true | Focus first option when overlay opens |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<CascadeSelectChangeEvent>` | Emitted on value change |
| onGroupChange | `EventEmitter<Event>` | Emitted when a group header is selected |
| onShow | `EventEmitter<Event>` | Emitted when overlay shows |
| onHide | `EventEmitter<Event>` | Emitted when overlay hides |
| onClear | `EventEmitter<Event>` | Emitted when selection cleared |
| onBeforeShow | `EventEmitter<Event>` | Emitted before overlay appears |
| onBeforeHide | `EventEmitter<Event>` | Emitted before overlay hides |

## Usage Example

```html
<p-cascadeselect
  [(ngModel)]="selectedCategory"
  [options]="categories"
  optionLabel="cname"
  optionGroupLabel="cname"
  [optionGroupChildren]="['subCategories', 'items']"
  placeholder="Select a City"
></p-cascadeselect>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `optionGroupChildren` specifies the nested array fields for each hierarchy level.
