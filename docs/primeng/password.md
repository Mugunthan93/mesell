# Password

**Import:** `import { Password } from 'primeng/password'`
**Selector:** `p-password`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| feedback | `boolean` | true | Whether to show the strength indicator |
| toggleMask | `boolean \| undefined` | undefined | Show/hide toggle button |
| placeholder | `string \| undefined` | undefined | Placeholder text |
| inputId | `string \| undefined` | undefined | Input element ID |
| disabled | `boolean` | false | Disables the component |
| variant | `'filled' \| 'outlined' \| undefined` | `'outlined'` | Input variant |
| fluid | `boolean \| undefined` | false | Spans 100% width |
| size | `'large' \| 'small' \| undefined` | undefined | Component size |
| promptLabel | `string` | locale | Prompt text |
| weakLabel | `string` | locale | Weak password label |
| mediumLabel | `string` | locale | Medium password label |
| strongLabel | `string` | locale | Strong password label |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onFocus | `EventEmitter<Event>` | Emitted on focus |
| onBlur | `EventEmitter<Event>` | Emitted on blur |

## Usage Example (from Sakai-ng)

```html
<!-- With toggle mask and no strength feedback -->
<p-password
  id="password1"
  [(ngModel)]="password"
  placeholder="Password"
  [toggleMask]="true"
  styleClass="mb-4"
  [fluid]="true"
  [feedback]="false"
></p-password>

<!-- Reactive form with strength indicator -->
<p-password formControlName="password" [toggleMask]="true" [feedback]="true"></p-password>
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `[feedback]="false"` hides the password strength panel — use for simple login forms.
- `[toggleMask]="true"` adds an eye icon to show/hide the password.
