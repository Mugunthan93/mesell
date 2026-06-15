/**
 * BrowseComponent — /categories/browse
 *
 * Standalone, OnPush page component for manual category browsing.
 *
 * Flow:
 *  - Optional ?q= query param pre-fills the search control.
 *  - Typing debounces 400ms then fires CategoryService.browse().
 *  - Results render as mee-card rows with a "Select" mee-button.
 *  - Prev/Next pagination via offset signal (page size = LIMIT = 20).
 *  - "Select" calls CategoryService.selectCategory(row.category_id) which
 *    navigates internally to /catalogs/:id/edit via tap() in the service.
 *
 * Session: mesell-section-2-frontend-session-1 (Plan 1-B)
 */
import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';

import {
  MeeButtonComponent,
  MeeCardComponent,
  MeeInputComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import {
  EmptyStateComponent,
  PageHeaderComponent,
} from '@mesell/composites';

import { CategoryService } from '../../smart-picker/services/category.service';
import type { BrowseResultRow } from '../../smart-picker/smart-picker.model';

const LIMIT = 20;

const BROWSE_ERROR_COPY: Record<string, string> = {
  'validation.browse.invalid_pagination': 'Page or limit is out of range. Please try a smaller page size.',
};
const GENERIC_BROWSE_ERROR_COPY = 'Something went wrong. Please try again.';

@Component({
  selector: 'app-browse',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MeeInputComponent,
    MeeButtonComponent,
    MeeSkeletonComponent,
    MeeCardComponent,
    EmptyStateComponent,
    PageHeaderComponent,
  ],
  providers: [CategoryService],
  template: `
    <div class="max-w-2xl mx-auto px-4 py-8">

      <mee-page-header
        title="Browse categories"
        subtitle="Find the right category for your product"
      />

      <form [formGroup]="form" class="mb-6">
        <mee-input
          formControlName="search"
          label="Search categories"
          placeholder="e.g. cotton kurti, steel bowl..."
        />
      </form>

      @if (browseError()) {
        <p class="mb-4 text-sm" role="alert" style="color: var(--mee-color-error);">
          {{ browseError() }}
        </p>
      }

      @if (loading()) {
        <div class="grid grid-cols-1 gap-3" aria-busy="true" aria-label="Loading categories">
          @for (_ of [1, 2, 3, 4]; track $index) {
            <mee-skeleton variant="card" />
          }
        </div>
      } @else if (results().length === 0) {
        <mee-empty-state
          icon="category"
          message="No categories found. Try a different search term."
        />
      } @else {
        <div class="grid grid-cols-1 gap-3" role="list" aria-label="Category results">
          @for (row of results(); track row.category_id) {
            <mee-card class="p-4">
              <div class="flex items-center justify-between gap-4">
                <div>
                  <p class="font-medium text-sm">{{ row.leaf_name }}</p>
                  <p class="text-xs text-gray-500 mt-0.5">{{ row.path }}</p>
                  <p class="text-xs text-gray-400">{{ row.super_name }}</p>
                </div>
                <mee-button
                  label="Select"
                  variant="secondary"
                  size="sm"
                  [fullWidth]="false"
                  (clicked)="onSelect(row)"
                />
              </div>
            </mee-card>
          }
        </div>

        <div class="flex justify-between items-center mt-6">
          <mee-button
            label="Previous"
            variant="ghost"
            [disabled]="!hasPrev()"
            (clicked)="prevPage()"
          />
          <span class="text-xs text-gray-500">
            {{ offset() + 1 }}–{{ offset() + results().length }} of {{ total() }}
          </span>
          <mee-button
            label="Next"
            variant="ghost"
            [disabled]="!hasNext()"
            (clicked)="nextPage()"
          />
        </div>
      }

    </div>
  `,
})
export class BrowseComponent implements OnInit {
  private readonly fb              = inject(FormBuilder);
  private readonly route           = inject(ActivatedRoute);
  private readonly categoryService = inject(CategoryService);
  private readonly destroyRef      = inject(DestroyRef);

  // ── Form ──────────────────────────────────────────────────────────────────
  readonly form = this.fb.group({ search: [''] });

  // ── Signals ───────────────────────────────────────────────────────────────
  readonly results     = signal<BrowseResultRow[]>([]);
  readonly total       = signal(0);
  readonly loading     = signal(false);
  readonly offset      = signal(0);
  readonly browseError = signal<string | null>(null);

  // ── Computed ──────────────────────────────────────────────────────────────
  readonly hasPrev = computed(() => this.offset() > 0);
  readonly hasNext = computed(() => this.offset() + LIMIT < this.total());

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  ngOnInit(): void {
    const initialQ = this.route.snapshot.queryParamMap.get('q') ?? '';
    this.form.get('search')!.setValue(initialQ, { emitEvent: false });

    if (initialQ) {
      this.doSearch();
    }

    this.form.get('search')!.valueChanges
      .pipe(
        debounceTime(400),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        this.offset.set(0);
        this.doSearch();
      });
  }

  // ── Private methods ───────────────────────────────────────────────────────

  private doSearch(): void {
    const q = this.form.get('search')!.value ?? '';
    this.loading.set(true);
    this.browseError.set(null);
    this.categoryService
      .browse(q, undefined, LIMIT, this.offset())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.results.set(res.results);
          this.total.set(res.total);
          this.loading.set(false);
        },
        error: (err: HttpErrorResponse) => {
          this.loading.set(false);
          const code = (err.error as { validation_message_id?: string })?.validation_message_id ?? '';
          if (err.status === 400 || err.status === 422) {
            this.browseError.set(BROWSE_ERROR_COPY[code] ?? GENERIC_BROWSE_ERROR_COPY);
          }
          // 404/429/5xx → degrade silently (results stay empty, handled by empty-state)
        },
      });
  }

  // ── Public handlers ───────────────────────────────────────────────────────

  prevPage(): void {
    this.offset.update(o => Math.max(0, o - LIMIT));
    this.doSearch();
  }

  nextPage(): void {
    this.offset.update(o => o + LIMIT);
    this.doSearch();
  }

  onSelect(row: BrowseResultRow): void {
    this.categoryService
      .selectCategory(row.category_id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe();
  }
}
