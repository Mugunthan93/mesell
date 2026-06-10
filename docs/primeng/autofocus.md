# AutoFocus

**Import:** `import { AutoFocus } from 'primeng/autofocus'`
**Selector:** `[pAutoFocus]` (DIRECTIVE on any focusable element)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> `AutoFocus` is a DIRECTIVE that manages focus on a focusable element when the component loads.

## @Input() Props

| Prop | Attribute alias | Type | Default | Description |
|------|----------------|------|---------|-------------|
| autofocus | `pAutoFocus` | `boolean` | true | When true, the element receives focus on mount |

## @Output() Events

None.

## Usage Example

```html
<!-- Focus the first input on form mount -->
<input pInputText pAutoFocus [pAutoFocus]="true" placeholder="Phone number" />

<!-- Conditionally auto-focus -->
<input pInputText [pAutoFocus]="isFirstField" placeholder="Name" />

<!-- Focus a button on dialog open -->
<p-button label="Confirm" [pAutoFocus]="true" />
```

## Notes

- Most PrimeNG form components already have an `autofocus` @Input prop — use that when available.
- Use `[pAutoFocus]` directive on native elements or custom components that do not expose an `autofocus` prop.
- Setting `[pAutoFocus]="false"` is a no-op — the directive only fires when the value is truthy.
