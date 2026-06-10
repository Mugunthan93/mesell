import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { MeeButtonComponent } from '../../ui';

@Component({
  selector: 'mee-empty-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeButtonComponent],
  template: `
    <div
      class="flex flex-col items-center justify-center gap-4 py-12 px-4 text-center"
      role="status"
      [attr.aria-label]="message()"
    >
      <!-- Icon -->
      <span
        class="material-symbols-outlined"
        aria-hidden="true"
        style="font-size:64px; color: var(--mee-color-on-surface-muted);"
      >{{ icon() }}</span>

      <!-- Message -->
      <p
        class="text-base max-w-xs"
        style="color: var(--mee-color-on-surface-muted);"
      >{{ message() }}</p>

      <!-- Optional CTA -->
      @if (hasCta()) {
        <mee-button
          [label]="cta_label()!"
          variant="primary"
          (clicked)="cta_click.emit()"
        />
      }
    </div>
  `,
})
export class EmptyStateComponent {
  readonly icon      = input.required<string>();
  readonly message   = input.required<string>();
  readonly cta_label = input<string | undefined>(undefined);

  readonly cta_click = output<void>();

  readonly hasCta = computed(() => !!this.cta_label());
}
