import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { Divider } from 'primeng/divider';

@Component({
  selector: 'mee-divider',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Divider],
  template: `
    <p-divider
      [layout]="layout()"
      [align]="align()"
      [type]="type()"
    >
      <ng-content></ng-content>
    </p-divider>
  `,
})
export class MeeDividerComponent {
  readonly layout = input<'horizontal' | 'vertical'>('horizontal');
  readonly align  = input<'left' | 'center' | 'right' | 'top' | 'bottom' | undefined>(undefined);
  readonly type   = input<'solid' | 'dashed' | 'dotted'>('solid');
}
