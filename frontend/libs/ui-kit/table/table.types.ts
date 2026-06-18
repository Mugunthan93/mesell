export interface MeeColumn {
  field: string;
  header: string;
  sortable?: boolean;
  width?: string;
}

export interface MeeTablePageEvent {
  first: number;
  rows: number;
}

export interface MeeTableSortEvent {
  field: string;
  order: number;
}

/**
 * Emitted on every lazy load trigger — page change, sort, or filter.
 * Parent uses this to fetch the next page from the server.
 */
export interface MeeTableLazyEvent {
  first: number;
  rows: number;
  sortField?: string;
  sortOrder?: number;    // 1 = ASC, -1 = DESC
  globalFilter?: string;
}
