import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  ElementRef,
  input,
  ViewChild,
} from '@angular/core';

export type MeeAlertVariant = 'error' | 'warning' | 'info' | 'success';

/**
 * MeeAlertBannerComponent — reusable inline alert banner.
 *
 * Visual layer only. No PrimeNG dependency.
 * Uses design tokens from _tokens.css exclusively (no hardcoded colours).
 *
 * Usage:
 *   <mee-alert-banner variant="error" [message]="errorMessage()" />
 *   <mee-alert-banner variant="warning" message="You are offline." />
 *
 * A11y:
 *   - role="alert" triggers immediate announcement for screen readers.
 *   - aria-live="polite" queues the announcement (non-interruptive).
 *   - When the banner appears, it is programmatically focused so keyboard
 *     users receive context before attempting form re-submission.
 *   - The host element receives tabindex="-1" so focus() works without
 *     adding it to the Tab order.
 */
@Component({
  selector: 'mee-alert-banner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      #bannerEl
      class="mee-alert-banner"
      [class]="'mee-alert-banner mee-alert-banner--' + variant()"
      role="alert"
      aria-live="polite"
      tabindex="-1"
    >
      <span class="mee-alert-banner__icon" aria-hidden="true">
        {{ iconChar() }}
      </span>
      <span class="mee-alert-banner__message">{{ message() }}</span>
    </div>
  `,
  styles: [`
    /* Host sits flush with container — no extra margin (consumers add their own). */
    :host { display: block; }

    .mee-alert-banner {
      display: flex;
      align-items: flex-start;
      gap: 8px;
      border-radius: var(--mee-radius-sm, 7px);
      padding: 10px 14px;
      font-size: 14px;
      line-height: 1.4;
      /* Minimum touch-target height (WCAG 2.5.8 / MeeSell 44px rule) */
      min-height: 44px;
      outline: none; /* suppress focus ring on programmatic focus — visible ring not needed for non-interactive */
    }

    /* Per-variant colour mapping — all values from design tokens */
    .mee-alert-banner--error {
      background: var(--mee-color-error-light);
      border: 1px solid var(--mee-color-error);
      color: var(--mee-color-error);
    }
    .mee-alert-banner--warning {
      background: var(--mee-color-warning-light);
      border: 1px solid var(--mee-color-warning);
      color: var(--mee-color-warning);
    }
    .mee-alert-banner--info {
      background: var(--mee-color-info-light);
      border: 1px solid var(--mee-color-info);
      color: var(--mee-color-info);
    }
    .mee-alert-banner--success {
      background: var(--mee-color-success-light);
      border: 1px solid var(--mee-color-success);
      color: var(--mee-color-success);
    }

    .mee-alert-banner__icon {
      flex-shrink: 0;
      font-size: 16px;
      line-height: 1.4;
    }

    .mee-alert-banner__message {
      flex: 1;
    }

    /* 360px — no layout change, but ensure text wraps gracefully */
    @media (max-width: 400px) {
      .mee-alert-banner {
        font-size: 13px;
        padding: 8px 12px;
      }
    }
  `],
})
export class MeeAlertBannerComponent implements AfterViewInit {
  readonly variant = input<MeeAlertVariant>('error');
  readonly message = input.required<string>();

  @ViewChild('bannerEl') bannerEl?: ElementRef<HTMLDivElement>;

  /** Move focus to the banner when it first renders so keyboard/AT users hear it. */
  ngAfterViewInit(): void {
    // Defer one microtask so the host binding cycle finishes before focus().
    Promise.resolve().then(() => {
      this.bannerEl?.nativeElement.focus({ preventScroll: false });
    });
  }

  readonly iconChar = computed(() => {
    switch (this.variant()) {
      case 'error':   return '!';
      case 'warning': return '⚠';
      case 'info':    return 'i';
      case 'success': return '✓';
      default:        return '!';
    }
  });
}
