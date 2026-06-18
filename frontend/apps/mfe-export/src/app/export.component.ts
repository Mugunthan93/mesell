import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';

import { MeeButtonComponent }       from '@mesell/ui-kit';
import { MeeCardComponent }         from '@mesell/ui-kit';
import { MeeIconComponent }         from '@mesell/ui-kit';
import { PageHeaderComponent }      from '@mesell/composites';

import {
  type ExportStatus,
  type ExportFailedCheck,
  type ExportInitiatedResponse,
  type ExportResponseDTO,
  canGenerate,
  resolveCheckMessage,
} from './export.model';

import {
  ExportApiService,
  type InitiateValidationError,
  type InitiateErrorShape,
} from './export.service';

/** Polling interval in milliseconds. */
const TICK_INTERVAL_MS = 2000;

@Component({
  selector: 'app-export',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [ExportApiService],
  imports: [
    MeeButtonComponent,
    MeeCardComponent,
    MeeIconComponent,
    PageHeaderComponent,
  ],
  styles: [`
    /* ── Page layout ─────────────────────────────────────────────── */
    :host { display: block; }
    .export-page {
      max-width: 900px;
      margin: 0 auto;
      padding: var(--mee-space-4);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }
    @media (min-width: 768px) {
      .export-page { padding: var(--mee-space-6); }
    }
    .export-layout {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }
    .export-left,
    .export-right {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      min-width: 0;
    }
    @media (min-width: 1024px) {
      .export-layout {
        flex-direction: row;
        align-items: flex-start;
      }
      .export-left { width: 40%; }
      .export-right { width: 60%; }
    }

    /* ── Checklist inner ─────────────────────────────────────────── */
    .export-checklist-inner {
      padding: var(--mee-space-2);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }
    .export-checklist-title {
      font-size: 15px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0;
    }

    /* ── Idle state ──────────────────────────────────────────────── */
    .export-idle {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: var(--mee-space-3);
      padding: var(--mee-space-8) var(--mee-space-4);
      text-align: center;
    }
    .export-idle__icon {
      width: 56px;
      height: 56px;
      border-radius: var(--mee-radius-full);
      background: var(--mee-color-bg);
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .export-idle__icon i {
      font-size: 24px;
      color: var(--mee-color-on-surface-muted);
    }
    .export-idle__title {
      font-size: 16px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0;
    }
    .export-idle__hint {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
      max-width: 280px;
    }

    /* ── Generating state ────────────────────────────────────────── */
    .export-generating {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
      padding: var(--mee-space-6) var(--mee-space-2);
    }
    .export-generating__label {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      font-size: 15px;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin: 0;
    }
    .export-generating__hint {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    /* ── Ready state ─────────────────────────────────────────────── */
    .export-ready {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding: var(--mee-space-4) var(--mee-space-2);
    }
    .export-ready__banner {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      padding: var(--mee-space-3) var(--mee-space-4);
      background: rgba(22, 163, 74, 0.1);
      border-radius: var(--mee-radius-md);
      color: var(--mee-color-success);
      font-weight: 600;
      font-size: 15px;
    }
    .export-ready__file {
      display: flex;
      align-items: center;
      gap: var(--mee-space-3);
      padding: var(--mee-space-3) var(--mee-space-4);
      background: var(--mee-color-bg);
      border-radius: var(--mee-radius-md);
      border: 1px solid var(--mee-color-outline);
    }
    .export-ready__file i {
      font-size: 22px;
      color: var(--mee-color-success);
    }
    .export-ready__filename {
      font-size: 14px;
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }
    .export-download-btn {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-2);
      min-height: 44px;
      background: var(--mee-color-primary);
      color: var(--mee-color-on-primary);
      border: none;
      border-radius: var(--mee-radius-md);
      font-size: 15px;
      font-weight: 600;
      cursor: pointer;
      text-decoration: none;
      transition: opacity var(--mee-transition-fast);
      padding: var(--mee-space-3) var(--mee-space-4);
    }
    .export-download-btn:hover {
      opacity: 0.9;
    }

    /* ── Error state ─────────────────────────────────────────────── */
    .export-error {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding: var(--mee-space-4) var(--mee-space-2);
    }
    .export-error__banner {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      padding: var(--mee-space-3) var(--mee-space-4);
      background: rgba(220, 38, 38, 0.08);
      border-radius: var(--mee-radius-md);
      color: var(--mee-color-error);
      font-weight: 600;
      font-size: 15px;
    }
  `],
  template: `
    <div class="export-page">

      <!-- Page Header -->
      <mee-page-header
        title="Export Catalog"
        subtitle="Generate Meesho-format XLSX"
      />

      <!-- Main layout: stacked on mobile, 2-col on desktop -->
      <div class="export-layout">

        <!-- LEFT: VALIDATION GATE -->
        <div class="export-left">
          <mee-card>
            <div class="export-checklist-inner">

              <h2 class="export-checklist-title">
                Pre-export checklist
              </h2>

              @if (failedChecks().length > 0) {
                <ul class="space-y-2" aria-label="Items to resolve before export">
                  @for (check of failedChecks(); track check.check_id) {
                    <li class="flex items-start gap-2 text-sm" style="color: var(--mee-color-error)">
                      <mee-icon name="warning" aria-hidden="true" />
                      <span>{{ resolveMessage(check) }}</span>
                    </li>
                  }
                </ul>
              } @else {
                <p class="text-sm" role="status" aria-live="polite" style="color: var(--mee-color-on-surface-muted)">
                  No blocking issues detected. Click "Generate Export" to proceed.
                </p>
              }

            </div>
          </mee-card>

          <!-- Generate Export button -->
          <mee-button
            class="block"
            label="Generate Export"
            variant="primary"
            [fullWidth]="true"
            [disabled]="!canGenerateSignal()"
            [loading]="exportStatus() === 'processing'"
            (clicked)="onGenerate()"
          />
        </div>

        <!-- RIGHT: STATUS PANEL -->
        <div class="export-right">

          <!-- State 2: Generating (job in progress) -->
          @if (exportStatus() === 'processing') {
            <mee-card>
              <div class="export-generating">
                <p class="export-generating__label">
                  <mee-icon name="spinner" />
                  Preparing your file&hellip;
                </p>
                <p class="export-generating__hint">This usually takes a few seconds.</p>
              </div>
            </mee-card>
          }

          <!-- State 3: Ready (file available) -->
          @if (exportStatus() === 'ready') {
            <mee-card>
              <div class="export-ready">
                <div class="export-ready__banner">
                  <mee-icon name="check-circle" />
                  <span>Your file is ready!</span>
                </div>
                <div class="export-ready__file">
                  <mee-icon name="file-excel" />
                  <span class="export-ready__filename">{{ downloadUrl() ?? 'catalog.xlsx' }}</span>
                </div>
                <a
                  [href]="downloadUrl() ?? '#'"
                  download
                  class="export-download-btn"
                  aria-label="Download XLSX file"
                >
                  <mee-icon name="download" />
                  Download XLSX
                </a>
                <mee-button
                  class="block"
                  label="Back to Dashboard"
                  variant="ghost"
                  [fullWidth]="true"
                  (clicked)="onBackToDashboard()"
                />
              </div>
            </mee-card>
          }

          <!-- State 4: Error -->
          @if (exportStatus() === 'failed') {
            <mee-card>
              <div class="export-error">
                <div class="export-error__banner">
                  <mee-icon name="times-circle" />
                  <span>{{ notReadyMessage() ?? 'Export failed. Please try again.' }}</span>
                </div>
                <mee-button
                  class="block"
                  label="Retry"
                  variant="danger"
                  [fullWidth]="true"
                  (clicked)="onRetry()"
                />
              </div>
            </mee-card>
          }

          <!-- State 1: Idle (no job yet) -->
          @if (exportStatus() === 'idle') {
            <mee-card>
              <div class="export-idle">
                <div class="export-idle__icon">
                  <mee-icon name="file-export" />
                </div>
                <p class="export-idle__title">Ready to export</p>
                <p class="export-idle__hint">Your Meesho-format XLSX will be generated once all checks pass.</p>
              </div>
            </mee-card>
          }

        </div>
      </div>

    </div>
  `,
})
export class ExportComponent implements OnInit, OnDestroy {
  private readonly router = inject(Router);
  private readonly exportApi = inject(ExportApiService);

