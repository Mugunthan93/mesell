import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { TableModule, TablePageEvent } from 'primeng/table';
import type { TableLazyLoadEvent } from 'primeng/types/table';
import type { SortMeta } from 'primeng/api';
import type { MeeColumn, MeeTablePageEvent, MeeTableSortEvent, MeeTableLazyEvent } from './table.types';

@Component({
  selector: 'mee-table',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TableModule],
  styles: [`
    :host { display: block; }
    .mee-tr-row {
      cursor: pointer;
    }
    ::ng-deep .mee-tr-row > td { min-height: 44px; }
    .mee-td-empty {
      text-align: center;
      padding-block: var(--mee-space-8);
      color: var(--mee-color-on-surface-muted);
    }
  `],
  template: `
    <p-table
      [value]="rows()"
      [loading]="loading()"
      [paginator]="paginator()"
      [rows]="rows_per_page()"
      [totalRecords]="total_records() ?? 0"
      [rowHover]="true"
      [lazy]="lazy()"
      [scrollable]="!!scrollHeight()"
      [scrollHeight]="scrollHeight() ?? ''"
      [virtualScroll]="virtualScroll()"
      [virtualScrollItemSize]="virtualRowHeight()"
      (onPage)="onPage($event)"
      (onSort)="onSort($event)"
      (onLazyLoad)="onLazyLoad($event)"
    >
      <ng-template pTemplate="header">
        <tr>
          @for (col of columns(); track col.field) {
            <th
              [pSortableColumn]="col.sortable ? col.field : ''"
              [style.width]="col.width ?? 'auto'"
            >
              {{ col.header }}
            </th>
          }
        </tr>
      </ng-template>
      <ng-template pTemplate="body" let-rowData>
        <tr
          class="mee-tr-row"
          (click)="row_click.emit(rowData)"
          tabindex="0"
          (keydown.enter)="row_click.emit(rowData)"
        >
          @for (col of columns(); track col.field) {
            <td>{{ rowData[col.field] }}</td>
          }
        </tr>
      </ng-template>
      <ng-template pTemplate="emptymessage">
        <tr>
          <td [attr.colspan]="columns().length" class="mee-td-empty">
            {{ empty_message() }}
          </td>
        </tr>
      </ng-template>
    </p-table>
  `,
})
export class MeeTableComponent {
  readonly columns = input.required<MeeColumn[]>();
  readonly rows = input.required<unknown[]>();
  readonly loading = input<boolean>(false);
  readonly paginator = input<boolean>(false);
  readonly rows_per_page = input<number>(10);
  readonly total_records = input<number | undefined>(undefined);
  readonly empty_message = input<string>('No data found');

  /**
   * Enable server-side lazy mode.
   * When true: disables client-side pagination/sort/filter.
   * p-table fires (onLazyLoad) → mee-table emits (lazy_load) output.
   */
  readonly lazy = input<boolean>(false);
  /**
   * Fixed height for the scrollable table body (e.g. '400px', '60vh').
   * Required for virtual scroll. Leave undefined for auto height.
   */
  readonly scrollHeight = input<string | undefined>(undefined);
  /**
   * Enable row virtualization — only renders visible rows in DOM.
   * REQUIRES scrollHeight to be set. Use for 100+ row tables.
   */
  readonly virtualScroll = input<boolean>(false);
  /**
   * Exact row height in px — must match the actual rendered row height.
   * Default 44px matches our min-height: 44px rule on mee-tr-row > td.
   */
  readonly virtualRowHeight = input<number>(44);

  readonly row_click = output<unknown>();
  readonly page = output<MeeTablePageEvent>();
  readonly sort = output<MeeTableSortEvent>();
  /**
   * Fires on page/sort/filter when lazy=true.
   * Parent calls the API with these params and updates [rows] + [total_records].
   */
  readonly lazy_load = output<MeeTableLazyEvent>();

  onPage(event: TablePageEvent): void {
    this.page.emit({ first: event.first, rows: event.rows });
  }

  onSort(event: { field?: string; order?: number; multisortmeta?: SortMeta[] }): void {
    if (event.field) {
      this.sort.emit({ field: event.field, order: event.order ?? 1 });
    }
  }

  onLazyLoad(event: TableLazyLoadEvent): void {
    this.lazy_load.emit({
      first: event.first ?? 0,
      rows: event.rows ?? this.rows_per_page(),
      sortField: Array.isArray(event.sortField) ? event.sortField[0] : event.sortField ?? undefined,
      sortOrder: event.sortOrder ?? undefined,
      globalFilter: (Array.isArray(event.globalFilter) ? event.globalFilter[0] : event.globalFilter) ?? '',
    });
  }
}
