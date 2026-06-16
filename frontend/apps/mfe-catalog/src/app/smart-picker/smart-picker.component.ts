/**
 * SmartPickerComponent — /catalogs/new
 *
 * Standalone, OnPush page component for the Smart Category Picker (V1 Feature 2).
 *
 * Flow:
 *  - Seller types a product description (10-5000 chars).
 *  - Pressing Enter or clicking the Send button fires onSubmit().
 *  - CategoryService.suggest(description) is called; results render in place.
 *  - Top-3 of the returned suggestions (max 5) are rendered via CategoryCardComponent.
 *  - fallback_offered=true and empty suggestions -> EmptyStateComponent + "Browse all categories".
 *  - fallback_offered=true and non-empty -> 3 cards + secondary "Browse if none match" link.
 *  - "Use this category" on a card -> CategoryService.selectCategory(category_id).
 *
 * D4 rename: folder was catalog-new/, class was CatalogNewComponent. Renamed per FEATURE_PLAN §D4.
 * Contract fix: §9.E-locked interfaces (no commission_pct; confidence 0-1 float). Port from e97c4f5.
 * MeeTreeSelect/SIMULATED_TREE removed per D1 (browse routes to /categories/browse, not inline tree).
 * Plan 4-B: auto-fire debounce pipeline removed; replaced with explicit onSubmit() handler.
 */
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
  computed,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';

import {
  MeeTextareaComponent,
  MeeSkeletonComponent,
  MeeButtonComponent,
  MeeToastService,
} from '@mesell/ui-kit';
import {
  PageHeaderComponent,
  EmptyStateComponent,
} from '@mesell/composites';

import { CategoryService } from './services/category.service';
import { CategoryCardComponent } from './category-card.component';
import type { CategorySuggestion, SuggestResponse } from './smart-picker.model';

const SMART_PICKER_ERROR_COPY: Record<string, string> = {
  'validation.suggest_q.too_short_or_long': 'Please enter between 1 and 5000 characters to search categories.',
  'category.lookup.not_found': "We couldn't find that category. Please pick another from the list.",
  'category.field_enum.not_found': "We couldn't load the options for this field. Please refresh the page.",
  'rate_limit.window.exceeded': "You've reached the category suggestion limit. Try again in an hour.",
};
const GENERIC_ERROR_COPY = 'Something went wrong. Please try again.';

