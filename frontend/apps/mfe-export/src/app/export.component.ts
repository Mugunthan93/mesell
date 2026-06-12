import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  OnDestroy,
  OnInit,
  ViewChild,
  computed,
  effect,
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
// UI-KIT SPINNER GAP: @mesell/ui-kit has no MeeSpinnerComponent (indeterminate spinner).
// The local .mee-export-spinner is the V1 workaround. This gap is queued for the lead's
// frozen-surface amendment channel — do NOT add MeeSpinnerComponent to libs/ui-kit directly.
@Component({
  selector: 'app-export',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    /* ── host-level token gap scoping ───────────────────────────────────────────
       All tokens below exist in libs/design-tokens/_tokens.css (Layer 1).
       No missing tokens — no :host override needed for Layer 1 values.
    ── */

    /* ── 360px layout: responsive padding + card stacking already handled by
       Tailwind flex-col + lg:flex-row. Additional touch-target enforcement: ── */
    :host {
      display: block;
    }

    /* 44px min-height on all interactive elements inside this component. */
    :host mee-button {
      min-height: 44px;
    }

    /* Checklist table rows: 44px effective touch target via padding */
    :host .mee-check-row {
      min-height: 44px;
    }

    /* Idle/empty-state card: visual centering at all breakpoints */
    :host .mee-export-idle {
      min-height: 120px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 24px 16px;
    }

    /* ── Indeterminate spinner (local workaround — ui-kit gap flagged above) ── */
    @keyframes mee-spin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }

    /* Spinner: tokens only — NO hardcoded hex fallbacks (lane discipline). */
    .mee-export-spinner {
      width: 44px;
      height: 44px;
      border-radius: 50%;
      border: 4px solid var(--mee-color-outline);
      border-top-color: var(--mee-color-primary);
      animation: mee-spin 0.8s linear infinite;
    }

    /* Respect user's motion preference (WCAG 2.3.3 — animation from interaction). */
    @media (prefers-reduced-motion: reduce) {
      .mee-export-spinner {
        animation-duration: 2s;
        border-top-color: var(--mee-color-primary);
        /* Slowed rather than removed — still communicates "in progress" to sighted users. */
      }
    }

    /* Ready card: visual emphasis via surface token (no hardcoded color) */
    :host .mee-export-ready-card {
      border-left: 3px solid var(--mee-color-success);
      outline: none; /* focus ring suppressed — browser default removed; component manages focus */
    }

    /* Failed card: visual emphasis */
    :host .mee-export-failed-card {
      border-left: 3px solid var(--mee-color-error);
      outline: none;
    }
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
    <!-- §6 degradation matrix: offline banner (self-contained, no wiring needed).
         Placement: FIRST element in template — above all page chrome (Wave 6B offline pattern). -->
    <mee-offline-banner />

    <div class="max-w-5xl mx-auto px-4 py-6 space-y-6">

      <!-- Page Header -->
      <mee-page-header
        title="Export Catalog"
        subtitle="Generate Meesho-format XLSX"
      />

      <!-- §6 general error banner: 5xx / network error from initiate (idle error state).
           MeeAlertBannerComponent: tabindex="-1" + aria-live="assertive" + focus on AfterViewInit
           (handled internally by MeeAlertBannerComponent per Wave 6A a11y pattern). -->
      @if (errorMessage() && exportStatus() === 'idle') {
        <mee-alert-banner variant="error" [message]="errorMessage()!" />
      }

      <!-- Not-ready / validation error surface (422 gate — GAP-1 Option A real gate, R-W6-1).
           variant="warning" — actionable guidance, not a system error. -->
      @if (notReadyMessage()) {
        <mee-alert-banner variant="warning" [message]="notReadyMessage()!" />
      }

      <!-- Main layout: flex-col on mobile (360px stacks cleanly), lg:flex-row on desktop. -->
      <div class="flex flex-col gap-6 lg:flex-row lg:items-start">

        <!-- LEFT: PRE-EXPORT CHECKLIST + GENERATE BUTTON -->
        <div class="lg:w-2/5 space-y-4">
          <mee-card>
            <div class="p-4 space-y-4">

              <h2 id="checklist-heading" class="text-base font-semibold" style="color: var(--mee-color-on-surface)">
                Pre-export checklist
              </h2>

              <!-- Display-only checklist (GAP-1 Option A — not backend-backed; 422 is real gate).
                   scope="col" on th: WCAG 1.3.1 table header association. -->
              <table class="w-full text-sm" aria-labelledby="checklist-heading">
                <thead>
                  <tr>
                    <th scope="col" class="text-left py-2 font-medium" style="color: var(--mee-color-on-surface-muted)">Check</th>
                    <th scope="col" class="text-right py-2 font-medium" style="color: var(--mee-color-on-surface-muted)">Result</th>
                  </tr>
                </thead>
                <tbody>
                  @for (check of checkItems(); track check.label) {
                    <tr class="mee-check-row border-t" style="border-color: var(--mee-color-outline)">
                      <td class="py-2" style="color: var(--mee-color-on-surface)">{{ check.label }}</td>
                      <td class="py-2 text-right">
                        <mee-badge [value]="check.ok ? 'PASS' : 'FAIL'" [severity]="check.ok ? 'success' : 'danger'" />
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
              <!-- Checklist summary: live region so screen readers announce readiness change -->
              <p
                id="checklist-status"
                class="text-sm"
                role="status"
                aria-live="polite"
                aria-atomic="true"
                [style.color]="allChecksPassed() ? 'var(--mee-color-success)' : 'var(--mee-color-error)'"
              >
                {{ allChecksPassed() ? 'All checks passed. Ready to generate export.' : 'Some checks failed. Please fix issues before exporting.' }}
              </p>

            </div>
          </mee-card>

          <!-- Generate Export button: aria-describedby ties it to checklist status.
               44px min-height enforced via :host mee-button style rule. -->
          <mee-button
            label="Generate Export"
            variant="primary"
            [fullWidth]="true"
            [disabled]="!canGenerate()"
            [loading]="exportStatus() === 'processing'"
            aria-describedby="checklist-status"
            (clicked)="onGenerate()"
          />
        </div>

        <!-- RIGHT: STATUS / DOWNLOAD / ERROR cards.
             aria-live="polite" on the wrapper: announces card transitions (processing→ready,
             processing→failed) to screen readers without interrupting current speech. -->
        <div
          class="lg:w-3/5 space-y-4"
          aria-live="polite"
          aria-atomic="false"
          aria-label="Export status"
        >

          <!-- Processing: indeterminate spinner (no progress_pct on wire, status-based only).
               role="status" on inner div: provides secondary announce hook for AT.
               aria-hidden on spinner div: purely decorative animation. -->
          @if (exportStatus() === 'processing') {
            <mee-card>
              <div class="p-4 space-y-4" role="status" aria-label="Generating XLSX export">
                <div class="flex items-center gap-3">
                  <mee-status-badge status="processing" />
                  <span class="text-sm font-medium" style="color: var(--mee-color-on-surface)">Generating XLSX&hellip;</span>
                </div>
                <div class="flex items-center justify-center py-4" aria-hidden="true">
                  <!-- Local indeterminate spinner (ui-kit gap flagged — frozen-surface amendment queue) -->
                  <div class="mee-export-spinner"></div>
                </div>
                <p class="text-xs text-center" style="color: var(--mee-color-on-surface-muted)">This may take up to 2 minutes. Do not close the page.</p>
              </div>
            </mee-card>
          }

          <!-- Ready: signed-URL download. tabindex="-1" + #readyCardRef → focus on transition.
               mee-export-ready-card: left-border success accent (token-only, no hardcoded hex). -->
          @if (exportStatus() === 'ready') {
            <div
              #readyCardRef
              class="mee-export-ready-card"
              tabindex="-1"
              style="outline: none;"
            >
              <mee-card>
                <div class="p-4 space-y-4">
                  <div class="flex items-center gap-3">
                    <mee-status-badge status="ready" />
                    <p class="text-base font-semibold" style="color: var(--mee-color-on-surface)">Your export is ready!</p>
                  </div>
                  <p class="text-xs" style="color: var(--mee-color-on-surface-muted)">Link expires in 1 hour. Re-generate if the link has expired.</p>
                  <mee-button label="Download XLSX" variant="secondary" [fullWidth]="true" (clicked)="onDownload()" />
                  @if (zipDownloadUrl()) {
                    <mee-button label="Download ZIP (with images)" variant="ghost" [fullWidth]="true" (clicked)="onDownloadZip()" />
                  }
                  <mee-button label="Back to Dashboard" variant="ghost" [fullWidth]="true" (clicked)="onBackToDashboard()" />
                </div>
              </mee-card>
            </div>
          }

          <!-- Failed: error message + retry. tabindex="-1" + #failedCardRef → focus on transition.
               mee-export-failed-card: left-border error accent (token-only). -->
          @if (exportStatus() === 'failed') {
            <div
              #failedCardRef
              class="mee-export-failed-card"
              tabindex="-1"
              style="outline: none;"
            >
              <mee-card>
                <div class="p-4 space-y-4">
                  <div class="flex items-center gap-3">
                    <mee-status-badge status="failed" />
                    <p class="text-sm font-semibold" style="color: var(--mee-color-error)">Export failed</p>
                  </div>
                  @if (errorMessage()) {
                    <p class="text-sm" style="color: var(--mee-color-error)">{{ errorMessage() }}</p>
                  } @else {
                    <p class="text-sm" style="color: var(--mee-color-on-surface)">Export failed. Please try again.</p>
                  }
                  <mee-button label="Retry Export" variant="danger" [fullWidth]="true" (clicked)="onRetry()" />
                </div>
              </mee-card>
            </div>
          }

          <!-- Idle / first-visit: empty-state guidance card.
               mee-export-idle: vertically centred, consistent min-height at all breakpoints. -->
          @if (exportStatus() === 'idle') {
            <mee-card>
              <div class="mee-export-idle" aria-label="Export not yet started">
                <p
                  class="text-sm font-medium text-center"
                  style="color: var(--mee-color-on-surface)"
                >
                  Ready to generate your Meesho XLSX
                </p>
                <p
                  class="text-xs text-center"
                  style="color: var(--mee-color-on-surface-muted)"
                >
                  Complete the checklist on the left, then click "Generate Export".
                </p>
              </div>
            </mee-card>
          }

        </div>
      </div>

    </div>
  `,
})
export class ExportComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly router    = inject(Router);
  private readonly route     = inject(ActivatedRoute);
  private readonly exportApi = inject(ExportApiService);

  // ViewChild refs for programmatic focus on state transitions (WCAG 2.4.3 focus order).
  // Deferred via Promise.resolve().then() — same pattern as Wave 6B onboarding (profile.component.ts).
  @ViewChild('readyCardRef')  private readyCardRef?: ElementRef<HTMLDivElement>;
  @ViewChild('failedCardRef') private failedCardRef?: ElementRef<HTMLDivElement>;

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
  readonly checkItems      = computed<ValidationCheckItem[]>(() => buildCheckItems(this.validationChecks()));
  readonly allChecksPassed = computed<boolean>(() => allChecksPassed(this.validationChecks()));
  readonly canGenerate     = computed<boolean>(() => canGenerate(this.exportStatus(), this.validationChecks()));

  constructor() {
    // effect() runs in the component injection context — safe for signal writes.
    // Focus on ready/failed transition: deferred microtask avoids focus during CD cycle.
    // Per Wave 6B onboarding pattern (profile.component.ts: Promise.resolve().then(...)).
    effect(() => {
      const status = this.exportStatus();
      if (status === 'ready') {
        Promise.resolve().then(() => this.readyCardRef?.nativeElement.focus());
      } else if (status === 'failed') {
        Promise.resolve().then(() => this.failedCardRef?.nativeElement.focus());
      }
    });
  }

  ngOnInit(): void { /* Product ID read on-demand in onGenerate() via snapshot.params (V1). */ }
  ngAfterViewInit(): void { /* No-op — programmatic focus triggered from effect(), not lifecycle. */ }

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
