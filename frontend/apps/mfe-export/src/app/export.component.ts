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

import { MeeBadgeComponent }        from '@mesell/ui-kit';
import { MeeButtonComponent }       from '@mesell/ui-kit';
import { MeeCardComponent }         from '@mesell/ui-kit';
import { MeeIconComponent }         from '@mesell/ui-kit';
import { MeeProgressBarComponent }  from '@mesell/ui-kit';
import { PageHeaderComponent }      from '@mesell/composites';

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
    MeeIconComponent,
    MeeProgressBarComponent,
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
    .export-th-check {
      text-align: left;
      padding-block: var(--mee-space-1);
      font-weight: 500;
      width: 100%;
    }
    .export-th-result {
      text-align: right;
      padding-block: var(--mee-space-1);
      font-weight: 500;
      white-space: nowrap;
      padding-left: var(--mee-space-3);
    }
    .export-td-check {
      width: 100%;
    }
    .export-check-pass {
      font-size: 14px;
      color: var(--mee-color-success);
      margin: 0;
    }
    .export-check-fail {
      font-size: 14px;
      color: var(--mee-color-error);
      margin: 0;
    }

    /* ── Checklist table ─────────────────────────────────────────── */
    .export-checklist-table thead th {
      color: var(--mee-color-on-surface-muted);
    }
    .export-checklist-table tbody tr {
      border-bottom: 1px solid var(--mee-color-outline);
    }
    .export-checklist-table tbody tr:hover {
      background: var(--mee-color-bg);
    }
    .export-checklist-table td {
      padding: var(--mee-space-3) 0;
      color: var(--mee-color-on-surface);
    }
    .export-checklist-table td.result-col {
      text-align: right;
      width: 1px;
      white-space: nowrap;
      padding-left: var(--mee-space-3);
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

              <table class="export-checklist-table" aria-label="Validation checklist">
                <thead>
                  <tr>
                    <th class="export-th-check">
                      Check
                    </th>
                    <th class="export-th-result">
                      Result
                    </th>
                  </tr>
                </thead>
                <tbody>
                  @for (check of checkItems(); track check.label) {
                    <tr>
                      <td class="export-td-check">
                        {{ check.label }}
                      </td>
                      <td class="result-col">
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
                <p class="export-check-pass">
                  All checks passed. Ready to generate export.
                </p>
              } @else {
                <p class="export-check-fail">
                  Some checks failed. Please fix issues before exporting.
                </p>
              }

            </div>
          </mee-card>

          <!-- Generate Export button -->
          <mee-button
            class="block"
            label="Generate Export"
            variant="primary"
            icon="download"
            [fullWidth]="true"
            [disabled]="!canGenerate()"
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
                <mee-progress-bar
                  [value]="progress()"
                  label="Generating&hellip;"
                  [show_value]="true"
                />
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
                  <span>Export failed. Please try again.</span>
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
