import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';

import {
  MeeButtonComponent,
  MeeCardComponent,
  MeeIconComponent,
  MeeSkeletonComponent,
} from '@mesell/ui-kit';
import {
  PageHeaderComponent,
  StatusBadgeComponent,
  EmptyStateComponent,
} from '@mesell/composites';
import type { ProductStatus } from '@mesell/composites';

// ---------------------------------------------------------------------------
// View model — typed shape for a catalog list row.
// Wired to real API in Wave 6; simulated for responsive polish in Wave 5.
// ---------------------------------------------------------------------------
interface CatalogRow {
  id: string;
  name: string;
  category: string;
  sku_count: number;
  status: ProductStatus;
  updated_at: string;
}

// Simulated catalog data — 3 entries so layout is exercised at all breakpoints.
const SIMULATED_CATALOGS: CatalogRow[] = [
  {
    id:         'cat-001',
    name:       'Blue Cotton Kurti Collection',
    category:   'Fashion > Women > Ethnic > Kurti',
    sku_count:  12,
    status:     'ready',
    updated_at: '2026-06-17',
  },
  {
    id:         'cat-002',
    name:       'Printed Silk Saree Set',
    category:   'Fashion > Women > Ethnic > Saree',
    sku_count:  6,
    status:     'draft',
    updated_at: '2026-06-16',
  },
  {
    id:         'cat-003',
    name:       'Kids Hooded Jacket',
    category:   'Fashion > Kids > Winterwear > Jackets',
    sku_count:  8,
    status:     'exported',
    updated_at: '2026-06-15',
  },
];

