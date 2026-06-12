/**
 * DashboardComponent — Wave 6B wired dashboard.
 *
 * Endpoints: GET /api/v1/products (DashboardApiService) + DELETE /api/v1/products/{id}.
 * Degradation: mee-offline-banner (NetworkService) + mee-alert-banner (ErrorService) + mee-empty-state.
 * Status: 2-value draft|ready (A2). Category column absent (A4). onboarding_completeness decoded, unrendered (A5).
 */

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule, FormControl } from '@angular/forms';
import { Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { MeeConfirmService } from '@mesell/ui-kit';
import {
  StatCardComponent,
  StatusBadgeComponent,
  PageHeaderComponent,
  EmptyStateComponent,
  LoadingSkeletonComponent,
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
} from '@mesell/composites';
import { NetworkService, ErrorService } from '@mesell/core';

import {
  DashboardApiService,
  ProductListItem,
  StatusCounts,
} from './services/dashboard-api.service';
import { ProfileCompletenessSummary, formatRelativeTime, filterProductsByName } from './dashboard.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [DashboardApiService],
  imports: [
    ReactiveFormsModule,
    StatCardComponent,
    StatusBadgeComponent,
    PageHeaderComponent,
    EmptyStateComponent,
    LoadingSkeletonComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
  ],
  template: `
    <div class="mee-dashboard w-full flex flex-col">

      <!-- Offline banner — always at viewport top; MeeOfflineBannerComponent reads NetworkService.online() (§6). -->
      <mee-offline-banner />

      <div class="px-4 py-6 sm:px-6 max-w-7xl mx-auto w-full flex flex-col gap-6">

        <!-- Page header -->
        <mee-page-header
          title="My Catalogs"
          cta_label="New Catalog"
          cta_icon="add"
          (cta_click)="onNewCatalog()"
        />

        <!-- Error banner (§6 row "error") — non-null errorMessage triggers mee-alert-banner + retry. -->
        @if (errorMessage()) {
          <div class="flex flex-col gap-3" role="status" aria-live="polite" aria-atomic="true">
            <mee-alert-banner
              variant="error"
              [message]="errorMessage()!"
            />
            <button
              class="mee-retry-btn self-start"
              (click)="onRetry()"
              aria-label="Retry loading catalogs"
            >
              Retry
            </button>
          </div>
        }

        <!--
          Main async region — aria-live="polite" so screen readers announce transitions
          between loading / data / empty states (WCAG 4.1.3).
        -->
        <div aria-live="polite" aria-atomic="false" class="flex flex-col gap-6">

          <!-- Loading skeleton — 2 stat-card skeletons matching the V1 2-card layout (A2) -->
          @if (loading()) {
            <div class="flex flex-col gap-6" aria-label="Loading catalogs" role="status">
              <div class="mee-stat-grid">
                <mee-loading-skeleton variant="stat-card" />
                <mee-loading-skeleton variant="stat-card" />
              </div>
              <mee-loading-skeleton variant="table-row" [lines]="5" />
            </div>
          } @else {

            <!-- Stat cards — Draft + Ready only (A2; V1 wire is 2-value draft|ready) -->
            <div class="mee-stat-grid">
              <mee-stat-card
                label="Draft"
                [value]="statusCounts().draft"
                icon="edit_note"
                color="blue"
              />
              <mee-stat-card
                label="Ready"
                [value]="statusCounts().ready"
                icon="check_circle"
                color="green"
              />
            </div>

            <!-- Search + filter toolbar (client-side only — A3: page+limit go to server; name/status stay local) -->
            <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
              <input type="search" [formControl]="searchCtrl" placeholder="Search catalogs..."
                class="mee-control flex-1"
                aria-label="Search catalogs by name" />
              <!-- Status filter — V1 options: All / Draft / Ready (A2 — no exported/live on wire) -->
              <select class="mee-control mee-control--select"
                aria-label="Filter by status"
                (change)="onStatusFilterChange($event)">
                <option value="">All Statuses</option>
                <option value="draft">Draft</option>
                <option value="ready">Ready</option>
              </select>
            </div>

            <!-- Empty state (§6 row "empty") — no products + no error -->
            @if (isEmpty()) {
              <mee-empty-state
                icon="inventory_2"
                message="No catalogs yet. Create your first catalog to get started."
                cta_label="New Catalog"
                (cta_click)="onNewCatalog()"
              />
            } @else {
              <!-- Products table — horizontal scroll at 360px (overflow-x-auto wrapper) -->
              <div class="mee-table-wrap">
                <table class="mee-table" aria-label="Product catalog list">
                  <thead>
                    <tr class="mee-table__head-row">
                      <th class="mee-table__th" scope="col">Name</th>
                      <th class="mee-table__th" scope="col">Status</th>
                      <th class="mee-table__th" scope="col">Updated</th>
                      <th class="mee-table__th mee-table__th--actions sr-only" scope="col">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (row of visibleProducts(); track row.product_id) {
                      <tr class="mee-table__row"
                        tabindex="0"
                        (click)="onRowClick(row)"
                        (keydown.enter)="onRowClick(row)"
                        (keydown.space)="$event.preventDefault(); onRowClick(row)"
                        [attr.aria-label]="'Open ' + (row.name ?? 'untitled product')"
                        role="row"
                      >
                        <td class="mee-table__td mee-table__td--name">
                          <span class="block truncate font-medium" [title]="row.name ?? ''">
                            {{ row.name ?? '(untitled)' }}
                          </span>
                        </td>
                        <td class="mee-table__td">
                          <mee-status-badge [status]="row.status" />
                        </td>
                        <td class="mee-table__td mee-table__td--muted">
                          {{ formatRelativeTime(row.updated_at) }}
                        </td>
                        <td class="mee-table__td mee-table__td--actions">
                          <button
                            class="mee-delete-btn"
                            [attr.aria-label]="'Delete ' + (row.name ?? 'this product')"
                            (click)="onDeleteClick(row, $event)"
                          >
                            <span class="material-symbols-outlined" aria-hidden="true">delete</span>
                          </button>
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>

                <!-- Pagination -->
                @if (totalCount() > pageSize) {
                  <div class="mee-pagination">
                    <span class="mee-pagination__info">
                      Showing {{ pageStart() }}–{{ pageEnd() }} of {{ totalCount() }}
                    </span>
                    <div class="flex gap-2">
                      <button
                        class="mee-page-btn"
                        [disabled]="page() <= 1"
                        (click)="onPreviousPage()"
                        aria-label="Previous page"
                      >Prev</button>
                      <button
                        class="mee-page-btn"
                        [disabled]="page() * pageSize >= totalCount()"
                        (click)="onNextPage()"
                        aria-label="Next page"
                      >Next</button>
                    </div>
                  </div>
                }
              </div>
            }
          }
        </div>
      </div>
    </div>
  `,
  styles: [`
    /* ---------------------------------------------------------------
     * DashboardComponent — scoped CSS (design token values only, no
     * hardcoded hex). Supplement Tailwind utilities with layout rules
     * that Tailwind cannot cleanly express (hover state, min-width
     * column, component-scoped token wiring).
     * --------------------------------------------------------------- */

    /* --- Stat card grid ---
       2-column at all breakpoints (V1: Draft + Ready only — A2).
       Mobile (360px): gap-3 = 12px; cards fill the column naturally.
       Tablet/desktop: same 2-column layout; larger cards grow with the
       content via the implicit stretch. */
    .mee-stat-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }

    /* --- Search / filter controls ---
       Both input and select share the same baseline look.
       min-height 44px = WCAG 2.5.8 touch target.
       Focus ring uses primary color to signal interaction. */
    .mee-control {
      min-height: 44px;
      border-radius: var(--mee-radius-sm);
      border: 1px solid var(--mee-color-outline);
      padding: 0 12px;
      font-size: 14px;
      color: var(--mee-color-on-surface);
      background: var(--mee-color-surface);
      outline: none;
      transition: border-color var(--mee-transition-fast);
    }
    .mee-control:focus {
      border-color: var(--mee-color-primary);
      box-shadow: 0 0 0 2px var(--mee-color-primary-light);
    }
    /* Prevent select from collapsing below content on 360px */
    .mee-control--select {
      min-width: 140px;
      cursor: pointer;
    }

    /* --- Retry button ---
       Error-colored affordance; 44px touch target; no PrimeNG. */
    .mee-retry-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      padding: 0 16px;
      border-radius: var(--mee-radius-sm);
      border: 1px solid var(--mee-color-error);
      background: var(--mee-color-error-light);
      color: var(--mee-color-error);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background var(--mee-transition-fast);
    }
    .mee-retry-btn:hover {
      background: color-mix(in srgb, var(--mee-color-error-light) 70%, var(--mee-color-error));
    }
    .mee-retry-btn:focus-visible {
      outline: 2px solid var(--mee-color-error);
      outline-offset: 2px;
    }

    /* --- Table wrapper ---
       overflow-x-auto allows horizontal scroll at 360px so the table
       never collapses columns below a readable minimum width.
       The table itself sets min-width so rows are never clipped. */
    .mee-table-wrap {
      overflow-x: auto;
      border: 1px solid var(--mee-color-outline);
      border-radius: var(--mee-radius-md);
    }
    .mee-table {
      width: 100%;
      min-width: 520px;   /* minimum before horizontal scroll activates at 360px */
      border-collapse: collapse;
      font-size: 14px;
    }

    /* --- Table head row --- */
    .mee-table__head-row {
      background: var(--mee-color-surface-variant);
      border-bottom: 1px solid var(--mee-color-outline);
    }
    .mee-table__th {
      padding: 12px 16px;
      text-align: left;
      font-weight: 600;
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
      white-space: nowrap;
    }
    /* Actions column: right-aligned, no text shown (sr-only + icon) */
    .mee-table__th--actions {
      width: 64px;
      text-align: right;
    }

    /* --- Table body rows ---
       min-height via line-height (min-height on <tr> is ignored in most browsers);
       effective touch target via padding + 44px min-height equivalent. */
    .mee-table__row {
      background: var(--mee-color-surface);
      border-bottom: 1px solid var(--mee-color-outline);
      cursor: pointer;
      transition: background var(--mee-transition-fast);
    }
    .mee-table__row:last-child {
      border-bottom: none;
    }
    .mee-table__row:hover {
      background: var(--mee-color-surface-variant);
    }
    .mee-table__row:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: -2px;
    }
    .mee-table__td {
      padding: 12px 16px;
      /* effective row height ≥ 44px via padding + font-size */
    }
    .mee-table__td--name {
      color: var(--mee-color-on-surface);
      max-width: 200px;
    }
    /* 360px: relax max-width so the name column gets as much space as available */
    @media (max-width: 640px) {
      .mee-table__td--name {
        max-width: 120px;
      }
    }
    .mee-table__td--muted {
      color: var(--mee-color-on-surface-muted);
      white-space: nowrap;
    }
    .mee-table__td--actions {
      width: 64px;
      text-align: right;
    }

    /* --- Delete button ---
       44×44px touch target. Icon only — label is sr-only via aria-label on the button.
       Visible at all times on mobile (no hover-reveal on touch screens). */
    .mee-delete-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-width: 44px;
      min-height: 44px;
      border-radius: var(--mee-radius-sm);
      border: none;
      background: transparent;
      color: var(--mee-color-error);
      cursor: pointer;
      transition: background var(--mee-transition-fast), color var(--mee-transition-fast);
      font-size: 0;   /* collapse text node; icon is sized via material-symbols */
    }
    .mee-delete-btn .material-symbols-outlined {
      font-size: 20px;
      line-height: 1;
    }
    .mee-delete-btn:hover {
      background: var(--mee-color-error-light);
    }
    .mee-delete-btn:focus-visible {
      outline: 2px solid var(--mee-color-error);
      outline-offset: 2px;
    }

    /* --- Pagination bar --- */
    .mee-pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 12px 16px;
      border-top: 1px solid var(--mee-color-outline);
      background: var(--mee-color-surface);
    }
    .mee-pagination__info {
      font-size: 13px;
      color: var(--mee-color-on-surface-muted);
    }
    .mee-page-btn {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      min-width: 64px;
      padding: 0 12px;
      border-radius: var(--mee-radius-sm);
      border: 1px solid var(--mee-color-outline);
      background: var(--mee-color-surface-variant);
      color: var(--mee-color-on-surface);
      font-size: 14px;
      font-weight: 500;
      cursor: pointer;
      transition: background var(--mee-transition-fast), border-color var(--mee-transition-fast);
    }
    .mee-page-btn:hover:not(:disabled) {
      background: var(--mee-color-outline-variant);
    }
    .mee-page-btn:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
    }
    .mee-page-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
  `],
})
export class DashboardComponent implements OnInit {
  private readonly api        = inject(DashboardApiService);
  private readonly router     = inject(Router);
  private readonly confirmSvc = inject(MeeConfirmService);
  private readonly destroyRef = inject(DestroyRef);
  /** Injected to gate the offline banner (§6 degradation matrix row "offline"). */
  readonly networkSvc         = inject(NetworkService);
  /** Injected to read last interceptor-recorded error and surface MeeAlertBanner (§6). */
  private readonly errSvc     = inject(ErrorService);

