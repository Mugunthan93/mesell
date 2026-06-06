// shared/components/empty-state/empty-state.component.ts

import { ChangeDetectionStrategy, Component, EventEmitter, input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'mee-empty-state',
  standalone: true,
  imports: [MatIconModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:48px; gap:16px; text-align:center;">
      <mat-icon style="font-size:48px; width:48px; height:48px; color:#9CA3AF;">{{ icon() }}</mat-icon>
      <p style="font-size:18px; font-weight:600; color:#1F2937; margin:0;">{{ headline() }}</p>
      @if (body()) {
        <p style="font-size:14px; color:#6B7280; max-width:360px; margin:0;">{{ body() }}</p>
      }
      @if (ctaLabel()) {
        <button
          (click)="ctaClick.emit()"
          style="background:#F26B23; color:#FFFFFF; border:none; border-radius:8px; padding:10px 20px; font-size:14px; font-weight:600; cursor:pointer; min-height:44px; min-width:44px;"
        >
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

  @Output() readonly ctaClick = new EventEmitter<void>();
}