@Component({
  selector: 'app-smart-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MeeTextareaComponent,
    MeeSkeletonComponent,
    MeeButtonComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    CategoryCardComponent,
  ],
  providers: [CategoryService],
  template: `
    <div class="max-w-2xl mx-auto px-4 py-8">

      <!-- Page title -->
      <div class="text-center mb-8">
        <mee-page-header
          [title]="'New Catalog'"
          [subtitle]="'Describe your product and we will suggest the best category.'"
        />
      </div>

      <!-- ChatGPT-style centered input zone -->
      <div class="rounded-2xl border border-gray-200 shadow-sm p-4">
        <form
          [formGroup]="form"
          (ngSubmit)="onSubmit()"
          (keydown.enter)="onSubmit(); $event.preventDefault()"
          aria-label="Product description form"
        >
          <mee-textarea
            formControlName="description"
            [label]="'Describe your product'"
            [placeholder]="'e.g. Blue cotton kurti with mirror work for women, size M to XXL'"
            [rows]="4"
            [required]="true"
            [error]="descError()"
          />
          <p
            class="mt-1 text-xs"
            style="color: var(--mee-color-on-surface-muted);"
          >
            Between 10 and 5000 characters.
          </p>

          <!-- Send button — right-aligned inside the card -->
          <div class="flex justify-end mt-3">
            <mee-button
              label="Send"
              variant="primary"
              icon="pi pi-send"
              [loading]="loading()"
              [disabled]="form.invalid || loading()"
              (clicked)="onSubmit()"
            />
          </div>
        </form>
      </div>

      <!-- Inline API error (400/404/422 responses) -->
      @if (apiError()) {
        <p class="mt-3 text-sm text-center" role="alert" style="color: var(--mee-color-error);">
          {{ apiError() }}
        </p>
      }

      <!-- Results zone -->
      <div class="mt-6">

        <!-- Loading skeletons while suggestion in flight -->
        @if (loading()) {
          <div
            class="grid grid-cols-1 gap-4 sm:grid-cols-3"
            aria-busy="true"
            aria-label="Loading category suggestions"
          >
            <mee-skeleton variant="card" />
            <mee-skeleton variant="card" />
            <mee-skeleton variant="card" />
          </div>
        }

        <!-- Top-3 suggestion cards -->
        @if (!loading() && suggestions().length > 0) {
          <div
            class="grid grid-cols-1 gap-4 sm:grid-cols-3"
            role="list"
            aria-label="Category suggestions"
          >
            @for (s of suggestions().slice(0, 3); track s.category_id) {
              <app-category-card
                [suggestion]="s"
                (picked)="onPicked($event)"
              />
            }
          </div>

          <!-- Secondary fallback link (shown when fallback_offered=true and there ARE results) -->
          @if (fallbackOffered()) {
            <div class="mt-4 text-center">
              <mee-button
                label="Browse if none match"
                variant="ghost"
                size="sm"
                [fullWidth]="false"
                (clicked)="onBrowse()"
              />
            </div>
          }
        }

        <!-- Empty state: fallback_offered=true AND no suggestions -->
        @if (!loading() && suggestions().length === 0 && fallbackOffered()) {
          <mee-empty-state
            icon="category"
            message="Smart suggestions are unavailable right now — browse categories manually instead."
            cta_label="Browse all categories"
            (cta_click)="onBrowse()"
          />
        }

      </div>
    </div>
  `,
})
export class SmartPickerComponent {
  private readonly fb = inject(FormBuilder);
  private readonly categoryService = inject(CategoryService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly toastService = inject(MeeToastService);

  // ── Form ──────────────────────────────────────────────────────────
  readonly form = this.fb.group({
    description: [
      '',
      [
        Validators.required,
        Validators.minLength(10),
        Validators.maxLength(5000),
      ],
    ],
  });

  // ── Signals ───────────────────────────────────────────────────────
  readonly loading          = signal(false);
  readonly suggestions      = signal<CategorySuggestion[]>([]);
  readonly fallbackOffered  = signal(false);
  readonly apiError         = signal<string | null>(null);

  // ── Computed error for template binding ───────────────────────────
  readonly descError = computed<string | undefined>(() => {
    const ctrl = this.form.get('description');
    if (!ctrl || !ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Please describe your product.';
    if (ctrl.hasError('minlength')) return 'Please enter at least 10 characters.';
    if (ctrl.hasError('maxlength')) return 'Description must be 5000 characters or fewer.';
    return undefined;
  });

  // ── Handlers ───────────────────────────────────────────────────────

  /** Fires on Enter keypress or Send button click. */
  onSubmit(): void {
    const ctrl = this.form.get('description')!;
    ctrl.markAsTouched();
    if (ctrl.invalid || this.loading()) return;
    const q = (ctrl.value ?? '').trim();
    this.loading.set(true);
    this.suggestions.set([]);
    this.fallbackOffered.set(false);
    this.apiError.set(null);
    this.categoryService.suggest(q)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (response: SuggestResponse) => {
          this.suggestions.set(response.suggestions);
          this.fallbackOffered.set(response.fallback_offered);
          this.loading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.loading.set(false);
          const code = (err.error as { validation_message_id?: string })?.validation_message_id ?? '';
          if (err.status === 429) {
            this.toastService.error(SMART_PICKER_ERROR_COPY['rate_limit.window.exceeded']);
          } else if (err.status >= 400 && err.status < 500) {
            this.apiError.set(SMART_PICKER_ERROR_COPY[code] ?? GENERIC_ERROR_COPY);
          } else {
            // 5xx
            this.toastService.error(GENERIC_ERROR_COPY);
          }
        },
      });
  }

  /** Called when a category card emits 'picked' with a category_id. */
  onPicked(categoryId: string): void {
    this.categoryService.selectCategory(categoryId).subscribe({
      error: () => {
        this.loading.set(false);
      },
    });
  }

  /** Delegate browse navigation to the service. */
  onBrowse(): void {
    this.categoryService.browseRedirect();
  }
}
