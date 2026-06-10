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

import { MeeConfirmService } from '../../ui';
import {
  StatCardComponent,
  StatusBadgeComponent,
  PageHeaderComponent,
  EmptyStateComponent,
  LoadingSkeletonComponent,
} from '../../shared';

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
  ],
  template: `
    <div class="w-full px-4 py-6 sm:px-6 max-w-7xl mx-auto flex flex-col gap-6">

      <!-- Page header -->
      <mee-page-header
        title="My Catalogs"
        cta_label="New Catalog"
        cta_icon="add"
        (cta_click)="onNewCatalog()"
      />

      <!-- Loading skeleton — stat cards + table rows -->
      @if (loading()) {
        <div class="flex flex-col gap-6">
          <mee-loading-skeleton variant="stat-card" />
          <mee-loading-skeleton variant="table-row" [lines]="5" />
        </div>
      } @else {

        <!-- Stat cards -->
        <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
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
          <mee-stat-card
            label="Exported"
            [value]="statusCounts().exported"
            icon="download"
            color="purple"
          />
          <mee-stat-card
            label="Live"
            [value]="statusCounts().live"
            icon="storefront"
            color="orange"
          />
        </div>

        <!-- Search + filter bar -->
        <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
          <input
            type="search"
            [formControl]="searchCtrl"
            placeholder="Search catalogs..."
            class="flex-1 min-h-[44px] rounded-lg border px-3 text-sm outline-none focus:ring-2"
            style="
              border-color: var(--mee-color-outline);
              color: var(--mee-color-on-surface);
              background: var(--mee-color-surface);
              focus-ring-color: var(--mee-color-primary);
            "
            aria-label="Search catalogs"
          />
          <select
            class="min-h-[44px] rounded-lg border px-3 text-sm outline-none focus:ring-2"
            style="
              border-color: var(--mee-color-outline);
              color: var(--mee-color-on-surface);
              background: var(--mee-color-surface);
            "
            aria-label="Filter by status"
            (change)="onStatusFilterChange($event)"
          >
            <option value="">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="ready">Ready</option>
            <option value="exported">Exported</option>
            <option value="live">Live</option>
          </select>
        </div>

        <!-- Empty state -->
        @if (isEmpty()) {
          <mee-empty-state
            icon="inventory_2"
            message="No catalogs yet. Create your first catalog to get started."
            cta_label="New Catalog"
            (cta_click)="onNewCatalog()"
          />
        } @else {
          <!-- Product table -->
          <div class="overflow-x-auto rounded-xl" style="border: 1px solid var(--mee-color-outline);">
            <table class="w-full text-sm" role="table" aria-label="Product catalog list">
              <thead>
                <tr style="background: var(--mee-color-surface-variant); border-bottom: 1px solid var(--mee-color-outline);">
                  <th class="px-4 py-3 text-left font-semibold" style="color: var(--mee-color-on-surface-muted);">Name</th>
                  <th class="px-4 py-3 text-left font-semibold" style="color: var(--mee-color-on-surface-muted);">Category</th>
                  <th class="px-4 py-3 text-left font-semibold" style="color: var(--mee-color-on-surface-muted);">Status</th>
                  <th class="px-4 py-3 text-left font-semibold" style="color: var(--mee-color-on-surface-muted);">Updated</th>
                  <th class="px-4 py-3 text-left font-semibold sr-only">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (row of products(); track row.id) {
                  <tr
                    class="cursor-pointer transition-colors"
                    style="
                      min-height: 44px;
                      border-bottom: 1px solid var(--mee-color-outline);
                    "
                    [style.background]="'var(--mee-color-surface)'"
                    tabindex="0"
                    (click)="onRowClick(row)"
                    (keydown.enter)="onRowClick(row)"
                    (keydown.space)="onRowClick(row)"
                    [attr.aria-label]="'Edit ' + row.name"
                    role="row"
                  >
                    <td class="px-4 py-3 min-h-[44px]" style="color: var(--mee-color-on-surface);">
                      <span class="block max-w-[200px] truncate font-medium" [title]="row.name">
                        {{ row.name }}
                      </span>
                    </td>
                    <td class="px-4 py-3" style="color: var(--mee-color-on-surface-muted);">
                      <span class="block max-w-[120px] truncate" [title]="row.category_name">
                        {{ row.category_name }}
                      </span>
                    </td>
                    <td class="px-4 py-3">
                      <mee-status-badge [status]="row.status" />
                    </td>
                    <td class="px-4 py-3" style="color: var(--mee-color-on-surface-muted);">
                      {{ formatRelativeTime(row.updated_at) }}
                    </td>
                    <td class="px-4 py-3">
                      <button
                        class="min-h-[44px] min-w-[44px] rounded-lg px-3 py-2 text-sm font-medium transition-colors"
                        style="color: var(--mee-color-error); background: transparent;"
                        aria-label="Delete catalog"
                        (click)="onDeleteClick(row, $event)"
                      >
                        <span class="material-symbols-outlined" aria-hidden="true" style="font-size:20px; vertical-align:middle;">delete</span>
                      </button>
                    </td>
                  </tr>
                }
              </tbody>
            </table>

            <!-- Pagination -->
            @if (totalCount() > pageSize) {
              <div
                class="flex items-center justify-between px-4 py-3"
                style="border-top: 1px solid var(--mee-color-outline); background: var(--mee-color-surface);"
              >
                <span class="text-sm" style="color: var(--mee-color-on-surface-muted);">
                  Showing {{ pageStart() }}–{{ pageEnd() }} of {{ totalCount() }}
                </span>
                <div class="flex gap-2">
                  <button
                    class="min-h-[44px] min-w-[44px] px-3 rounded-lg text-sm font-medium disabled:opacity-40"
                    style="
                      background: var(--mee-color-surface-variant);
                      color: var(--mee-color-on-surface);
                      border: 1px solid var(--mee-color-outline);
                    "
                    [disabled]="page() <= 1"
                    (click)="onPreviousPage()"
                    aria-label="Previous page"
                  >Prev</button>
                  <button
                    class="min-h-[44px] min-w-[44px] px-3 rounded-lg text-sm font-medium disabled:opacity-40"
                    style="
                      background: var(--mee-color-surface-variant);
                      color: var(--mee-color-on-surface);
                      border: 1px solid var(--mee-color-outline);
                    "
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
  readonly statusCounts = signal<StatusCounts>({ draft: 0, ready: 0, exported: 0, live: 0 });
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
    this.router.navigate(['/catalogs', row.id, 'edit']);
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
        status_filter: this.statusFilter() || undefined,
        search: this.searchQuery() || undefined,
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
    this.api.deleteProduct(row.id).subscribe({
      next: () => {
        this.products.update(items => items.filter(p => p.id !== row.id));
        this.totalCount.update(n => n - 1);
        const counts = this.api.deriveStatusCounts(this.products());
        this.statusCounts.set(counts);
      },
    });
  }
}
