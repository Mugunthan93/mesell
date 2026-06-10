import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Card } from 'primeng/card';

@Component({
  selector: 'mee-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Card],
  template: `
    <p-card>
      <ng-content />
    </p-card>
  `,
})
export class MeeCardComponent {}
