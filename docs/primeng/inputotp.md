# InputOtp

**Import:** `import { InputOtp } from 'primeng/inputotp'`
**Selector:** `p-inputOtp`, `p-inputotp`, `p-input-otp` (all three aliases work)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| length | `number` | — | Number of OTP characters to display |
| readonly | `boolean` | false | When present, specifies that the field is read-only |
| tabindex | `number \| null` | null | Index of the element in tabbing order |
| styleClass | `string \| undefined` | undefined | Style class of the input element |
| mask | `boolean` | false | Mask pattern (hides input characters) |
| integerOnly | `boolean` | false | When present, restricts input to integers only |
| autofocus | `boolean \| undefined` | undefined | Component auto-focuses on load |
| variant | `'filled' \| 'outlined' \| undefined` | undefined | Input variant style |
| size | `'large' \| 'small' \| undefined` | undefined | Component size |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<InputOtpChangeEvent>` | Callback invoked on value change |
| onFocus | `EventEmitter<Event>` | Callback invoked when component receives focus |
| onBlur | `EventEmitter<Event>` | Callback invoked when component loses focus |

## Key Interfaces / Types

```typescript
// InputOtpChangeEvent (from primeng/types/inputotp)
interface InputOtpChangeEvent {
  value: any;
  originalEvent: Event;
}
```

## Usage Example (from Sakai-ng)

No direct Sakai-ng example found. Minimal usage:

```html
<!-- Basic OTP input, 6 digits -->
<p-inputotp [length]="6" [(ngModel)]="otpValue" />

<!-- Reactive form binding -->
<p-inputotp [length]="6" formControlName="otp" [integerOnly]="true" />

<!-- Masked OTP -->
<p-inputotp [length]="6" [mask]="true" [(ngModel)]="otpValue" />
```

## Notes

- Implements ControlValueAccessor — works directly with `formControlName` and `[(ngModel)]`.
- The `length` prop defines how many individual input boxes are rendered.
- `integerOnly="true"` limits input to digits only — recommended for numeric OTPs.
- The component selector has three aliases: use `p-inputotp` (lowercase) for consistency.
- Standalone component — import `InputOtp` directly in component's `imports[]` array.
- Module export: `InputOtpModule` also available.
