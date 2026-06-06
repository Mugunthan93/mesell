// features/smart-picker/smart-picker-state.service.ts
// Feature-scoped state service per §3.D — NOT providedIn root
// Holds suggestion state + orchestrates suggest + createProduct flows

import { inject, Injectable, signal } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';
import { debounceTime, map, switchMap, tap } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { SmartPickerApiService } from './smart-picker-api.service';
import {
  CategorySuggestion,
  BrowseSelection,
  ProfileIncompleteError,
} from './smart-picker.model';

export interface SelectCategoryResult {
  productId: string;
}

@Injectable()
export class SmartPickerStateService {
  private readonly api = inject(SmartPickerApiService);

  /** Current AI suggestions — cleared on each new suggest call */
  readonly suggestions$ = new BehaviorSubject<CategorySuggestion[]>([]);

  /** True while the suggest HTTP call is in flight */
  readonly loading = signal(false);

  /** Non-null when a non-422 error has occurred; null when clear */
  readonly error = signal<string | null>(null);

  /** True when the suggest rate limit (429) has been hit */
  readonly rateLimitHit = signal(false);

  /** True when fallback_offered=true OR rateLimitHit */
  readonly showBrowseFallback = signal(false);

  /** Internal subject to feed description values with debounce */
  private readonly descriptionInput$ = new Subject<string>();

  constructor() {
    // Debounce + switchMap: cancel in-flight calls when new description arrives
    this.descriptionInput$
      .pipe(
        debounceTime(500),
        tap(() => {
          this.loading.set(true);
          this.error.set(null);
          this.rateLimitHit.set(false);
        }),
        switchMap((description) =>
          this.api.suggest(description),
        ),
        takeUntilDestroyed(),
      )
      .subscribe({
        next: (response) => {
          this.suggestions$.next(response.suggestions);
          this.loading.set(false);
          if (response.fallback_offered) {
            this.showBrowseFallback.set(true);
          }
        },
        error: (err: unknown) => {
          this.loading.set(false);
          const status = (err as { status?: number })?.status;
          if (status === 429) {
            this.rateLimitHit.set(true);
            this.showBrowseFallback.set(true);
          } else {
            this.error.set(
              (err as { displayMessage?: string })?.displayMessage ??
              'Failed to get category suggestions.',
            );
          }
        },
      });
  }

  /**
   * Triggers a debounced suggest call (500ms debounce, switchMap cancels prior in-flight).
   * Called by SmartPickerComponent when the description form emits.
   */
  suggest(description: string): void {
    this.descriptionInput$.next(description);
  }

  /**
   * Calls POST /api/v1/products to create a draft.
   * On 201 → returns {productId}.
   * On 422 profile-incomplete → propagates the typed error; does NOT show UI (page component does).
   * All other errors propagate as-is for ErrorInterceptor to handle.
   */
  selectCategory(
    selection: CategorySuggestion | BrowseSelection,
  ): Observable<SelectCategoryResult> {
    const leafCategoryId =
      'leaf_category_id' in selection
        ? selection.leaf_category_id      // CategorySuggestion
        : selection.leaf_id;              // BrowseSelection

    return this.api.createProduct(leafCategoryId).pipe(
      map((response) => ({ productId: response.id })),
      // 422 profile-incomplete errors propagate upward intentionally — page component handles modal.
      // ErrorInterceptor has already normalised the error; we just re-throw shape so callers can
      // distinguish profile-incomplete from generic 422.
    );
  }

  /** Opens the browse fallback explicitly (e.g., "Browse manually" link click) */
  openBrowseFallback(): void {
    this.showBrowseFallback.set(true);
  }
}
