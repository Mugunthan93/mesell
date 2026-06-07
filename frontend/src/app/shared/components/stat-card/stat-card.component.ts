// shared/components/stat-card/stat-card.component.ts

import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatColor = 'orange' | 'blue' | 'green' | 'purple';
type TrendDir = 'up' | 'down' | 'neutral';

const CIRCLE_CLASSES: Record<StatColor, string> = {
  orange: 'bg-orange-50',
  blue:   'bg-blue-50',
  green:  'bg-green-50',
  purple: 'bg-violet-50',
};

const ICON_CLASSES: Record<StatColor, string> = {
  orange: 'text-primary',    // var(--mee-color-primary) = #F26B23
  blue:   'text-secondary',  // var(--mee-color-secondary) = #1E40AF
  green:  'text-success',    // var(--mee-color-success) = #16A34A
  purple: 'text-violet-700', // Tailwind palette — no design token for purple
};

const TREND_CLASSES: Record<TrendDir, string> = {
  up:      'text-success',   // var(--mee-color-success)
  down:    'text-error',     // var(--mee-color-error)
  neutral: 'text-gray-400',
};

@Component({
  selector: 'mee-stat-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; }
  `],
  template: `
    <div class="bg-bg-elevated rounded-mee-md py-5 px-6 shadow-mee-1 flex flex-col">
      <!-- Top row: icon circle -->
      <div class="flex items-center">
        <div class="inline-flex items-center justify-center w-9 h-9 rounded-full" [class]="circleClass()">
          <!-- Material icon via CSS mask — use a simple unicode fallback rendered as text -->
          <span style="font-family:'Material Icons','Material Symbols Outlined',sans-serif; font-size:20px; user-select:none;"
                [class]="iconClass()"
                aria-hidden="true">{{ icon() }}</span>
        </div>
      </div>

      <!-- Value -->
      <div class="mt-3 text-[28px] font-bold text-on-surface leading-none">
        {{ value() }}
      </div>

      <!-- Label -->
      <div class="mt-1 text-[13px] text-on-surface-variant">
        {{ label() }}
      </div>

      <!-- Trend row -->
      @if (trendLabel()) {
        <div class="mt-2 text-xs" [class]="trendClass()">
          {{ trendLabel() }}
        </div>
      }
    </div>
  `,
})
export class StatCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string | number>();
  readonly icon = input<string>('bar_chart');
  readonly trend = input<TrendDir>('neutral');
  readonly trendLabel = input<string | undefined>(undefined);
  readonly color = input<StatColor>('orange');

  readonly circleClass = computed(() => CIRCLE_CLASSES[this.color()]);

  readonly iconClass = computed(() => ICON_CLASSES[this.color()]);

  readonly trendClass = computed(() => TREND_CLASSES[this.trend()]);
}
