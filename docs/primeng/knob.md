# Knob

**Import:** `import { Knob } from 'primeng/knob'`
**Selector:** `p-knob`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| min | `number` | 0 | Minimum value |
| max | `number` | 100 | Maximum value |
| step | `number` | 1 | Step size |
| disabled | `boolean` | false | Disables the component |
| readonly | `boolean` | false | Read-only mode |
| valueColor | `string` | — | Color of the value arc |
| rangeColor | `string` | — | Background color of the range arc |
| textColor | `string` | — | Color of the value text |
| valueTemplate | `string` | `'{value}'` | Template string for value display (e.g. `'{value}%'`) |
| size | `number` | 100 | Size of the component in pixels |
| strokeWidth | `number` | 14 | Width of the stroke |
| showValue | `boolean` | true | Whether to display the value label |
| tabindex | `number` | 0 | Tab index |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<KnobChangeEvent>` | Emitted on value change |

## Usage Example (from Sakai-ng)

```html
<!-- Basic knob -->
<p-knob [(ngModel)]="knobValue" [step]="10" [min]="-50" [max]="50" valueTemplate="{value}%" />

<!-- Reactive form -->
<p-knob formControlName="brightness" [min]="0" [max]="100" valueTemplate="{value}%"></p-knob>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `valueTemplate` uses `{value}` as the placeholder for the current value.
