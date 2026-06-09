# Overlay

**Import:** `import { Overlay } from 'primeng/overlay'`
**Selector:** `p-overlay`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| visible | `boolean` | false | Visibility of the overlay |
| appendTo | `any` | `'body'` | Target element to attach the overlay |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when overlay shows |
| onHide | `EventEmitter<any>` | Emitted when overlay hides |
| visibleChange | `EventEmitter<boolean>` | Two-way visibility change |

## Notes

- Low-level overlay primitive used internally by PrimeNG components like `p-select`, `p-datepicker`, etc.
- For most use cases, prefer higher-level components (`p-dialog`, `p-popover`, `p-drawer`) instead of using `p-overlay` directly.
