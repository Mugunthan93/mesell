import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { Skeleton } from 'primeng/skeleton';
import type { MeeSkeletonVariant } from './skeleton.types';

@Component({
  selector: 'mee-skeleton',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [Skeleton],
  template: `
    @switch (variant()) {
      @case ('text') {
        <div class="flex flex-col gap-2">
          @for (item of linesArray(); track item) {
            <p-skeleton width="100%" height="1rem" />
          }
        </div>
      }
      @case ('card') {
        <div class="flex flex-col gap-3 p-4" style="background: var(--mee-color-surface); border-radius: var(--mee-radius-md)">
          <p-skeleton width="100%" height="160px" />
          <p-skeleton width="70%" height="1rem" />
          <p-skeleton width="50%" height="1rem" />
        </div>
      }
      @case ('table-row') {
        <div class="flex gap-4 items-center py-2">
          <p-skeleton width="30%" height="1rem" />
          <p-skeleton width="25%" height="1rem" />
          <p-skeleton width="20%" height="1rem" />
          <p-skeleton width="15%" height="1rem" />
        </div>
      }
      @case ('stat-card') {
        <div class="flex flex-col gap-2 p-4" style="background: var(--mee-color-surface); border-radius: var(--mee-radius-md)">
          <p-skeleton width="40%" height="1rem" />
          <p-skeleton width="60%" height="2rem" />
        </div>
      }
      @default {
        <p-skeleton width="100%" height="1rem" />
      }
    }
  `,
})
export class MeeSkeletonComponent {
  readonly variant = input<MeeSkeletonVariant>('text');
  readonly lines = input<number>(1);

  readonly linesArray = computed<number[]>(() =>
    Array.from({ length: this.lines() }, (_, i) => i)
  );
}
