import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule, FormControl } from '@angular/forms';
import { Router } from '@angular/router';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';

import { MeeConfirmService, MeeIconComponent } from '@mesell/ui-kit';
import {
  StatCardComponent,
  StatusBadgeComponent,
  PageHeaderComponent,
  EmptyStateComponent,
  LoadingSkeletonComponent,
} from '@mesell/composites';

import {
  DashboardApiService,
  ProductListItem,
  StatusCounts,
} from './services/dashboard-api.service';
import { formatRelativeTime } from './dashboard.model';

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
    MeeIconComponent,
  ],
  styles: [`
    :host {
      display: block;
    }

    .dash-page {
      max-width: 1200px;
      margin: 0 auto;
      padding: var(--mee-space-6);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }

    /* Loading skeleton wrapper */
    .dash-skeleton {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
    }

    /* Stat-card grid */
    .stat-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: var(--mee-space-4);
    }

    /* Search + filter toolbar */
    .toolbar {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
    }

    .toolbar__search,
    .toolbar__filter {
      min-height: 44px;
      border-radius: var(--mee-radius-sm);
      border: 1px solid var(--mee-color-outline);
      padding: 0 var(--mee-space-3);
      font-size: 14px;
      color: var(--mee-color-on-surface);
      background: var(--mee-color-surface);
      outline: none;
      transition: border-color var(--mee-transition-fast), box-shadow var(--mee-transition-fast);
    }

    .toolbar__search {
      flex: 1;
    }

    .toolbar__search:focus,
    .toolbar__filter:focus {
      border-color: var(--mee-color-primary);
      box-shadow: 0 0 0 3px var(--mee-color-primary-light);
    }

    /* Table card surface */
    .table-card {
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
      box-shadow: var(--mee-shadow-sm);
      border: 1px solid var(--mee-color-outline);
      overflow: hidden;
    }

    .table-scroll {
      overflow-x: auto;
    }

    .catalog-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }

    .catalog-table thead tr {
      background: var(--mee-color-bg);
      border-bottom: 1px solid var(--mee-color-outline);
    }

    .catalog-table th {
      padding: var(--mee-space-3) var(--mee-space-4);
      text-align: left;
      font-weight: 600;
      color: var(--mee-color-on-surface-muted);
      white-space: nowrap;
    }

    .catalog-table tbody tr {
      border-bottom: 1px solid var(--mee-color-outline);
      background: var(--mee-color-surface);
      cursor: pointer;
      transition: background var(--mee-transition-fast);
    }

    .catalog-table tbody tr:last-child {
      border-bottom: none;
    }

    .catalog-table tbody tr:hover,
    .catalog-table tbody tr:focus-visible {
      background: var(--mee-color-bg);
      outline: none;
    }

    .catalog-table td {
      padding: var(--mee-space-3) var(--mee-space-4);
      color: var(--mee-color-on-surface);
    }

    .cell-name {
      display: block;
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      font-weight: 500;
      color: var(--mee-color-on-surface);
    }

    .cell-category {
      display: block;
      max-width: 140px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: var(--mee-color-on-surface-muted);
    }

    .cell-updated {
      color: var(--mee-color-on-surface-muted);
      white-space: nowrap;
    }

    .btn-delete {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 44px;
      min-width: 44px;
      padding: var(--mee-space-2);
      border: none;
      border-radius: var(--mee-radius-sm);
      color: var(--mee-color-error);
      background: transparent;
      cursor: pointer;
      transition: background var(--mee-transition-fast);
    }

    .btn-delete:hover {
      background: var(--mee-color-bg);
    }

    .btn-delete mee-icon i {
      font-size: 20px;
      line-height: 1;
    }

    /* Pagination */
    .pagination {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--mee-space-3) var(--mee-space-4);
      border-top: 1px solid var(--mee-color-outline);
      background: var(--mee-color-surface);
    }

    .pagination__info {
      font-size: 14px;
      color: var(--mee-color-on-surface-muted);
    }

    .pagination__controls {
      display: flex;
      gap: var(--mee-space-2);
    }

    .pagination__btn {
      min-height: 44px;
      min-width: 44px;
      padding: 0 var(--mee-space-3);
      border-radius: var(--mee-radius-sm);
      font-size: 14px;
      font-weight: 500;
      color: var(--mee-color-on-surface);
      background: var(--mee-color-surface);
      border: 1px solid var(--mee-color-outline);
      cursor: pointer;
      transition: background var(--mee-transition-fast), border-color var(--mee-transition-fast);
    }

    .pagination__btn:hover:not(:disabled) {
      background: var(--mee-color-bg);
      border-color: var(--mee-color-outline-variant);
    }

    .pagination__btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .sr-only {
      position: absolute;
      width: 1px;
      height: 1px;
      padding: 0;
      margin: -1px;
      overflow: hidden;
      clip: rect(0, 0, 0, 0);
      white-space: nowrap;
      border: 0;
    }

    /* ── Mobile-first responsive ──────────────────────────────────── */
    @media (max-width: 639px) {
      .dash-page {
        padding: var(--mee-space-4);
      }
      .stat-grid {
        grid-template-columns: repeat(2, 1fr);
        gap: var(--mee-space-3);
      }
    }

    /* DESKTOP — 640px+ */
    @media (min-width: 640px) {
      .toolbar {
        flex-direction: row;
        align-items: center;
      }
    }
  `],
  template: `
    <div class="dash-page">

      <!-- Page header — F-IA-1: renamed from "My Catalogs" to "Home" so /dashboard and
           /catalogs are no longer both titled "My Catalogs". The /catalogs grid keeps
           its "My Catalogs" heading exclusively. -->
      <mee-page-header
        data-testid="dashboard-heading"
        title="Home"
        cta_label="New Catalog"
        cta_icon="add"
        (cta_click)="onNewCatalog()"
      />

      <!-- Loading skeleton — stat cards + table rows -->
      @if (loading()) {
        <div class="dash-skeleton">
          <mee-loading-skeleton variant="stat-card" />
          <mee-loading-skeleton variant="table-row" [lines]="5" />
        </div>
      } @else {

        <!-- Stat cards -->
        <div class="stat-grid">
          <mee-stat-card
            label="Draft"
            [value]="statusCounts().draft"
            icon="edit-note"
            color="blue"
          />
          <mee-stat-card
            label="Ready"
            [value]="statusCounts().ready"
            icon="check-circle"
            color="green"
          />
        </div>

        <!-- Search + filter bar -->
        <div class="toolbar">
          <input
            type="search"
            [formControl]="searchCtrl"
            placeholder="Search catalogs..."
            class="toolbar__search"
            aria-label="Search catalogs"
          />
          <select
            class="toolbar__filter"
            aria-label="Filter by status"
            (change)="onStatusFilterChange($event)"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="ready">Ready</option>
          </select>
        </div>

        <!-- Empty state -->
        @if (isEmpty()) {
          <mee-empty-state
            data-testid="dashboard-empty-state"
            icon="inventory"
            message="No catalogs yet. Create your first catalog to get started."
            cta_label="New Catalog"
            (cta_click)="onNewCatalog()"
          />
        } @else {
          <!-- Product table card -->
          <div class="table-card">
            <div class="table-scroll">
              <table class="catalog-table" role="table" aria-label="Product catalog list">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Updated</th>
                    <th class="sr-only">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (row of products(); track row.product_id) {
                    <tr
                      tabindex="0"
                      data-testid="dashboard-product-row"
                      (click)="onRowClick(row)"
                      (keydown.enter)="onRowClick(row)"
                      (keydown.space)="onRowClick(row)"
                      [attr.aria-label]="'Edit ' + row.name"
                      role="row"
                    >
                      <td>
                        <span class="cell-name" [title]="row.name">{{ row.name }}</span>
                      </td>
                      <td>
                        <mee-status-badge [status]="row.status" />
                      </td>
                      <td class="cell-updated">
                        {{ formatRelativeTime(row.updated_at) }}
                      </td>
                      <td>
                        <button
                          class="btn-delete"
                          aria-label="Delete catalog"
                          (click)="onDeleteClick(row, $event)"
                        >
                          <mee-icon name="delete" />
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>

            <!-- Pagination -->
            @if (totalCount() > pageSize) {
              <div class="pagination">
                <span class="pagination__info">
                  Showing {{ pageStart() }}–{{ pageEnd() }} of {{ totalCount() }}
                </span>
                <div class="pagination__controls">
                  <button
                    class="pagination__btn"
                    [disabled]="page() <= 1"
                    (click)="onPreviousPage()"
                    aria-label="Previous page"
                  >Prev</button>
                  <button
                    class="pagination__btn"
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
  `,
})
export class DashboardComponent implements OnInit {
  private readonly api = inject(DashboardApiService);
  private readonly router = inject(Router);
  private readonly confirmSvc = inject(MeeConfirmService);
  private readonly destroyRef = inject(DestroyRef);

