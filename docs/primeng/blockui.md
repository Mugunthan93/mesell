# BlockUI

**Import:** `import { BlockUI } from 'primeng/blockui'`
**Selector:** `p-blockUI`, `p-blockui`, `p-block-ui` (all three aliases)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| blocked | `boolean` | false | Current blocked state |
| target | `any` | undefined | Local ng-template variable referring to the element to block |
| autoZIndex | `boolean` | true | Whether to automatically manage layering |
| baseZIndex | `number` | 0 | Base zIndex value |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Usage Example

```html
<!-- Block entire page -->
<p-blockui [blocked]="loading">
  <ng-template pTemplate="content">
    <p-progressspinner></p-progressspinner>
  </ng-template>
</p-blockui>

<!-- Block a specific panel (use [target]) -->
<p-panel #myPanel header="Panel">...</p-panel>
<p-blockui [target]="myPanel" [blocked]="blocked"></p-blockui>
```

## Notes

- When no `target` is specified, blocks the entire page.
- Use `pTemplate="content"` inside for custom overlay content (spinner, message, etc.).
