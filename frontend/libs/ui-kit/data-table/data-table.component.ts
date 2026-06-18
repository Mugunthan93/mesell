import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
  output,
  signal,
  viewChildren,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { debounceTime, distinctUntilChanged } from 'rxjs/operators';
import { TableModule } from 'primeng/table';
import type { TableLazyLoadEvent } from 'primeng/types/table';

import { MeeInputComponent } from '../input/input.component';
import { MeeBadgeComponent } from '../badge/badge.component';
import { MeeIconComponent } from '../icon/icon.component';
import { MeeButtonComponent } from '../button/button.component';
import { MeeMenuComponent } from '../menu/menu.component';
import { MeeSpinnerComponent } from '../spinner/spinner.component';
import { MeeSkeletonComponent } from '../skeleton/skeleton.component';

import type {
  MeeDataTableColumn,
  MeeDataTableActionsColumn,
  MeeDataTableBulkAction,
  MeeDataTablePageEvent,
  MeeDataTableSortEvent,
  MeeDataTableBulkActionEvent,
} from './data-table.types';
import type { MeeIconName } from '../icon/icon.registry';
import type { MeeMenuItem } from '../menu/menu.types';

/** Tracks the last-emitted page/sort state to avoid duplicate initial-fetch emissions. */
interface LastEmitted {
  first: number;
  rows: number;
  sortField: string | undefined;
  sortOrder: number | undefined;
}

