# InputGroup

**Import:** `import { InputGroup } from 'primeng/inputgroup'`
**Also import:** `import { InputGroupAddon } from 'primeng/inputgroupaddon'`
**Selector:** `p-inputgroup` (group wrapper), `p-inputgroup-addon` / `p-inputGroupAddon` (addon slot)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

None (layout wrapper only).

## @Output() Events

None.

## Usage Example

```html
<!-- Input with icon addon -->
<p-inputgroup>
  <p-inputgroup-addon>
    <i class="pi pi-user"></i>
  </p-inputgroup-addon>
  <input pInputText placeholder="Username" />
</p-inputgroup>

<!-- Input with text addon -->
<p-inputgroup>
  <p-inputgroup-addon>₹</p-inputgroup-addon>
  <input pInputText type="number" placeholder="Amount" />
  <p-inputgroup-addon>.00</p-inputgroup-addon>
</p-inputgroup>

<!-- Input with button addon -->
<p-inputgroup>
  <input pInputText placeholder="Search..." />
  <p-inputgroup-addon>
    <p-button icon="pi pi-search"></p-button>
  </p-inputgroup-addon>
</p-inputgroup>
```

## Notes

- `InputGroup` is the outer wrapper; `InputGroupAddon` is the prefix/suffix slot.
- Import both from their respective modules: `'primeng/inputgroup'` and `'primeng/inputgroupaddon'`.
