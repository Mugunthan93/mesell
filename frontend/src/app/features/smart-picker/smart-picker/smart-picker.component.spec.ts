// features/smart-picker/smart-picker/smart-picker.component.spec.ts
// Per AC-10: (a) renders cards on suggest success, (b) shows spinner while loading,
// (c) navigates to /catalogs/:id/edit on card click success
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks

import { TestBed } from '@angular/core/testing';
import { Component, signal } from '@angular/core';
import { Router, provideRouter } from '@angular/router';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { MatDialogModule } from '@angular/material/dialog';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { BehaviorSubject, of } from 'rxjs';

import { SmartPickerComponent } from './smart-picker.component';
import { SmartPickerStateService } from '../smart-picker-state.service';
import { CategoryCardComponent } from '../category-card/category-card.component';
import { DescriptionInputComponent } from '../description-input/description-input.component';
import { BrowseFallbackComponent } from '../browse-fallback/browse-fallback.component';
import type { CategorySuggestion } from '../smart-picker.model';

// ── Stubs to avoid input.required() errors from sub-components ──

@Component({
  selector: 'mee-category-card',
  standalone: true,
  template: '<div class="mee-category-card" (click)="categorySelected.emit(suggestion)"></div>',
})
class CategoryCardStub {
  suggestion: CategorySuggestion | undefined;
  categorySelected = { emit: vi.fn() };
}

@Component({
  selector: 'mee-description-input',
  standalone: true,
  template: '<div></div>',
})
class DescriptionInputStub {
  disabled = false;
  descriptionSubmit = { emit: vi.fn() };
}

@Component({
  selector: 'mee-browse-fallback',
  standalone: true,
  template: '<div></div>',
})
class BrowseFallbackStub {
  categorySelected = { emit: vi.fn() };
}

// ── Transloco test setup ──

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'smartPicker.title': 'Create a new catalog',
      'smartPicker.description.placeholder': 'Describe your product',
      'smartPicker.description.submitLabel': 'Find category',
      'smartPicker.description.minLengthError': 'Please describe your product (at least 10 characters)',
      'smartPicker.rateLimitMessage': 'Daily suggestion limit reached. Please use browse.',
      'smartPicker.browse.link': 'Browse categories manually',
      'smartPicker.browse.superCategoryLabel': 'Select a product category',
      'smartPicker.browse.leafSearchPlaceholder': 'Search within category...',
      'smartPicker.browse.noResults': 'No categories found.',
      'smartPicker.profileIncomplete.title': 'Complete your seller profile',
      'smartPicker.profileIncomplete.body': 'Missing fields:',
      'smartPicker.profileIncomplete.goToProfile': 'Go to Profile',
      'smartPicker.profileIncomplete.cancel': 'Cancel',
      'common.error': 'Something went wrong.',
      'common.dismiss': 'Dismiss',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

const MOCK_SUGGESTIONS: CategorySuggestion[] = [
  {
    super_category: 'Clothing',
    leaf_category: 'Kurti',
    leaf_category_id: 'leaf-1',
    confidence: 0.92,
    sample_attributes: [{ canonical_name: 'color', display_label: 'Color' }],
  },
  {
    super_category: 'Clothing',
    leaf_category: 'Dupatta',
    leaf_category_id: 'leaf-2',
    confidence: 0.78,
    sample_attributes: [],
  },
];

describe('SmartPickerComponent', () => {
  let router: Router;
  let navigateSpy: ReturnType<typeof vi.fn>;

  function buildStateStub(
    overrides: {
      loading?: boolean;
      suggestions?: CategorySuggestion[];
      rateLimitHit?: boolean;
      showBrowseFallback?: boolean;
      selectResult?: { productId: string };
      selectError?: unknown;
    } = {},
  ) {
    const suggestions$ = new BehaviorSubject<CategorySuggestion[]>(
      overrides.suggestions ?? [],
    );

    return {
      suggestions$,
      loading: signal(overrides.loading ?? false),
      error: signal<string | null>(null),
      rateLimitHit: signal(overrides.rateLimitHit ?? false),
      showBrowseFallback: signal(overrides.showBrowseFallback ?? false),
      suggest: vi.fn(),
      openBrowseFallback: vi.fn(),
      selectCategory: vi.fn(() => {
        if (overrides.selectError) {
          const { throwError: rxThrowError } = require('rxjs');
          return rxThrowError(() => overrides.selectError);
        }
        return of(overrides.selectResult ?? { productId: 'prod-new' });
      }),
    };
  }

  async function setup(stateStub: ReturnType<typeof buildStateStub>) {
    navigateSpy = vi.fn();

    await TestBed.configureTestingModule({
      imports: [
        SmartPickerComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
        MatDialogModule,
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        { provide: SmartPickerStateService, useValue: stateStub },
      ],
    })
    .overrideComponent(SmartPickerComponent, {
      remove: {
        imports: [CategoryCardComponent, DescriptionInputComponent, BrowseFallbackComponent],
      },
      add: {
        imports: [CategoryCardStub, DescriptionInputStub, BrowseFallbackStub],
      },
    })
    .compileComponents();

    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockImplementation(navigateSpy);
  }

  // ── Test (a): renders category cards on suggest success ──

  it('renders mee-category-card elements for each suggestion', async () => {
    const stateStub = buildStateStub({ suggestions: MOCK_SUGGESTIONS });
    await setup(stateStub);

    const fixture = TestBed.createComponent(SmartPickerComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const cards = fixture.nativeElement.querySelectorAll('mee-category-card');
    expect(cards.length).toBe(2);
  });

  // ── Test (b): shows spinner while loading ──

  it('shows mat-spinner while state.loading() is true', async () => {
    const stateStub = buildStateStub({ loading: true });
    await setup(stateStub);

    const fixture = TestBed.createComponent(SmartPickerComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const spinner = fixture.nativeElement.querySelector('mat-spinner');
    expect(spinner).toBeTruthy();
  });

  it('hides spinner when state.loading() is false', async () => {
    const stateStub = buildStateStub({ loading: false });
    await setup(stateStub);

    const fixture = TestBed.createComponent(SmartPickerComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const spinner = fixture.nativeElement.querySelector('mat-spinner');
    expect(spinner).toBeNull();
  });

  // ── Test (c): navigates to /catalogs/:id/edit on card click success ──

  it('navigates to /catalogs/:productId/edit on successful selectCategory', async () => {
    const stateStub = buildStateStub({
      suggestions: [MOCK_SUGGESTIONS[0]],
      selectResult: { productId: 'prod-xyz' },
    });
    await setup(stateStub);

    const fixture = TestBed.createComponent(SmartPickerComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    // Simulate card selection
    component.onCategorySelected(MOCK_SUGGESTIONS[0]);
    await fixture.whenStable();

    expect(navigateSpy).toHaveBeenCalledWith(['/catalogs', 'prod-xyz', 'edit']);
  });
});
