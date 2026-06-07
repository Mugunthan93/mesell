// features/catalog-form/primitives/image-upload/image-upload.component.ts
// Primitive 10: placeholder redirect to /catalogs/:id/images per §18.E
// Actual upload is in features/images/ (Wave 3). This primitive renders a hint only.
// ControlValueAccessor: writeValue accepts a string (URL or null); onChange/onTouched are no-ops.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  forwardRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { ActivatedRoute } from '@angular/router';
import { FieldSchema } from '@core/models/field-schema.model';
import { AiSuggestion } from '@core/models/ai-suggestion.model';
import { LocaleLabelPipe } from '@shared/pipes/locale-label.pipe';
import { ValueChange } from '../primitive.contract';

@Component({
  selector: 'mee-image-upload',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, MatFormFieldModule, MatInputModule, MatIconModule, LocaleLabelPipe],
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => ImageUploadPrimitiveComponent),
      multi: true,
    },
  ],
  template: `
    <mat-form-field appearance="outline" class="w-full">
      <mat-label>
        {{ schema().displayLabel | localeLabel }}
        @if (schema().marker === 'compulsory') {
          <span style="color:var(--mee-color-error)" aria-hidden="true"> *</span>
        }
      </mat-label>
      <input
        matInput
        [value]="innerValue()"
        disabled
        placeholder="Upload images in the Images step"
        readonly
      />
      <mat-icon matSuffix style="color:var(--mee-color-primary)">photo_camera</mat-icon>
      <mat-hint>
        <a [routerLink]="imagesUrl()" style="color:var(--mee-color-primary)">
          Go to Images step to upload photos
        </a>
      </mat-hint>
    </mat-form-field>
  `,
})
export class ImageUploadPrimitiveComponent implements ControlValueAccessor {
  readonly schema = input.required<FieldSchema>();
  readonly value = input<unknown>(null);
  readonly aiSuggestion = input<AiSuggestion | null>(null);
  readonly disabled = input<boolean>(false);

  // image-upload is display-only — no valueChange emitted per §18.E
  readonly valueChange = output<ValueChange>();

  readonly innerValue = signal<string>('');

  private readonly route = inject(ActivatedRoute);

  readonly imagesUrl = computed<string>(() => {
    const id = this.route.snapshot.params['id'] as string | undefined;
    return id ? `/catalogs/${id}/images` : '/dashboard';
  });

  writeValue(val: unknown): void {
    this.innerValue.set(val != null ? String(val) : '');
  }

  // no-ops per spec: this is a display-only placeholder
  registerOnChange(_fn: (v: unknown) => void): void {}
  registerOnTouched(_fn: () => void): void {}
}
