# Toolbar

**Import:** `import { Toolbar } from 'primeng/toolbar'`
**Selector:** `p-toolbar`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| styleClass | `string \| undefined` | undefined | CSS class for the toolbar container |
| ariaLabelledBy | `string \| undefined` | undefined | ARIA labelledby |

## @Output() Events

None.

## Templates

| pTemplate | Purpose |
|-----------|---------|
| start | Left section content |
| end | Right section content |
| center | Center section content |

## Usage Example (from Sakai-ng)

```html
<p-toolbar styleClass="mb-4">
  <ng-template pTemplate="start">
    <p-button label="New" icon="pi pi-plus" severity="secondary" class="mr-2" />
    <p-button label="Delete" icon="pi pi-trash" severity="secondary" />
  </ng-template>
  <ng-template pTemplate="end">
    <p-iconfield>
      <p-inputicon class="pi pi-search" />
      <input pInputText [(ngModel)]="globalFilter" placeholder="Search..." />
    </p-iconfield>
    <p-button icon="pi pi-upload" severity="secondary" class="ml-2" />
    <p-button icon="pi pi-download" severity="secondary" class="ml-2" />
  </ng-template>
</p-toolbar>
```

## Notes

- Three layout zones: `start` (left), `center` (middle), `end` (right) — all optional.
- Toolbar itself provides the flex layout — no additional flex/grid CSS needed inside.
- Combine with `p-table` for standard CRUD toolbars above data tables.