@Component({
  selector: 'mee-data-table',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    TableModule,
    FormsModule,
    ReactiveFormsModule,
    MeeInputComponent,
    MeeBadgeComponent,
    MeeIconComponent,
    MeeButtonComponent,
    MeeMenuComponent,
    MeeSpinnerComponent,
    MeeSkeletonComponent,
  ],
  styles: [`
    :host { display: block; }

    .mee-dt-search {
      margin-bottom: var(--mee-space-4);
    }
    .mee-dt-search mee-input {
      display: block;
      width: 100%;
    }
    @media (min-width: 768px) {
      .mee-dt-search mee-input {
        max-width: 360px;
      }
    }

    .mee-td-truncate {
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      display: inline-block;
    }

    .mee-td-empty {
      text-align: center;
      padding-block: var(--mee-space-10, 2.5rem);
      color: var(--mee-color-on-surface-muted);
    }

    .mee-dt-skeleton {
      padding: var(--mee-space-2);
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);
    }

    /* Bulk action bar */
    .mee-dt-bulk-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--mee-space-3);
      padding: var(--mee-space-3) var(--mee-space-4);
      background: var(--mee-color-surface-overlay, rgba(255,255,255,0.96));
      box-shadow: 0 -2px 12px rgba(0,0,0,0.12);
      z-index: 200;
      position: sticky;
      bottom: 0;
    }

    @media (max-width: 640px) {
      .mee-dt-bulk-bar {
        position: fixed;
        left: 0;
        right: 0;
        bottom: 0;
        padding-bottom: max(var(--mee-space-3), env(safe-area-inset-bottom));
        animation: mee-bulk-slide-up 180ms ease-out;
      }
    }

    @media (prefers-reduced-motion: reduce) {
      .mee-dt-bulk-bar {
        animation: none;
      }
    }

    @keyframes mee-bulk-slide-up {
      from { transform: translateY(100%); }
      to   { transform: translateY(0); }
    }

    .mee-dt-bulk-left {
      display: flex;
      align-items: center;
      gap: var(--mee-space-3);
      color: var(--mee-color-on-surface);
      font-size: 0.875rem;
    }
    .mee-dt-bulk-right {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
    }
    .mee-dt-clear-btn {
      background: none;
      border: none;
      cursor: pointer;
      color: var(--mee-color-on-surface-muted);
      min-height: 44px;
      min-width: 44px;
      padding: 0 var(--mee-space-2);
      font-size: 0.875rem;
      text-decoration: underline;
    }
    .mee-dt-clear-btn:hover {
      color: var(--mee-color-on-surface);
    }

    /* Row styles */
    ::ng-deep .mee-dt-row {
      cursor: pointer;
    }
    ::ng-deep .mee-dt-row > td {
      min-height: 44px;
    }

    .mee-dt-kebab-trigger {
      background: none;
      border: none;
      cursor: pointer;
      min-height: 44px;
      min-width: 44px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--mee-radius-sm, 4px);
      color: var(--mee-color-on-surface-muted);
    }
    .mee-dt-kebab-trigger:hover {
      background: var(--mee-color-surface-variant);
    }
  `],
  template: `
    <!-- 1. Search bar -->
    @if (searchable()) {
      <div class="mee-dt-search" role="search">
        <mee-input
          [placeholder]="search_placeholder()"
          [formControl]="searchCtrl"
        />
      </div>
    }

    <!-- 2. First-load skeleton (replaces table while loading with no data yet) -->
    @if (loading() && rows().length === 0) {
      <div class="mee-dt-skeleton" role="status" aria-label="Loading data">
        @for (i of skeletonRows; track i) {
          <mee-skeleton variant="table-row" />
        }
      </div>
    } @else {
      <!-- 3. Main p-table -->
      <p-table
        [value]="rows()"
        [loading]="loading() && rows().length > 0"
        [lazy]="true"
        [paginator]="true"
        [rows]="page_size()"
        [totalRecords]="total_records()"
        [rowHover]="true"
        [dataKey]="row_key()"
        (onLazyLoad)="onLazyLoad($event)"
      >
        <!-- Header -->
        <ng-template pTemplate="header">
          <tr>
            @if (selectionEnabled()) {
              <th
                scope="col"
                style="width: 44px;"
                aria-label="Select all"
              >
                <input
                  type="checkbox"
                  [checked]="allSelected()"
                  [indeterminate]="someSelected()"
                  (change)="toggleSelectAll($event)"
                  (click)="$event.stopPropagation()"
                  aria-label="Select all rows on this page"
                  style="width: 18px; height: 18px; cursor: pointer;"
                />
              </th>
            }
            @for (col of columns(); track col.field) {
              <th
                scope="col"
                [style.width]="col.width ?? 'auto'"
                [style.textAlign]="col.align ?? 'left'"
                [pSortableColumn]="isSortableCol(col) ? col.field : ''"
                [attr.aria-sort]="getColSortAriaLabel(col.field)"
              >
                {{ col.header }}
                @if (isSortableCol(col)) {
                  <p-sortIcon [field]="col.field" />
                }
              </th>
            }
          </tr>
        </ng-template>

        <!-- Body -->
        <ng-template pTemplate="body" let-rowData>
          <tr
            class="mee-dt-row"
            tabindex="0"
            (click)="emitRowClick(rowData)"
            (keydown.enter)="emitRowClick(rowData)"
            (keydown.space)="onRowSpaceKey($event, rowData)"
            [attr.aria-selected]="selectionEnabled() ? isSelected(rowData) : null"
          >
            @if (selectionEnabled()) {
              <td (click)="$event.stopPropagation()" style="width: 44px;">
                <input
                  type="checkbox"
                  [checked]="isSelected(rowData)"
                  (change)="toggleRowSelection(rowData)"
                  [attr.aria-label]="'Select row'"
                  style="width: 18px; height: 18px; cursor: pointer;"
                />
              </td>
            }
            @for (col of columns(); track col.field) {
              <td
                [style.textAlign]="col.align ?? 'left'"
              >
                @switch (col.kind) {
                  @case ('text') {
                    @if (col.truncate) {
                      <span
                        class="mee-td-truncate"
                        [title]="asString(asRecord(rowData)[col.field])"
                      >{{ asString(asRecord(rowData)[col.field]) }}</span>
                    } @else {
                      {{ asString(asRecord(rowData)[col.field]) }}
                    }
                  }
                  @case ('status') {
                    @let statusVal = asString(asRecord(rowData)[col.field]);
                    <mee-badge
                      [value]="col.labelMap?.[statusVal] ?? statusVal"
                      [severity]="col.statusMap[statusVal] ?? 'neutral'"
                    />
                  }
                  @case ('actions') {
                    <span
                      style="display: inline-flex; position: relative;"
                      (click)="$event.stopPropagation()"
                    >
                      <button
                        type="button"
                        class="mee-dt-kebab-trigger"
                        [attr.aria-label]="'Row actions'"
                        (click)="openRowMenu($event, asActionsCol(col), rowData)"
                      >
                        <mee-icon name="ellipsis-v" />
                      </button>
                    </span>
                  }
                }
              </td>
            }
          </tr>
        </ng-template>

        <!-- Empty message -->
        <ng-template pTemplate="emptymessage">
          <tr>
            <td
              [attr.colspan]="columns().length + (selectionEnabled() ? 1 : 0)"
              class="mee-td-empty"
              role="status"
            >
              <mee-icon [name]="empty_icon()" />
              <div>{{ empty_message() }}</div>
            </td>
          </tr>
        </ng-template>
      </p-table>
    }

    <!-- Shared per-row actions popup (reused across rows; items set before toggle) -->
    <mee-menu #rowActionsMenu [items]="activeRowMenuItems()" />

    <!-- 4. Bulk action bar -->
    @if (selectionEnabled() && selectedCount() > 0) {
      <div
        class="mee-dt-bulk-bar"
        role="toolbar"
        [attr.aria-label]="selectedCount() + ' rows selected'"
      >
        <div class="mee-dt-bulk-left">
          <span>{{ selectedCount() }} selected</span>
          <button
            type="button"
            class="mee-dt-clear-btn"
            (click)="clearSelection()"
            aria-label="Clear selection"
          >
            Clear
          </button>
        </div>
        <div class="mee-dt-bulk-right">
          @for (a of bulk_actions(); track a.action) {
            <mee-button
              [label]="a.label"
              [variant]="a.severity === 'danger' ? 'danger' : 'secondary'"
              [icon]="a.icon"
              (clicked)="emitBulk(a.action)"
            />
          }
        </div>
      </div>
    }
  `,
})
export class MeeDataTableComponent implements OnInit {
  // ── Inputs ──────────────────────────────────────────────────────────────────
  readonly columns             = input.required<MeeDataTableColumn[]>();
  readonly rows                = input.required<unknown[]>();
  readonly total_records       = input<number>(0);
  readonly loading             = input<boolean>(false);
  readonly page_size           = input<number>(20);
  readonly searchable          = input<boolean>(false);
  readonly search_placeholder  = input<string>('Search...');
  readonly search_debounce_ms  = input<number>(300);
  readonly bulk_actions        = input<MeeDataTableBulkAction[]>([]);
  readonly empty_message       = input<string>('No data found');
  readonly empty_icon          = input<MeeIconName>('list');
  readonly row_key             = input<string>('id');

