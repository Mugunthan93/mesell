// core/models/paginated-response.model.ts
// Generic paginated API response shape per §4.I + CLAUDE.md API design

export interface PaginatedResponse<T> {
  readonly data: readonly T[];
  readonly total: number;
  readonly page: number;
  readonly limit: number;
}
