import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { Tag } from 'primeng/tag';
import type { MeeBadgeSeverity } from './badge.types';

type PgTagSeverity = 'success' | 'secondary' | 'info' | 'warn' | 'danger' | 'contrast' | null;

@Component({
  selector: 'mee-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Tag],
  template: `
    <p-tag
      [value]="value()"
      [severity]="pgSeverity()"
      [rounded]="true"
    />
  `,
})
export class MeeBadgeComponent {
  readonly value = input.required<string>();
  readonly severity = input<MeeBadgeSeverity>('neutral');

  readonly pgSeverity = computed((): PgTagSeverity => {
    const s = this.severity();
    switch (s) {
      case 'success':  return 'success';
      case 'warning':  return 'warn';
      case 'danger':   return 'danger';
      case 'info':     return 'info';
      case 'neutral':  return 'secondary';
      default:         return 'secondary';
    }
  });
}
