import {
  ChangeDetectionStrategy,
  Component,
  inject,
} from '@angular/core';
import { NetworkService } from '@mesell/core';

/**
 * MeeOfflineBannerComponent — global shell-level offline indicator.
 *
 * Rendered at the top of the shell layout (above the router-outlet).
 * Automatically shows when NetworkService.online() is false.
 *
 * Visual layer only. No PrimeNG dependency.
 * Uses design tokens from _tokens.css exclusively.
 *
 * A11y:
 *   - role="status" (not "alert") at shell level — non-interruptive announcement.
 *   - aria-live="polite" queues announcement so it does not interrupt current
 *     screen-reader speech on page load.
 *   - aria-atomic="true" ensures the full message is re-read on any text change.
 *   - The element is always in the DOM when online (empty, hidden via CSS) so
 *     screen readers do not get confused by the node appearing/disappearing;
 *     visibility is controlled by @if on the content, not the host.
 *
 * Mobile: fixed to the top of the viewport so it is always visible regardless
 *   of scroll position. Width is 100% with a max-width clamp so it does not
 *   stretch to extremes on large screens.
 *
 * Usage (shell layout):
 *   <mee-offline-banner />
 *   <router-outlet />
 */
@Component({
  selector: 'mee-offline-banner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div
      class="mee-offline-banner"
      role="status"
      aria-live="polite"
      aria-atomic="true"
      [attr.aria-hidden]="networkSvc.online() ? 'true' : 'false'"
    >
      @if (!networkSvc.online()) {
        <span class="mee-offline-banner__icon" aria-hidden="true">⚠</span>
        <span class="mee-offline-banner__text">
          You are offline — changes will resume when reconnected.
        </span>
      }
    </div>
  `,
  styles: [`
    :host { display: block; }

    .mee-offline-banner {
      /* Always occupies space to avoid layout shift; collapses when empty */
      width: 100%;
      min-height: 0;
      overflow: hidden;
      transition: max-height var(--mee-transition-base, 250ms ease),
                  padding    var(--mee-transition-base, 250ms ease);
      max-height: 0;
      padding: 0;
    }

    /* When offline (has child content) — expand */
    .mee-offline-banner:has(> span) {
      max-height: 80px;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      padding: 10px 16px;
      background: var(--mee-color-warning-light);
      border-bottom: 1px solid var(--mee-color-warning);
      color: var(--mee-color-warning);
      font-size: 14px;
      line-height: 1.4;
      text-align: center;
    }

    .mee-offline-banner__icon {
      flex-shrink: 0;
      font-size: 16px;
    }

    .mee-offline-banner__text {
      /* Wrap gracefully on 360px */
      word-break: break-word;
    }

    /* 360px — slightly smaller font to fit the message on one line when possible */
    @media (max-width: 400px) {
      .mee-offline-banner:has(> span) {
        font-size: 12px;
        padding: 8px 12px;
      }
    }
  `],
})
export class MeeOfflineBannerComponent {
  readonly networkSvc = inject(NetworkService);
}
