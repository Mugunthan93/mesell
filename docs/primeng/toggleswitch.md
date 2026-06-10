# ToggleSwitch

**Import:** `import { ToggleSwitch } from 'primeng/toggleswitch'`
**Selector:** `p-toggleswitch`, `p-toggleSwitch`, `p-toggle-switch`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| inputId | `string \| undefined` | undefined | Underlying input ID (for `<label for>`) |
| tabindex | `number \| undefined` | undefined | Tab index |
| readonly | `boolean` | false | Makes the switch read-only |
| trueValue | `any` | true | Value emitted when switch is on |
| falseValue | `any` | false | Value emitted when switch is off |
| ariaLabel | `string \| undefined` | undefined | ARIA label |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |
| autofocus | `boolean \| undefined` | undefined | Auto-focus on init |
| size | (signal) `'small' \| 'large' \| undefined` | undefined | Size variant |
| disabled | `boolean` | false | Disables the switch |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onChange | `EventEmitter<ToggleSwitchChangeEvent>` | Emitted when switch state changes |

## Usage Example

```html
<!-- Basic toggle switch -->
<p-toggleswitch [(ngModel)]="isEnabled" />

<!-- With label -->
<div class="flex items-center gap-2">
  <p-toggleswitch inputId="notif" [(ngModel)]="notifications" />
  <label for="notif">Enable notifications</label>
</div>

<!-- Reactive form -->
<p-toggleswitch formControlName="autoPublish" />

<!-- Custom true/false values -->
<p-toggleswitch [(ngModel)]="status" trueValue="active" falseValue="paused" />
```

## Notes

- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- `trueValue` / `falseValue` allow binding non-boolean values (e.g., string status codes).
- Always pair with `<label [for]="inputId">` for accessibility (44px touch target required for MeeSell mobile-first audience).
