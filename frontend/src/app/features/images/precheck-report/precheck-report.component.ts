// features/images/precheck-report/precheck-report.component.ts
// Selector: mee-precheck-report
// 5-item precheck status list per §12.B

import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { TranslocoModule } from '@jsverse/transloco';
import type { ProductImage } from '../images-api.service';

export interface PrecheckItem {
  readonly key: string;
  readonly labelKey: string;
  readonly value: boolean | null;
  readonly hint: string | null;
}

/**
 * Pure function — computes the 5 precheck items from an image.
 * Exported for direct testing without component instantiation.
 */
export function buildPrecheckItems(image: ProductImage): PrecheckItem[] {
  const p = image.precheck_jsonb;

  // color_space check: pass if value === 'RGB'
  const colorSpaceOk: boolean | null =
    p?.color_space === null || p?.color_space === undefined
      ? null
      : p.color_space === 'RGB';

  return [
    {
      key: 'is_jpeg',
      labelKey: 'images.precheck.is_jpeg',
      value: p?.is_jpeg ?? null,
      hint: null,
    },
    {
      key: 'color_space',
      labelKey: 'images.precheck.color_space',
      value: colorSpaceOk,
      hint: colorSpaceOk === false ? 'Convert image to RGB color mode' : null,
    },
    {
      key: 'resolution_ok',
      labelKey: 'images.precheck.resolution',
      value: p?.resolution_ok ?? null,
      hint: p?.resolution_ok === false
        ? 'Image must be at least 1500×1500 pixels'
        : null,
    },
    {
      key: 'white_bg_ok',
      labelKey: 'images.precheck.white_bg',
      value: p?.white_bg_ok ?? null,
      hint: p?.white_bg_ok === false ? 'Use a plain white background' : null,
    },
    {
      key: 'watermark_pass',
      labelKey: 'images.precheck.watermark',
      value: p?.watermark_pass ?? null,
      hint: p?.watermark_pass === false
        ? 'Remove watermarks and logos from the image'
        : null,
    },
  ];
}

@Component({
  selector: 'mee-precheck-report',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TranslocoModule],
  template: `
    <div class="bg-white rounded-[var(--mee-radius-md)] border border-[var(--mee-color-outline)] p-4">
      <h3 class="text-sm font-semibold text-gray-700 mb-3">
        {{ 'images.precheck.fail' | transloco }}
      </h3>
      <ul class="space-y-2" role="list">
        @for (item of precheckItems(); track item.key) {
          <li class="flex flex-col gap-1">
            <div class="flex items-center gap-2 min-h-[44px]">
              <!-- Status icon -->
              @if (item.value === null) {
                <span
                  class="text-lg leading-none text-[var(--mee-color-warning)]"
                  aria-label="Pending"
                >⏳</span>
              } @else if (item.value === true) {
                <span
                  class="text-lg leading-none text-[var(--mee-color-success)]"
                  aria-label="Pass"
                >✓</span>
              } @else {
                <span
                  class="text-lg leading-none text-[var(--mee-color-error)]"
                  aria-label="Fail"
                >✗</span>
              }
              <!-- Label -->
              <span class="text-sm text-gray-700">
                {{ item.labelKey | transloco }}
              </span>
              <!-- Pass/Fail badge -->
              @if (item.value === true) {
                <span class="ml-auto text-xs px-2 py-0.5 rounded-full
                             bg-green-50 text-[var(--mee-color-success)] font-medium">
                  {{ 'images.precheck.pass' | transloco }}
                </span>
              } @else if (item.value === false) {
                <span class="ml-auto text-xs px-2 py-0.5 rounded-full
                             bg-red-50 text-[var(--mee-color-error)] font-medium">
                  {{ 'images.precheck.fail' | transloco }}
                </span>
              } @else {
                <span class="ml-auto text-xs px-2 py-0.5 rounded-full
                             bg-yellow-50 text-[var(--mee-color-warning)] font-medium">
                  {{ 'images.precheck.processing' | transloco }}
                </span>
              }
            </div>
            <!-- Fix hint for failed items -->
            @if (item.value === false && item.hint) {
              <p class="text-xs text-[var(--mee-color-error)] pl-7">
                {{ item.hint }}
              </p>
            }
          </li>
        }
      </ul>
    </div>
  `,
})
export class PrecheckReportComponent {
  readonly image = input.required<ProductImage>();

  readonly precheckItems = computed<PrecheckItem[]>(() =>
    buildPrecheckItems(this.image()),
  );
}
