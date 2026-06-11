import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
  output,
} from '@angular/core';
import { TableModule, TablePageEvent } from 'primeng/table';
import type { SortMeta } from 'primeng/api';
import type { MeeColumn, MeeTablePageEvent, MeeTableSortEvent } from './table.types';

@Component({
  selector: 'mee-table',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [TableModule],
  template: `
    <p-table
      [value]="rows()"
      [loading]="loading()"
      [paginator]="paginator()"
      [rows]="rows_per_page()"
      [totalRecords]="total_records() ?? 0"
      [rowHover]="true"
      (onPage)="onPage($event)"
      (onSort)="onSort($event)"
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
          class="cursor-pointer"
          style="min-height: 44px;"
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
          <td [attr.colspan]="columns().length" class="text-center py-8" style="color: var(--mee-color-on-surface-muted)">
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

  readonly row_click = output<unknown>();
  readonly page = output<MeeTablePageEvent>();
  readonly sort = output<MeeTableSortEvent>();

  onPage(event: TablePageEvent): void {
    this.page.emit({ first: event.first, rows: event.rows });
  }

  onSort(event: { field?: string; order?: number; multisortmeta?: SortMeta[] }): void {
    if (event.field) {
      this.sort.emit({ field: event.field, order: event.order ?? 1 });
    }
  }
}
