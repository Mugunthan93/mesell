# Toast

**Import:** `import { Toast } from 'primeng/toast'`
**Import service:** `import { MessageService } from 'primeng/api'`
**Selector:** `p-toast`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| key | `string \| undefined` | undefined | Named channel (used for multiple toast instances) |
| life | `number` | 3000 | Auto-dismiss timeout in milliseconds |
| position | `ToastPositionType` | `'top-right'` | Display position: `'top-right'`, `'top-left'`, `'top-center'`, `'bottom-right'`, `'bottom-left'`, `'bottom-center'`, `'center'` |
| preventDuplicates | `boolean` | false | Prevent duplicate messages |
| preventOpenDuplicates | `boolean` | false | Prevent duplicates while existing toasts are shown |
| baseZIndex | `number` | 0 | Base z-index |
| autoZIndex | `boolean` | true | Auto-manage z-index |
| breakpoints | `object` | undefined | Responsive breakpoint config |
| motionOptions | (signal) | — | Animation config |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onClose | `EventEmitter<ToastCloseEvent>` | Emitted when a toast is closed |

## Templates

| pTemplate | Purpose |
|-----------|---------|
| message | Custom toast body (receives `message` context) |

## MessageService API

```typescript
import { MessageService } from 'primeng/api';

// In component or service
const msgSvc = inject(MessageService);

// Show a toast
msgSvc.add({ severity: 'success', summary: 'Saved', detail: 'Catalog updated.' });
msgSvc.add({ severity: 'error', summary: 'Error', detail: 'Upload failed. Try again.' });
msgSvc.add({ severity: 'warn', summary: 'Warning', detail: 'Image quality low.' });
msgSvc.add({ severity: 'info', summary: 'Processing', detail: 'AI is generating fields...' });

// Dismiss all
msgSvc.clear();
// Dismiss specific key
msgSvc.clear('upload-toast');
```

## Severity Values

| Value | Appearance |
|-------|-----------|
| `success` | Green |
| `info` | Blue |
| `warn` | Orange |
| `error` | Red |
| `secondary` | Grey |
| `contrast` | Inverted |

## Usage Example

```html
<!-- Place once in AppComponent or layout -->
<p-toast position="top-right" [life]="4000" />

<!-- Named toast for specific contexts -->
<p-toast key="upload" position="bottom-center" />
```

```typescript
// In any component — inject MessageService
readonly msgSvc = inject(MessageService);

onSave() {
  this.catalogSvc.save(this.form.value).subscribe({
    next: () => this.msgSvc.add({ severity: 'success', summary: 'Saved', detail: 'Catalog saved successfully.' }),
    error: (e) => this.msgSvc.add({ severity: 'error', summary: 'Error', detail: e.message })
  });
}
```

## Notes

- `MessageService` must be provided: add `MessageService` to the `providers` array in `app.config.ts` or the component.
- Place `<p-toast>` once at the app shell level (e.g., `AppComponent` template) — not inside each page component.
- For named toast channels (multiple positions), use `key` on `<p-toast>` and pass `{ key: '...', severity: ... }` to `MessageService.add()`.
- `life: 0` makes a toast sticky (does not auto-dismiss).
