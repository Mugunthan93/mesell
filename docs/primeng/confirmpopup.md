# ConfirmPopup

**Import:** `import { ConfirmPopup } from 'primeng/confirmpopup'`
**Import service:** `import { ConfirmationService } from 'primeng/api'`
**Selector:** `p-confirmpopup`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| key | `string \| undefined` | undefined | Optional key to match confirm objects |
| defaultFocus | `string` | `'accept'` | Element to focus: `'accept'`, `'reject'`, or `'none'` |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None (use `ConfirmationService` callbacks).

## Usage Example

```html
<!-- Place in template -->
<p-confirmpopup></p-confirmpopup>
<p-button label="Delete" (onClick)="confirmDelete($event)"></p-button>
```

```typescript
confirmDelete(event: Event) {
  this.confirmationService.confirm({
    target: event.target as EventTarget,
    message: 'Are you sure?',
    accept: () => { this.delete(); }
  });
}
```

## Notes

- Similar to `ConfirmDialog` but appears near the triggering element (popup style).
- `target` in the confirmation object points the popup to the source element.
- Requires `ConfirmationService` in providers.