  // ── Outputs ─────────────────────────────────────────────────────────────────
  readonly page_change   = output<MeeDataTablePageEvent>();
  readonly sort_change   = output<MeeDataTableSortEvent>();
  readonly search_change = output<string>();
  readonly row_click     = output<unknown>();
  readonly bulk_action   = output<MeeDataTableBulkActionEvent>();

  // ── Internal state ──────────────────────────────────────────────────────────
  readonly selectionEnabled = computed(() => this.bulk_actions().length > 0);
  readonly selectedRows     = signal<unknown[]>([]);
  readonly selectedCount    = computed(() => this.selectedRows().length);

  readonly allSelected  = computed(() => {
    const r = this.rows();
    return r.length > 0 && this.selectedRows().length === r.length;
  });
  readonly someSelected = computed(() => {
    const cnt = this.selectedRows().length;
    return cnt > 0 && cnt < this.rows().length;
  });

  /** Menu items for the currently-open kebab row. */
  readonly activeRowMenuItems = signal<MeeMenuItem[]>([]);

  /** Ref to the shared <mee-menu #rowActionsMenu> popup. */
  private readonly rowMenuQueryList = viewChildren<MeeMenuComponent>('rowActionsMenu');

  /** Non-nullable search FormControl. */
  readonly searchCtrl = new FormControl<string>('', { nonNullable: true });

  /** Static skeleton placeholder row count. */
  readonly skeletonRows = [0, 1, 2, 3, 4];

  /** Last-emitted lazy params (avoids duplicate initial fetch on first load). */
  private lastEmitted: LastEmitted | null = null;

  private readonly destroyRef = inject(DestroyRef);

