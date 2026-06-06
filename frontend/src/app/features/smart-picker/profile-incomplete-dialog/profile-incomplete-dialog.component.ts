// features/smart-picker/profile-incomplete-dialog/profile-incomplete-dialog.component.ts
// Inline dialog shown when POST /products returns 422 profile-incomplete error
// Per AC-8: shows missing fields, CTA to profile_url || /profile

import {
  ChangeDetectionStrategy,
  Component,
  inject,
} from '@angular/core';
import { Router } from '@angular/router';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { TranslocoModule } from '@jsverse/transloco';
import { ProfileIncompleteError } from '../smart-picker.model';

@Component({
  selector: 'mee-profile-incomplete-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatDialogModule, MatButtonModule, TranslocoModule],
  template: `
    <h2 mat-dialog-title>
      {{ 'smartPicker.profileIncomplete.title' | transloco }}
    </h2>

    <mat-dialog-content>
      <p class="mb-3 text-gray-700">
        {{ 'smartPicker.profileIncomplete.body' | transloco }}
      </p>

      @if (data.missing_compliance_fields.length > 0) {
        <ul class="list-disc pl-5 text-sm text-gray-600 space-y-1">
          @for (field of data.missing_compliance_fields; track field) {
            <li>{{ field }}</li>
          }
        </ul>
      }
    </mat-dialog-content>

    <mat-dialog-actions align="end" class="gap-2">
      <button
        mat-button
        (click)="cancel()"
        class="min-h-[44px]"
      >
        {{ 'smartPicker.profileIncomplete.cancel' | transloco }}
      </button>

      <button
        mat-raised-button
        color="primary"
        (click)="goToProfile()"
        class="min-h-[44px]"
      >
        {{ 'smartPicker.profileIncomplete.goToProfile' | transloco }}
      </button>
    </mat-dialog-actions>
  `,
})
export class ProfileIncompleteDialogComponent {
  readonly data = inject<ProfileIncompleteError>(MAT_DIALOG_DATA);
  private readonly dialogRef = inject(MatDialogRef<ProfileIncompleteDialogComponent>);
  private readonly router = inject(Router);

  cancel(): void {
    this.dialogRef.close(false);
  }

  goToProfile(): void {
    this.dialogRef.close(true);
    const url = this.data.profile_url || '/profile';
    // Navigate to external profile deep-link or fallback
    this.router.navigateByUrl(url);
  }
}
