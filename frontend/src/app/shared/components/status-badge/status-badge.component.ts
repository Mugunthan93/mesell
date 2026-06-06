// shared/components/status-badge/status-badge.component.ts

import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { ProductStatus, ExportStatus } from '@shared/enums/product-status.enum';
import { ImagePrecheckResult } from '@shared/enums/image-precheck-result.enum';

type StatusValue = ProductStatus | ExportStatus | ImagePrecheckResult;

interface BadgeStyle {
  background: string;
  color: string;
  borderColor: string;
}

const STATUS_STYLES: Record<string, BadgeStyle> = {
  draft: { background: '#F3F4F6', color: '#6B7280', borderColor: '#D1D5DB' },
  ready: { background: '#DCFCE7', color: '#15803D', borderColor: '#BBF7D0' },
  exported: { background: '#DBEAFE', color: '#1D4ED8', borderColor: '#BFDBFE' },
  live: { background: '#DBEAFE', color: '#1D4ED8', borderColor: '#BFDBFE' },
  processing: { background: '#FEF3C7', color: '#D97706', borderColor: '#FDE68A' },
  pending: { background: '#FEF3C7', color: '#D97706', borderColor: '#FDE68A' },
  failed: { background: '#FEE2E2', color: '#DC2626', borderColor: '#FECACA' },
  deleted: { background: '#FEE2E2', color: '#DC2626', borderColor: '#FECACA' },
};

const DEFAULT_STYLE: BadgeStyle = {
  background: '#F3F4F6',
  color: '#6B7280',
  borderColor: '#D1D5DB',
};

const BASE_STYLE = [
  'display: inline-flex',
  'align-items: center',
  'font-size: 11px',
  'font-weight: 600',
  'padding: 2px 8px',
  'border-radius: 999px',
  'border: 1px solid',
  'letter-spacing: 0.04em',
  'text-transform: uppercase',
  'white-space: nowrap',
].join('; ');

@Component({
  selector: 'mee-status-badge',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span [style]="badgeStyle()">{{ status() }}</span>
  `,
})
export class StatusBadgeComponent {
  readonly status = input.required<StatusValue>();

  readonly badgeStyle = computed(() => {
    const s = STATUS_STYLES[this.status() as string] ?? DEFAULT_STYLE;
    return `${BASE_STYLE}; background: ${s.background}; color: ${s.color}; border-color: ${s.borderColor};`;
  });
}
