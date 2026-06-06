// shared/components/stat-card/stat-card.component.ts

import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type StatColor = 'orange' | 'blue' | 'green' | 'purple';
type TrendDir = 'up' | 'down' | 'neutral';

interface ColorTokens {
  circleBg: string;
  iconColor: string;
}

const COLOR_MAP: Record<StatColor, ColorTokens> = {
  orange: { circleBg: '#FFF3E8', iconColor: '#F26B23' },
  blue:   { circleBg: '#EFF6FF', iconColor: '#1E40AF' },
  green:  { circleBg: '#F0FDF4', iconColor: '#16A34A' },
  purple: { circleBg: '#F3E8FF', iconColor: '#7C3AED' },
};

const TREND_COLOR: Record<TrendDir, string> = {
  up: '#16A34A',
  down: '#DC2626',
  neutral: '#9CA3AF',
};

@Component({
  selector: 'mee-stat-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; }
  `],
  template: `
    <div style="background:#FFFFFF; border-radius:16px; padding:20px 24px; box-shadow:0 1px 3px rgba(0,0,0,0.08); display:flex; flex-direction:column;">
      <!-- Top row: icon circle -->
      <div style="display:flex; align-items:center; justify-content:flex-start;">
        <div [style]="iconCircleStyle()">
          <!-- Material icon via CSS mask — use a simple unicode fallback rendered as text -->
          <span [style]="iconTextStyle()" aria-hidden="true">{{ icon() }}</span>
        </div>
      </div>

      <!-- Value -->
      <div style="margin-top:12px; font-size:28px; font-weight:700; color:#1F2937; line-height:1;">
        {{ value() }}
      </div>

      <!-- Label -->
      <div style="margin-top:4px; font-size:13px; color:#6B7280;">
        {{ label() }}
      </div>

      <!-- Trend row -->
      @if (trendLabel()) {
        <div [style]="trendRowStyle()" style="margin-top:8px; font-size:12px;">
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

  readonly iconCircleStyle = computed(() => {
    const tokens = COLOR_MAP[this.color()];
    return `display:inline-flex; align-items:center; justify-content:center; width:36px; height:36px; border-radius:50%; background:${tokens.circleBg};`;
  });

  readonly iconTextStyle = computed(() => {
    const tokens = COLOR_MAP[this.color()];
    // Render as Material icon font character using font-family; falls back to text
    return `font-family:'Material Icons','Material Symbols Outlined',sans-serif; font-size:20px; color:${tokens.iconColor}; user-select:none;`;
  });

  readonly trendRowStyle = computed(() => {
    return `color:${TREND_COLOR[this.trend()]};`;
  });
}