  readonly pageSize = 20;

  // --- Local state signals ---
  readonly loading      = signal(true);
  readonly products     = signal<ProductListItem[]>([]);
  readonly totalCount   = signal(0);
  /** V1 2-value counts (A2). */
  readonly statusCounts = signal<StatusCounts>({ draft: 0, ready: 0 });
  /** Decoded but NOT rendered in V1 (A5/§2.2) — never silently dropped. */
  readonly onboardingCompleteness = signal<ProfileCompletenessSummary | null>(null);
  readonly page         = signal(1);
  readonly searchQuery  = signal('');
  readonly statusFilter = signal('');
  /** Non-null → render mee-alert-banner (§6). Set via ErrorService effect (primary) or subscribe error. */
  readonly errorMessage = signal<string | null>(null);

  readonly searchCtrl = new FormControl('');

  // --- Computed ---
  readonly isEmpty  = computed(() => !this.loading() && this.products().length === 0 && !this.errorMessage());
  readonly pageStart = computed(() => (this.page() - 1) * this.pageSize + 1);
  readonly pageEnd   = computed(() => Math.min(this.page() * this.pageSize, this.totalCount()));

  /** Client-side name filter over the current page (A3 — never sent to server). */
  readonly visibleProducts = computed(() => {
    const q = this.searchQuery();
    const sf = this.statusFilter();
    let items = this.products();
    if (sf) { items = items.filter(p => p.status === sf); }
    return filterProductsByName(items, q);
  });

