// shared/components/loading-skeleton/loading-skeleton.component.ts

import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type SkeletonVariant = 'card' | 'table-row' | 'text' | 'stat-card';

@Component({
  selector: 'mee-loading-skeleton',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    @keyframes shimmer {
      from { background-position: -200% 0; }
      to   { background-position:  200% 0; }
    }
    .shimmer-box {
      background: linear-gradient(90deg, var(--mee-color-surface-variant) 25%, var(--mee-color-outline) 50%, var(--mee-color-surface-variant) 75%);
      background-size: 200% 100%;
      animation: shimmer 1.5s infinite linear;
    }
  `],
  template: `
    @switch (variant()) {
      @case ('stat-card') {
        <div style="display:flex; flex-direction:row; gap:16px;">
          @for (box of statBoxes; track box) {
            <div class="shimmer-box" style="height:120px; border-radius:16px; flex:1;"></div>
          }
        </div>
      }
      @case ('table-row') {
        <div style="display:flex; flex-direction:column; gap:8px;">
          @for (row of tableRows(); track row.index) {
            <div class="shimmer-box" [style]="'height:40px; border-radius:6px; width:' + row.width + ';'"></div>
          }
        </div>
      }
      @case ('text') {
        <div style="display:flex; flex-direction:column; gap:8px;">
          <div class="shimmer-box" style="height:16px; border-radius:4px; width:80%;"></div>
          <div class="shimmer-box" style="height:12px; border-radius:4px; width:60%;"></div>
          <div class="shimmer-box" style="height:12px; border-radius:4px; width:90%;"></div>
        </div>
      }
      @default {
        <!-- card (default) -->
        <div class="shimmer-box" style="height:80px; border-radius:16px; width:100%;"></div>
      }
    }
  `,
})
export class LoadingSkeletonComponent {
  readonly variant = input<SkeletonVariant>('card');
  readonly rows = input<number>(3);

  readonly statBoxes = [0, 1, 2, 3];

  readonly tableRows = computed(() => {
    const count = this.rows();
    return Array.from({ length: count }, (_, i) => ({
      index: i,
      width: i % 2 === 0 ? '100%' : '70%',
    }));
  });
}
