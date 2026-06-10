import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { ProgressBar } from 'primeng/progressbar';

@Component({
  selector: 'mee-progress-bar',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ProgressBar],
  template: `
    @if (label()) {
      <div class="flex justify-between items-center mb-1">
        <span class="text-sm font-medium" style="color: var(--mee-color-on-surface)">
          {{ label() }}
        </span>
        @if (show_value()) {
          <span class="text-sm" style="color: var(--mee-color-on-surface-muted)">
            {{ value() }}%
          </span>
        }
      </div>
    }
    <p-progressbar
      [value]="value()"
      [showValue]="!label() && show_value()"
      style="min-height: 8px;"
    />
  `,
})
export class MeeProgressBarComponent {
  readonly value = input.required<number>();
  readonly label = input<string | undefined>(undefined);
  readonly show_value = input<boolean>(true);
}
