// shared/components/loading-spinner/loading-spinner.component.ts

import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

@Component({
  selector: 'mee-loading-spinner',
  standalone: true,
  imports: [MatProgressSpinnerModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex flex-col items-center justify-center gap-2">
      <div class="flex flex-col items-center gap-1">
        <mat-spinner [diameter]="diameter()" />
        @if (caption()) {
          <p class="text-xs text-on-surface-variant text-center mt-1">{{ caption() }}</p>
        }
      </div>
    </div>
  `,
})
export class LoadingSpinnerComponent {
  readonly diameter = input<number>(32);
  readonly caption = input<string | undefined>(undefined);
}
