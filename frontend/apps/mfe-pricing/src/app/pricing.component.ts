import {
  AfterViewChecked,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';

import { MeeAlertBannerComponent }  from '@mesell/composites';
import { MeeOfflineBannerComponent } from '@mesell/composites';
import { PageHeaderComponent }       from '@mesell/composites';
import { MeeBadgeComponent }         from '@mesell/ui-kit';
import { MeeButtonComponent }        from '@mesell/ui-kit';
import { MeeCardComponent }          from '@mesell/ui-kit';
import { MeeInputComponent }         from '@mesell/ui-kit';

import { formatRupee, formatPct, parseDecimal } from './pricing.utils';
import { PricingApiService }         from './pricing.service';
import type { PriceCalcResponse, PriceCalcErrorShape, PriceCalcServerError } from './pricing.model';
import { ALERT_MESSAGES } from './pricing.model';

// ── Error-state type (W3 §3.1 degradation matrix) ────────────────────────────
// null          = initial / cleared
// unavailable   = 404 (flag-off or product not found)
// no_pricing_data = 422 pricing.category.no_pricing_data (category leaf absent from lookup)
// validation    = 400 / 422 Pydantic constraint violation
// server_error  = 5xx / EMPTY path
// W3 CHANGE: 'commission_missing' → 'no_pricing_data' (W2 §2.3 error code rename)
export type PricingErrorState =
  | 'unavailable'
  | 'no_pricing_data'
  | 'validation'
  | 'server_error'
  | null;

@Component({
  selector: 'app-pricing',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [PricingApiService],
  imports: [
    ReactiveFormsModule,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    PageHeaderComponent,
    MeeBadgeComponent,
    MeeButtonComponent,
    MeeCardComponent,
    MeeInputComponent,
  ],

  // ─── Component-scoped CSS ─────────────────────────────────────────────────
  // All values use var(--mee-*) tokens. Zero hardcoded hex (lane guard).
  // Undefined tokens defined locally in :host per wave6b dashboard-styler lesson.
  // libs/design-tokens/_tokens.css is FROZEN — not touched here.
  styles: [`
    :host {
      /* --mee-color-surface-variant missing from Layer 1 — local scope only.
         Escalation: lead queues a frozen-surface Wave-A amendment. */
      --mee-color-surface-variant: #f2f6fa;
    }

    /* ── Spinner ────────────────────────────────────────────────────────── */
    /* MeeSpinnerComponent is a queued ui-kit amendment (NOT yet available).
       Local spinner bridge used until the ui-kit component lands. */
    .mee-pricing__spinner {
      display: inline-block;
      width: 32px;
      height: 32px;
      border: 3px solid var(--mee-color-outline);
      border-top-color: var(--mee-color-primary);
      border-radius: 50%;
      animation: mee-pricing-spin 0.8s linear infinite;
    }

    /* prefers-reduced-motion: halt the spinner, use opacity pulse instead */
    @media (prefers-reduced-motion: reduce) {
      .mee-pricing__spinner {
        animation: mee-pricing-fade 1.2s ease-in-out infinite;
        border-top-color: var(--mee-color-primary);
      }
    }

    @keyframes mee-pricing-spin {
      to { transform: rotate(360deg); }
    }

    @keyframes mee-pricing-fade {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.35; }
    }

    /* ── P&L table ──────────────────────────────────────────────────────── */
    .mee-pricing__table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.875rem; /* 14px */
    }

    .mee-pricing__table td {
      padding: var(--mee-space-2) 0;
      vertical-align: middle;
    }

    /* Label column: left-align, muted colour */
    .mee-pricing__table .mee-pricing__table-label {
      color: var(--mee-color-on-surface-muted);
      text-align: left;
    }

    /* Value column: right-align, tabular numbers for rupee alignment */
    .mee-pricing__table .mee-pricing__table-value {
      color: var(--mee-color-on-surface);
      text-align: right;
      font-variant-numeric: tabular-nums;
      font-weight: 500;
      white-space: nowrap;
    }

    /* Body rows (non-profit) */
    .mee-pricing__row {
      border-bottom: 1px solid var(--mee-color-outline);
    }

    /* Profit summary row — thicker border above, semibold text */
    .mee-pricing__row--profit {
      border-bottom: 2px solid var(--mee-color-outline);
    }

    .mee-pricing__row--profit .mee-pricing__table-label {
      color: var(--mee-color-on-surface);
      font-weight: 600;
    }

    .mee-pricing__row--profit .mee-pricing__table-value {
      font-weight: 600;
    }

    /* Profit % row — last row, no bottom border */
    .mee-pricing__row--profit-pct {
      border-bottom: none;
    }

    /* Semantic colour classes (token-only, no hardcoded hex) */
    .mee-pricing__value--positive {
      color: var(--mee-color-success) !important;
    }

    .mee-pricing__value--negative {
      color: var(--mee-color-error) !important;
    }

    /* 360px: ensure table label doesn't truncate — allow wrap */
    @media (max-width: 400px) {
      .mee-pricing__table-label {
        max-width: 140px;
        word-break: break-word;
      }

      .mee-pricing__table {
        font-size: 0.8125rem; /* 13px at 360px */
      }
    }

    /* ── Alert chips ────────────────────────────────────────────────────── */
    .mee-pricing__alert-chip {
      display: flex;
      align-items: flex-start;
      gap: var(--mee-space-2);
      padding: var(--mee-space-2) var(--mee-space-3);
      border-radius: var(--mee-radius-sm);
      font-size: 0.8125rem; /* 13px */
      line-height: 1.4;
      min-height: 44px; /* WCAG 2.5.8 touch target */
    }

    .mee-pricing__alert-chip--warning {
      background: var(--mee-color-warning-light);
      color: var(--mee-color-warning);
      border-left: 3px solid var(--mee-color-warning);
    }

    .mee-pricing__alert-chip--info {
      background: var(--mee-color-info-light);
      color: var(--mee-color-info);
      border-left: 3px solid var(--mee-color-info);
    }

    /* ── Empty / first-visit state ──────────────────────────────────────── */
    .mee-pricing__empty {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: var(--mee-space-10) var(--mee-space-4);
      gap: var(--mee-space-3);
      text-align: center;
    }

    .mee-pricing__empty-icon {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: var(--mee-color-primary-light);
      color: var(--mee-color-primary);
      font-size: 1.25rem;
    }

    .mee-pricing__empty-title {
      font-size: 0.875rem;
      font-weight: 600;
      color: var(--mee-color-on-surface);
    }

    .mee-pricing__empty-hint {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Form layout at 360px ───────────────────────────────────────────── */
    .mee-pricing__form {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding: var(--mee-space-3);
    }

    /* ── Result region wrapper — used for focus target ──────────────────── */
    .mee-pricing__result-region {
      outline: none; /* focus ring suppressed for programmatic focus only */
    }

    /* ── 44px minimum touch targets on interactive buttons ─────────────── */
    .mee-pricing__calculate-area {
      min-height: 44px;
    }

    /* ── Calculating state wrapper ─────────────────────────────────────── */
    .mee-pricing__calculating {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-3);
      padding: var(--mee-space-10) 0;
    }

    .mee-pricing__calculating-label {
      font-size: 0.875rem;
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Disclaimer ─────────────────────────────────────────────────────── */
    .mee-pricing__disclaimer {
      font-size: 0.75rem;
      color: var(--mee-color-on-surface-muted);
      margin-top: var(--mee-space-2);
    }

    /* ── Section headings ───────────────────────────────────────────────── */
    .mee-pricing__section-title {
      font-size: 0.9375rem;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin-bottom: var(--mee-space-1);
    }

    /* ── Results region top: badge + alerts row ─────────────────────────── */
    .mee-pricing__results-footer {
      padding-top: var(--mee-space-3);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }
  `],

  template: `
    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Offline banner (R-W6-1 degradation matrix) -->
      <mee-offline-banner />

      <mee-page-header
        title="Price Calculator"
        subtitle="Enter your cost and target margin to calculate pricing"
      />

      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

        <!-- INPUT SECTION -->
        <div class="lg:w-2/5">
          <mee-card>
            <form
              [formGroup]="form"
              aria-label="Pricing calculation form"
              class="mee-pricing__form"
            >
              <h2 class="mee-pricing__section-title">Enter pricing details</h2>

              <!-- selling_price: primary input (listed Meesho price, gt 0) -->
              <mee-input
                label="Selling price (listed on Meesho)"
                type="number"
                prefix="&#8377;"
                placeholder="e.g. 70"
                formControlName="selling_price"
                [error]="sellingPriceError()"
              />

              <!-- commission_pct: optional override (default 0%, omit key when blank) -->
              <mee-input
                label="Commission % (optional)"
                type="number"
                suffix="%"
                placeholder="0"
                formControlName="commission_pct"
                [error]="commissionPctError()"
              />

              <!-- Disabled when form invalid OR calculating in-flight (§4.4 disabled-submit) -->
              <div class="mee-pricing__calculate-area">
                <mee-button
                  label="Calculate"
                  variant="primary"
                  [fullWidth]="true"
                  [disabled]="form.invalid || calculating()"
                  (clicked)="onCalculate()"
                />
              </div>
            </form>
          </mee-card>
        </div>

        <!-- P&L BREAKDOWN + ERROR STATES -->
        <div class="lg:w-3/5">
          <mee-card>
            <div class="p-3 space-y-4">
              <h2 class="mee-pricing__section-title">P&amp;L Breakdown</h2>

              <!--
                Error banners: role="alert" + aria-live="assertive" is handled
                inside MeeAlertBannerComponent (Wave 6A composites — verified).
                Focus is moved programmatically to #resultRegion after any
                state transition (calculate success, error) via _focusPending.
              -->

              <!-- 404 — flag off or product not found. NO local math (DECISION-1) -->
              @if (errorState() === 'unavailable') {
                <mee-alert-banner
                  variant="error"
                  message="Price Calculator is unavailable. Please try again later or contact support."
                />
              }

              <!-- 422 pricing.category.no_pricing_data — category leaf absent from pricing lookup -->
              @if (errorState() === 'no_pricing_data') {
                <div class="mee-pricing__no-data-error" role="alert">
                  <mee-alert-banner
                    variant="warning"
                    message="Pricing isn't available for this category yet."
                  />
                </div>
              }

              <!-- 400 — Pydantic constraint violation (form validators prevent most) -->
              @if (errorState() === 'validation') {
                <mee-alert-banner
                  variant="warning"
                  [message]="validationDetail()"
                />
              }

              <!-- 5xx / network — manual re-submit (export-lane pattern §3.2) -->
              @if (errorState() === 'server_error') {
                <mee-alert-banner
                  variant="error"
                  message="Couldn't calculate price — please try again."
                />
              }

              <!--
                Calculating state spinner.
                MeeSpinnerComponent is queued as a ui-kit amendment — NOT yet available.
                FLAG: replace .mee-pricing__spinner with <mee-spinner /> when landed.
                prefers-reduced-motion: CSS @media rule switches animation → opacity pulse.
                aria-live="polite" + role="status" announces to screen readers.
              -->
              @if (calculating()) {
                <div
                  role="status"
                  aria-live="polite"
                  aria-label="Calculating price, please wait"
                  class="mee-pricing__calculating"
                >
                  <span class="mee-pricing__spinner" aria-hidden="true"></span>
                  <span class="mee-pricing__calculating-label">Calculating…</span>
                </div>
              }

              <!--
                P&L result table.
                aria-live="polite" announces to screen readers when results arrive.
                tabindex="-1" allows programmatic focus (AfterViewChecked → _focusPending).
                Results focus is deferred one microtask to avoid CD-cycle conflicts.
              -->
              <div
                #resultRegion
                class="mee-pricing__result-region"
                tabindex="-1"
                role="region"
                aria-label="Pricing results"
                aria-live="polite"
                aria-atomic="false"
              >

                @if (breakdown()) {
                  <!--
                    W3 SETTLEMENT BREAKDOWN — 5 rows (W3 §2.2 Meesho-mirror layout).
                    Rows: Selling price / Commission fee / GST / TDS / Estimated Bank Settlement.
                    tcs (always "0.00") is NOT rendered. shipping/total_price are optional context lines (omitted V1).
                  -->

                  <!-- NEGATIVE_SETTLEMENT alert — renders above the table when present -->
                  @if (breakdown()!.alerts.length > 0) {
                    <div
                      role="list"
                      aria-label="Pricing alerts"
                      class="flex flex-col gap-2"
                    >
                      @for (alert of breakdown()!.alerts; track alert.code) {
                        <div
                          role="listitem"
                          class="mee-pricing__alert-chip mee-pricing__alert-chip--warning"
                        >
                          {{ resolveAlertMessage(alert.message_id) }}
                        </div>
                      }
                    </div>
                  }

                  <table
                    class="mee-pricing__table"
                    aria-label="Settlement breakdown"
                  >
                    <thead class="sr-only">
                      <tr>
                        <th scope="col">Item</th>
                        <th scope="col">Amount</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr class="mee-pricing__row">
                        <td class="mee-pricing__table-label" scope="row">Selling price</td>
                        <td class="mee-pricing__table-value">{{ formatRupeeLabel(breakdown()!.selling_price) }}</td>
                      </tr>
                      <tr class="mee-pricing__row">
                        <td class="mee-pricing__table-label" scope="row">
                          Commission fee ({{ formatPctLabel(breakdown()!.commission_pct) }})
                        </td>
                        <td class="mee-pricing__table-value">{{ formatRupeeLabel(breakdown()!.commission_fees) }}</td>
                      </tr>
                      <tr class="mee-pricing__row">
                        <td class="mee-pricing__table-label" scope="row">GST</td>
                        <td class="mee-pricing__table-value">{{ formatRupeeLabel(breakdown()!.gst_on_shipping) }}</td>
                      </tr>
                      <tr class="mee-pricing__row">
                        <td class="mee-pricing__table-label" scope="row">TDS</td>
                        <td class="mee-pricing__table-value">{{ formatRupeeLabel(breakdown()!.tds) }}</td>
                      </tr>
                      <!-- HEADLINE row: Estimated Bank Settlement -->
                      <tr class="mee-pricing__row mee-pricing__row--profit">
                        <td class="mee-pricing__table-label" scope="row">Estimated Bank Settlement</td>
                        <td
                          class="mee-pricing__table-value"
                          [class.mee-pricing__value--positive]="marginIsPositive()"
                          [class.mee-pricing__value--negative]="!marginIsPositive()"
                          [attr.aria-label]="'Estimated Bank Settlement: ' + formatRupeeLabel(breakdown()!.estimated_bank_settlement)"
                        >
                          {{ formatRupeeLabel(breakdown()!.estimated_bank_settlement) }}
                        </td>
                      </tr>
                    </tbody>
                  </table>

                  <!-- Disclaimer — server-sent literal; muted fine-print below headline -->
                  <p class="mee-pricing__disclaimer">
                    {{ breakdown()!.disclaimer }}
                  </p>

                  <!-- POSITIVE / NEGATIVE badge -->
                  <div class="mee-pricing__results-footer">
                    <div class="flex items-center gap-2">
                      <mee-badge
                        [value]="marginIsPositive() ? 'POSITIVE' : 'NEGATIVE'"
                        [severity]="marginIsPositive() ? 'success' : 'danger'"
                      />
                    </div>
                  </div>

                } @else if (!calculating() && !errorState()) {

                  <!--
                    Empty / first-visit state.
                    Shown when: no breakdown, not calculating, no error.
                    Design: centred icon + heading + hint copy.
                  -->
                  <div class="mee-pricing__empty" aria-label="No results yet">
                    <div class="mee-pricing__empty-icon" aria-hidden="true">&#8377;</div>
                    <p class="mee-pricing__empty-title">Ready to calculate</p>
                    <p class="mee-pricing__empty-hint">
                      Enter a selling price to estimate your settlement.
                    </p>
                  </div>

                }
              </div><!-- /#resultRegion -->

            </div>
          </mee-card>
        </div>

      </div>

      <!-- Save & Continue: full-width, min 44px touch target via mee-button internals -->
      <div class="pt-2">
        <mee-button
          label="Save &amp; Continue"
          variant="primary"
          [fullWidth]="true"
          (clicked)="onSaveContinue()"
        />
      </div>

    </div>
  `,
})
export class PricingComponent implements OnInit, AfterViewChecked {
  private readonly fb      = inject(FormBuilder);
  private readonly route   = inject(ActivatedRoute);
  private readonly router  = inject(Router);
  private readonly service = inject(PricingApiService);

  /** Reference to the P&L result region — used for programmatic focus after calculate. */
  @ViewChild('resultRegion') private resultRegionEl?: ElementRef<HTMLElement>;

  /** Pending focus flag: set true after a calc completes/errors; consumed in AfterViewChecked. */
  private _focusPending = false;

  readonly formatRupeeLabel    = formatRupee;
  readonly formatPctLabel      = formatPct;
  readonly resolveAlertMessage = (messageId: string): string =>
    ALERT_MESSAGES[messageId] ?? messageId;

  // W3 FORM: selling_price (required, >0) + commission_pct (optional override).
  // selling_price: Decimal string from input; must be > 0 (Validators.min(0.01)).
  // commission_pct: Optional override; omit key entirely when blank (NOT sent as "").
  //   Backend defaults to 0 — census confirms 0% for all 3,772 categories.
  readonly form = this.fb.group({
    selling_price:  ['', [Validators.required, Validators.min(0.01)]],
    commission_pct: ['', [Validators.min(0), Validators.max(100)]],
  });

  // P&L breakdown — null until successful server response; stays null on any error (R-W6-1).
  readonly breakdown = signal<PriceCalcResponse | null>(null);

  // True while HTTP POST is in-flight.
  readonly calculating = signal<boolean>(false);

  // Typed error state per §3.1 degradation matrix. null = no error.
  readonly errorState = signal<PricingErrorState>(null);

  // Detail copy for 422 no_pricing_data — set from server response (W3: replaces commissionMissingDetail).
  readonly noPricingDataDetail = signal<string>('Pricing is not available for this category yet.');

  // Detail copy for 400 validation — set from server response.
  readonly validationDetail = signal<string>('Invalid pricing input.');

  private productId = '';

  // True when estimated_bank_settlement > 0 — drives badge + warning colour.
  // W3: was breakdown()?.profit (dead field); now uses the W2 headline field.
  readonly marginIsPositive = computed<boolean>(
    () => parseDecimal(this.breakdown()?.estimated_bank_settlement ?? '0') > 0,
  );

  // Inline field error signals — W3 stubs (component-builder rebuilds full error copy in step-2).
  readonly sellingPriceError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.selling_price;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Selling price is required.';
    if (ctrl.hasError('min'))      return 'Selling price must be greater than 0.';
    return 'Invalid selling price.';
  });

  readonly commissionPctError = computed<string | undefined>(() => {
    const ctrl = this.form.controls.commission_pct;
    if (!ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('min'))  return 'Commission cannot be negative.';
    if (ctrl.hasError('max'))  return 'Commission cannot exceed 100%.';
    return 'Invalid commission rate.';
  });

  ngOnInit(): void {
    this.productId = this.route.snapshot.paramMap.get('id') ?? '';
  }

  /**
   * After Angular updates the view: if a focus is pending (result or error arrived),
   * shift focus to the result region so screen readers announce the updated content.
   * Deferred microtask avoids focusing during change-detection cycle.
   * Pattern mirrors wave6b_onboarding_builder3_polish error-banner focus.
   */
  ngAfterViewChecked(): void {
    if (this._focusPending && this.resultRegionEl) {
      this._focusPending = false;
      const el = this.resultRegionEl.nativeElement;
      // Defer to next microtask — avoids NG0100 ExpressionChangedAfterChecked
      Promise.resolve().then(() => el.focus());
    }
  }

  // DECISION-1: NEVER compute locally. Server-calc only. No ApiClient retry (§3.2 defect + POST).
  onCalculate(): void {
    if (this.form.invalid) return;

    this.calculating.set(true);
    this.errorState.set(null);
    this.breakdown.set(null);

    const raw  = this.form.getRawValue();
    // W3 body: selling_price (required) + optional commission_pct.
    // backend extra="forbid" rejects any extra field — do NOT add category or overrides.
    // commission_pct key is OMITTED entirely when blank (not sent as "" or null).
    const commissionPct = raw.commission_pct?.trim();
    const body = {
      selling_price: String(raw.selling_price ?? ''),
      ...(commissionPct ? { commission_pct: commissionPct } : {}),
    };

    this.service.calc(this.productId, body).subscribe({
      next: (result) => {
        this.calculating.set(false);
        if ('kind' in result) {
          this._handleErrorShape(result);
        } else {
          this.breakdown.set(result);
        }
        // Shift focus to result region after any calc outcome (success or error).
        this._focusPending = true;
      },
      error: () => {
        // Service absorbs all errors via catchError. Defensive guard.
        this.calculating.set(false);
        this.errorState.set('server_error');
        this._focusPending = true;
      },
      complete: () => {
        // Fires on EMPTY (401/5xx). Ensure calculating is cleared.
        this.calculating.set(false);
      },
    });
  }

  onSaveContinue(): void {
    void this.router.navigate(['/catalogs', this.productId, 'export']);
  }

  private _handleErrorShape(shape: PriceCalcErrorShape): void {
    switch (shape.kind) {
      case 'unavailable':
        this.errorState.set('unavailable');
        break;
      case 'no_pricing_data':
        // W3: replaces 'commission_missing' — category leaf absent from pricing lookup.
        this.errorState.set('no_pricing_data');
        this.noPricingDataDetail.set(shape.detail);
        break;
      case 'validation':
        this.errorState.set('validation');
        this.validationDetail.set(shape.detail);
        break;
      case 'server_error':
        // 5xx or network error — surface retry affordance banner (spec §3.1).
        // Service emits this shape instead of bare EMPTY so the component can render
        // the "Couldn't calculate — please try again" banner.
        this.errorState.set('server_error');
        break;
    }
  }
}
