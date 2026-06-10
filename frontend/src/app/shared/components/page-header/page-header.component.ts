// shared/components/page-header/page-header.component.ts

import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'mee-page-header',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; }
  `],
  template: `
    <div class="flex items-start justify-between gap-4 mb-6">
      <!-- Left: title + subtitle -->
      <div>
        <h1 class="text-2xl font-bold text-on-surface m-0 leading-snug">
          {{ title() }}
        </h1>
        @if (subtitle()) {
          <p class="text-sm text-on-surface-variant mt-1 mb-0">{{ subtitle() }}</p>
        }
      </div>

      <!-- Right: CTA button -->
      @if (ctaLabel()) {
        <button mat-flat-button color="primary" (click)="ctaClick.emit()" class="inline-flex items-center gap-1.5 whitespace-nowrap min-h-[44px] flex-shrink-0">
          @if (ctaIcon()) {
            <mat-icon style="font-size:18px; width:18px; height:18px; line-height:18px;">{{ ctaIcon() }}</mat-icon>
          }
          {{ ctaLabel() }}
        </button>
      }
    </div>
  `,
})
export class PageHeaderComponent {
  readonly title = input.required<string>();
  readonly subtitle = input<string | undefined>(undefined);
  readonly ctaLabel = input<string | undefined>(undefined);
  readonly ctaIcon = input<string | undefined>(undefined);

  readonly ctaClick = output<void>();
}
