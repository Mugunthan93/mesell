import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { MeeCardComponent, MeeIconComponent } from '@mesell/ui-kit';
import type { MeeIconName } from '@mesell/ui-kit';

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
  imports: [MeeCardComponent, MeeIconComponent],
  styles: [`
    :host { display: block; }
    .sc-body {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
      padding: var(--mee-space-1);
    }
    .sc-header {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
    }
    .sc-icon {
      display: flex;
      align-items: center;
      width: 48px;
      height: 48px;
      line-height: 1;
    }
    .sc-icon mee-icon i {
      font-size: 48px;
      line-height: 1;
    }
    .sc-trend {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      font-size: 12px;
      font-weight: 600;
      padding: 2px 8px;
      border-radius: var(--mee-radius-full);
    }
    .sc-trend--positive {
      color: var(--mee-color-success);
      background: rgba(22, 163, 74, 0.12);
    }
    .sc-trend--negative {
      color: var(--mee-color-error);
      background: rgba(220, 38, 38, 0.12);
    }
    .sc-trend-icon {
      display: flex;
      align-items: center;
      line-height: 1;
    }
    .sc-trend-icon mee-icon i {
      font-size: 14px;
      line-height: 1;
    }
    .sc-value {
      font-size: 30px;
      font-weight: 700;
      line-height: 1;
      color: var(--mee-color-on-surface);
      margin: 0;
    }
    .sc-label {
      font-size: 14px;
      line-height: 1.4;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }
    .sc-trend-label {
      font-size: 12px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }
  `],
  template: `
    <mee-card>
      <div class="sc-body">
        <!-- Icon row + optional trend -->
        <div class="sc-header">
          <span
            class="sc-icon"
            [style.color]="accentColor()"
          >
            <mee-icon [name]="icon()" />
          </span>

          @if (trend() !== undefined && trend() !== null) {
            <span
              class="sc-trend"
              [class.sc-trend--positive]="trendPositive()"
              [class.sc-trend--negative]="!trendPositive()"
              [attr.aria-label]="trend_label() ?? 'trend'"
            >
              <span class="sc-trend-icon">
                <mee-icon [name]="trendPositive() ? 'trending-up' : 'trending-down'" />
              </span>
              {{ trend()! > 0 ? '+' : '' }}{{ trend() }}%
            </span>
          }
        </div>

        <!-- Value -->
        <p class="sc-value">{{ value() }}</p>

        <!-- Label + optional trend label -->
        <p class="sc-label">{{ label() }}</p>

        @if (trend_label()) {
          <p class="sc-trend-label">{{ trend_label() }}</p>
        }
      </div>
    </mee-card>
  `,
})
export class StatCardComponent {
  readonly label       = input.required<string>();
  readonly value       = input.required<string | number>();
  readonly icon        = input.required<MeeIconName>();
  readonly trend       = input<number | undefined>(undefined);
  readonly trend_label = input<string | undefined>(undefined);
  readonly color       = input<StatCardColor>('orange');

  readonly trendPositive = computed(() => (this.trend() ?? 0) > 0);
  readonly accentColor   = computed(() => COLOR_VAR_MAP[this.color()]);
}