  // ── Lifecycle ────────────────────────────────────────────────────────────────
  ngOnInit(): void {
    // Read debounce_ms once at init time (spec requirement: "read once at construction").
    const debounceMs = this.search_debounce_ms();
    this.searchCtrl.valueChanges
      .pipe(
        debounceTime(debounceMs),
        distinctUntilChanged(),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((val) => this.search_change.emit(val));
  }

  // ── Lazy load handler ────────────────────────────────────────────────────────
  onLazyLoad(event: TableLazyLoadEvent): void {
    const first = event.first ?? 0;
    const rows  = event.rows ?? this.page_size();
    const sortField = Array.isArray(event.sortField)
      ? event.sortField[0]
      : (event.sortField ?? undefined);
    const sortOrder = event.sortOrder ?? undefined;

    const pageChanged = !this.lastEmitted
      || this.lastEmitted.first !== first
      || this.lastEmitted.rows  !== rows;

    const sortChanged = !this.lastEmitted
      || this.lastEmitted.sortField !== sortField
      || this.lastEmitted.sortOrder !== sortOrder;

    if (pageChanged) {
      const page = Math.floor(first / rows) + 1;
      this.page_change.emit({ page, size: rows });
      // Clear selection on page turn (spec: "clears on page_change").
      this.clearSelection();
    }

    if (sortChanged && sortField) {
      const order = (sortOrder === -1 ? -1 : 1) as 1 | -1;
      this.sort_change.emit({ field: sortField, order });
    }

    this.lastEmitted = { first, rows, sortField, sortOrder };
  }

  // ── Row interaction ──────────────────────────────────────────────────────────
  emitRowClick(rowData: unknown): void {
    this.row_click.emit(rowData);
  }

  onRowSpaceKey(event: Event, rowData: unknown): void {
    event.preventDefault();
    if (this.selectionEnabled()) {
      this.toggleRowSelection(rowData);
    } else {
      this.emitRowClick(rowData);
    }
  }

  // ── Selection ────────────────────────────────────────────────────────────────
  isSelected(rowData: unknown): boolean {
    const key = this.row_key();
    const rowVal = (rowData as Record<string, unknown>)[key];
    return this.selectedRows().some(
      (r) => (r as Record<string, unknown>)[key] === rowVal,
    );
  }

  toggleRowSelection(rowData: unknown): void {
    if (this.isSelected(rowData)) {
      const key = this.row_key();
      const rowVal = (rowData as Record<string, unknown>)[key];
      this.selectedRows.update((rows) =>
        rows.filter((r) => (r as Record<string, unknown>)[key] !== rowVal),
      );
    } else {
      this.selectedRows.update((rows) => [...rows, rowData]);
    }
  }

  toggleSelectAll(event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    this.selectedRows.set(checked ? [...this.rows()] : []);
  }

  clearSelection(): void {
    this.selectedRows.set([]);
  }

  // ── Bulk actions ─────────────────────────────────────────────────────────────
  emitBulk(action: string): void {
    this.bulk_action.emit({ action, rows: [...this.selectedRows()] });
  }

  // ── Row kebab menu ───────────────────────────────────────────────────────────
  openRowMenu(
    event: MouseEvent,
    col: MeeDataTableActionsColumn,
    rowData: unknown,
  ): void {
    event.stopPropagation();
    this.activeRowMenuItems.set(col.actions(rowData));
    const menuRefs = this.rowMenuQueryList();
    if (menuRefs.length > 0) {
      menuRefs[0].toggle(event);
    }
  }

  // ── A11y helpers ─────────────────────────────────────────────────────────────
  getColSortAriaLabel(field: string): string {
    if (!this.lastEmitted?.sortField || this.lastEmitted.sortField !== field) {
      return 'none';
    }
    return this.lastEmitted.sortOrder === -1 ? 'descending' : 'ascending';
  }

  // ── Template helpers (type narrowing) ────────────────────────────────────────
  isSortableCol(col: MeeDataTableColumn): boolean {
    return col.kind !== 'actions' && (col.sortable ?? false);
  }

  asActionsCol(col: MeeDataTableColumn): MeeDataTableActionsColumn {
    return col as MeeDataTableActionsColumn;
  }

  asRecord(value: unknown): Record<string, unknown> {
    return value as Record<string, unknown>;
  }

  asString(value: unknown): string {
    if (value === null || value === undefined) return '';
    return String(value);
  }
}
