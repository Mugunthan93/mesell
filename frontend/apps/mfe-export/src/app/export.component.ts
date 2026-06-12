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
import { MeeProgressBarComponent }  from '@mesell/ui-kit';
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

@Component({
  selector: 'app-export',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MeeBadgeComponent,
    MeeButtonComponent,
    MeeCardComponent,
    MeeProgressBarComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
  ],
  providers: [ExportApiService],
  template: `
    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Page Header -->
      <mee-page-header
        title="Export Catalog"
        subtitle="Generate Meesho-format XLSX"
      />

      <!-- Not-ready / validation error message (422 gate — GAP-1 Option A) -->
      @if (notReadyMessage()) {
        <div role="alert" class="rounded-md px-4 py-3 text-sm"
             style="background: var(--mee-color-error-container); color: var(--mee-color-on-error-container)">
          {{ notReadyMessage() }}
        </div>
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

              <!-- Display-only checklist (GAP-1 Option A — SIMULATED_PASSING_CHECKS constant).
                   Real readiness gate is the 422 response from POST export-xlsx. -->
              <table class="w-full text-sm" aria-label="Validation checklist">
                <thead>
                  <tr>
                    <th class="text-left py-1 font-medium" style="color: var(--mee-color-on-surface-muted)">
                      Check
                    </th>
                    <th class="text-right py-1 font-medium" style="color: var(--mee-color-on-surface-muted)">
                      Result
                    </th>
                  </tr>
                </thead>
                <tbody>
                  @for (check of checkItems(); track check.label) {
                    <tr class="border-t" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface)">
                        {{ check.label }}
                      </td>
                      <td class="py-2 text-right">
                        <mee-badge
                          [value]="check.ok ? 'PASS' : 'FAIL'"
                          [severity]="check.ok ? 'success' : 'danger'"
                        />
                      </td>
                    </tr>
                  }
                </tbody>
              </table>

              @if (allChecksPassed()) {
                <p class="text-sm" style="color: var(--mee-color-success)">
                  All checks passed. Ready to generate export.
                </p>
              } @else {
                <p class="text-sm" style="color: var(--mee-color-error)">
                  Some checks failed. Please fix issues before exporting.
                </p>
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

          <!-- Processing card: indeterminate spinner during pending poll (no progress_pct on wire) -->
          @if (exportStatus() === 'processing') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="processing" />
                  <span class="text-sm font-medium" style="color: var(--mee-color-on-surface)">
                    Generating XLSX&hellip;
                  </span>
                </div>
                <!-- Indeterminate mode: value=0 placeholder — builder 2 replaces with
                     proper indeterminate spinner (no fake progress, no numeric value). -->
                <mee-progress-bar
                  [value]="0"
                  label="Generating&hellip;"
                  [show_value]="false"
                />
              </div>
            </mee-card>
          }

          <!-- Download card: visible when ready -->
          @if (exportStatus() === 'ready') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="ready" />
                </div>
                <p class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                  Your export is ready!
                </p>
                <p class="text-xs" style="color: var(--mee-color-on-surface-muted)">
                  Link expires in 1 hour.
                </p>
                <mee-button
                  label="Download XLSX"
                  variant="secondary"
                  [fullWidth]="true"
                  (clicked)="onDownload()"
                />
                @if (zipDownloadUrl()) {
                  <mee-button
                    label="Download ZIP (with images)"
                    variant="ghost"
                    [fullWidth]="true"
                    (clicked)="onDownloadZip()"
                  />
                }
                <mee-button
                  label="Back to Dashboard"
                  variant="ghost"
                  [fullWidth]="true"
                  (clicked)="onBackToDashboard()"
                />
              </div>
            </mee-card>
          }

          <!-- Error card: visible on failure or timeout -->
          @if (exportStatus() === 'failed') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="failed" />
                </div>
                @if (errorMessage()) {
                  <p class="text-sm" style="color: var(--mee-color-error)">
                    {{ errorMessage() }}
                  </p>
                } @else {
                  <p class="text-sm" style="color: var(--mee-color-on-surface)">
                    Export failed. Please try again.
                  </p>
                }
                <mee-button
                  label="Retry"
                  variant="danger"
                  [fullWidth]="true"
                  (clicked)="onRetry()"
                />
              </div>
            </mee-card>
          }

          <!-- Idle placeholder -->
          @if (exportStatus() === 'idle') {
            <mee-card>
              <div class="p-2">
                <p class="text-sm py-6 text-center" style="color: var(--mee-color-on-surface-muted)">
                  Click "Generate Export" to start XLSX generation.
                </p>
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

  // ── State signals ──────────────────────────────────────────────────────────

  readonly exportStatus    = signal<ExportStatus>('idle');
  readonly downloadUrl     = signal<string | null>(null);
  readonly zipDownloadUrl  = signal<string | null>(null);
  readonly exportId        = signal<string | null>(null);
  /** User-facing error message (from failed poll or network error). */
  readonly errorMessage    = signal<string | null>(null);
  /** Actionable not-ready message from 422 initiate response (GAP-1 Option A real gate). */
  readonly notReadyMessage = signal<string | null>(null);

  /** All 4 validation checks (display-only per GAP-1 Option A; not backend-backed). */
  readonly validationChecks = signal<ValidationChecks>(SIMULATED_PASSING_CHECKS);

  /**
   * D18 timer-preserve: setInterval handle.
   * Cleared on: terminal status ('ready' / 'failed') + ngOnDestroy (navigate-away).
   */
  private pollingIntervalId: ReturnType<typeof setInterval> | null = null;
  private pollAttempts = 0;

  // ── Computed ───────────────────────────────────────────────────────────────

  /** Flat list of check items for @for iteration. Delegates to pure function. */
  readonly checkItems = computed<ValidationCheckItem[]>(
    () => buildCheckItems(this.validationChecks())
  );

  /** All 4 checks must pass. Delegates to pure function. */
  readonly allChecksPassed = computed<boolean>(
    () => allChecksPassed(this.validationChecks())
  );

  /**
   * Generate button is enabled only when all checks pass AND status is idle.
   * Delegates to pure function.
   */
  readonly canGenerate = computed<boolean>(
    () => canGenerate(this.exportStatus(), this.validationChecks())
  );

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  ngOnInit(): void {
    // Product ID is read from route on demand in onGenerate() via snapshot.params.
    // Validation checks are synchronous display-only in V1 (GAP-1 Option A).
  }

  ngOnDestroy(): void {
    // D18 — PROVEN SP02: navigate-away must clear the poll interval.
    this.clearPollInterval();
  }

  // ── Behaviours ─────────────────────────────────────────────────────────────

  /**
   * Initiates real XLSX export via POST /api/v1/products/{id}/export-xlsx (202).
   * On success: stores export_id and starts the setInterval poll (D18 timer-preserve).
   * On 422 not-ready: shows actionable message; does NOT start polling.
   * On 404 unavailable: shows unavailable message; does NOT start polling.
   */
  onGenerate(): void {
    if (!this.canGenerate()) return;

    const productId = this.route.snapshot.params['id'] as string | undefined;
    if (!productId) {
      console.error('[ExportComponent] No product ID in route params — route must be catalogs/:id/export');
      return;
    }

    // Reset any previous error / not-ready state.
    this.notReadyMessage.set(null);
    this.errorMessage.set(null);
    this.exportStatus.set('processing');
    this.pollAttempts = 0;

    this.exportApi.initiate(productId, 'xlsx_with_images').subscribe({
      next: (resp) => {
        if ('kind' in resp) {
          // Error shape emitted by the service (422 / 404 — non-throwing contract).
          const errShape = resp as InitiateErrorShape;
          this.exportStatus.set('idle');
          if (errShape.kind === 'validation') {
            this.notReadyMessage.set(errShape.detail);
          } else {
            this.notReadyMessage.set('Export is currently unavailable. Please try again later.');
          }
          return;
        }
        // Happy path — 202 ExportInitiatedResponse.
        const initiated = resp as ExportInitiatedResponse;
        this.exportId.set(initiated.export_id);
        this.startPollInterval(initiated.export_id);
      },
      error: () => {
        // Should not reach here (service maps all errors to emitted shapes or EMPTY).
        this.exportStatus.set('idle');
        this.errorMessage.set('Export could not be started. Please try again.');
      },
    });
  }

  /**
   * Open the real GCS signed XLSX URL in a new tab.
   * URL expires in 1 hour — re-poll to refresh if needed.
   */
  onDownload(): void {
    const url = this.downloadUrl();
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }

  /** Open the ZIP (xlsx + images) signed URL if available. */
  onDownloadZip(): void {
    const url = this.zipDownloadUrl();
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }

  /**
   * Re-trigger a fresh initiate (new export_id) — NOT just a state reset.
   * Clears existing poll interval first per D18.
   */
  onRetry(): void {
    this.clearPollInterval();
    this.exportStatus.set('idle');
    this.downloadUrl.set(null);
    this.zipDownloadUrl.set(null);
    this.exportId.set(null);
    this.errorMessage.set(null);
    this.notReadyMessage.set(null);
    this.pollAttempts = 0;
    // Re-trigger a fresh initiate — produces a new export_id (new job in Celery queue).
    this.onGenerate();
  }

  onBackToDashboard(): void {
    void this.router.navigate(['/dashboard']);
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  /**
   * D18 timer-preserve: starts the setInterval poll loop.
   * Each tick calls poll() once. Clears on terminal status or maxPolls reached.
   * DO NOT convert to RxJS interval — D18 ruling forbids it.
   */
  private startPollInterval(exportId: string): void {
    this.clearPollInterval();
    this.pollingIntervalId = setInterval(() => {
      this.pollAttempts++;

      // Timeout guard: cap at MAX_POLL_ATTEMPTS (2 min at 2 s interval).
      if (this.pollAttempts > MAX_POLL_ATTEMPTS) {
        this.clearPollInterval();
        this.exportStatus.set('failed');
        this.errorMessage.set('Export is taking too long. Please retry.');
        return;
      }

      this.exportApi.poll(exportId).subscribe({
        next: (pollResp) => {
          if (isTerminalStatus(pollResp.status)) {
            // D18: clear on terminal status (ready or failed).
            this.clearPollInterval();
            if (pollResp.status === 'ready') {
              this.exportStatus.set('ready');
              this.downloadUrl.set(pollResp.xlsx_signed_url);
              this.zipDownloadUrl.set(pollResp.zip_signed_url);
            } else {
              // 'failed'
              this.exportStatus.set('failed');
              this.errorMessage.set(
                pollResp.error_message ?? 'Export failed on the server. Please retry.'
              );
            }
          }
          // 'pending' → keep polling (no state change; indeterminate spinner stays visible).
        },
        error: (err: unknown) => {
          // ExportNotFoundError (404) — unrecoverable, clear interval.
          if (err instanceof ExportNotFoundError) {
            this.clearPollInterval();
            this.exportStatus.set('failed');
            this.errorMessage.set('Export record not found. Please retry.');
          }
          // Other errors are mapped to EMPTY by the service — no emission here.
          // The next tick fires naturally; maxPolls bounds the loop.
        },
      });
    }, POLL_INTERVAL_MS);
  }

  /** D18: clears the setInterval poll. Called on terminal status + ngOnDestroy. */
  private clearPollInterval(): void {
    if (this.pollingIntervalId !== null) {
      clearInterval(this.pollingIntervalId);
      this.pollingIntervalId = null;
    }
  }
}
