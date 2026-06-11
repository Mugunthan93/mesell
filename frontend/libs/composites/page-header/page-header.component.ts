import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { MeeButtonComponent } from '@mesell/ui-kit';

@Component({
  selector: 'mee-page-header',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeButtonComponent],
  template: `
    <div
      class="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between py-4"
      style="border-bottom: 1px solid var(--mee-color-outline);"
    >
      <!-- Title + subtitle -->
      <div class="flex flex-col gap-0.5">
        <h1
          class="text-2xl font-bold leading-tight"
          style="color: var(--mee-color-on-surface);"
        >{{ title() }}</h1>

        @if (subtitle()) {
          <p
            class="text-sm"
            style="color: var(--mee-color-on-surface-muted);"
          >{{ subtitle() }}</p>
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
  readonly cta_icon  = input<string | undefined>(undefined);

  readonly cta_click = output<void>();

  readonly hasCta = computed(() => !!this.cta_label());
}
