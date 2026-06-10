# Popover

**Import:** `import { Popover } from 'primeng/popover'`
**Selector:** `p-popover`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| dismissable | `boolean` | true | Close when clicking outside |
| appendTo | `any` | `'self'` | Target for overlay attachment |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when popover shows |
| onHide | `EventEmitter<any>` | Emitted when popover hides |

## Usage Example

```html
<p-popover #op>
  <div class="p-3">
    <h4>Info</h4>
    <p>Some helpful information here.</p>
  </div>
</p-popover>
<p-button label="Show Info" (onClick)="op.toggle($event)"></p-button>
```

## Notes

- Use `#op` template reference and call `op.toggle($event)` or `op.show($event)` / `op.hide()` programmatically.
- Popover appears relative to the trigger element.
- `dismissable="true"` (default) closes the popover when clicking anywhere outside it.
