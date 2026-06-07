// features/pricing/pricing/pricing.component.ts
// Selector: mee-pricing
// Route: /catalogs/:id/pricing — P&L calculator per §14

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { EMPTY } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoModule } from '@jsverse/transloco';

import { PricingApiService, PricingCalc } from '../pricing-api.service';
import { MarginSliderComponent } from '../margin-slider/margin-slider.component';
import { PnlBreakdownComponent } from '../pnl-breakdown/pnl-breakdown.component';
import { PricingChartComponent } from '../pricing-chart/pricing-chart.component';
import { LoadingSpinnerComponent } from '@shared/components/loading-spinner/loading-spinner.component';

/** Default initial values per spec §14.D */
const DEFAULT_MRP = 999;
const DEFAULT_TARGET_PAYOUT = 500;

@Component({
  selector: 'mee-pricing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MatButtonModule,
    MatSnackBarModule,
    TranslocoModule,
    MarginSliderComponent,
    PnlBreakdownComponent,
    PricingChartComponent,
    LoadingSpinnerComponent,
  ],
  styles: [`
    :host { display: block; }
    .pricing-page {
      max-width: 720px;
      margin: 0 auto;
      padding: 24px 16px;
    }
    .pricing-header {
      margin-bottom: 24px;
    }
    .pricing-header h1 {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 4px;
    }
    .pricing-header p {
      font-size: 13px;
      color: #6B7280;
      margin: 0;
    }
    .pricing-card {
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
      padding: 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.08);
      margin-bottom: 20px;
    }
    .pricing-card-title {
      font-size: 13px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 16px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .pricing-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 32px;
      gap: 12px;
    }
    .loading-wrap {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 300px;
    }
    .estimate-banner {
      font-size: 11px;
      color: #9CA3AF;
      text-align: right;
      margin-bottom: 4px;
    }
    @media (max-width: 480px) {
      .pricing-actions {
        flex-direction: column;
      }
      .pricing-actions button {
        width: 100%;
      }
    }
  `],
  template: `
    <div class="pricing-page">
      <!-- Page header -->
      <div class="pricing-header">
        <h1>{{ 'pricing.title' | transloco }}</h1>
        <p>Adjust your MRP to see how it affects your payout and margin.</p>
      </div>

      <!-- Loading state -->
      @if (loading()) {
        <div class="loading-wrap">
          <mee-loading-spinner [diameter]="40" caption="Calculating..." />
        </div>
      }

      @if (!loading()) {
        <!-- MRP Slider card -->
        <div class="pricing-card">
          <p class="pricing-card-title">Set your price</p>
          <mee-margin-slider
            [mrp]="mrp()"
            [minMrp]="50"
            [maxMrp]="10000"
            (mrpChanged)="onMrpChanged($event)"
            (mrpCommitted)="onMrpCommitted($event)"
          />
        </div>

        @if (displayCalc()) {
          <!-- Show estimate banner when no committed calc yet -->
          @if (!calc()) {
            <p class="estimate-banner" aria-live="polite">Estimated (move slider to calculate)</p>
          }

          <!-- P&L Breakdown card -->
          <div class="pricing-card">
            <p class="pricing-card-title">Cost breakdown</p>
            <mee-pnl-breakdown [calc]="displayCalc()!" />
          </div>

          <!-- Chart card -->
          <div class="pricing-card">
            <p class="pricing-card-title">Visual breakdown</p>
            <mee-pricing-chart [calc]="displayCalc()!" />
          </div>
        }

        <!-- Navigation actions -->
        <div class="pricing-actions">
          <button
            mat-stroked-button
            (click)="navigateBack()"
            class="min-h-[44px]"
            aria-label="Go back to preview"
          >
            Back to Preview
          </button>

          <button
            mat-flat-button
            color="primary"
            (click)="navigateNext()"
            class="min-h-[44px]"
            aria-label="Go to export"
            id="next-step-btn"
          >
            Next: Export
          </button>
        </div>
      }
    </div>
  `,
})
export class PricingComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly pricingApi = inject(PricingApiService);
  private readonly snackBar = inject(MatSnackBar);

  /** Committed calc from the API (null until first successful call) */
  readonly calc = signal<PricingCalc | null>(null);

  /** Current MRP value tracked by the slider */
  readonly mrp = signal<number>(DEFAULT_MRP);

  readonly loading = signal<boolean>(true);

  /**
   * Snapshot of percentage rates from the last committed API call.
   * Used for local recompute on slider movement (no API call needed).
   */
  private ratesSnapshot: { commission_pct: number; gst_pct: number; platform_fee_pct: number } | null = null;

  /**
   * Local estimate for instant slider feedback.
   * Per §14.D: fires on every slider move, no API call.
   */
  readonly localEstimate = computed<Partial<PricingCalc>>(() => {
    const snapshot = this.ratesSnapshot;
    if (!snapshot) return {};
    const { commission_pct, gst_pct, platform_fee_pct } = snapshot;
    const mrpVal = this.mrp();
    const seller_payout = mrpVal * (1 - commission_pct / 100 - gst_pct / 100 - platform_fee_pct / 100);
    const net_margin_pct = mrpVal > 0 ? (seller_payout / mrpVal) * 100 : 0;
    return { seller_payout, net_margin_pct };
  });

  /**
   * Merged display calc: committed calc merged with local estimate overrides
   * for seller_payout and net_margin_pct (instant feedback while dragging).
   */
  readonly displayCalc = computed<PricingCalc | null>(() => {
    const committed = this.calc();
    if (!committed) return null;
    const estimate = this.localEstimate();
    return {
      ...committed,
      mrp: this.mrp(),
      seller_payout: estimate.seller_payout ?? committed.seller_payout,
      net_margin_pct: estimate.net_margin_pct ?? committed.net_margin_pct,
    };
  });

  private get productId(): string {
    return this.route.snapshot.parent?.paramMap.get('id') ??
           this.route.snapshot.paramMap.get('id') ?? '';
  }

  ngOnInit(): void {
    const id = this.productId;
    this.callApi(id, DEFAULT_MRP, DEFAULT_TARGET_PAYOUT);
  }

  /**
   * Fires on every slider move (100ms debounced inside MarginSliderComponent).
   * Updates local mrp signal → localEstimate recomputes instantly via computed().
   */
  onMrpChanged(mrp: number): void {
    this.mrp.set(mrp);
  }

  /**
   * Fires 500ms after slide end — triggers actual API call.
   */
  onMrpCommitted(mrp: number): void {
    this.mrp.set(mrp);
    this.callApi(this.productId, mrp, DEFAULT_TARGET_PAYOUT);
  }

  private callApi(productId: string, mrp: number, targetPayout: number): void {
    if (!productId) {
      this.loading.set(false);
      return;
    }
    this.loading.set(true);

    this.pricingApi.calculate(productId, mrp, targetPayout).pipe(
      catchError((err: unknown) => {
        this.loading.set(false);
        this.snackBar.open('Failed to calculate pricing. Please try again.', 'Dismiss', {
          duration: 4000,
          panelClass: ['mee-snackbar-error'],
        });
        return EMPTY;
      }),
    ).subscribe((result) => {
      // Snapshot rates for local recompute
      this.ratesSnapshot = {
        commission_pct: result.commission_pct,
        gst_pct: result.gst_pct,
        platform_fee_pct: result.platform_fee_pct,
      };
      this.calc.set(result);
      this.loading.set(false);
    });
  }

  navigateBack(): void {
    const id = this.productId;
    void this.router.navigate(['/catalogs', id, 'preview']);
  }

  navigateNext(): void {
    const id = this.productId;
    void this.router.navigate(['/catalogs', id, 'export']);
  }
}
