# Dialog

**Import:** `import { Dialog } from 'primeng/dialog'`
**Selector:** `p-dialog`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| visible | `boolean` | false | Visibility of the dialog; use `[(visible)]` for two-way binding |
| header | `string \| undefined` | undefined | Title text in the dialog header |
| modal | `boolean` | true | Block background when dialog is visible |
| draggable | `boolean` | true | Enable drag to reposition |
| resizable | `boolean` | true | Enable resize |
| closable | `boolean` | true | Show close icon in header |
| closeOnEscape | `boolean` | true | Close on Escape key |
| dismissableMask | `boolean` | false | Close when clicking the mask overlay |
| showHeader | `boolean` | true | Whether to render the header |
| breakpoints | `any` | — | Responsive width map: `{ '960px': '75vw' }` |
| style | `object \| null` | undefined | Inline style (use for `{ width: '30vw' }`) |
| styleClass | `string \| undefined` | undefined | CSS class |
| maskStyleClass | `string \| undefined` | undefined | Mask CSS class |
| contentStyle | `any` | — | Style for the content section |
| appendTo | `any` | `'body'` | Target element to attach the overlay |
| rtl | `boolean` | false | RTL direction |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onShow | `EventEmitter<any>` | Emitted when dialog is shown |
| onHide | `EventEmitter<any>` | Emitted when dialog is hidden |
| visibleChange | `EventEmitter<boolean>` | Two-way binding change event |
| onResizeInit | `EventEmitter<MouseEvent>` | Emitted on resize start |
| onResizeEnd | `EventEmitter<MouseEvent>` | Emitted on resize end |
| onDragEnd | `EventEmitter<DragEvent>` | Emitted on drag end |
| onMaximize | `EventEmitter<any>` | Emitted when maximized/restored |

## Usage Example (from Sakai-ng)

```html
<!-- Basic dialog -->
<p-dialog header="Dialog" [(visible)]="display"
  [breakpoints]="{ '960px': '75vw' }"
  [style]="{ width: '30vw' }"
  [modal]="true">
  <p>Dialog content here.</p>
</p-dialog>
<p-button label="Open" (onClick)="display = true"></p-button>

<!-- Confirmation dialog -->
<p-dialog header="Confirmation" [(visible)]="displayConfirmation"
  [style]="{ width: '350px' }" [modal]="true">
  <p>Are you sure?</p>
  <ng-template pTemplate="footer">
    <p-button label="No" (onClick)="displayConfirmation = false" [text]="true"></p-button>
    <p-button label="Yes" (onClick)="confirm()" severity="danger"></p-button>
  </ng-template>
</p-dialog>
```

## Notes

- Use `[(visible)]` for two-way binding (split: `[visible]` + `(visibleChange)`).
- For programmatic dialogs (create at runtime), use `DynamicDialogService` instead.
- `breakpoints` takes an object mapping viewport widths to dialog widths.
