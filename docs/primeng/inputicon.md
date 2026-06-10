# InputIcon

**Import:** `import { InputIcon } from 'primeng/inputicon'`
**Selector:** `p-inputicon`, `p-inputIcon`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

None (icon content slot only).

## @Output() Events

None.

## Usage Example (from Sakai-ng)

```html
<!-- Left icon (default) -->
<p-iconfield>
  <p-inputicon class="pi pi-search" />
  <input pInputText type="text" placeholder="Search..." />
</p-iconfield>

<!-- Right icon using iconPosition -->
<p-iconfield iconPosition="right">
  <input pInputText type="text" formControlName="email" />
  <p-inputicon class="pi pi-envelope" />
</p-iconfield>
```

## Notes

- Always used inside `p-iconfield`. Do not use standalone.
- The icon class (`pi pi-*`) goes on the `p-inputicon` element itself as a regular CSS class.
- Import `InputIcon` from `'primeng/inputicon'` and `IconField` from `'primeng/iconfield'` together.
