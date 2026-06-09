# ConfirmDialog

**Import:** `import { ConfirmDialog } from 'primeng/confirmdialog'`
**Import service:** `import { ConfirmationService } from 'primeng/api'`
**Selector:** `p-confirmDialog`, `p-confirmdialog`, `p-confirm-dialog`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| header | `string \| undefined` | undefined | Title text of the dialog |
| message | `string \| undefined` | undefined | Message content |
| icon | `string \| undefined` | undefined | Icon next to the message |
| acceptLabel | `string \| undefined` | undefined | Accept button label |
| rejectLabel | `string \| undefined` | undefined | Reject button label |
| acceptIcon | `string \| undefined` | undefined | Accept button icon |
| rejectIcon | `string \| undefined` | undefined | Reject button icon |
| acceptButtonStyleClass | `string \| undefined` | undefined | Accept button CSS class |
| rejectButtonStyleClass | `string \| undefined` | undefined | Reject button CSS class |
| acceptVisible | `boolean` | true | Whether accept button is visible |
| rejectVisible | `boolean` | true | Whether reject button is visible |
| closeOnEscape | `boolean` | true | Close on Escape key |
| dismissableMask | `boolean` | false | Close by clicking the mask |
| key | `string \| undefined` | undefined | Key to match confirmation objects |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| maskStyleClass | `string \| undefined` | undefined | Mask CSS class |

## @Output() Events

None (use `ConfirmationService` callbacks instead).

## Usage Example

```html
<!-- Place once in app or layout template -->
<p-confirmdialog></p-confirmdialog>
```

```typescript
// In component
import { ConfirmationService } from 'primeng/api';

confirmDelete() {
  this.confirmationService.confirm({
    message: 'Are you sure you want to delete this product?',
    header: 'Confirm Delete',
    icon: 'pi pi-exclamation-triangle',
    accept: () => { this.deleteProduct(); },
    reject: () => { /* cancelled */ }
  });
}
```

## Notes

- Requires `ConfirmationService` in providers: `providers: [ConfirmationService]`.
- Only one `<p-confirmdialog>` per page. Use `key` prop for multiple independent dialogs.
- The `ConfirmationService` is from `'primeng/api'` (same module as `MenuItem`).
