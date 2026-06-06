// features/dashboard/dashboard/dashboard.component.spec.ts
// Unit tests for DashboardComponent — 6 tests per dispatch acceptance criteria
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks for DashboardApiService

import { TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest';
import { of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';

import { DashboardComponent } from './dashboard.component';
import {
  DashboardApiService,
  DashboardResponse,
} from '../dashboard-api.service';
import { ErrorService } from '@core/services/error.service';
import { StatusBadgeComponent } from '@shared/components/status-badge/status-badge.component';
import { EmptyStateComponent } from '@shared/components/empty-state/empty-state.component';

// ── Stubs for sub-components with required inputs ──
// These allow testing DashboardComponent in isolation without sub-component
// required-input errors (NG0950) from Angular's input.required() API.

@Component({ selector: 'mee-status-badge', standalone: true, template: '<span>{{status}}</span>' })
class StatusBadgeStub { status: string = ''; }

@Component({
  selector: 'mee-empty-state',
  standalone: true,
  template: '<div class="mee-empty-state"><button (click)="ctaClick.emit()">{{ ctaLabel }}</button></div>',
})
class EmptyStateStub {
  icon = '';
  headline = '';
  body = '';
  ctaLabel = '';
  ctaClick = new (class { emit = () => {} })();
}

// ── Helpers ──

function makeResponse(
  overrides: Partial<DashboardResponse> = {},
): DashboardResponse {
  return {
    products: [],
    total: 0,
    page: 1,
    limit: 20,
    profile_completeness: {
      base_complete_count: 0,
      base_total_count: 0,
      extension_complete_count: 0,
      extension_total_count: 0,
      profile_complete: true,
    },
    ...overrides,
  };
}

function makeProduct(overrides: Record<string, unknown> = {}) {
  return {
    product_id: 'prod-001',
    name: 'Blue Kurti',
    category_id: 'cat-abc',
    status: 'draft' as const,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-06-01T12:00:00Z',
    ...overrides,
  };
}

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'dashboard.title': 'Your catalogs',
      'dashboard.filter.all': 'All',
      'dashboard.filter.draft': 'Draft',
      'dashboard.filter.ready': 'Ready',
      'dashboard.filter.exported': 'Exported',
      'dashboard.search.placeholder': 'Search catalogs...',
      'dashboard.table.name': 'Catalog Name',
      'dashboard.table.status': 'Status',
      'dashboard.table.updated': 'Last Updated',
      'dashboard.table.untitled': 'Untitled',
      'dashboard.empty.headline': 'No catalogs yet',
      'dashboard.empty.body': 'Create your first catalog to start listing on Meesho',
      'dashboard.empty.cta': 'Create your first catalog',
      'dashboard.noResults': 'No catalogs match your search.',
      'dashboard.profileBanner.message': 'Complete your seller profile',
      'dashboard.profileBanner.link': 'Go to profile',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Test Suite ──

describe('DashboardComponent', () => {
  let listProductsSpy: ReturnType<typeof vi.fn>;
  let showErrorSpy: ReturnType<typeof vi.fn>;

  afterEach(() => {
    vi.useRealTimers();
  });

  beforeEach(async () => {
    listProductsSpy = vi.fn();
    showErrorSpy = vi.fn();

    await TestBed.configureTestingModule({
      imports: [
        DashboardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        {
          provide: DashboardApiService,
          useValue: {
            listProducts: listProductsSpy,
            deleteProduct: vi.fn(),
          },
        },
        {
          provide: ErrorService,
          useValue: { showError: showErrorSpy },
        },
      ],
    })
    // Override sub-components with stubs so DashboardComponent is tested in isolation.
    // StatusBadgeComponent uses input.required() which triggers NG0950 during
    // mat-table's internal render cycles without stable input binding.
    .overrideComponent(DashboardComponent, {
      remove: { imports: [StatusBadgeComponent, EmptyStateComponent] },
      add: { imports: [StatusBadgeStub, EmptyStateStub] },
    })
    .compileComponents();
  });

  // ── Test 1: Loading spinner while products are loading ──

  it('renders loading spinner while products are loading', async () => {
    // Arrange: never-resolving observable so loading stays true
    listProductsSpy.mockReturnValue(of(makeResponse()).pipe(delay(10_000)));

    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    // Assert: spinner is present, table is not
    const spinner = fixture.nativeElement.querySelector('mat-spinner');
    const table = fixture.nativeElement.querySelector('table[mat-table]');

    expect(spinner).toBeTruthy();
    expect(table).toBeNull();
  });

  // ── Test 2: Product rows render when API returns products ──

  it('renders product rows when products return from API', async () => {
    // Arrange: API returns 2 products
    listProductsSpy.mockReturnValue(
      of(
        makeResponse({
          products: [makeProduct({ name: 'Blue Kurti', product_id: 'prod-001' }),
                     makeProduct({ name: 'Red Saree',  product_id: 'prod-002' })],
          total: 2,
        }),
      ),
    );

    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const rows = fixture.nativeElement.querySelectorAll('tr.mee-product-row');
    expect(rows.length).toBe(2);

    const firstRowText: string = rows[0].textContent ?? '';
    expect(firstRowText).toContain('Blue Kurti');
  });

  // ── Test 3: Empty state when total=0 and no filter/search ──

  it('renders empty-state component when total=0 and no filter/search', async () => {
    // Arrange: API returns empty list
    listProductsSpy.mockReturnValue(of(makeResponse({ products: [], total: 0 })));

    const fixture = TestBed.createComponent(DashboardComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const emptyState = fixture.nativeElement.querySelector('mee-empty-state');
    const noResults = fixture.nativeElement.querySelector('.mee-no-results');

    expect(emptyState).toBeTruthy();
    expect(noResults).toBeNull();
  });

  // ── Test 4: "No results" paragraph when total=0 but filter/search is active ──

  it('renders "no results" paragraph when total=0 and filter/search is active', async () => {
    // Arrange: API returns empty with active status filter
    listProductsSpy.mockReturnValue(of(makeResponse({ products: [], total: 0 })));

    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;

    // Set an active filter before init renders content
    component.activeStatus.set('draft');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const noResults = fixture.nativeElement.querySelector('.mee-no-results');
    const emptyState = fixture.nativeElement.querySelector('mee-empty-state');

    expect(noResults).toBeTruthy();
    expect(emptyState).toBeNull();
  });

  // ── Test 5: API called with status_filter when chip is selected ──

  it('calls API with status_filter when chip is selected', async () => {
    // Arrange: initial load returns empty; second call after filter also returns empty
    listProductsSpy.mockReturnValue(of(makeResponse()));

    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    // Act: simulate status chip selection (the "ready" chip)
    component.onStatusChange('ready');
    fixture.detectChanges();
    await fixture.whenStable();

    // Assert: last call should have status_filter='ready'
    const calls = listProductsSpy.mock.calls;
    const lastCallParams = calls[calls.length - 1][0];

    expect(lastCallParams.status_filter).toBe('ready');
    expect(lastCallParams.page).toBe(1); // should reset to page 1
  });

  // ── Test 6: API called with search param after 300ms debounce ──

  it('calls API with search param after 300ms debounce', async () => {
    // Arrange: use Vitest fake timers (zone-testing.js is not loaded in this setup)
    vi.useFakeTimers();
    listProductsSpy.mockReturnValue(of(makeResponse()));

    const fixture = TestBed.createComponent(DashboardComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    const initialCallCount = listProductsSpy.mock.calls.length;

    // Act: type into the search control — debounce is 300ms
    component.searchCtrl.setValue('kurti');
    fixture.detectChanges();

    // Before debounce fires (100ms elapsed): no new call yet
    vi.advanceTimersByTime(100);
    expect(listProductsSpy.mock.calls.length).toBe(initialCallCount);

    // After debounce fires (300ms total elapsed)
    vi.advanceTimersByTime(200);
    fixture.detectChanges();

    // Assert: a new API call was made with the search param
    const calls = listProductsSpy.mock.calls;
    const lastCallParams = calls[calls.length - 1][0];
    expect(lastCallParams.search).toBe('kurti');
    expect(lastCallParams.page).toBe(1); // reset to page 1
  });
});
