# Button

**Import:** `import { Button } from 'primeng/button'`
**Selector:** `p-button` (component) or `[pButton]` (directive on native `<button>`)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Two usages: `<p-button>` component (preferred) or `<button pButton>` directive on native element.

## @Input() Props — `<p-button>` component

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | `string \| undefined` | undefined | Text of the button |
| icon | `string \| undefined` | undefined | Name of the icon (PrimeIcons class, e.g. `pi pi-check`) |
| iconPos | `'left' \| 'right' \| 'top' \| 'bottom'` | `'left'` | Position of the icon |
| type | `string` | `'button'` | Type of the button element |
| severity | `ButtonSeverity` | — | Style of the button (`'primary' \| 'secondary' \| 'success' \| 'info' \| 'warn' \| 'help' \| 'danger' \| 'contrast'`) |
| size | `'small' \| 'large' \| undefined` | undefined | Defines the size of the button |
| variant | `'outlined' \| 'text' \| undefined` | undefined | Specifies the variant of the component |
| disabled | `boolean \| undefined` | undefined | Disables the button |
| loading | `boolean` | false | Whether the button is in loading state |
| loadingIcon | `string \| undefined` | undefined | Icon to display in loading state |
| raised | `boolean` | false | Add a shadow to indicate elevation |
| rounded | `boolean` | false | Add a circular border radius |
| text | `boolean` | false | Textual button without background |
| plain | `boolean` | false | Plain textual button without background |
| outlined | `boolean` | false | Border without background |
| link | `boolean` | false | Link-style button |
| badge | `string \| undefined` | undefined | Value of the badge |
| badgeSeverity | `'success' \| 'info' \| 'warn' \| 'danger' \| 'help' \| 'primary' \| 'secondary' \| 'contrast' \| null` | `'secondary'` | Severity of the badge |
| tabindex | `number \| undefined` | undefined | Tab index |
| ariaLabel | `string \| undefined` | undefined | Aria label for accessibility |
| autofocus | `boolean \| undefined` | undefined | Auto-focuses on load |
| fluid | `boolean \| undefined` | undefined | Spans 100% width of container |
| style | `object \| null \| undefined` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |
| buttonProps | `ButtonProps` | — | Pass all props as a single object (deprecated: assign directly) |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onClick | `EventEmitter<MouseEvent>` | Emitted on button click (use on `<p-button>`, not `<button>`) |
| onFocus | `EventEmitter<FocusEvent>` | Emitted when button receives focus |
| onBlur | `EventEmitter<FocusEvent>` | Emitted when button loses focus |

## Key Interfaces / Types

```typescript
type ButtonSeverity = 'primary' | 'secondary' | 'success' | 'info' | 'warn' | 'help' | 'danger' | 'contrast' | null | undefined;
type ButtonIconPosition = 'left' | 'right' | 'top' | 'bottom';
```

## Usage Example (from Sakai-ng)

```html
<!-- Basic button -->
<p-button label="Sign In" styleClass="w-full" routerLink="/"></p-button>

<!-- With fluid prop -->
<p-button label="Submit" [fluid]="false"></p-button>

<!-- Directive on native button -->
<button pButton label="Click me" icon="pi pi-check"></button>

<!-- Loading state -->
<p-button label="Save" [loading]="saving" icon="pi pi-save"></p-button>

<!-- Outlined / secondary -->
<p-button label="Cancel" [outlined]="true" severity="secondary"></p-button>
```

## Notes

- Prefer `<p-button>` over `[pButton]` directive for new code.
- Use `(onClick)` on `<p-button>` component; use native `(click)` on a native `<button pButton>`.
- `ButtonDirective` (`[pButton]`) exports: `label`, `icon`, `loading`, `severity` are deprecated setters — assign as regular attrs or use `<p-button>` instead.
- `pButtonLabel` and `pButtonIcon` are sub-directives for fine-grained content slots.
- Module export: `ButtonModule` also available (covers `ButtonDirective`, `Button`, `ButtonLabel`, `ButtonIcon`).
