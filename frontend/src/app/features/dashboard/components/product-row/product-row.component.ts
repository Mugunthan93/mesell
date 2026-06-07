// features/dashboard/components/product-row/product-row.component.ts
// Presentational action-menu component for DashboardComponent's MatTable actions column.
// Emits editRequest and deleteRequest to parent — no dialog or HTTP calls here.
//
// Template pattern: pass row() as a parameter to click handlers rather than reading
// the input.required() signal inside the handlers. This avoids Angular's NG0950 when
// the mat-menu items are rendered in a CDK overlay embedded view context.

import {
  ChangeDetectionStrategy,
  Component,
  input,
  output,
} from '@angular/core';

import { MatIconButton } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';

import { TranslocoModule } from '@jsverse/transloco';

import { ProductListItem } from '../../dashboard-api.service';

@Component({
  selector: 'mee-product-row',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MatIconButton,
    MatIconModule,
    MatMenuModule,
    TranslocoModule,
  ],
  styleUrl: './product-row.component.scss',
  template: `
    <!-- 44 px touch target is provided by mat-icon-button (inherits 40px + 4px ripple) -->
    <button
      mat-icon-button
      [matMenuTriggerFor]="rowMenu"
      [attr.aria-label]="'dashboard.row.actions' | transloco"
    >
      <mat-icon>more_vert</mat-icon>
    </button>

    <mat-menu #rowMenu="matMenu">
      <!-- row() is evaluated in the template context (where the signal is bound)
           and passed as a value parameter to the method — avoids NG0950 in CDK overlays -->
      <button mat-menu-item (click)="onEdit(row())">
        <mat-icon>edit</mat-icon>
        <span>{{ 'dashboard.row.edit' | transloco }}</span>
      </button>
      <button
        mat-menu-item
        class="mee-action--destructive"
        (click)="onDeleteRequest(row())"
      >
        <mat-icon>delete_outline</mat-icon>
        <span>{{ 'dashboard.row.delete' | transloco }}</span>
      </button>
    </mat-menu>
  `,
})
export class ProductRowComponent {
  /** The product row data passed from the parent MatTable row. */
  readonly row = input.required<ProductListItem>();

  /** Emitted when the Edit menu item is clicked. */
  readonly editRequest = output<ProductListItem>();

  /** Emitted when the Delete menu item is clicked.
   *  The parent is responsible for opening the ConfirmDialog and calling deleteProduct(). */
  readonly deleteRequest = output<ProductListItem>();

  /** Called from the Edit menu item. Receives the row value from the template. */
  onEdit(row: ProductListItem): void {
    this.editRequest.emit(row);
  }

  /** Called from the Delete menu item. Receives the row value from the template.
   *  The parent handles the confirm dialog and API call. */
  onDeleteRequest(row: ProductListItem): void {
    this.deleteRequest.emit(row);
  }
}
