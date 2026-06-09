# PanelMenu

**Import:** `import { PanelMenu } from 'primeng/panelmenu'`
**Selector:** `p-panelMenu`, `p-panelmenu`, `p-panel-menu`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| model | `MenuItem[]` | undefined | Array of menu items (with nested `items`) |
| multiple | `boolean` | true | Allow multiple panels to be open simultaneously |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onItemClick | `EventEmitter<PanelMenuItemClickEvent>` | Emitted when an item is clicked |

## Usage Example (from Sakai-ng)

```html
<p-panelmenu [model]="panelMenuItems" />
```

```typescript
panelMenuItems: MenuItem[] = [
  {
    label: 'Catalogs',
    icon: 'pi pi-folder',
    items: [
      { label: 'New Catalog', icon: 'pi pi-plus', routerLink: ['/catalogs/new'] },
      { label: 'My Catalogs', icon: 'pi pi-list', routerLink: ['/dashboard'] }
    ]
  }
];
```

## Notes

- Combines accordion-style panels with nested menu items.
- Each top-level item in `model` becomes a collapsible panel.
- Nested `items` appear inside the panel body.
