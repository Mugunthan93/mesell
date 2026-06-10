# DynamicDialog

**Import:** `import { DynamicDialogRef, DynamicDialogConfig } from 'primeng/dynamicdialog'`
**Service:** `import { DialogService } from 'primeng/dynamicdialog'`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

> DynamicDialog creates dialog components at runtime via the `DialogService`. It does not have a template selector — it is programmatic only.

## DialogService.open() Options (DynamicDialogConfig)

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| header | `string` | undefined | Dialog header text |
| width | `string` | undefined | Width of the dialog |
| height | `string` | undefined | Height of the dialog |
| data | `any` | undefined | Data passed to the component |
| modal | `boolean` | true | Block background |
| closable | `boolean` | true | Show close button |
| closeOnEscape | `boolean` | true | Close on Escape |
| dismissableMask | `boolean` | false | Close on mask click |
| styleClass | `string` | undefined | CSS class |
| breakpoints | `object` | undefined | Responsive breakpoints |
| templates | `any` | undefined | Custom templates |

## Usage Example

```typescript
// In component
import { DialogService, DynamicDialogRef } from 'primeng/dynamicdialog';

ref: DynamicDialogRef | undefined;

constructor(private dialogService: DialogService) {}

open() {
  this.ref = this.dialogService.open(MyDialogComponent, {
    header: 'Title',
    width: '50vw',
    data: { id: 123 }
  });
  this.ref.onClose.subscribe((result) => {
    console.log(result);
  });
}
```

```typescript
// Inside MyDialogComponent
import { DynamicDialogRef, DynamicDialogConfig } from 'primeng/dynamicdialog';

constructor(
  private ref: DynamicDialogRef,
  private config: DynamicDialogConfig
) {
  console.log(this.config.data); // { id: 123 }
}

close() {
  this.ref.close({ result: 'ok' });
}
```

## Notes

- Provide `DialogService` in the component's providers: `providers: [DialogService]`.
- Access passed data via `DynamicDialogConfig.data` injection.
- Close and pass result via `DynamicDialogRef.close(result)`.
- `ref.onClose` is an Observable that emits when the dialog closes.
