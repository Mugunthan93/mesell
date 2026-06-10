import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { delay } from 'rxjs/operators';

import {
  ProductListItem,
  ProductListResponse,
  StatusCounts,
  LoadProductsParams,
  deriveStatusCounts,
  filterProducts,
} from '../dashboard.model';

// Re-export types for consumers (dashboard.component.ts) that already import from this path.
export type { ProductListItem, ProductListResponse, StatusCounts, LoadProductsParams };

const SEED_PRODUCTS: ProductListItem[] = [
  {
    id: 'prod-001',
    name: 'Kurti Ethnic Floral Print - Women',
    category_name: 'Ethnic Wear',
    status: 'draft',
    updated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'prod-002',
    name: 'Salwar Suit Embroidered Cotton',
    category_name: 'Ethnic Wear',
    status: 'live',
    updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'prod-003',
    name: 'Tops Casual Solid Color V-Neck',
    category_name: 'Tops',
    status: 'ready',
    updated_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'prod-004',
    name: 'Lehenga Choli Festive Zari Work',
    category_name: 'Ethnic Wear',
    status: 'exported',
    updated_at: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000).toISOString(),
  },
  {
    id: 'prod-005',
    name: 'Kurti Anarkali Long Georgette',
    category_name: 'Ethnic Wear',
    status: 'draft',
    updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
  },
];

/**
 * Feature-scoped service — NOT providedIn: 'root'.
 * Provided via DashboardComponent providers[] in the component decorator.
 * Simulates GET /api/v1/products with seed data for Wave 5.
 */
@Injectable()
export class DashboardApiService {

  loadProducts(params: LoadProductsParams): Observable<ProductListResponse> {
    const filtered = filterProducts(SEED_PRODUCTS, params);
    const total = filtered.length;
    const limit = params.limit ?? 20;
    const start = (params.page - 1) * limit;
    const products = filtered.slice(start, start + limit);

    return of({ products, total, page: params.page }).pipe(delay(800));
  }

  deleteProduct(_id: string): Observable<null> {
    return of(null).pipe(delay(500));
  }

  deriveStatusCounts(products: ProductListItem[]): StatusCounts {
    return deriveStatusCounts(products);
  }
}
