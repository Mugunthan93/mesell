/**
 * SmartPickerComponent — /catalogs/new
 *
 * Standalone, OnPush page component for the Smart Category Picker (V1 Feature 2).
 *
 * Flow:
 *  - Seller types a product description (10-500 chars).
 *  - On valueChanges, after 400 ms debounce + distinctUntilChanged + valid filter,
 *    CategoryService.suggest(description) is called.
 *  - Top-3 of the returned suggestions (max 5) are rendered via CategoryCardComponent.
 *  - fallback_offered=true and empty suggestions -> EmptyStateComponent + "Browse all categories".
 *  - fallback_offered=true and non-empty -> 3 cards + secondary "Browse if none match" link.
 *  - "Use this category" on a card -> CategoryService.selectCategory(category_id).
 *
 * D4 rename: folder was catalog-new/, class was CatalogNewComponent. Renamed per FEATURE_PLAN §D4.
 * Contract fix: §9.E-locked interfaces (no commission_pct; confidence 0-1 float). Port from e97c4f5.
 * MeeTreeSelect/SIMULATED_TREE removed per D1 (browse routes to /categories/browse, not inline tree).
 */
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  signal,
  OnInit,
  computed,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  debounceTime,
  distinctUntilChanged,
  filter,
  switchMap,
} from 'rxjs/operators';

import {
  MeeTextareaComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import {
  PageHeaderComponent,
  EmptyStateComponent,
} from '@mesell/composites';

import { CategoryService } from './services/category.service';
import { CategoryCardComponent } from './category-card.component';
import type { CategorySuggestion, SuggestResponse } from './smart-picker.model';

@Component({
  selector: 'app-smart-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MeeTextareaComponent,
    MeeSkeletonComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    CategoryCardComponent,
  ],
  providers: [CategoryService],
  template: `
    <div class="p-4 sm:p-6 max-w-4xl mx-auto">

      <!-- Page title -->
      <mee-page-header
        [title]="'New Catalog'"
        [subtitle]="'Describe your product and we will suggest the best category.'"
      />

      <!-- Description form -->
      <form
        [formGroup]="form"
        class="mt-6"
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
          Between 10 and 500 characters.
        </p>
      </form>

      <!-- Loading skeletons while suggestion in flight -->
      @if (loading()) {
        <div
          class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3"
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
          class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3"
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
            <button
              type="button"
              class="text-sm underline min-h-[44px] px-2"
              style="color: var(--mee-color-on-surface-muted); background: none; border: none; cursor: pointer;"
              (click)="onBrowse()"
              aria-label="Browse all categories if none of the suggestions match"
            >
              Browse if none match
            </button>
          </div>
        }
      }

      <!-- Empty state: fallback_offered=true AND no suggestions -->
      @if (!loading() && suggestions().length === 0 && fallbackOffered()) {
        <div class="mt-6">
          <mee-empty-state
            icon="category"
            message="No automatic suggestions found. Browse the full category list manually."
            cta_label="Browse all categories"
            (cta_click)="onBrowse()"
          />
        </div>
      }

    </div>
  `,
})
export class SmartPickerComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly categoryService = inject(CategoryService);
  private readonly destroyRef = inject(DestroyRef);

  // ── Form ──────────────────────────────────────────────────────────
  readonly form = this.fb.group({
    description: [
      '',
      [
        Validators.required,
        Validators.minLength(10),
        Validators.maxLength(500),
      ],
    ],
  });

  // ── Signals ───────────────────────────────────────────────────────
  readonly loading          = signal(false);
  readonly suggestions      = signal<CategorySuggestion[]>([]);
  readonly fallbackOffered  = signal(false);

  // ── Computed error for template binding ───────────────────────────
  readonly descError = computed<string | undefined>(() => {
    const ctrl = this.form.get('description');
    if (!ctrl || !ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Please describe your product.';
    if (ctrl.hasError('minlength')) return 'Please enter at least 10 characters.';
    if (ctrl.hasError('maxlength')) return 'Description must be 500 characters or fewer.';
    return undefined;
  });

  // ── Lifecycle ──────────────────────────────────────────────────────
  ngOnInit(): void {
    const descCtrl = this.form.get('description')!;

    descCtrl.valueChanges
      .pipe(
        debounceTime(400),
        distinctUntilChanged(),
        filter(() => descCtrl.valid),
        switchMap((value) => {
          const q = value ?? '';
          this.loading.set(true);
          this.suggestions.set([]);
          this.fallbackOffered.set(false);
          return this.categoryService.suggest(q);
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (response: SuggestResponse) => {
          this.suggestions.set(response.suggestions);
          this.fallbackOffered.set(response.fallback_offered);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
          this.fallbackOffered.set(true);
        },
      });
  }

  // ── Handlers ───────────────────────────────────────────────────────

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
