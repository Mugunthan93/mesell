/**
 * CatalogListComponent — entry point for /catalogs (Wave 3).
 *
 * Shows the seller's product list. Entry point for the catalog funnel:
 *   1. Empty state → "Create First Catalog" → /catalogs/new (SmartPicker)
 *   2. Product cards → click → /catalogs/:id/edit (CatalogForm)
 *   3. "Create New Catalog" button in header → /catalogs/new
 *
 * Data source: CatalogListApiService.listProducts() wraps GET /api/v1/products
 * (dashboard-owned endpoint). V1 loads page 1 only — no pagination UI.
 *
 * Service injection: CatalogListApiService is route-scoped (see catalog.routes.ts
 * path:'' providers:[CatalogListApiService] — added in Wave 3.2).
 *
 * Template adjustments vs spec:
 *   - Uses <mee-card> (selector from MeeCardComponent) with direct content projection.
 *     MeeCardComponent wraps <p-card> internally via <ng-content /> — callers must NOT
 *     use <p-card> directly, and must NOT use <ng-template #content> (that is PrimeNG's
 *     internal slotting API, not exposed by MeeCardComponent).
 *   - Uses <mee-page-header> for the title + CTA row (PageHeaderComponent is available
 *     and correctly handles the "Create New Catalog" button via cta_label + (cta_click)).
 *   - StatusBadgeComponent input is [status] (input.required<ProductStatus>()).
 *     CatalogListItem.status ('draft'|'ready') is a strict subtype of ProductStatus — no cast needed.
 */

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
} from '@mesell/ui-kit';
import {
  LoadingSkeletonComponent,
  PageHeaderComponent,
  StatusBadgeComponent,
  MeeAlertBannerComponent,
  EmptyStateComponent,
} from '@mesell/composites';

import { CatalogListApiService } from './catalog-list-api.service';
import type { CatalogListItem } from './catalog-list.model';
import { formatRelativeTime } from './catalog-list-util';

@Component({
  selector: 'mee-catalog-list',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [],  // CatalogListApiService provided at route level (catalog.routes.ts)
  imports: [
    MeeButtonComponent,
    MeeCardComponent,
    LoadingSkeletonComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    MeeAlertBannerComponent,
    EmptyStateComponent,
  ],
  template: `
    <div class="mee-catalog-list-page">

      <!-- Page header: title + Create button -->
      <mee-page-header
        title="My Catalogs"
        cta_label="Create New Catalog"
        cta_icon="auto_awesome"
        (cta_click)="onCreate()"
      />

      <!-- Loading state: 3 skeleton cards -->
      @if (loading()) {
        <div class="mee-catalog-list-grid" aria-busy="true" aria-label="Loading products">
          <mee-loading-skeleton variant="card" />
          <mee-loading-skeleton variant="card" />
          <mee-loading-skeleton variant="card" />
        </div>
      }

      <!-- Error state -->
      @else if (error()) {
        <div class="mee-catalog-list-error">
          <mee-alert-banner
            variant="error"
            [message]="error()!"
          />
          <div class="mee-catalog-list-error-cta">
            <mee-button
              label="Retry"
              variant="secondary"
              (clicked)="onRetry()"
            />
          </div>
        </div>
      }

      <!-- Empty state -->
      @else if (products().length === 0) {
        <mee-empty-state
          icon="inventory_2"
          message="No products yet. Create your first catalog to get started."
          cta_label="Create First Catalog"
          (cta_click)="onCreate()"
        />
      }

      <!-- Product grid -->
      @else {
        <div class="mee-catalog-list-grid">
          @for (product of products(); track product.id) {
            <div
              class="mee-catalog-card"
              role="button"
              tabindex="0"
              [attr.aria-label]="'Open ' + product.name"
              (click)="onOpenProduct(product.id)"
              (keydown.enter)="onOpenProduct(product.id)"
              (keydown.space)="onOpenProduct(product.id)"
            >
              <mee-card>
                <div class="mee-catalog-card__body">
                  <div class="mee-catalog-card__meta">
                    <mee-status-badge [status]="product.status" />
                  </div>
                  <h2 class="mee-catalog-card__name" [title]="product.name">{{ product.name }}</h2>
                  <p class="mee-catalog-card__updated">
                    Updated {{ formatRelativeTime(product.updatedAt) }}
                  </p>
                </div>
              </mee-card>
            </div>
          }
        </div>
      }

    </div>
  `,
  styles: [`
    :host { display: block; }

    .mee-catalog-list-page {
      max-width: 1280px;
      margin: 0 auto;
      padding: var(--mee-space-4);
    }

    /* Grid: 1 col mobile, 2 cols tablet, 3 cols desktop */
    .mee-catalog-list-grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: var(--mee-space-4);
      margin-top: var(--mee-space-6);
    }
    @media (min-width: 640px) {
      .mee-catalog-list-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
    @media (min-width: 1024px) {
      .mee-catalog-list-grid {
        grid-template-columns: repeat(3, 1fr);
      }
    }

    /* Product card wrapper */
    .mee-catalog-card {
      cursor: pointer;
      outline: none;
      border-radius: var(--mee-radius-md);
      transition: box-shadow var(--mee-transition-fast), transform var(--mee-transition-fast);
    }
    .mee-catalog-card:hover {
      box-shadow: var(--mee-shadow-lg);
      transform: translateY(-2px);
    }
    .mee-catalog-card:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
    }

    /* Card body (projected into mee-card) */
    .mee-catalog-card__body {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
      min-height: 120px;
      /* Ensure 44px touch target height minimum */
      min-height: max(120px, 44px);
    }
    .mee-catalog-card__meta {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
    }
    .mee-catalog-card__name {
      font-size: 1rem;
      font-weight: 500;
      color: var(--mee-color-on-surface);
      margin: 0;
      /* Truncate long names */
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .mee-catalog-card__updated {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
      margin: 0;
    }

    /* Error state */
    .mee-catalog-list-error {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
      margin-top: var(--mee-space-6);
    }
    .mee-catalog-list-error-cta {
      display: flex;
      justify-content: center;
    }

    /* Tablet+ padding */
    @media (min-width: 768px) {
      .mee-catalog-list-page {
        padding: var(--mee-space-6) var(--mee-space-8);
      }
    }
  `],
})
export class CatalogListComponent implements OnInit {
  private readonly api    = inject(CatalogListApiService);
  private readonly router = inject(Router);

  // Expose utility for template use
  readonly formatRelativeTime = formatRelativeTime;

  // Signals
  readonly loading  = signal(true);
  readonly products = signal<CatalogListItem[]>([]);
  readonly error    = signal<string | null>(null);

  ngOnInit(): void {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.listProducts({ page: 1, limit: 20 }).subscribe({
      next: (resp) => {
        this.products.set(resp.items);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Failed to load your catalogs. Check your connection and retry.');
        this.loading.set(false);
      },
    });
  }

  onRetry(): void {
    this.load();
  }

  onCreate(): void {
    void this.router.navigate(['/catalogs', 'new']);
  }

  onOpenProduct(id: string): void {
    void this.router.navigate(['/catalogs', id, 'edit']);
  }
}
