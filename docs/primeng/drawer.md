# Drawer

**Import:** `import { Drawer } from 'primeng/drawer'`
**Selector:** `p-drawer`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> **PrimeNG v21 note:** `p-sidebar` / `SidebarModule` was REMOVED. Use `Drawer` from `'primeng/drawer'` instead.

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| visible | `boolean` | false | Visibility state; use `[(visible)]` for two-way binding |
| header | `string \| undefined` | undefined | Header title text |
| position | `'left' \| 'right' \| 'top' \| 'bottom' \| 'full'` | `'left'` | Position of the drawer |
| modal | `boolean` | true | Show overlay mask behind the drawer |
| blockScroll | `boolean` | false | Block document scrolling when drawer is active |
| dismissible | `boolean` | true | Close when clicking the mask |
| showCloseIcon | `boolean` | true | Display the close button |
| closeOnEscape | `boolean` | true | Close on Escape key |
| ariaCloseLabel | `string \| undefined` | undefined | Aria label for the close button |
| autoZIndex | `boolean` | true | Automatically manage z-index |
| baseZIndex | `number` | 0 | Base z-index |
| appendTo | `any` | `'self'` | Target for overlay attachment |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when drawer is shown |
| onHide | `EventEmitter<any>` | Emitted when drawer is hidden |
| visibleChange | `EventEmitter<boolean>` | Two-way binding change event |

## Usage Example (from Sakai-ng)

```html
<!-- Left drawer (default) -->
<p-drawer [(visible)]="visibleLeft" header="Drawer">
  <p>Drawer content here.</p>
</p-drawer>
<p-button label="Open" (onClick)="visibleLeft = true"></p-button>

<!-- Right drawer -->
<p-drawer [(visible)]="visibleRight" header="Drawer" position="right">
  <p>Right side content.</p>
</p-drawer>

<!-- Full screen drawer -->
<p-drawer [(visible)]="visibleFull" header="Drawer" position="full">
  <p>Full screen content.</p>
</p-drawer>
```

```typescript
// Signal-based two-way binding pattern
mobileSidebarVisible = signal(false);
// Template: [visible]="mobileSidebarVisible()" (visibleChange)="mobileSidebarVisible.set($event)"
```

## Notes

- `[(visible)]` is shorthand for `[visible]` + `(visibleChange)`.
- When using signals, use explicit split: `[visible]="mobileSidebarVisible()"` + `(visibleChange)="mobileSidebarVisible.set($event)"`.
- The `position="full"` option creates a full-screen overlay drawer.