  readonly pageSize = 20;

  // --- Local state signals ---
  readonly loading      = signal(true);
  readonly products     = signal<ProductListItem[]>([]);
  readonly totalCount   = signal(0);
  readonly statusCounts = signal<StatusCounts>({ draft: 0, ready: 0 });
  readonly page         = signal(1);
  readonly searchQuery  = signal('');
  readonly statusFilter = signal('');

  readonly searchCtrl = new FormControl('');

  // --- Computed ---
  readonly isEmpty  = computed(() => !this.loading() && this.products().length === 0);
  readonly pageStart = computed(() => (this.page() - 1) * this.pageSize + 1);
  readonly pageEnd   = computed(() => Math.min(this.page() * this.pageSize, this.totalCount()));

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
        this.page.set(1);
        this.fetchProducts();
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
    this.page.set(1);
    this.fetchProducts();
  }

  onDeleteClick(row: ProductListItem, event: MouseEvent): void {
    event.stopPropagation(); // prevent row click nav
    this.confirmSvc.confirm({
      header: 'Delete Catalog',
      message: `Delete "${row.name}"? This action cannot be undone.`,
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

  formatRelativeTime(isoString: string): string {
    return formatRelativeTime(isoString);
  }

  private fetchProducts(): void {
    this.loading.set(true);
    this.api
      .loadProducts({
        page: this.page(),
        limit: this.pageSize,
        // status_filter and search are client-side only (A3 — server params are page+limit only).
      })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: res => {
          this.products.set(res.products);
          this.totalCount.set(res.total);
          // Derive status counts from full unfiltered seed for dashboard cards
          const counts = this.api.deriveStatusCounts(res.products);
          this.statusCounts.set(counts);
          this.loading.set(false);
        },
        error: () => {
          this.loading.set(false);
        },
      });
  }

  private deleteProduct(row: ProductListItem): void {
    this.api.deleteProduct(row.product_id).subscribe({
      next: () => {
        this.products.update(items => items.filter(p => p.product_id !== row.product_id));
        this.totalCount.update(n => n - 1);
        const counts = this.api.deriveStatusCounts(this.products());
        this.statusCounts.set(counts);
      },
    });
  }
}
