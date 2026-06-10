# Timeline

**Import:** `import { Timeline } from 'primeng/timeline'`
**Selector:** `p-timeline`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| value | `any[]` | undefined | Array of timeline event data |
| layout | `'vertical' \| 'horizontal'` | `'vertical'` | Layout direction |
| align | `string` | `'left'` | Bar position: `'left'`, `'right'`, `'alternate'` (vertical) or `'top'`, `'bottom'` (horizontal) |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

None.

## Templates

| pTemplate | Purpose |
|-----------|---------|
| content | Right-side (or bottom) event content |
| opposite | Left-side (or top) event content |
| marker | Custom marker/icon element |

## Usage Example (from Sakai-ng)

```html
<!-- Vertical timeline -->
<p-timeline [value]="events" align="alternate">
  <ng-template pTemplate="marker" let-event>
    <span class="flex w-8 h-8 items-center justify-center rounded-full text-white"
          [style.backgroundColor]="event.color">
      <i [class]="event.icon"></i>
    </span>
  </ng-template>
  <ng-template pTemplate="content" let-event>
    <p-card [header]="event.status" [subheader]="event.date">
      <p>{{ event.description }}</p>
    </p-card>
  </ng-template>
  <ng-template pTemplate="opposite" let-event>
    <small class="text-surface-500">{{ event.date }}</small>
  </ng-template>
</p-timeline>

<!-- Horizontal timeline -->
<p-timeline [value]="steps" layout="horizontal" align="bottom">
  <ng-template pTemplate="content" let-step>{{ step.label }}</ng-template>
</p-timeline>
```

## Notes

- `value` is a plain data array — define your own shape (e.g., `{ status, date, icon, color }`).
- Use `pTemplate="marker"` to render custom icons/badges at each event point.
- `align="alternate"` alternates content left/right for visual variety.
