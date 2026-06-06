// shared/components/loading-spinner/loading-spinner.component.ts

import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'mee-loading-spinner',
  standalone: true,
  imports: [MatProgressSpinnerModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px;">
      <div class="mee-loading-spinner">
        <mat-spinner [diameter]="diameter()" />
        @if (caption()) {
          <p class="mee-loading-spinner__caption">{{ caption() }}</p>
        }
      </div>
    </div>
  `,
})
export class LoadingSpinnerComponent {
  readonly diameter = input<number>(32);
  readonly caption = input<string | undefined>(undefined);
}
