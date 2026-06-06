// shared/components/confirm-dialog/confirm-dialog.component.ts
// Stub — full implementation by meesell-angular-component-builder per §5.C.4

import { ChangeDetectionStrategy, Component, inject, input } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';

@Component({
  selector: 'mee-confirm-dialog',
  standalone: true,
  imports: [MatDialogModule, MatButtonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <h2 mat-dialog-title>{{ title() }}</h2>
    <mat-dialog-content>{{ message() }}</mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="close(false)">{{ cancelLabel() }}</button>
      <button mat-button [color]="destructive() ? 'warn' : 'primary'" (click)="close(true)">
        {{ confirmLabel() }}
      </button>
    </mat-dialog-actions>
  `,
})
export class ConfirmDialogComponent {
  private readonly dialogRef = inject(MatDialogRef<ConfirmDialogComponent>);

  readonly title = input<string>('Confirm');
  readonly message = input<string>('Are you sure?');
  readonly confirmLabel = input<string>('Confirm');
  readonly cancelLabel = input<string>('Cancel');
  readonly destructive = input<boolean>(false);

  close(result: boolean): void {
    this.dialogRef.close(result);
  }
}