  constructor() {
    // Debounced search — wired in constructor so takeUntilDestroyed can use default injection context
    this.searchCtrl.valueChanges
      .pipe(
        debounceTime(400),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef)
      )
      .subscribe(value => {
        this.searchQuery.set(value ?? '');
        // No page reset — search is client-side over current page (A3)
      });

    // Primary error-surface path (§6 degradation matrix):
    // When errorInterceptor records an error (5xx/4xx that reached it), set the errorMessage
    // signal so the template renders mee-alert-banner. The service's catchError has already
    // returned a fallback empty DashboardResponse — this effect surfaces the error to the user.
    // effect() runs in the component's injection context so ChangeDetection picks up the signal write.
    effect(() => {
      const lastErr = this.errSvc.lastError();
      if (lastErr) {
        this.errorMessage.set('Unable to load products. Please try again.');
      }
    });
  }

  ngOnInit(): void {
    this.fetchProducts();
  }

  onNewCatalog(): void {
    this.router.navigate(['/catalogs/new']);
  }

  onRowClick(row: ProductListItem): void {
    this.router.navigate(['/catalogs', row.product_id, 'edit']);
  }

  onStatusFilterChange(event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.statusFilter.set(select.value);
  }

  onDeleteClick(row: ProductListItem, event: MouseEvent): void {
    event.stopPropagation(); // prevent row click nav
    this.confirmSvc.confirm({
      header: 'Delete Catalog',
      message: `Delete "${row.name ?? 'this product'}"? This action cannot be undone.`,
      accept: () => this.deleteProduct(row),
    });
  }

  onPreviousPage(): void {
    if (this.page() > 1) {
      this.page.update(p => p - 1);
      this.fetchProducts();
    }
  }

  onNextPage(): void {
    if (this.page() * this.pageSize < this.totalCount()) {
      this.page.update(p => p + 1);
      this.fetchProducts();
    }
  }

  /** Retry loading after an error — clears the error surface and re-fetches. */
  onRetry(): void {
    this.errSvc.clear();
    this.errorMessage.set(null);
    this.fetchProducts();
  }

  formatRelativeTime(isoString: string): string {
    return formatRelativeTime(isoString);
  }

  private fetchProducts(): void {
    this.loading.set(true);
    this.errorMessage.set(null);
    this.api
      .loadProducts({
        page: this.page(),
        limit: this.pageSize,
        // status_filter and search are NOT sent to the server (A3 — DashboardQuery extra="forbid")
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: res => {
          this.products.set(res.products);
          this.totalCount.set(res.total);
          this.onboardingCompleteness.set(res.onboarding_completeness);
          const counts = this.api.deriveStatusCounts(res.products);
          this.statusCounts.set(counts);
          this.loading.set(false);
        },
        error: () => {
          // Defence-in-depth (§6): the service's catchError should prevent this branch,
          // but set errorMessage here as a safety net in case the matrix itself threw.
          this.errorMessage.set('Unable to load products. Please try again.');
          this.loading.set(false);
        },
      });
  }

  private deleteProduct(row: ProductListItem): void {
    this.api.deleteProduct(row.product_id).subscribe({
      next: () => {
        // Optimistic remove on success (or 404-as-success from the service matrix).
        this.products.update(items => items.filter(p => p.product_id !== row.product_id));
        this.totalCount.update(n => Math.max(0, n - 1));
        const counts = this.api.deriveStatusCounts(this.products());
        this.statusCounts.set(counts);
      },
      // EMPTY on non-404 error (from EMPTY catchError branch) — no next fires, no error fires.
      // Row stays in the list — the user can retry via the delete button again.
    });
  }
}
