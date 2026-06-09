# ToggleButton

**Import:** `import { ToggleButton } from 'primeng/togglebutton'`
**Selector:** `p-toggleButton`, `p-togglebutton`, `p-toggle-button`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| onLabel | `string` | `'Yes'` | Label when checked (on state) |
| offLabel | `string` | `'No'` | Label when unchecked (off state) |
| onIcon | `string \| undefined` | undefined | PrimeIcon class when checked |
| offIcon | `string \| undefined` | undefined | PrimeIcon class when unchecked |
| iconPos | `string` | `'left'` | Icon position (`'left'`, `'right'`) |
| size | `string \| undefined` | undefined | `'small'` or `'large'` |
| allowEmpty | `boolean` | true | Allow clicking to deselect (unchecked → unchecked) |
| tabindex | `number \| undefined` | undefined | Tab index |
| inputId | `string \| undefined` | undefined | Underlying input ID |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| autofocus | `boolean \| undefined` | undefined | Auto-focus on init |
| fluid | (signal) `boolean` | false | Full-width layout |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<ToggleButtonChangeEvent>` | Emitted when checked state changes |

## Usage Example

```html
<!-- Basic toggle button -->
<p-togglebutton
  onLabel="Active"
  offLabel="Inactive"
  onIcon="pi pi-check"
  offIcon="pi pi-times"
  [(ngModel)]="isActive"
/>

<!-- Reactive form -->
<p-togglebutton
  formControlName="featuredListing"
  onLabel="Featured"
  offLabel="Not Featured"
/>

<!-- Icon-only toggle -->
<p-togglebutton [(ngModel)]="isFavorite" onIcon="pi pi-heart-fill" offIcon="pi pi-heart" />
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `allowEmpty="false"` makes it radio-button-like (one state is always selected).
- Use `onIcon` / `offIcon` together with empty `onLabel` / `offLabel` for icon-only toggle buttons.
