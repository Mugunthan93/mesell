// features/pricing/pricing-chart/pricing-chart.component.ts
// Selector: mee-pricing-chart
// Horizontal stacked bar chart showing P&L cost breakdown using chart.js + ng2-charts

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';
import { COLORS_RESOLVED } from '@design-system/tokens';
import { PricingCalc } from '../pricing-api.service';

@Component({
  selector: 'mee-pricing-chart',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BaseChartDirective],
  styles: [`
    :host { display: block; width: 100%; }
    .chart-container {
      width: 100%;
      height: 80px;
      position: relative;
    }
    .chart-legend {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 16px;
      margin-top: 8px;
    }
    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--mee-color-on-surface);
    }
    .legend-swatch {
      width: 12px;
      height: 12px;
      border-radius: 2px;
      flex-shrink: 0;
    }
  `],
  template: `
    <div>
      <div class="chart-container" role="img" aria-label="Pricing breakdown chart">
        <canvas
          baseChart
          [data]="chartData()"
          [options]="chartOptions"
          type="bar"
          aria-hidden="true"
        ></canvas>
      </div>

      <!-- Accessible legend (canvas is aria-hidden) -->
      <div class="chart-legend" role="list" aria-label="Chart legend">
        @for (item of legendItems; track item.label) {
          <div class="legend-item" role="listitem">
            <span class="legend-swatch" [style.background]="item.color" aria-hidden="true"></span>
            <span>{{ item.label }}</span>
          </div>
        }
      </div>
    </div>
  `,
})
export class PricingChartComponent {
  readonly calc = input.required<PricingCalc>();

  readonly legendItems = [
    { label: 'Commission',   color: COLORS_RESOLVED.error },
    { label: 'GST',          color: COLORS_RESOLVED.warning },
    { label: 'Platform fee', color: COLORS_RESOLVED.secondary },
    { label: 'Logistics',    color: '#9CA3AF' },
    { label: 'Your payout',  color: COLORS_RESOLVED.success },
  ];

  /** chart.js options — horizontal stacked bar, no axes labels, minimal chrome */
  readonly chartOptions: ChartConfiguration['options'] = {
    indexAxis: 'y',
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const val = ctx.parsed.x as number;
            return ` ${ctx.dataset.label}: ₹${Math.round(val)}`;
          },
        },
      },
    },
    scales: {
      x: {
        stacked: true,
        display: false,
        grid: { display: false },
      },
      y: {
        stacked: true,
        display: false,
        grid: { display: false },
      },
    },
    animation: { duration: 200 },
  };

  readonly chartData = computed<ChartConfiguration['data']>(() => {
    const c = this.calc();
    return {
      labels: ['Price breakdown'],
      datasets: [
        {
          label: 'Commission',
          data: [c.commission],
          backgroundColor: COLORS_RESOLVED.error,
          borderWidth: 0,
        },
        {
          label: 'GST',
          data: [c.gst],
          backgroundColor: COLORS_RESOLVED.warning,
          borderWidth: 0,
        },
        {
          label: 'Platform fee',
          data: [c.platform_fee],
          backgroundColor: COLORS_RESOLVED.secondary,
          borderWidth: 0,
        },
        {
          label: 'Logistics',
          data: [c.logistics_deduction],
          backgroundColor: '#9CA3AF', // neutral gray — no semantic token for logistics
          borderWidth: 0,
        },
        {
          label: 'Your payout',
          data: [Math.max(0, c.seller_payout)],
          backgroundColor: COLORS_RESOLVED.success,
          borderWidth: 0,
        },
      ],
    };
  });
}
