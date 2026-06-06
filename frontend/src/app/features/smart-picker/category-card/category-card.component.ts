// features/smart-picker/category-card/category-card.component.ts
// Single category suggestion card — per AC-3
// Displays path, confidence %, sample attribute chips (up to 4 + overflow indicator)

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { CategorySuggestion } from '../smart-picker.model';

@Component({
  selector: 'mee-category-card',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MatChipsModule, MatIconModule],
  template: `
    <div
      class="mee-category-card rounded-lg border border-gray-200 p-4 cursor-pointer
             transition-all duration-200 hover:border-primary hover:ring-2 hover:ring-primary
             focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
      tabindex="0"
      role="button"
      [attr.aria-label]="'Select ' + suggestion().super_category + ' > ' + suggestion().leaf_category"
      (click)="select()"
      (keydown.enter)="select()"
      (keydown.space)="select()"
    >
      <!-- Category path -->
      <div class="flex items-center justify-between mb-2">
        <div class="flex-1">
          <span class="text-sm text-gray-500">{{ suggestion().super_category }}</span>
          <div class="flex items-center gap-1">
            <mat-icon class="text-gray-400" style="font-size: 16px; width: 16px; height: 16px;">chevron_right</mat-icon>
            <span class="font-semibold text-gray-900">{{ suggestion().leaf_category }}</span>
          </div>
        </div>

        <!-- Confidence badge -->
        <div
          class="ml-3 flex-shrink-0 px-2 py-1 rounded-full text-xs font-medium"
          [class]="confidenceClass()"
        >
          {{ confidencePercent() }}
        </div>
      </div>

      <!-- Sample attribute chips -->
      @if (visibleAttributes().length > 0) {
        <div class="flex flex-wrap gap-1 mt-2">
          @for (attr of visibleAttributes(); track attr.canonical_name) {
            <mat-chip class="text-xs" [disableRipple]="true">
              {{ attr.display_label }}
            </mat-chip>
          }
          @if (overflowCount() > 0) {
            <span class="text-xs text-gray-500 self-center">
              +{{ overflowCount() }} more
            </span>
          }
        </div>
      }
    </div>
  `,
})
export class CategoryCardComponent {
  readonly suggestion = input.required<CategorySuggestion>();
  readonly categorySelected = output<CategorySuggestion>();

  readonly visibleAttributes = computed(() =>
    this.suggestion().sample_attributes.slice(0, 4),
  );

  readonly overflowCount = computed(() =>
    Math.max(0, this.suggestion().sample_attributes.length - 4),
  );

  readonly confidencePercent = computed(() => {
    const pct = Math.round(this.suggestion().confidence * 100);
    return `${pct}%`;
  });

  readonly confidenceClass = computed(() => {
    const conf = this.suggestion().confidence;
    if (conf >= 0.8) return 'bg-green-100 text-green-800';
    if (conf >= 0.5) return 'bg-yellow-100 text-yellow-800';
    return 'bg-red-100 text-red-800';
  });

  select(): void {
    this.categorySelected.emit(this.suggestion());
  }
}
