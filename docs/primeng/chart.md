# Chart

**Import:** `import { UIChart } from 'primeng/chart'`
**Selector:** `p-chart`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| type | `'bar' \| 'line' \| 'scatter' \| 'bubble' \| 'pie' \| 'doughnut' \| 'polarArea' \| 'radar'` | undefined | Type of the chart |
| data | `any` | — | Data object in Chart.js format |
| options | `any` | — | Options object in Chart.js format |
| plugins | `any[]` | `[]` | Per-chart plugins |
| width | `string \| undefined` | undefined | Width of the chart canvas |
| height | `string \| undefined` | undefined | Height of the chart canvas |
| responsive | `boolean` | true | Whether to redraw on screen resize |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby IDs |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onDataSelect | `EventEmitter<any>` | Emitted when a dataset element is selected |

## Usage Example (from Sakai-ng)

```html
<!-- Line chart -->
<p-chart type="line" [data]="lineData()" [options]="lineOptions()"></p-chart>

<!-- Bar chart -->
<p-chart type="bar" [data]="barData()" [options]="barOptions()" class="h-100"></p-chart>

<!-- Pie chart -->
<p-chart type="pie" [data]="pieData()" [options]="pieOptions()"></p-chart>

<!-- Doughnut -->
<p-chart type="doughnut" [data]="pieData()" [options]="pieOptions()"></p-chart>
```

## Notes

- Built on top of **Chart.js**. The `data` and `options` shapes follow Chart.js conventions.
- The exported class name is `UIChart` (not `Chart`) to avoid collision with the native JS `Chart` class.
- Import: `import { UIChart } from 'primeng/chart'`
- Wrap in a container with explicit height for vertical sizing control.
