# Chip

**Import:** `import { Chip } from 'primeng/chip'`
**Selector:** `p-chip`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| label | `string \| undefined` | undefined | Text to display |
| icon | `string \| undefined` | undefined | PrimeIcons class for the icon |
| image | `string \| undefined` | undefined | Image URL to display |
| alt | `string \| undefined` | undefined | Alt text for the image |
| styleClass | `string \| undefined` | undefined | CSS class |
| disabled | `boolean \| undefined` | undefined | Disables the chip when true |
| removable | `boolean \| undefined` | undefined | Whether to display a remove icon |
| removeIcon | `string \| undefined` | undefined | Icon class for the remove button |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onRemove | `EventEmitter<MouseEvent>` | Emitted when the remove icon is clicked |
| onImageError | `EventEmitter<Event>` | Emitted when image loading fails |

## Usage Example (from Sakai-ng)

```html
<!-- Basic chips -->
<p-chip label="Action" styleClass="m-1"></p-chip>
<p-chip label="Comedy" styleClass="m-1"></p-chip>

<!-- Removable chip -->
<p-chip label="Thriller" styleClass="m-1" [removable]="true" (onRemove)="onChipRemove($event)"></p-chip>

<!-- Icon chip -->
<p-chip label="Google" icon="pi pi-google" styleClass="m-1"></p-chip>

<!-- Image chip -->
<p-chip label="Amy Elsner" image="https://example.com/avatar.png" styleClass="m-1"></p-chip>
```

## Notes

- Not a form control — no ControlValueAccessor. Used for display/tagging purposes.
- For selectable chip groups, use `p-selectbutton` or `mat-chip-listbox` instead.
