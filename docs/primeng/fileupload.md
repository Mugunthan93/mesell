# FileUpload

**Import:** `import { FileUpload } from 'primeng/fileupload'`
**Selector:** `p-fileupload`, `p-fileUpload`
**Angular version:** PrimeNG 21.1.9 (Angular 21)

## @Input() Props

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| name | `string \| undefined` | undefined | Request parameter name for files |
| url | `string \| undefined` | undefined | Remote URL for auto-upload |
| method | `'post' \| 'put' \| undefined` | `'post'` | HTTP method |
| multiple | `boolean \| undefined` | undefined | Allow selecting multiple files |
| accept | `string \| undefined` | undefined | Accepted file types (MIME or extension, e.g. `'image/*'`) |
| disabled | `boolean \| undefined` | undefined | Disables the upload |
| auto | `boolean \| undefined` | undefined | Auto-upload after file selection |
| maxFileSize | `number \| undefined` | undefined | Maximum file size in bytes |
| fileLimit | `number \| undefined` | undefined | Maximum number of files |
| mode | `'advanced' \| 'basic'` | `'advanced'` | Upload UI mode |
| chooseLabel | `string \| undefined` | undefined | Label for the choose button |
| uploadLabel | `string \| undefined` | undefined | Label for the upload button |
| cancelLabel | `string \| undefined` | undefined | Label for the cancel button |
| chooseIcon | `string \| undefined` | undefined | Icon for the choose button |
| withCredentials | `boolean \| undefined` | undefined | Send credentials with CORS requests |
| style | `object \| null` | undefined | Inline style |
| styleClass | `string \| undefined` | undefined | CSS class |

## @Output() Events

| Event | Type | Description |
|-------|------|-------------|
| onBeforeUpload | `EventEmitter<FileBeforeUploadEvent>` | Emitted before upload starts |
| onSend | `EventEmitter<FileSendEvent>` | Emitted when request is sent |
| onUpload | `EventEmitter<FileUploadEvent>` | Emitted when upload completes |
| onError | `EventEmitter<FileUploadErrorEvent>` | Emitted on upload failure |
| onClear | `EventEmitter<Event>` | Emitted when queue is cleared |
| onRemove | `EventEmitter<FileRemoveEvent>` | Emitted when a file is removed |
| onSelect | `EventEmitter<FileSelectEvent>` | Emitted when files are selected |
| onProgress | `EventEmitter<FileProgressEvent>` | Emitted during upload progress |
| uploadHandler | `EventEmitter<FileUploadHandlerEvent>` | Custom upload handler for `customUpload="true"` |

## Usage Example (from Sakai-ng)

```html
<!-- Advanced mode with multiple file support -->
<p-fileupload
  name="demo[]"
  (onUpload)="onUpload($event)"
  [multiple]="true"
  accept="image/*"
  maxFileSize="1000000"
  mode="advanced"
  url="https://your-api.com/upload"
>
  <ng-template pTemplate="content">
    <p>Drag and drop files here</p>
  </ng-template>
</p-fileupload>

<!-- Basic mode (compact) -->
<p-fileupload
  mode="basic"
  chooseLabel="Choose"
  chooseIcon="pi pi-upload"
  name="file[]"
  accept="image/*"
  maxFileSize="1000000"
  (onUpload)="onUpload($event)"
/>
```

## Notes

- For custom upload (via Angular services), use `customUpload="true"` + `(uploadHandler)` output.
- `mode="basic"` shows only the choose button; `mode="advanced"` shows the full upload UI.
- The `auto` prop uploads immediately after selection (no explicit upload button needed).
