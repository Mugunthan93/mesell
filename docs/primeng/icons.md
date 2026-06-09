# PrimeIcons

**Import:** No import required — global CSS via stylesheet
**Usage:** Apply class `pi pi-{icon-name}` to any `<i>` or `<span>` element
**Angular version:** PrimeNG 21.1.9 (bundled PrimeIcons v7)

## Setup

```css
/* In angular.json styles array (already configured in MeeSell) */
"node_modules/primeicons/primeicons.css"
```

```typescript
// Or in styles.css
@import 'primeicons/primeicons.css';
```

## Usage Pattern

```html
<!-- Standalone icon -->
<i class="pi pi-check"></i>
<i class="pi pi-times text-red-500 text-xl"></i>

<!-- Fixed-width icon (menu items, aligned lists) -->
<i class="pi pi-fw pi-table"></i>

<!-- In p-button -->
<p-button icon="pi pi-save" label="Save" />
<p-button icon="pi pi-plus" severity="primary" />

<!-- In p-inputicon (inside p-iconfield) -->
<p-iconfield>
  <p-inputicon class="pi pi-search" />
  <input pInputText placeholder="Search" />
</p-iconfield>

<!-- In MenuItem.icon -->
items: MenuItem[] = [
  { label: 'New', icon: 'pi pi-fw pi-plus' },
  { label: 'Delete', icon: 'pi pi-fw pi-trash' }
];
```

## Common Icons (MeeSell use cases)

| Icon class | Description |
|-----------|-------------|
| `pi pi-plus` | Add / create |
| `pi pi-pencil` | Edit |
| `pi pi-trash` | Delete |
| `pi pi-save` | Save |
| `pi pi-check` | Success / confirm |
| `pi pi-times` | Close / cancel |
| `pi pi-search` | Search / filter |
| `pi pi-filter` | Filter |
| `pi pi-filter-slash` | Clear filter |
| `pi pi-upload` | Upload |
| `pi pi-download` | Download |
| `pi pi-file` | File |
| `pi pi-image` | Image |
| `pi pi-images` | Multiple images |
| `pi pi-camera` | Camera |
| `pi pi-tag` | Tag / label |
| `pi pi-tags` | Multiple tags |
| `pi pi-list` | List view |
| `pi pi-th-large` | Grid view |
| `pi pi-bars` | Menu / hamburger |
| `pi pi-ellipsis-v` | More options (vertical) |
| `pi pi-ellipsis-h` | More options (horizontal) |
| `pi pi-info-circle` | Info |
| `pi pi-exclamation-triangle` | Warning |
| `pi pi-times-circle` | Error |
| `pi pi-check-circle` | Success circle |
| `pi pi-spinner` | Loading (CSS animated) |
| `pi pi-spin pi-spinner` | Spinning loader |
| `pi pi-arrow-left` | Back |
| `pi pi-arrow-right` | Forward |
| `pi pi-angle-up` | Collapse / up |
| `pi pi-angle-down` | Expand / down |
| `pi pi-chevron-right` | Breadcrumb separator |
| `pi pi-home` | Home / dashboard |
| `pi pi-shopping-cart` | Cart / catalog |
| `pi pi-dollar` | Pricing / money |
| `pi pi-percentage` | Margin / discount |
| `pi pi-chart-bar` | Analytics |
| `pi pi-table` | Table / export |
| `pi pi-file-excel` | Excel / XLSX export |
| `pi pi-eye` | Preview |
| `pi pi-eye-slash` | Hide |
| `pi pi-copy` | Copy |
| `pi pi-share-alt` | Share |
| `pi pi-star` | Rating (empty) |
| `pi pi-star-fill` | Rating (filled) |
| `pi pi-user` | User / profile |
| `pi pi-phone` | Phone |
| `pi pi-lock` | Security / OTP |
| `pi pi-unlock` | Unlocked |
| `pi pi-sign-out` | Logout |
| `pi pi-cog` | Settings |
| `pi pi-refresh` | Refresh / retry |
| `pi pi-sort` | Sort |
| `pi pi-sort-up` | Sort ascending |
| `pi pi-sort-down` | Sort descending |

## Sizing

Icons inherit font-size from parent. Override with Tailwind text-size utilities:

```html
<i class="pi pi-check text-sm"></i>   <!-- 14px -->
<i class="pi pi-check text-base"></i> <!-- 16px -->
<i class="pi pi-check text-xl"></i>   <!-- 20px -->
<i class="pi pi-check text-2xl"></i>  <!-- 24px -->
```

## Fixed-width (`pi-fw`)

Add `pi-fw` alongside the icon class for fixed-width icons (useful in menus to keep labels aligned):

```html
<i class="pi pi-fw pi-table"></i>
```

## Notes

- Full icon list: https://primeng.org/icons (or run `grep "pi-" node_modules/primeicons/primeicons.css`)
- Icons are vector (font-based) — color with `text-*` Tailwind or CSS `color`.
- `pi pi-spin pi-spinner` creates a CSS-animated spinner — use for inline loading states.
- `p-button[icon]`, `MenuItem.icon`, and `p-inputicon[class]` all accept the `pi pi-*` string directly.
