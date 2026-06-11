import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { Dialog } from 'primeng/dialog';

@Component({
  selector: 'mee-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Dialog],
  template: `
    <p-dialog
      [header]="header()"
      [visible]="visible()"
      [closable]="closable()"
      [modal]="true"
      [style]="{ width: width() }"
      (visibleChange)="visibleChange.emit($event)"
      (onHide)="closed.emit()"
    >
      <ng-content />
    </p-dialog>
  `,
})
export class MeeDialogComponent {
  readonly header = input.required<string>();
  readonly visible = input<boolean>(false);
  readonly width = input<string>('480px');
  readonly closable = input<boolean>(true);

  readonly visibleChange = output<boolean>();
  readonly closed = output<void>();
}
