// shared/components/page-header/page-header.component.ts

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'mee-page-header',
  standalone: true,
  imports: [MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    :host { display: block; }
  `],
  template: `
    <div style="display:flex; align-items:flex-start; justify-content:space-between; gap:16px; margin-bottom:24px;">
      <!-- Left: title + subtitle -->
      <div>
        <h1 style="font-size:24px; font-weight:700; color:#1F2937; margin:0; line-height:1.3;">
          {{ title() }}
        </h1>
        @if (subtitle()) {
          <p style="font-size:14px; color:#6B7280; margin:4px 0 0;">{{ subtitle() }}</p>
        }
      </div>

      <!-- Right: CTA button -->
      @if (ctaLabel()) {
        <button
          (click)="ctaClick.emit()"
          style="display:inline-flex; align-items:center; gap:6px; background:#F26B23; color:#FFFFFF; border:none; border-radius:8px; padding:10px 20px; font-size:14px; font-weight:600; cursor:pointer; white-space:nowrap; min-height:44px; flex-shrink:0;"
        >
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

  @Output() readonly ctaClick = new EventEmitter<void>();
}
