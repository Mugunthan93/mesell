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
  styles: [`
    :host { display: block; }
    .mee-pb-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: var(--mee-space-1);
    }
    .mee-pb-label {
      font-size: 14px;
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }
    .mee-pb-value {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
    }
    ::ng-deep .p-progressbar { min-height: 8px; }
  `],
  template: `
    @if (label()) {
      <div class="mee-pb-header">
        <span class="mee-pb-label">
          {{ label() }}
        </span>
        @if (show_value()) {
          <span class="mee-pb-value">
            {{ value() }}%
          </span>
        }
      </div>
    }
    <p-progressbar
      [value]="value()"
      [showValue]="!label() && show_value()"
    />
  `,
})
export class MeeProgressBarComponent {
  readonly value = input.required<number>();
  readonly label = input<string | undefined>(undefined);
  readonly show_value = input<boolean>(true);
}
