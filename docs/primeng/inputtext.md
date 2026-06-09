# InputText

**Import:** `import { InputText } from 'primeng/inputtext'`
**Selector:** `[pInputText]` (directive applied to native `<input>`)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> **DIRECTIVE — NOT a component.** Apply the `pInputText` attribute to a native `<input>` element. Do NOT use `<p-inputtext>`.

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| pSize | `'large' \| 'small' \| undefined` | undefined | Defines the size of the component |
| variant | `'filled' \| 'outlined' \| undefined` | undefined | Specifies the input variant |
| fluid | `boolean \| undefined` | undefined | Spans 100% width of the container when enabled |
| invalid | `boolean \| undefined` | false | When present, applies invalid state style |
| pInputTextPT | `InputTextPassThrough` | undefined | Pass-through attributes to DOM elements (use this, not deprecated `ptInputText`) |
| pInputTextUnstyled | `boolean \| undefined` | undefined | Renders without PrimeNG styles |

## @Output() Events

None (directive delegates to native input events: `(input)`, `(change)`, `(focus)`, `(blur)`).

## Key Interfaces / Types

```typescript
// From primeng/types/inputtext — pass-through only, no unique event types
```

## Usage Example (from Sakai-ng)

```html
<!-- Basic usage — directive on native input -->
<input pInputText id="name1" type="text" />

<!-- With placeholder and full-width -->
<input pInputText id="email" type="text" placeholder="Email address" class="w-full" />

<!-- With ngModel binding -->
<input pInputText id="email1" type="text" placeholder="Email address" [(ngModel)]="email" />

<!-- With reactive forms -->
<input pInputText id="phone" type="tel" formControlName="phone" class="w-full" />
```

## Notes

- `InputText` is a **directive**, not a component. The selector is `[pInputText]` on a native `<input>`.
- Use with `p-floatlabel` or `p-iconfield` for enhanced layouts.
- The `fluid` prop makes the input span 100% width. Alternative: use `class="w-full"`.
- `invalid` prop applies error styling — set from reactive form validation state.
- Module export: `InputTextModule` is also available for NgModule-based usage.
