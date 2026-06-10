import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { FileUpload, FileUploadHandlerEvent, FileUploadErrorEvent } from 'primeng/fileupload';
import type { MeeFileUploadEvent } from './file-upload.types';

@Component({
  selector: 'mee-file-upload',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FileUpload],
  template: `
    <p-fileupload
      mode="advanced"
      [customUpload]="true"
      [accept]="accept()"
      [maxFileSize]="maxFileSizeBytes()"
      [multiple]="multiple()"
      [chooseLabel]="label()"
      (uploadHandler)="onUploadHandler($event)"
      (onError)="onError($event)"
      [style]="{ minHeight: '44px' }"
    />
  `,
})
export class MeeFileUploadComponent {
  readonly accept = input<string>('image/*');
  readonly max_size_mb = input<number>(5);
  readonly multiple = input<boolean>(false);
  readonly label = input<string>('Drop files here or click to upload');

  readonly files_selected = output<MeeFileUploadEvent>();
  readonly upload_error = output<string>();

  readonly maxFileSizeBytes = computed(() => this.max_size_mb() * 1024 * 1024);

  onUploadHandler(event: FileUploadHandlerEvent): void {
    const files = event.files as File[];
    this.files_selected.emit({ files });
  }

  onError(event: FileUploadErrorEvent): void {
    const message = event.error?.message ?? 'Upload failed';
    this.upload_error.emit(message);
  }
}
