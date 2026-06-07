// features/catalog-form/autofill-overlay/autofill-overlay.component.ts
// B4: Wraps any field with a pending AI suggestion per §18.G
// The primitive renders inside <ng-content>. This overlay adds accept/dismiss bar.
// Accept/reject events bubble to CatalogFormComponent — this component does NOT patch itself.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { AiSuggestion } from '@core/models/ai-suggestion.model';

export interface AutofillAccepted {
  readonly canonicalName: string;
  readonly value: unknown;
}

export interface AutofillRejected {
  readonly canonicalName: string;
  readonly rejectedReason: string;
}

@Component({
  selector: 'mee-autofill-overlay',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  styles: [`
    .autofill-wrapper {
      position: relative;
    }
    .autofill-wrapper.has-suggestion {
      border: 1px solid var(--mee-color-warning);
      border-radius: var(--mee-radius-sm);
    }
    .autofill-bar {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 4px 8px;
      background: var(--mee-color-primary-light);
      border-top: 1px solid var(--mee-color-warning);
      font-size: 12px;
    }
    .ai-label {
      flex: 1;
      color: var(--mee-color-on-surface);
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .accept-btn {
      color: var(--mee-color-primary);
      background: transparent;
      border: none;
      cursor: pointer;
      font-weight: 600;
      font-size: 13px;
      min-height: 44px;
      min-width: 44px;
      padding: 0 8px;
    }
    .reject-btn {
      color: var(--mee-color-on-surface-variant, #5a6a85);
      background: transparent;
      border: none;
      cursor: pointer;
      font-size: 13px;
      min-height: 44px;
      min-width: 44px;
      padding: 0 8px;
    }
    .accept-btn:focus-visible,
    .reject-btn:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
      border-radius: var(--mee-radius-sm);
    }
  `],
  template: `
    <div class="autofill-wrapper" [class.has-suggestion]="showOverlay()">
      <ng-content />
      @if (showOverlay()) {
        <div class="autofill-bar" role="status" aria-live="polite">
          <span class="ai-label">AI suggests: {{ displayValue() }}</span>
          <button
            class="accept-btn"
            type="button"
            aria-label="Accept AI suggestion"
            (click)="onAccept()"
          >Accept</button>
          <button
            class="reject-btn"
            type="button"
            aria-label="Dismiss AI suggestion"
            (click)="onReject()"
          >Dismiss</button>
        </div>
      }
    </div>
  `,
})
export class AutofillOverlayComponent {
  readonly fieldName = input.required<string>();
  readonly suggestion = input<AiSuggestion | null>(null);
  readonly productId = input<string>('');

  readonly accepted = output<AutofillAccepted>();
  readonly rejected = output<AutofillRejected>();

  readonly showOverlay = computed<boolean>(() => {
    const s = this.suggestion();
    return s !== null && !s?.accepted && !s?.rejectedReason;
  });

  readonly displayValue = computed<string>(() => {
    const s = this.suggestion();
    if (!s) return '';
    if (Array.isArray(s.value)) return s.value.join(', ');
    return String(s.value);
  });

  onAccept(): void {
    const s = this.suggestion();
    if (!s) return;
    this.accepted.emit({
      canonicalName: this.fieldName(),
      value: s.value,
    });
  }

  onReject(): void {
    this.rejected.emit({
      canonicalName: this.fieldName(),
      rejectedReason: 'seller_dismissed',
    });
  }
}
