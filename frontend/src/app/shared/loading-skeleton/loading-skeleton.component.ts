import {
  ChangeDetectionStrategy,
  Component,
  input,
} from '@angular/core';
import { MeeSkeletonComponent } from '../../ui';
import type { MeeSkeletonVariant } from '../../ui';

@Component({
  selector: 'mee-loading-skeleton',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MeeSkeletonComponent],
  template: `
    @switch (variant()) {
      @case ('text') {
        <mee-skeleton variant="text" [lines]="lines()" />
      }
      @case ('card') {
        <mee-skeleton variant="card" [lines]="lines()" />
      }
      @case ('table-row') {
        <div class="flex flex-col gap-2">
          <mee-skeleton variant="table-row" [lines]="lines()" />
          <mee-skeleton variant="table-row" [lines]="lines()" />
          <mee-skeleton variant="table-row" [lines]="lines()" />
          <mee-skeleton variant="table-row" [lines]="lines()" />
        </div>
      }
      @case ('stat-card') {
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
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
