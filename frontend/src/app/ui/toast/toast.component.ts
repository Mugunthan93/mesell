import { ChangeDetectionStrategy, Component } from '@angular/core';
import { Toast } from 'primeng/toast';

/**
 * Host component — place ONCE in AppComponent or shell template.
 * Services call MeeToastService.success/error/warn/info to trigger notifications.
 */
@Component({
  selector: 'mee-toast',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Toast],
  template: `<p-toast position="top-right" [life]="4000" />`,
})
export class MeeToastComponent {}
