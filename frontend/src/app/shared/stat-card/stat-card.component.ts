import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MeeCardComponent } from '../../ui';

export type StatCardColor = 'orange' | 'blue' | 'green' | 'purple';

const COLOR_VAR_MAP: Record<StatCardColor, string> = {
  orange: 'var(--mee-color-primary)',
  blue:   'var(--mee-color-info)',
  green:  'var(--mee-color-success)',
  purple: 'var(--mee-color-purple, #7C3AED)',
};

@Component({
  selector: 'mee-stat-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeCardComponent],
  template: `
    <mee-card>
      <div class="flex flex-col gap-2 p-1">
        <!-- Icon row + optional trend -->
        <div class="flex items-start justify-between">
          <span
            class="material-symbols-outlined"
            aria-hidden="true"
            [style.color]="accentColor()"
            style="font-size:48px; width:48px; height:48px; line-height:1;"
          >{{ icon() }}</span>

          @if (trend() !== undefined && trend() !== null) {
            <span
              class="inline-flex items-center gap-0.5 text-xs font-semibold px-2 py-0.5 rounded-full"
              [class.text-green-700]="trendPositive()"
              [class.bg-green-100]="trendPositive()"
              [class.text-red-700]="!trendPositive()"
              [class.bg-red-100]="!trendPositive()"
              [attr.aria-label]="trend_label() ?? 'trend'"
            >
              <span class="material-symbols-outlined" aria-hidden="true" style="font-size:14px; line-height:1;">
                {{ trendPositive() ? 'trending_up' : 'trending_down' }}
              </span>
              {{ trend()! > 0 ? '+' : '' }}{{ trend() }}%
            </span>
          }
        </div>

        <!-- Value -->
        <p
          class="text-3xl font-bold leading-none"
          style="color: var(--mee-color-on-surface);"
        >{{ value() }}</p>

        <!-- Label + optional trend label -->
        <p
          class="text-sm leading-snug"
          style="color: var(--mee-color-on-surface-muted);"
        >{{ label() }}</p>

        @if (trend_label()) {
          <p class="text-xs" style="color: var(--mee-color-on-surface-muted);">{{ trend_label() }}</p>
        }
      </div>
    </mee-card>
  `,
})
export class StatCardComponent {
  readonly label       = input.required<string>();
  readonly value       = input.required<string | number>();
  readonly icon        = input.required<string>();
  readonly trend       = input<number | undefined>(undefined);
  readonly trend_label = input<string | undefined>(undefined);
  readonly color       = input<StatCardColor>('orange');

  readonly trendPositive = computed(() => (this.trend() ?? 0) > 0);
  readonly accentColor   = computed(() => COLOR_VAR_MAP[this.color()]);
}
