# Inplace

**Import:** `import { Inplace, InplaceDisplay, InplaceContent } from 'primeng/inplace'`
**Selector:** `p-inplace` (container), `p-inplacedisplay` / `p-inplaceDisplay` (display slot), `p-inplacecontent` / `p-inplaceContent` (content slot)
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| active | `boolean \| undefined` | false | Whether the edit content is visible |
| disabled | `boolean \| undefined` | undefined | Disables click activation |
| preventClick | `boolean \| undefined` | undefined | Prevents click activation (use `activate()` programmatically) |
| styleClass | `string \| undefined` | undefined | **Deprecated v20.** Use `class` instead |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onActivate | `EventEmitter<Event>` | Emitted when inplace is activated (display → edit) |
| onDeactivate | `EventEmitter<Event>` | Emitted when inplace is deactivated (edit → display) |

## Usage Example

```html
<p-inplace>
  <ng-template pTemplate="display">
    <span>Click to edit</span>
  </ng-template>
  <ng-template pTemplate="content">
    <input pInputText type="text" [(ngModel)]="editValue" />
  </ng-template>
</p-inplace>
```

## Notes

- Renders display content by default; clicking activates the edit content slot.
- Use `[(active)]` or listen to `(onActivate)` / `(onDeactivate)` for state tracking.
- The close button (to go back to display) uses `closeCallback` in the content template context (v20+).
