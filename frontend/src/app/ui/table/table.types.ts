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
