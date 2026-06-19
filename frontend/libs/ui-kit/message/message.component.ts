/**
 * mee-message — inline section/field-level message (NOT toast).
 *
 * Distinct from mee-toast (transient overlay) and page-level alert-banner.
 * Use for inline validation feedback, section-level notices, form hints.
 *
 * Content can be supplied via [text] input OR projected via <ng-content>.
 */
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { Message } from 'primeng/message';
import { resolveIcon } from '../icon/icon.registry';
import type { MeeIconName } from '../icon/icon.registry';
import type { MeeMessageSeverity } from './message.types';

/** PrimeNG Message severity string union */
type PgMessageSeverity = 'success' | 'info' | 'warn' | 'error' | 'secondary' | 'contrast';

@Component({
  selector: 'mee-message',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Message],
  template: `
    <p-message
      [severity]="pgSeverity()"
      [closable]="closable()"
      [icon]="pgIcon()"
      [variant]="variant()"
      (onClose)="closed.emit()"
    >
      @if (text()) {
        {{ text() }}
      } @else {
        <ng-content></ng-content>
      }
    </p-message>
  `,
})
export class MeeMessageComponent {
  readonly severity = input<MeeMessageSeverity>('info');
  readonly text     = input<string | undefined>(undefined);
  readonly icon     = input<MeeIconName | undefined>(undefined);
  readonly closable = input<boolean>(false);
  readonly variant  = input<'outlined' | 'simple' | undefined>(undefined);

  /** Emits when the user dismisses the message (closable=true). */
  readonly closed = output<void>();

  readonly pgSeverity = computed<PgMessageSeverity>(() => {
    const s = this.severity();
    // All 4 MeeSell values map directly to PrimeNG severity string
    return s; // 'success' | 'info' | 'warn' | 'error'
  });

  readonly pgIcon = computed<string | undefined>(() => {
    const i = this.icon();
    return i ? resolveIcon(i) : undefined;
  });
}
