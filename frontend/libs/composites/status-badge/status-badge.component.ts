import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { TitleCasePipe } from '@angular/common';
import { MeeBadgeComponent } from '@mesell/ui-kit';
import type { MeeBadgeSeverity } from '@mesell/ui-kit';

export type ProductStatus =
  | 'draft'
  | 'ready'
  | 'exported'
  | 'live'
  | 'deleted'
  | 'processing'
  | 'pending'
  | 'failed';

const STATUS_MAP: Record<ProductStatus, MeeBadgeSeverity> = {
  draft:      'neutral',
  ready:      'info',
  exported:   'warning',
  live:       'success',
  deleted:    'danger',
  processing: 'info',
  pending:    'neutral',
  failed:     'danger',
};

@Component({
  selector: 'mee-status-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeBadgeComponent, TitleCasePipe],
  template: `
    <mee-badge
      [value]="status() | titlecase"
      [severity]="severity()"
    />
  `,
})
export class StatusBadgeComponent {
  readonly status = input.required<ProductStatus>();

  readonly severity = computed<MeeBadgeSeverity>(
    () => STATUS_MAP[this.status()] ?? 'neutral'
  );
}
