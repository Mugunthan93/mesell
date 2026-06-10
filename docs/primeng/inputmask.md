# InputMask

**Import:** `import { InputMask } from 'primeng/inputmask'`
**Selector:** `[pInputMask]` (directive applied to native `<input>`)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> **DIRECTIVE — NOT a component.** Apply the `pInputMask` attribute (with the mask pattern) to a native `<input>` element.

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| pInputMask | `string \| undefined` | undefined | Mask pattern string (e.g. `'99/99/9999'`, `'+91-9999999999'`) |
| slotChar | `string` | `'_'` | Character shown in empty mask slots |
| autoClear | `boolean` | true | Clear incomplete value on blur |
| characterPattern | `string` | — | Custom regex for alpha chars in mask |
| keepBuffer | `boolean` | false | Keep buffer value in model |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onCompleteEvent | `OutputEmitterRef<void>` | Emitted when the mask is fully completed |

## Mask Format Characters

| Char | Matches |
|------|---------|
| `9` | Digit (0–9) |
| `a` | Alpha character |
| `*` | Alphanumeric |

## Usage Example

```html
<!-- Phone number mask -->
<input pInputText [pInputMask]="'+91-9999999999'" type="text" formControlName="phone" />

<!-- Date mask -->
<input pInputText [pInputMask]="'99/99/9999'" type="text" placeholder="DD/MM/YYYY" />
```

## Notes

- Import `InputMask` from `'primeng/inputmask'` — the directive selector is `[pInputMask]`.
- Implements ControlValueAccessor — works with `formControlName` and `[(ngModel)]`.
- The model value contains the actual characters typed (not the mask characters like `_`).