@Component({
  selector: 'mee-catalog-list',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MeeButtonComponent,
    MeeCardComponent,
    MeeIconComponent,
    MeeSkeletonComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    EmptyStateComponent,
  ],
  styles: [`
    :host { display: block; }

    .mee-catalog-page {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-6);
      max-width: 1200px;
      margin: 0 auto;
      padding: var(--mee-space-6) var(--mee-space-4);
    }

    /* ── Search bar ─────────────────────────────────────────────────── */
    .mee-search {
      width: 100%;
      height: 44px;
      padding: 0 var(--mee-space-4);
      font-size: 0.875rem;
      color: var(--mee-color-on-surface);
      background: var(--mee-color-surface);
      border: 1px solid var(--mee-color-outline);
      border-radius: var(--mee-radius-sm);
      outline: none;
      transition: border-color var(--mee-transition-fast),
                  box-shadow var(--mee-transition-fast);
    }
    .mee-search::placeholder { color: var(--mee-color-on-surface-muted); }
    .mee-search:focus-visible {
      border-color: var(--mee-color-primary);
      box-shadow: 0 0 0 3px var(--mee-color-primary-light);
    }

    /* ── Filter chips ─────────────────────────────────────────────── */
    .mee-filter-chips {
      display: flex;
      gap: var(--mee-space-2);
      overflow-x: auto;
      padding-bottom: var(--mee-space-1);
      scrollbar-width: none;
    }
    .mee-filter-chips::-webkit-scrollbar { display: none; }

    .mee-chip {
      flex-shrink: 0;
      min-height: 36px;
      padding: 0 var(--mee-space-4);
      border-radius: var(--mee-radius-full);
      border: 1.5px solid var(--mee-color-outline);
      background: var(--mee-color-surface);
      color: var(--mee-color-on-surface);
      font-size: 13px;
      font-weight: 500;
      cursor: pointer;
      transition: background var(--mee-transition-fast), color var(--mee-transition-fast), border-color var(--mee-transition-fast);
      white-space: nowrap;
      text-transform: capitalize;
    }

    .mee-chip--active {
      background: var(--mee-color-primary);
      color: var(--mee-color-on-primary);
      border-color: var(--mee-color-primary);
    }

    .mee-chip:hover:not(.mee-chip--active) {
      border-color: var(--mee-color-primary);
      color: var(--mee-color-primary);
    }

    /* ── Card grid ──────────────────────────────────────────────────── */
    .mee-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--mee-space-4);
    }
    @media (min-width: 640px) {
      .mee-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (min-width: 1024px) {
      .mee-grid { grid-template-columns: repeat(3, 1fr); }
    }

    /* ── Card body ──────────────────────────────────────────────────── */
    .mee-card-body { display: flex; flex-direction: column; gap: var(--mee-space-3); }

    .mee-card-body--row {
      display: flex;
      gap: var(--mee-space-3);
      align-items: flex-start;
    }

    .mee-card-thumb {
      flex-shrink: 0;
      width: 64px;
      height: 64px;
      border-radius: var(--mee-radius-sm);
      background: var(--mee-color-bg);
      border: 1px solid var(--mee-color-outline);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--mee-color-on-surface-muted);
      font-size: 22px;
    }

    .mee-card-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
    }

    .mee-card-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: var(--mee-space-2);
    }
    .mee-card-title {
      flex: 1;
      min-width: 0;
      font-size: 0.9375rem;
      font-weight: 600;
      line-height: 1.4;
      color: var(--mee-color-on-surface);
    }

    .mee-card-category {
      font-size: 0.75rem;
      line-height: 1.4;
      color: var(--mee-color-on-surface-muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .mee-card-meta {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 0.75rem;
      color: var(--mee-color-on-surface-muted);
    }

    .mee-card-actions {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
      padding-top: var(--mee-space-3);
      border-top: 1px solid var(--mee-color-outline);
    }

    /* ── FAB ─────────────────────────────────────────────────────── */
    .mee-fab {
      position: fixed;
      bottom: calc(72px + env(safe-area-inset-bottom, 0px));
      right: var(--mee-space-5);
      width: 56px;
      height: 56px;
      border-radius: var(--mee-radius-full);
      background: var(--mee-color-primary);
      color: var(--mee-color-on-primary);
      border: none;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
      box-shadow: var(--mee-shadow-lg);
      z-index: 300;
      transition: transform var(--mee-transition-fast), box-shadow var(--mee-transition-fast);
    }

    .mee-fab:hover {
      transform: scale(1.06);
      box-shadow: 0 8px 28px rgba(0,0,0,0.18);
    }

    .mee-fab:active {
      transform: scale(0.97);
    }

    @media (min-width: 640px) {
      .mee-fab {
        bottom: var(--mee-space-8);
        right: var(--mee-space-8);
      }
    }
  `],
  template: `
    <!-- Page wrapper: shell .page-content provides bottom-nav clearance at mobile -->
    <div class="mee-catalog-page">

      <!-- Page header with "New Catalog" CTA -->
      <mee-page-header
        title="My Catalogs"
        subtitle="Manage your product catalogs and track listing quality."
        cta_label="New Catalog"
        cta_icon="add"
        (cta_click)="onNewCatalog()"
      />

      <!-- Search bar — full-width on mobile -->
      <input
        type="search"
        class="mee-search"
        placeholder="Search catalogs..."
        [value]="searchQuery()"
        (input)="onSearch($event)"
        aria-label="Search catalogs"
      />

      <!-- Status filter chips -->
      <div class="mee-filter-chips" role="group" aria-label="Filter by status">
        @for (s of ALL_STATUSES; track s) {
          <button
            type="button"
            class="mee-chip"
            [class.mee-chip--active]="statusFilter() === s"
            (click)="statusFilter.set(s)"
          >{{ s === 'all' ? 'All' : s }}</button>
        }
      </div>

      <!-- Loading state: 3 card skeletons in same grid pattern -->
      @if (loading()) {
        <div class="mee-grid">
          @for (i of [0, 1, 2]; track i) {
            <mee-skeleton variant="card" />
          }
        </div>

      <!-- Empty state: no catalogs yet -->
      } @else if (filteredCatalogs().length === 0) {
        <mee-empty-state
          icon="inventory_2"
          [message]="searchQuery()
            ? 'No catalogs match your search.'
            : 'No catalogs yet. Create your first catalog to get started.'"
          [cta_label]="searchQuery() ? undefined : 'New Catalog'"
          (cta_click)="onNewCatalog()"
        />

      <!-- Catalog grid — 1-col on mobile, 2-col at sm, 3-col at lg -->
      } @else {
        <div class="mee-grid" aria-label="Catalog list">
          @for (cat of filteredCatalogs(); track cat.id) {
            <mee-card>
              <div class="mee-card-body--row">

                <!-- Thumbnail placeholder -->
                <div class="mee-card-thumb" aria-hidden="true">
                  <mee-icon name="image" />
                </div>

                <!-- Card info -->
                <div class="mee-card-info">

                  <!-- Card header: name + status badge -->
                  <div class="mee-card-head">
                    <h2 class="mee-card-title">{{ cat.name }}</h2>
                    <mee-status-badge [status]="cat.status" />
                  </div>

                  <!-- Category path — truncated to 1 line -->
                  <p class="mee-card-category" [title]="cat.category">{{ cat.category }}</p>

                  <!-- Meta row: SKU count + updated date -->
                  <div class="mee-card-meta">
                    <span>{{ cat.sku_count }} SKUs</span>
                    <span>{{ cat.updated_at }}</span>
                  </div>

                  <!-- Action buttons -->
                  <div class="mee-card-actions">
                    <mee-button
                      label="Edit"
                      variant="secondary"
                      size="sm"
                      (clicked)="onEdit(cat.id)"
                    />
                    <mee-button
                      label="Preview"
                      variant="ghost"
                      size="sm"
                      (clicked)="onPreview(cat.id)"
                    />
                  </div>

                </div>
              </div>
            </mee-card>
          }
        </div>
      }

    </div>

    <!-- FAB: new catalog (mobile primary CTA, above bottom nav) -->
    <button
      type="button"
      class="mee-fab"
      aria-label="Create new catalog"
      (click)="onNewCatalog()"
    >
      <mee-icon name="add" />
    </button>
  `,
})
export class CatalogListComponent implements OnInit {
  private readonly router = inject(Router);

  readonly loading      = signal<boolean>(true);
  readonly catalogs     = signal<CatalogRow[]>([]);
  readonly searchQuery  = signal<string>('');
  readonly statusFilter = signal<ProductStatus | 'all'>('all');

  readonly ALL_STATUSES: Array<ProductStatus | 'all'> = ['all', 'draft', 'ready', 'exported', 'live'];

  readonly filteredCatalogs = (): CatalogRow[] => {
    const q      = this.searchQuery().toLowerCase().trim();
    const status = this.statusFilter();
    let list     = this.catalogs();

    if (q) {
      list = list.filter(
        c => c.name.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)
      );
    }

    if (status !== 'all') {
      list = list.filter(c => c.status === status);
    }

    return list;
  };

  ngOnInit(): void {
    // Simulate 600ms load — Wave 6 replaces with real HTTP call.
    setTimeout(() => {
      this.catalogs.set(SIMULATED_CATALOGS);
      this.loading.set(false);
    }, 600);
  }

  onNewCatalog(): void {
    void this.router.navigate(['/catalogs', 'new']);
  }

  onEdit(id: string): void {
    void this.router.navigate(['/catalogs', id, 'edit']);
  }

  onPreview(id: string): void {
    void this.router.navigate(['/catalogs', id, 'preview']);
  }

  onSearch(event: Event): void {
    const val = (event.target as HTMLInputElement).value;
    this.searchQuery.set(val);
  }
}
