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

import { MeeBadgeComponent }        from '../../../ui';
import { MeeButtonComponent }       from '../../../ui';
import { MeeCardComponent }         from '../../../ui';
import { MeeProgressBarComponent }  from '../../../ui';
import { PageHeaderComponent }      from '../../../shared';
import { StatusBadgeComponent }     from '../../../shared';

import {
  type ExportStatus,
  type ValidationChecks,
  type ValidationCheckItem,
  SIMULATED_PASSING_CHECKS,
  MOCK_DOWNLOAD_URL,
  buildCheckItems,
  allChecksPassed,
  canGenerate,
} from './export.model';

/** Increment per tick (10 per 500 ms → 100% in ~5 s). */
const PROGRESS_TICK = 10;
/** Interval in milliseconds. */
const TICK_INTERVAL_MS = 500;

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
  template: `
    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Page Header -->
      <mee-page-header
        title="Export Catalog"
        subtitle="Generate Meesho-format XLSX"
      />

      <!-- Main layout: stacked on mobile, 2-col on desktop -->
      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

        <!-- LEFT: VALIDATION GATE -->
        <div class="lg:w-2/5 space-y-4">
          <mee-card>
            <div class="p-2 space-y-4">

              <h2 class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                Pre-export checklist
              </h2>

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

        <!-- RIGHT: PROGRESS / DOWNLOAD / ERROR cards -->
        <div class="lg:w-3/5 space-y-4">

          <!-- Progress card: visible during processing -->
          @if (exportStatus() === 'processing') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="processing" />
                  <span class="text-sm font-medium" style="color: var(--mee-color-on-surface)">
                    Generating XLSX + images&hellip;
                  </span>
                </div>
                <mee-progress-bar
                  [value]="progress()"
                  label="Generating&hellip;"
                  [show_value]="true"
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
                <mee-button
                  label="Back to Dashboard"
                  variant="ghost"
                  [fullWidth]="true"
                  (clicked)="onBackToDashboard()"
                />
              </div>
            </mee-card>
          }

          <!-- Error card: visible on failure -->
          @if (exportStatus() === 'failed') {
            <mee-card>
              <div class="p-2 space-y-4">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="failed" />
                </div>
                <p class="text-sm" style="color: var(--mee-color-on-surface)">
                  Export failed. Please try again.
                </p>
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
  private readonly router = inject(Router);

  // ── State signals ──────────────────────────────────────────────────────────

  readonly exportStatus  = signal<ExportStatus>('idle');
  readonly progress      = signal<number>(0);
  readonly downloadUrl   = signal<string | null>(null);
  readonly exportId      = signal<string | null>(null);

  /** All 4 validation checks (simulated as all-pass per journey step 10). */
  readonly validationChecks = signal<ValidationChecks>(SIMULATED_PASSING_CHECKS);

  /** Interval handle stored for clearInterval on destroy / ready / retry. */
  private pollingIntervalId: ReturnType<typeof setInterval> | null = null;

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
    // Validation checks are synchronous in V1 simulation — already initialised via signal default.
    // In Wave 6, this would call GET /products/:id/export-validation.
  }

  ngOnDestroy(): void {
    this.clearPollInterval();
  }

  // ── Behaviours ─────────────────────────────────────────────────────────────

  /**
   * Start simulated XLSX generation.
   * State machine: idle → processing → ready (after ~5 s).
   */
  onGenerate(): void {
    if (!this.canGenerate()) return;

    this.exportStatus.set('processing');
    this.progress.set(0);

    this.pollingIntervalId = setInterval(() => {
      this.progress.update(p => p + PROGRESS_TICK);

      if (this.progress() >= 100) {
        this.clearPollInterval();
        this.exportStatus.set('ready');
        this.downloadUrl.set(MOCK_DOWNLOAD_URL);
        this.exportId.set('mock-export-' + Date.now());
      }
    }, TICK_INTERVAL_MS);
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
    this.progress.set(0);
    this.downloadUrl.set(null);
  }

  onBackToDashboard(): void {
    void this.router.navigate(['/dashboard']);
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  private clearPollInterval(): void {
    if (this.pollingIntervalId !== null) {
      clearInterval(this.pollingIntervalId);
      this.pollingIntervalId = null;
    }
  }
}
