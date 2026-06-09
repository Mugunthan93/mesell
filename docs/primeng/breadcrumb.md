# Breadcrumb

**Import:** `import { Breadcrumb } from 'primeng/breadcrumb'`
**Selector:** `p-breadcrumb`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[] \| undefined` | undefined | Array of MenuItems for the breadcrumb path |
| home | `MenuItem \| undefined` | undefined | MenuItem configuration for the home icon |
| homeAriaLabel | `string \| undefined` | undefined | Aria label for the home icon |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onItemClick | `EventEmitter<BreadcrumbItemClickEvent>` | Emitted when an item is selected |

## Key Interfaces / Types

```typescript
// MenuItem (from primeng/api)
interface MenuItem {
  label?: string;
  icon?: string;
  routerLink?: any;
  command?: (event: MenuItemCommandEvent) => void;
  url?: string;
  // ...more fields
}
```

## Usage Example (from Sakai-ng)

```html
<p-breadcrumb [model]="breadcrumbItems" [home]="breadcrumbHome"></p-breadcrumb>
```

```typescript
breadcrumbItems: MenuItem[] = [
  { label: 'Dashboard', routerLink: '/dashboard' },
  { label: 'Catalogs', routerLink: '/catalogs' },
  { label: 'Edit' }
];
breadcrumbHome: MenuItem = { icon: 'pi pi-home', routerLink: '/' };
```

## Notes

- `MenuItem` is from `primeng/api` — `import { MenuItem } from 'primeng/api'`.
- The separator between items is rendered automatically.
