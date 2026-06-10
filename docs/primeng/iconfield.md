# IconField

**Import:** `import { IconField } from 'primeng/iconfield'`
**Selector:** `p-iconfield`, `p-iconField`, `p-icon-field` (all three aliases)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> Use with `p-inputicon` (companion component) to display icons inside an input field.

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| iconPosition | `'right' \| 'left'` | `'left'` | Position of the icon inside the field |
| styleClass | `string` | — | **Deprecated since v20.** Use `class` attribute instead |

## @Output() Events

None.

## Key Interfaces / Types

None.

## Usage Example (from Sakai-ng)

```html
<!-- Icon on the left (default) -->
<p-iconfield>
  <p-inputicon class="pi pi-user" />
  <input pInputText id="username" type="text" placeholder="Username" />
</p-iconfield>

<!-- Icon on the left, explicit position -->
<p-iconfield iconPosition="left">
  <p-inputicon class="pi pi-search" />
  <input pInputText type="text" placeholder="Search..." [(ngModel)]="searchTerm" />
</p-iconfield>

<!-- Icon on the right -->
<p-iconfield iconPosition="right">
  <input pInputText type="text" formControlName="email" />
  <p-inputicon class="pi pi-envelope" />
</p-iconfield>
```

## Notes

- `p-iconfield` wraps the input; `p-inputicon` positions the icon inside the field.
- Import both `IconField` and `InputIcon` when using this pattern:
  `import { IconField } from 'primeng/iconfield'` and `import { InputIcon } from 'primeng/inputicon'`
- The `styleClass` prop is deprecated — use standard Angular `class` attribute instead.
- Standalone component — import `IconField` directly in component's `imports[]` array.
