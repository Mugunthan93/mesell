# Message

**Import:** `import { Message } from 'primeng/message'`
**Selector:** `p-message`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| severity | `'success' \| 'info' \| 'warn' \| 'error' \| 'secondary' \| 'contrast' \| null` | `'info'` | Severity level of the message |
| text | `string \| undefined` | undefined | **Deprecated since v20.** Use content projection instead |
| escape | `boolean` | true | **Deprecated since v20.** Use content projection instead |
| closable | `boolean` | false | Whether message can be closed manually with a close icon |
| icon | `string \| undefined` | undefined | Icon to display in the message |
| closeIcon | `string \| undefined` | undefined | Icon for the close button |
| life | `number \| undefined` | undefined | Delay in milliseconds to auto-close the message |
| size | `'large' \| 'small' \| undefined` | undefined | Defines the size of the component |
| variant | `'outlined' \| 'text' \| 'simple' \| undefined` | undefined | Visual variant |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| showTransitionOptions | `string` | `'300ms ease-out'` | **Deprecated since v21.** Use `motionOptions` instead |
| hideTransitionOptions | `string` | `'200ms cubic-bezier(0.86, 0, 0.07, 1)'` | **Deprecated since v21.** Use `motionOptions` instead |
| motionOptions | `MotionOptions \| undefined` | undefined | Animation motion options |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onClose | `EventEmitter<{ originalEvent: Event }>` | Emitted when the message is closed |

## Key Interfaces / Types

```typescript
// MessageContainerTemplateContext — for custom containerTemplate
// IconTemplate / CloseIconTemplate — for custom icon slots
```

## Usage Example (from Sakai-ng)

No direct Sakai-ng example found. Minimal usage:

```html
<!-- Info message using content projection (preferred v20+ pattern) -->
<p-message severity="info">Your session will expire in 5 minutes.</p-message>

<!-- Error message with close button -->
<p-message severity="error" [closable]="true" (onClose)="onMessageClose($event)">
  Invalid phone number. Please try again.
</p-message>

<!-- Success message with auto-close -->
<p-message severity="success" [life]="3000">Profile saved successfully!</p-message>

<!-- Warn message, outlined variant -->
<p-message severity="warn" variant="outlined">Please complete your profile.</p-message>

<!-- Conditional display -->
@if (errorMessage) {
  <p-message severity="error">{{ errorMessage }}</p-message>
}
```

## Notes

- Since v20, use **content projection** (`<p-message>text</p-message>`) instead of the deprecated `text` prop.
- `severity` controls the color and icon: `info` = blue, `success` = green, `warn` = orange, `error` = red.
- For toast-style notifications (auto-dismiss at top of page), use `p-toast` + `MessageService` instead.
- Standalone component — import `Message` directly in component's `imports[]` array.
