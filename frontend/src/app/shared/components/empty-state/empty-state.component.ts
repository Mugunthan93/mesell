// shared/components/empty-state/empty-state.component.ts

import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'mee-empty-state',
  standalone: true,
  imports: [MatIconModule, MatButtonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex flex-col items-center justify-center p-12 gap-4 text-center">
      <mat-icon style="font-size:48px; width:48px; height:48px;" class="text-on-surface-variant">{{ icon() }}</mat-icon>
      <p class="text-lg font-semibold text-on-surface m-0">{{ headline() }}</p>
      @if (body()) {
        <p class="text-sm text-on-surface-variant max-w-[360px] m-0">{{ body() }}</p>
      }
      @if (ctaLabel()) {
        <button mat-flat-button color="primary" (click)="ctaClick.emit()" class="min-h-[44px]">
          {{ ctaLabel() }}
        </button>
      }
    </div>
  `,
})
export class EmptyStateComponent {
  readonly icon = input<string>('info');
  readonly headline = input<string>('');
  readonly body = input<string | undefined>(undefined);
  readonly ctaLabel = input<string | undefined>(undefined);

  readonly ctaClick = output<void>();
}
