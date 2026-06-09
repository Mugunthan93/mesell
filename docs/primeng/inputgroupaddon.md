# InputGroupAddon

**Import:** `import { InputGroupAddon } from 'primeng/inputgroupaddon'`
**Selector:** `p-inputgroup-addon`, `p-inputGroupAddon`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

None (content slot only).

## Usage Example

See `inputgroup.md` for combined usage with `p-inputgroup`.

```html
<p-inputgroup>
  <p-inputgroup-addon><i class="pi pi-phone"></i></p-inputgroup-addon>
  <input pInputText type="tel" formControlName="phone" />
</p-inputgroup>
```

## Notes

- Used inside `p-inputgroup` as a prefix or suffix slot.
- Can contain icons, text, or small buttons.
