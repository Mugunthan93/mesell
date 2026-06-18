import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { MeeSkeletonComponent } from '@mesell/ui-kit';
import type { MeeSkeletonVariant } from '@mesell/ui-kit';

@Component({
  selector: 'mee-loading-skeleton',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeSkeletonComponent],
  styles: [`
    :host { display: block; }
    .ls-table-rows {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }
    .ls-stat-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: var(--mee-space-3);
    }
    @media (min-width: 640px) {
      .ls-stat-grid { grid-template-columns: repeat(4, 1fr); }
    }
  `],
  template: `
    @switch (variant()) {
      @case ('text') {
        <mee-skeleton variant="text" [lines]="lines()" />
      }
      @case ('card') {
        <mee-skeleton variant="card" [lines]="lines()" />
      }
      @case ('table-row') {
        <div class="ls-table-rows">
          <mee-skeleton variant="table-row" [lines]="lines()" />
          <mee-skeleton variant="table-row" [lines]="lines()" />
          <mee-skeleton variant="table-row" [lines]="lines()" />
          <mee-skeleton variant="table-row" [lines]="lines()" />
        </div>
      }
      @case ('stat-card') {
        <div class="ls-stat-grid">
          <mee-skeleton variant="stat-card" [lines]="lines()" />
          <mee-skeleton variant="stat-card" [lines]="lines()" />
          <mee-skeleton variant="stat-card" [lines]="lines()" />
          <mee-skeleton variant="stat-card" [lines]="lines()" />
        </div>
      }
      @default {
        <mee-skeleton variant="text" [lines]="lines()" />
      }
    }
  `,
})
export class LoadingSkeletonComponent {
  readonly variant = input<MeeSkeletonVariant>('text');
  readonly lines   = input<number>(1);
}
