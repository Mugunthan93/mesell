import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

import { MeeBadgeComponent }        from '@mesell/ui-kit';
import { MeeButtonComponent }       from '@mesell/ui-kit';
import { MeeCardComponent }         from '@mesell/ui-kit';
import { MeeAlertBannerComponent }  from '@mesell/composites';
import { MeeOfflineBannerComponent } from '@mesell/composites';
import { PageHeaderComponent }      from '@mesell/composites';
import { StatusBadgeComponent }     from '@mesell/composites';

import {
  type ExportStatus,
  type ValidationChecks,
  type ValidationCheckItem,
  SIMULATED_PASSING_CHECKS,
  buildCheckItems,
  allChecksPassed,
  canGenerate,
  isTerminalStatus,
} from './export.model';
import {
  ExportApiService,
  ExportNotFoundError,
  type InitiateErrorShape,
} from './export.service';
import type { ExportInitiatedResponse } from './export.model';

/** Poll interval in milliseconds (D18 timer-preserve — real poll every 2 s). */
const POLL_INTERVAL_MS = 2000;
/** Maximum number of poll ticks before timing out (60 ticks × 2 s = 2 min). */
const MAX_POLL_ATTEMPTS = 60;

// FLAG(ui-styler builder-3): MeeProgressBarComponent.value is required — no indeterminate mode.
// Processing card uses .mee-export-spinner (native CSS animation) as a local workaround.
// ui-styler: introduce MeeSpinnerComponent to @mesell/ui-kit and swap. Do NOT edit ui-kit.
@Component({
  selector: 'app-export',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    @keyframes mee-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
    .mee-export-spinner { width:44px; height:44px; border-radius:50%; border:4px solid var(--mee-color-outline,#e5e7eb); border-top-color:var(--mee-color-primary,#f97316); animation:mee-spin 0.8s linear infinite; }
  `],
  imports: [
    MeeBadgeComponent,
    MeeButtonComponent,
    MeeCardComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  providers: [ExportApiService],
  template: `
    <!-- §6 degradation matrix: offline banner (self-contained, no wiring needed) -->
    <mee-offline-banner />

    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Page Header -->
      <mee-page-header
        title="Export Catalog"
        subtitle="Generate Meesho-format XLSX"
      />

      <!-- §6 general error banner: 5xx / network error from initiate (idle error state) -->
      @if (errorMessage() && exportStatus() === 'idle') {
        <mee-alert-banner variant="error" [message]="errorMessage()!" />
      }

      <!-- Not-ready / validation error surface (422 gate — GAP-1 Option A real gate, R-W6-1) -->
      @if (notReadyMessage()) {
        <mee-alert-banner variant="warning" [message]="notReadyMessage()!" />
      }

      <!-- Main layout: stacked on mobile, 2-col on desktop -->
      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

        <!-- LEFT: VALIDATION GATE -->
        <div class="lg:w-2/5 space-y-4">
          <mee-card>
            <div class="p-2 space-y-4">

              <h2 class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                Pre-export checklist
              </h2>

              <!-- Display-only checklist (GAP-1 Option A — not backend-backed; 422 is real gate). -->
              <table class="w-full text-sm" aria-label="Validation checklist">
                <thead><tr>
                  <th class="text-left py-1 font-medium" style="color: var(--mee-color-on-surface-muted)">Check</th>
                  <th class="text-right py-1 font-medium" style="color: var(--mee-color-on-surface-muted)">Result</th>
                </tr></thead>
                <tbody>
                  @for (check of checkItems(); track check.label) {
                    <tr class="border-t" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface)">{{ check.label }}</td>
                      <td class="py-2 text-right">
                        <mee-badge [value]="check.ok ? 'PASS' : 'FAIL'" [severity]="check.ok ? 'success' : 'danger'" />
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
              @if (allChecksPassed()) {
                <p class="text-sm" style="color: var(--mee-color-success)">All checks passed. Ready to generate export.</p>
              } @else {
                <p class="text-sm" style="color: var(--mee-color-error)">Some checks failed. Please fix issues before exporting.</p>
              }

            </div>
          </mee-card>

          <!-- Generate Export button -->
          <mee-button
            label="Generate Export"
            variant="primary"
            [fullWidth]="true"
            [disabled]="!canGenerate()"
            [loading]="exportStatus() === 'processing'"
            (clicked)="onGenerate()"
          />
        </div>

        <!-- RIGHT: STATUS / DOWNLOAD / ERROR cards -->
        <div class="lg:w-3/5 space-y-4">

          <!-- Processing: indeterminate spinner (no progress_pct on wire, status-based only).
               FLAG(ui-styler): swap .mee-export-spinner for MeeSpinnerComponent when available. -->
          @if (exportStatus() === 'processing') {
            <mee-card>
              <div class="p-2 space-y-4" role="status" aria-label="Generating XLSX export" aria-live="polite">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="processing" />
                  <span class="text-sm font-medium" style="color: var(--mee-color-on-surface)">Generating XLSX&hellip;</span>
                </div>
                <div class="flex items-center justify-center py-4" aria-hidden="true">
                  <div class="mee-export-spinner"></div>
                </div>
                <p class="text-xs text-center" style="color: var(--mee-color-on-surface-muted)">This may take up to 2 minutes. Do not close the page.</p>
              </div>
            </mee-card>
          }

          <!-- Ready: real signed-URL download from xlsx_signed_url + zip_signed_url (spec §4.3) -->
          @if (exportStatus() === 'ready') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3"><mee-status-badge status="ready" /></div>
                <p class="text-base font-semibold" style="color: var(--mee-color-on-surface)">Your export is ready!</p>
                <p class="text-xs" style="color: var(--mee-color-on-surface-muted)">Link expires in 1 hour.</p>
                <mee-button label="Download XLSX" variant="secondary" [fullWidth]="true" (clicked)="onDownload()" />
                @if (zipDownloadUrl()) {
                  <mee-button label="Download ZIP (with images)" variant="ghost" [fullWidth]="true" (clicked)="onDownloadZip()" />
                }
                <mee-button label="Back to Dashboard" variant="ghost" [fullWidth]="true" (clicked)="onBackToDashboard()" />
              </div>
            </mee-card>
          }

          <!-- Failed: error message + retry (onRetry → fresh onGenerate, new export_id) -->
          @if (exportStatus() === 'failed') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3"><mee-status-badge status="failed" /></div>
                @if (errorMessage()) {
                  <p class="text-sm" style="color: var(--mee-color-error)">{{ errorMessage() }}</p>
                } @else {
                  <p class="text-sm" style="color: var(--mee-color-on-surface)">Export failed. Please try again.</p>
                }
                <mee-button label="Retry" variant="danger" [fullWidth]="true" (clicked)="onRetry()" />
              </div>
            </mee-card>
          }

          <!-- Idle: placeholder before first generate -->
          @if (exportStatus() === 'idle') {
            <mee-card>
              <div class="p-2">
                <p class="text-sm py-6 text-center" style="color: var(--mee-color-on-surface-muted)">Click "Generate Export" to start XLSX generation.</p>
              </div>
            </mee-card>
          }

        </div>
      </div>

    </div>
  `,
})
export class ExportComponent implements OnInit, OnDestroy {
  private readonly router    = inject(Router);
  private readonly route     = inject(ActivatedRoute);
  private readonly exportApi = inject(ExportApiService);

  // Signals
  readonly exportStatus    = signal<ExportStatus>('idle');
  readonly downloadUrl     = signal<string | null>(null);
  readonly zipDownloadUrl  = signal<string | null>(null);
  readonly exportId        = signal<string | null>(null);
  readonly errorMessage    = signal<string | null>(null);
  readonly notReadyMessage = signal<string | null>(null);
  readonly validationChecks = signal<ValidationChecks>(SIMULATED_PASSING_CHECKS);
  // D18: setInterval handle cleared on terminal status + ngOnDestroy
  private pollingIntervalId: ReturnType<typeof setInterval> | null = null;
  private pollAttempts = 0;

  // Computed
  readonly checkItems    = computed<ValidationCheckItem[]>(() => buildCheckItems(this.validationChecks()));
  readonly allChecksPassed = computed<boolean>(() => allChecksPassed(this.validationChecks()));
  readonly canGenerate   = computed<boolean>(() => canGenerate(this.exportStatus(), this.validationChecks()));

  ngOnInit(): void { /* Product ID read on-demand in onGenerate() via snapshot.params (V1). */ }

  ngOnDestroy(): void {
    this.clearPollInterval(); // D18 proven SP02: navigate-away clears poll interval
  }
  onGenerate(): void {
    if (!this.canGenerate()) return;

    const productId = this.route.snapshot.params['id'] as string | undefined;
    if (!productId) {
      console.error('[ExportComponent] No product ID in route params — route must be catalogs/:id/export');
      return;
    }

    this.notReadyMessage.set(null);
    this.errorMessage.set(null);
    this.exportStatus.set('processing');
    this.pollAttempts = 0;

    this.exportApi.initiate(productId, 'xlsx_with_images').subscribe({
      next: (resp) => {
        if ('kind' in resp) {
          const errShape = resp as InitiateErrorShape;
          this.exportStatus.set('idle');
          this.notReadyMessage.set(
            errShape.kind === 'validation'
              ? errShape.detail
              : 'Export is currently unavailable. Please try again later.'
          );
          return;
        }
        const initiated = resp as ExportInitiatedResponse;
        this.exportId.set(initiated.export_id);
        this.startPollInterval(initiated.export_id);
      },
      error: () => {
        this.exportStatus.set('idle');
        this.errorMessage.set('Export could not be started. Please try again.');
      },
    });
  }

  onDownload(): void { const url = this.downloadUrl(); if (url) { window.open(url, '_blank', 'noopener,noreferrer'); } }
  onDownloadZip(): void { const url = this.zipDownloadUrl(); if (url) { window.open(url, '_blank', 'noopener,noreferrer'); } }

  // Retry: fresh initiate (new export_id) — NOT just state reset (spec §4.3)
  onRetry(): void {
    this.clearPollInterval();
    this.exportStatus.set('idle');
    this.downloadUrl.set(null);
    this.zipDownloadUrl.set(null);
    this.exportId.set(null);
    this.errorMessage.set(null);
    this.notReadyMessage.set(null);
    this.pollAttempts = 0;
    this.onGenerate();
  }

  onBackToDashboard(): void { void this.router.navigate(['/dashboard']); }

  // D18: setInterval poll loop — DO NOT convert to RxJS interval (D18 ruling)
  private startPollInterval(exportId: string): void {
    this.clearPollInterval();
    this.pollingIntervalId = setInterval(() => {
      this.pollAttempts++;
      if (this.pollAttempts > MAX_POLL_ATTEMPTS) {
        this.clearPollInterval();
        this.exportStatus.set('failed');
        this.errorMessage.set('Export is taking too long. Please retry.');
        return;
      }
      this.exportApi.poll(exportId).subscribe({
        next: (pollResp) => {
          if (isTerminalStatus(pollResp.status)) {
            this.clearPollInterval();
            if (pollResp.status === 'ready') {
              this.exportStatus.set('ready');
              this.downloadUrl.set(pollResp.xlsx_signed_url);
              this.zipDownloadUrl.set(pollResp.zip_signed_url);
            } else {
              this.exportStatus.set('failed');
              this.errorMessage.set(pollResp.error_message ?? 'Export failed on the server. Please retry.');
            }
          }
          // 'pending' → keep polling, indeterminate spinner stays visible
        },
        error: (err: unknown) => {
          if (err instanceof ExportNotFoundError) {
            this.clearPollInterval();
            this.exportStatus.set('failed');
            this.errorMessage.set('Export record not found. Please retry.');
          }
          // Other errors → EMPTY from service; next tick retries naturally (maxPolls bounds)
        },
      });
    }, POLL_INTERVAL_MS);
  }

  private clearPollInterval(): void {
    if (this.pollingIntervalId !== null) { clearInterval(this.pollingIntervalId); this.pollingIntervalId = null; }
  }
}
