// shared/components/status-badge/status-badge.component.ts

import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { ProductStatus, ExportStatus } from '@shared/enums/product-status.enum';
import { ImagePrecheckResult } from '@shared/enums/image-precheck-result.enum';

type StatusValue = ProductStatus | ExportStatus | ImagePrecheckResult;

const STATUS_CLASSES: Record<string, string> = {
  draft:      'bg-gray-100 text-gray-500 border-gray-200',
  ready:      'bg-green-100 text-green-700 border-green-200',
  exported:   'bg-blue-100 text-blue-700 border-blue-200',
  live:       'bg-blue-100 text-blue-700 border-blue-200',
  processing: 'bg-amber-100 text-amber-600 border-amber-200',
  pending:    'bg-amber-100 text-amber-600 border-amber-200',
  failed:     'bg-red-100 text-red-600 border-red-200',
  deleted:    'bg-red-100 text-red-600 border-red-200',
};

const DEFAULT_CLASSES = 'bg-gray-100 text-gray-500 border-gray-200';

@Component({
  selector: 'mee-status-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="inline-flex items-center text-[11px] font-semibold px-2 py-0.5 rounded-full border tracking-[0.04em] uppercase whitespace-nowrap"
      [class]="badgeClass()"
    >{{ status() }}</span>
  `,
})
export class StatusBadgeComponent {
  readonly status = input.required<StatusValue>();

  readonly badgeClass = computed(() => {
    return STATUS_CLASSES[this.status() as string] ?? DEFAULT_CLASSES;
  });
}
