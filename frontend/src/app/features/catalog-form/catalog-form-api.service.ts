// features/catalog-form/catalog-form-api.service.ts
// Feature-scoped service: product CRUD + schema + autofill per §11.C

import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { ApiClient } from '@core/api/api-client.service';
import { Product, FieldValue } from '@core/models/product.model';
import { CategorySchema } from '@core/models/category.model';

@Injectable()
export class CatalogFormApiService {
  private readonly api = inject(ApiClient);

  /** GET /api/v1/categories/:id/schema */
  getSchema(categoryId: string): Observable<CategorySchema> {
    return this.api.get<CategorySchema>(`/categories/${categoryId}/schema`);
  }

  /** GET /api/v1/products/:id */
  getProduct(productId: string): Observable<Product> {
    return this.api.get<Product>(`/products/${productId}`);
  }

  /** GET /api/v1/products/:id/draft — draft recovery on browser reload */
  getDraft(productId: string): Observable<Product> {
    return this.api.get<Product>(`/products/${productId}/draft`);
  }

  /** PATCH /api/v1/products/:id — autosave */
  patchProduct(productId: string, fields: Record<string, FieldValue>): Observable<Product> {
    return this.api.patch<Product>(`/products/${productId}`, { fields });
  }

  /** POST /api/v1/products/:id/autofill — AI autofill */
  autofill(productId: string): Observable<Product> {
    return this.api.post<Product>(`/products/${productId}/autofill`, {}, {
      retryOn503: true,
    });
  }

  /** GET /api/v1/categories/:id/enum/:fieldName?q= — dropdown_api search */
  lookupEnum(categoryId: string, fieldName: string, query: string): Observable<string[]> {
    return this.api.get<string[]>(`/categories/${categoryId}/enum/${fieldName}`, {
      params: { q: query },
    });
  }
}
