# Steps

**Import:** `import { Steps } from 'primeng/steps'`
**Selector:** `p-steps`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> `Steps` renders a horizontal wizard progress indicator. For the composable interactive stepper with panels, use `Stepper` (`p-stepper`) instead.

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[]` | undefined | Array of step items |
| activeIndex | `number` | 0 | Index of the currently active step |
| readonly | `boolean` | true | When false, steps are clickable |
| exact | `boolean` | true | Apply exact active match on router links |
| style | `object` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| activeIndexChange | `EventEmitter<number>` | Emitted when a step is clicked (requires `readonly="false"`) |

## Usage Example

```html
<p-steps
  [model]="stepItems"
  [(activeIndex)]="currentStep"
  [readonly]="false"
/>

<!-- In component -->
stepItems: MenuItem[] = [
  { label: 'Product Info' },
  { label: 'Images' },
  { label: 'Pricing' },
  { label: 'Review' }
];
currentStep = 0;
```

## Notes

- `Steps` is a **display-only** navigation indicator — it does not manage panel content.
- For a full wizard with panels, use `Stepper` (`p-stepper`).
- Set `[readonly]="false"` to make steps clickable for non-linear navigation.
- `model` uses the `MenuItem` interface from `primeng/api`.
