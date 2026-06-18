import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { MeeButtonComponent } from '@mesell/ui-kit';

@Component({
  selector: 'mee-empty-state',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeButtonComponent],
  styles: [`
    :host { display: block; }
    .es-root {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: var(--mee-space-4);
      padding: var(--mee-space-10) var(--mee-space-4);
      text-align: center;
    }
    .es-icon {
      font-size: 64px;
      color: var(--mee-color-on-surface-muted);
    }
    .es-message {
      font-size: 16px;
      max-width: 280px;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }
  `],
  template: `
    <div class="es-root" role="status" [attr.aria-label]="message()">
      <!-- Icon -->
      <span
        class="material-symbols-outlined es-icon"
        aria-hidden="true"
      >{{ icon() }}</span>

      <!-- Message -->
      <p class="es-message">{{ message() }}</p>

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
