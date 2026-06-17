import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MeeIconComponent } from '@mesell/ui-kit';
import type { MeeIconName } from '@mesell/ui-kit';

/**
 * `mee-nav-item` — a single sidebar navigation link (chrome primitive).
 *
 * Presentational: renders an `<a>` router link with a semantic icon + label,
 * native `routerLinkActive` highlighting (exact or prefix), and an optional
 * filled accent/CTA look. Emits `navigated` on click so a host drawer can
 * close itself on selection.
 *
 * SHELL-ONLY (FE-3): MFEs must never import this. Router coupling is expected
 * for chrome — it is app-coupled by design.
 *
 * Lifted verbatim from the pre-Phase-4 `apps/shell` ShellComponent markup/CSS;
 * class names (`nav-item`, `nav-item--active`, `nav-item--accent`) are preserved
 * exactly for visual + test parity.
 */
@Component({
  selector: 'mee-nav-item',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, RouterLinkActive, MeeIconComponent],
  template: `
    <a
      [routerLink]="route()"
      routerLinkActive="nav-item--active"
      [routerLinkActiveOptions]="{ exact: exact() }"
      class="nav-item"
      [class.nav-item--accent]="accent()"
      (click)="navigated.emit()"
    >
      <mee-icon [name]="icon()" />
      <span>{{ label() }}</span>
    </a>
  `,
  styles: [`
    :host { display: block; }

    .nav-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 20px;
      color: var(--mee-color-sidebar-text);
      text-decoration: none;
      font-size: 14px;
      font-weight: 500;
      transition: color var(--mee-transition-fast);
      border-left: 3px solid transparent;
      min-height: 44px;
    }

    .nav-item:hover {
      color: #ffffff;
    }

    .nav-item--active {
      color: var(--mee-color-sidebar-active) !important;
      border-left-color: var(--mee-color-sidebar-active);
      background: color-mix(in srgb, var(--mee-color-primary) 8%, transparent);
    }

    .nav-item i {
      font-size: 16px;
      width: 20px;
      text-align: center;
    }

    /* Accent / primary call-to-action item (+ New Catalog) */
    .nav-item--accent {
      margin: 6px 12px;
      padding: 10px 12px;
      color: var(--mee-color-on-primary);
      background: var(--mee-color-primary);
      border-left-color: transparent;
      border-radius: var(--mee-radius-sm);
      font-weight: 600;
    }

    .nav-item--accent:hover {
      color: var(--mee-color-on-primary);
      background: color-mix(in srgb, var(--mee-color-primary) 88%, #000);
    }

    /* When the accent CTA is the active route, keep the filled look (no left-border bleed) */
    .nav-item--accent.nav-item--active {
      color: var(--mee-color-on-primary) !important;
      background: color-mix(in srgb, var(--mee-color-primary) 88%, #000);
      border-left-color: transparent;
    }
  `],
})
export class MeeNavItemComponent {
  /** Router path this item navigates to. */
  readonly route = input.required<string>();
  /** Visible label text. */
  readonly label = input.required<string>();
  /** Semantic icon name (resolved by mee-icon via MEE_ICONS). */
  readonly icon = input.required<MeeIconName>();
  /** Render as a filled accent CTA. Default false. */
  readonly accent = input<boolean>(false);
  /** Exact active-match (true, default) vs prefix active-match (false). */
  readonly exact = input<boolean>(true);

  /** Emitted on click — hosts (e.g. the mobile drawer) listen to close on navigate. */
  readonly navigated = output<void>();
}