  // ── State signals ──────────────────────────────────────────────────────────

  readonly exportStatus    = signal<ExportStatus>('idle');
  readonly downloadUrl     = signal<string | null>(null);
  readonly exportId        = signal<string | null>(null);
  readonly notReadyMessage = signal<string | null>(null);

  /** Real failed checks populated from 422 body.failed_checks[]. Empty until a 422 occurs. */
  readonly failedChecks = signal<ExportFailedCheck[]>([]);

  /** Interval handle stored for clearInterval on destroy / ready / retry. */
  private pollingIntervalId: ReturnType<typeof setInterval> | null = null;

  // ── Computed ───────────────────────────────────────────────────────────────

  /**
   * Generate button is enabled only when status is idle.
   * The real readiness gate is the backend 422 — button is always enabled at idle.
   */
  readonly canGenerateSignal = computed<boolean>(
    () => canGenerate(this.exportStatus())
  );

  // ── Lifecycle ──────────────────────────────────────────────────────────────

  ngOnInit(): void {
    // Route param reading would go here for real product ID injection.
    // For V1: product ID read from ActivatedRoute in onGenerate().
  }

  ngOnDestroy(): void {
    this.clearPollInterval();
  }

  // ── Public method for template ─────────────────────────────────────────────

  /**
   * Resolves a human-readable display message for a failed check.
   * Delegates to pure function from export.model for testability.
   */
  resolveMessage(check: ExportFailedCheck): string {
    return resolveCheckMessage(check);
  }

