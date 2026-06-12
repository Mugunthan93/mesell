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
    <div class="w-full flex flex-col">

      <!-- Offline banner — MeeOfflineBannerComponent reads NetworkService.online() internally (§6). -->
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
          <div class="flex flex-col gap-2">
            <mee-alert-banner
              variant="error"
              [message]="errorMessage()!"
            />
            <button
              class="self-start min-h-[44px] px-4 rounded-lg text-sm font-medium transition-colors"
              style="
                background: var(--mee-color-error-light);
                border: 1px solid var(--mee-color-error);
                color: var(--mee-color-error);
              "
              (click)="onRetry()"
              aria-label="Retry loading catalogs"
            >
              Retry
            </button>
          </div>
        }

        <!-- Loading skeleton — stat cards + table rows -->
        @if (loading()) {
          <div class="flex flex-col gap-6">
            <mee-loading-skeleton variant="stat-card" />
            <mee-loading-skeleton variant="table-row" [lines]="5" />
          </div>
        } @else {

          <!-- Stat cards — Draft + Ready only (A2; V1 wire is 2-value) -->
          <div class="grid grid-cols-2 gap-3 sm:grid-cols-2">
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

          <!-- Search bar (client-side name search — A3) -->
          <div class="flex flex-col gap-2 sm:flex-row sm:items-center sm:gap-3">
            <input type="search" [formControl]="searchCtrl" placeholder="Search catalogs..."
              class="flex-1 min-h-[44px] rounded-lg border px-3 text-sm outline-none"
              style="border-color:var(--mee-color-outline);color:var(--mee-color-on-surface);background:var(--mee-color-surface);"
              aria-label="Search catalogs" />
            <!-- Status filter — V1: All/Draft/Ready only (A2) -->
            <select class="min-h-[44px] rounded-lg border px-3 text-sm outline-none"
              style="border-color:var(--mee-color-outline);color:var(--mee-color-on-surface);background:var(--mee-color-surface);"
              aria-label="Filter by status" (change)="onStatusFilterChange($event)">
              <option value="">All Statuses</option>
              <option value="draft">Draft</option>
              <option value="ready">Ready</option>
            </select>
          </div>

          <!-- Empty state (§6 row "empty") — isEmpty = no products + no error -->
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
                    <th class="px-4 py-3 text-left font-semibold" style="color: var(--mee-color-on-surface-muted);">Status</th>
                    <th class="px-4 py-3 text-left font-semibold" style="color: var(--mee-color-on-surface-muted);">Updated</th>
                    <th class="px-4 py-3 text-left font-semibold sr-only">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (row of visibleProducts(); track row.product_id) {
                    <tr class="cursor-pointer transition-colors"
                      style="min-height:44px;border-bottom:1px solid var(--mee-color-outline);background:var(--mee-color-surface);"
                      tabindex="0" (click)="onRowClick(row)"
                      (keydown.enter)="onRowClick(row)" (keydown.space)="onRowClick(row)"
                      [attr.aria-label]="'Edit ' + (row.name ?? 'product')" role="row"
                    >
                      <td class="px-4 py-3 min-h-[44px]" style="color: var(--mee-color-on-surface);">
                        <span class="block max-w-[200px] truncate font-medium" [title]="row.name ?? ''">
                          {{ row.name ?? '(untitled)' }}
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
    </div>
  `,
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
