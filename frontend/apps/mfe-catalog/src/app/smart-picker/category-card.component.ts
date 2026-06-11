/**
 * CategoryCardComponent — presentational smart-picker card.
 *
 * Standalone, OnPush.
 * Inputs:  suggestion: CategorySuggestion (the §9.E locked shape)
 * Outputs: picked: EventEmitter<string> — emits category_id when "Use this category" is clicked.
 *
 * Renders:
 *  - path as a breadcrumb heading
 *  - confidence as mee-progress-bar [value] (confidence * 100 to convert 0-1 -> 0-100 for display)
 *  - reasons[] as a bullet list (max 3 items)
 *  - "Use this category" mee-button -> emits picked(category_id)
 *
 * NO commission_pct — not in §9.E contract (lead ruling 2026-06-11).
 */
import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Output,
  input,
  computed,
} from '@angular/core';

import {
  MeeButtonComponent,
  MeeCardComponent,
  MeeProgressBarComponent,
} from '@mesell/ui-kit';

import type { CategorySuggestion } from './smart-picker.model';

@Component({
  selector: 'app-category-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MeeButtonComponent,
    MeeCardComponent,
    MeeProgressBarComponent,
  ],
  template: `
    <mee-card>
      <div
        class="flex flex-col gap-3 p-1"
        role="listitem"
        [attr.aria-label]="cardAriaLabel()"
      >

        <!-- Breadcrumb path -->
        <p
          class="text-sm font-semibold leading-snug"
          style="color: var(--mee-color-on-surface);"
        >
          {{ suggestion().path }}
        </p>

        <!-- Confidence bar (confidence is 0-1 float; scale * 100 for display) -->
        <mee-progress-bar
          [value]="confidencePct()"
          label="Match confidence"
          [show_value]="true"
        />

        <!-- Reasons list (max 3) -->
        @if (suggestion().reasons.length > 0) {
          <ul
            class="list-disc list-inside text-xs space-y-1"
            style="color: var(--mee-color-on-surface-muted);"
            aria-label="Reasons for this suggestion"
          >
            @for (reason of suggestion().reasons.slice(0, 3); track reason) {
              <li>{{ reason }}</li>
            }
          </ul>
        }

        <!-- CTA — 44px touch target enforced via min-h-[44px] on the button element -->
        <div class="flex justify-end mt-1">
          <mee-button
            label="Use this category"
            variant="secondary"
            size="sm"
            [fullWidth]="false"
            (clicked)="onUsed()"
          />
        </div>

      </div>
    </mee-card>
  `,
  styles: [`
    :host {
      display: block;
    }
    mee-button {
      min-height: 44px;
    }
  `],
})
export class CategoryCardComponent {
  /** The §9.E CategorySuggestion to display. */
  readonly suggestion = input.required<CategorySuggestion>();

  /** confidence * 100, rounded, for the progress bar (0-100 range). */
  readonly confidencePct = computed<number>(() =>
    Math.round(this.suggestion().confidence * 100),
  );

  /** Accessible label for the card listitem. */
  readonly cardAriaLabel = computed<string>(() =>
    `Category: ${this.suggestion().leaf_name}`,
  );

  /** Emits the category_id when "Use this category" is clicked. */
  @Output() readonly picked = new EventEmitter<string>();

  onUsed(): void {
    this.picked.emit(this.suggestion().category_id);
  }
}
