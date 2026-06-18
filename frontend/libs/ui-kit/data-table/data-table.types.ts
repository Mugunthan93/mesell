import type { MeeBadgeSeverity } from '../badge/badge.types';
import type { MeeMenuItem } from '../menu/menu.types';
import type { MeeIconName } from '../icon/icon.registry';

interface MeeDataTableColumnBase {
  field: string;
  header: string;
  sortable?: boolean;        // default false
  width?: string;            // e.g. '120px' | '20%'; default 'auto'
  align?: 'left' | 'center' | 'right';  // default 'left'
}

export interface MeeDataTableTextColumn extends MeeDataTableColumnBase {
  kind: 'text';
  truncate?: boolean;
}

export interface MeeDataTableStatusColumn extends MeeDataTableColumnBase {
  kind: 'status';
  statusMap: Record<string, MeeBadgeSeverity>;
  labelMap?: Record<string, string>;
}

export interface MeeDataTableActionsColumn extends MeeDataTableColumnBase {
  kind: 'actions';
  actions: (row: unknown) => MeeMenuItem[];
}

export type MeeDataTableColumn =
  | MeeDataTableTextColumn
  | MeeDataTableStatusColumn
  | MeeDataTableActionsColumn;

export interface MeeDataTableBulkAction {
  label: string;
  action: string;
  icon?: MeeIconName;
  severity?: 'danger' | 'default';
}

export interface MeeDataTablePageEvent  { page: number; size: number; }
export interface MeeDataTableSortEvent  { field: string; order: 1 | -1; }
export interface MeeDataTableBulkActionEvent { action: string; rows: unknown[]; }
