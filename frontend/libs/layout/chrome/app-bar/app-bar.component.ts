import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { MeeIconComponent } from '@mesell/ui-kit';

/**
 * `mee-app-bar` — the top header bar (chrome primitive).
 *
 * A sticky 60px bar with a mobile-only hamburger (emits `menuToggle`), a
 * flexible spacer, and a trailing actions region projected via `<ng-content />>`
 * (the host projects `<mee-user-menu>` there).
 *
 * `:host { display: contents }` keeps the `<header>` landmark a direct flex
 * child of the host's `.shell-main` column so `position: sticky` behaves
 * exactly as in the pre-Phase-4 shell. SHELL-ONLY (FE-3). Lifted verbatim;
 * class names preserved for parity.
 */
@Component({
  selector: 'mee-app-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeIconComponent],
  template: `
    <header class="shell-header">
      <button
        class="hamburger"
        [attr.aria-label]="menuLabel()"
        aria-haspopup="true"
        (click)="menuToggle.emit()"
      >
        <mee-icon name="menu" />
      </button>
      <div class="header-spacer"></div>
      <ng-content />
    </header>
  `,
  styles: [`
    :host { display: contents; }

    .shell-header {
      height: 60px;
      background: var(--mee-color-surface);
      border-bottom: 1px solid var(--mee-color-outline);
      display: flex;
      align-items: center;
      padding: 0 var(--mee-space-4);
      position: sticky;
      top: 0;
      z-index: 99;
    }

    .hamburger {
      display: none;
      background: none;
      border: none;
      cursor: pointer;
      font-size: 20px;
      color: var(--mee-color-on-surface);
      padding: 8px;
      border-radius: var(--mee-radius-sm);
      min-height: 44px;
      min-width: 44px;
      align-items: center;
      justify-content: center;
    }

    @media (max-width: 1023px) {
      .hamburger { display: flex; }
    }

    .header-spacer { flex: 1; }
  `],
})
export class MeeAppBarComponent {
  /** Accessible label for the hamburger button. Default 'Open navigation'. */
  readonly menuLabel = input<string>('Open navigation');

  /** Emitted when the hamburger is activated — host opens the mobile drawer. */
  readonly menuToggle = output<void>();
}
