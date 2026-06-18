import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { MeeButtonComponent } from '@mesell/ui-kit';
import type { MeeIconName } from '@mesell/ui-kit';

@Component({
  selector: 'mee-page-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeButtonComponent],
  styles: [`
    :host { display: block; }
    .ph-root {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-1);
      padding-block: var(--mee-space-4);
      border-bottom: 1px solid var(--mee-color-outline);
    }
    @media (min-width: 640px) {
      .ph-root {
        flex-direction: row;
        align-items: center;
        justify-content: space-between;
      }
    }
    .ph-text {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .ph-title {
      font-size: 24px;
      font-weight: 700;
      line-height: 1.2;
      color: var(--mee-color-on-surface);
      margin: 0;
    }
    .ph-subtitle {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }
  `],
  template: `
    <div class="ph-root">
      <!-- Title + subtitle -->
      <div class="ph-text">
        <h1 class="ph-title">{{ title() }}</h1>

        @if (subtitle()) {
          <p class="ph-subtitle">{{ subtitle() }}</p>
        }
      </div>

      <!-- Optional CTA -->
      @if (hasCta()) {
        <mee-button
          [label]="cta_label()!"
          [icon]="cta_icon()"
          variant="primary"
          (clicked)="cta_click.emit()"
        />
      }
    </div>
  `,
})
export class PageHeaderComponent {
  readonly title     = input.required<string>();
  readonly subtitle  = input<string | undefined>(undefined);
  readonly cta_label = input<string | undefined>(undefined);
  readonly cta_icon  = input<MeeIconName | undefined>(undefined);

  readonly cta_click = output<void>();

  readonly hasCta = computed(() => !!this.cta_label());
}
