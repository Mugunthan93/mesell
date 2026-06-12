import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { ProgressSpinner } from 'primeng/progressspinner';

/**
 * MeeSpinner — Layer-2 indeterminate spinner primitive (ui-kit).
 *
 * Frozen-surface amendment (2026-06-12, founder-approved §7.3): the codebase had
 * NO shared spinner wrapper, so lanes hand-rolled local PrimeNG progressspinners
 * (mfe-pricing, mfe-export, etc.). This seals PrimeNG's <p-progress-spinner>
 * behind the @mesell/ui-kit abstraction wall (FRONTEND_ARCHITECTURE §2 — no
 * PrimeNG imports outside ui-kit) with the a11y contract baked in:
 *
 *   - role="status" + aria-busy="true" on the host wrapper (screen-reader
 *     announces "busy" while the spinner is mounted).
 *   - an accessible name: the visible/sr-only `label` text is read out; when no
 *     label is given, a default "Loading" label is exposed via aria-label.
 *   - prefers-reduced-motion: the rotate animation is disabled (the spinner
 *     still renders as a static ring) for users who request reduced motion.
 *
 * Indeterminate only by design — there is MeeProgressBar for determinate %.
 *
 * V1.5 CLEANUP: migrate the existing local spinners (mfe-pricing, mfe-export
 * inline <p-progress-spinner> / CSS spinners) to this primitive. Not rewired in
 * this amendment — they work today; this only adds the shared primitive.
 */
@Component({
  selector: 'mee-spinner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ProgressSpinner],
  template: `
    <div
      class="mee-spinner-host"
      role="status"
      aria-busy="true"
      [attr.aria-label]="label() ?? 'Loading'"
    >
      <p-progress-spinner
        [style]="dimensionStyle()"
        [strokeWidth]="strokeWidth()"
        [attr.aria-hidden]="true"
      />
      @if (label()) {
        <span class="mee-spinner-sr">{{ label() }}</span>
      }
    </div>
  `,
  styles: [
    `
      .mee-spinner-host {
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }

      /* Visually-hidden accessible label (screen-reader only). */
      .mee-spinner-sr {
        position: absolute;
        width: 1px;
        height: 1px;
        padding: 0;
        margin: -1px;
        overflow: hidden;
        clip: rect(0, 0, 0, 0);
        white-space: nowrap;
        border: 0;
      }

      /* Respect a user's reduced-motion preference: freeze the rotation.
         The spinner still renders (a static ring) so the loading state is
         visible, but it does not spin. */
      @media (prefers-reduced-motion: reduce) {
        .mee-spinner-host ::ng-deep .p-progressspinner-circle {
          animation: none !important;
        }
        .mee-spinner-host ::ng-deep .p-progressspinner-spin,
        .mee-spinner-host ::ng-deep svg {
          animation: none !important;
        }
      }
    `,
  ],
})
export class MeeSpinnerComponent {
  /**
   * Accessible label announced by screen readers (e.g. "Loading catalogs").
   * When omitted, a default "Loading" aria-label is applied so the spinner is
   * never an unlabelled status region. A provided label also renders sr-only.
   */
  readonly label = input<string | undefined>(undefined);

  /** Diameter of the spinner in pixels. Default 40px. */
  readonly diameter = input<number>(40);

  /** Stroke width of the ring. Mirrors PrimeNG's strokeWidth. */
  readonly strokeWidth = input<string>('4');

  /** Inline style applied to <p-progress-spinner> to size it. */
  readonly dimensionStyle = computed(() => {
    const d = `${this.diameter()}px`;
    return { width: d, height: d };
  });
}