  // ── Behaviours ─────────────────────────────────────────────────────────────

  /**
   * Initiate XLSX export via backend. Wires real ExportApiService.
   * State machine: idle → processing → ready | failed.
   */
  onGenerate(): void {
    if (!this.canGenerateSignal()) return;

    // Clear any stale state from previous attempt.
    this.notReadyMessage.set(null);
    this.failedChecks.set([]);
    this.exportStatus.set('processing');

    // TODO(V1): read productId from ActivatedRoute snapshot.params['id']
    // Using a placeholder for V1; coordinator wires route params.
    const productId = 'current-product-id';

    this.exportApi.initiate(productId).subscribe({
      next: (result: ExportInitiatedResponse | InitiateErrorShape) => {
        if (!('kind' in result)) {
          // HTTP 202 — export job queued; start polling
          this.exportId.set(result.export_id);
          this.startPollInterval(result.export_id);
        } else if (result.kind === 'validation') {
          const valErr = result as InitiateValidationError;
          this.exportStatus.set('idle');
          this.notReadyMessage.set(valErr.detail);
          this.failedChecks.set(valErr.failedChecks);
        } else {
          // kind === 'unavailable' — flag-off or product not found
          this.exportStatus.set('idle');
          this.notReadyMessage.set('Export is currently unavailable. Please try again later.');
          this.failedChecks.set([]);
        }
      },
      error: () => {
        // EMPTY from service — network/5xx; service already logged
        this.exportStatus.set('idle');
        this.notReadyMessage.set('Export could not be started. Please try again.');
        this.failedChecks.set([]);
      },
    });
  }

  /**
   * Open the download URL in a new tab.
   * Uses window.open — NOT Router.navigate (external URL).
   */
  onDownload(): void {
    const url = this.downloadUrl();
    if (url) {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }

  /** Reset state machine back to idle so the user can re-trigger. */
  onRetry(): void {
    this.clearPollInterval();
    this.exportStatus.set('idle');
    this.downloadUrl.set(null);
    this.notReadyMessage.set(null);
    this.failedChecks.set([]);
  }

  onBackToDashboard(): void {
    void this.router.navigate(['/dashboard']);
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  /**
   * Start polling GET /api/v1/exports/{exportId} on a 2 s interval.
   * Stops on terminal status (ready | failed) or ngOnDestroy.
   */
  private startPollInterval(exportId: string): void {
    this.pollingIntervalId = setInterval(() => {
      this.exportApi.poll(exportId).subscribe({
        next: (pollResp: ExportResponseDTO) => {
          if (pollResp.status === 'ready') {
            this.clearPollInterval();
            this.exportStatus.set('ready');
            this.downloadUrl.set(pollResp.xlsx_signed_url);
          } else if (pollResp.status === 'failed') {
            this.clearPollInterval();
            this.exportStatus.set('failed');
            this.notReadyMessage.set(pollResp.error_message);
          }
          // 'pending': do nothing — poll loop continues
        },
        error: () => {
          // ExportNotFoundError or unhandled throw — stop polling gracefully
          this.clearPollInterval();
          this.exportStatus.set('failed');
          this.notReadyMessage.set('Export status could not be determined. Please retry.');
        },
      });
    }, TICK_INTERVAL_MS);
  }

  private clearPollInterval(): void {
    if (this.pollingIntervalId !== null) {
      clearInterval(this.pollingIntervalId);
      this.pollingIntervalId = null;
    }
  }
}
