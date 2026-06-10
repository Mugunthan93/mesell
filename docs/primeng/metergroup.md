# MeterGroup

**Import:** `import { MeterGroup } from 'primeng/metergroup'`
**Selector:** `p-meterGroup`, `p-metergroup`, `p-meter-group`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `MeterItem[]` | undefined | Array of meter items to display |
| min | `number` | 0 | Minimum value |
| max | `number` | 100 | Maximum value |
| orientation | `'horizontal' \| 'vertical'` | `'horizontal'` | Orientation |
| labelPosition | `'start' \| 'end'` | `'end'` | Position of the label |
| labelOrientation | `'horizontal' \| 'vertical'` | `'horizontal'` | Label layout direction |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Key Interfaces

```typescript
interface MeterItem {
  label?: string;
  value: number;
  color?: string;
  icon?: string;
}
```

## Usage Example

```html
<p-metergroup [value]="[
  { label: 'Apps', color: '#34d399', value: 25 },
  { label: 'Messages', color: '#fbbf24', value: 15 },
  { label: 'Media', color: '#60a5fa', value: 20 }
]"></p-metergroup>
```

## Notes

- Visualizes multiple values as stacked horizontal/vertical bars summing to 100%.
- `value` items should sum to ≤ max (100 by default).
