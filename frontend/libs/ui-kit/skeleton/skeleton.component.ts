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
  styles: [`
    :host { display: block; }
    .mee-sk-text {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }
    .mee-sk-card {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
      padding: var(--mee-space-4);
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
    }
    .mee-sk-table-row {
      display: flex;
      gap: var(--mee-space-4);
      align-items: center;
      padding-block: var(--mee-space-2);
    }
    .mee-sk-stat {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
      padding: var(--mee-space-4);
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
    }
  `],
  template: `
    @switch (variant()) {
      @case ('text') {
        <div class="mee-sk-text">
          @for (item of linesArray(); track item) {
            <p-skeleton width="100%" height="1rem" />
          }
        </div>
      }
      @case ('card') {
        <div class="mee-sk-card">
          <p-skeleton width="100%" height="160px" />
          <p-skeleton width="70%" height="1rem" />
          <p-skeleton width="50%" height="1rem" />
        </div>
      }
      @case ('table-row') {
        <div class="mee-sk-table-row">
          <p-skeleton width="30%" height="1rem" />
          <p-skeleton width="25%" height="1rem" />
          <p-skeleton width="20%" height="1rem" />
          <p-skeleton width="15%" height="1rem" />
        </div>
      }
      @case ('stat-card') {
        <div class="mee-sk-stat">
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
