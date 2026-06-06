// features/dashboard/dashboard/dashboard.component.ts
// /dashboard page — paginated product table with filter chips + debounced search
// per FRONTEND_ARCHITECTURE.md §9

import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';

import { MatTableModule } from '@angular/material/table';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { TranslocoModule, TranslocoService } from '@jsverse/transloco';

import { debounceTime, distinctUntilChanged, catchError } from 'rxjs/operators';
import { EMPTY } from 'rxjs';

import { ErrorService } from '@core/services/error.service';
import { StatusBadgeComponent } from '@shared/components/status-badge/status-badge.component';
import { EmptyStateComponent } from '@shared/components/empty-state/empty-state.component';
import { RelativeTimePipe } from '@shared/pipes/relative-time.pipe';
import { StatCardComponent } from '@shared/components/stat-card/stat-card.component';

import {
  DashboardApiService,
  ProductListItem,
} from '../dashboard-api.service';

type StatusFilter = 'draft' | 'ready' | 'exported';

@Component({
  selector: 'mee-dashboard',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    // Angular
    ReactiveFormsModule,
    RouterLink,
    // Material
    MatTableModule,
    MatPaginatorModule,
    MatChipsModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatProgressSpinnerModule,
    // i18n
    TranslocoModule,
    // Shared UI
    StatusBadgeComponent,
    EmptyStateComponent,
    RelativeTimePipe,
    StatCardComponent,
  ],
  template: `
    <div class="mee-dashboard-page">

      <!-- Page header -->
      <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:20px;">
        <div>
          <h1 style="font-size:22px; font-weight:700; color:#1F2937; margin:0;">My Catalogs</h1>
          <p style="font-size:13px; color:#6B7280; margin:4px 0 0;">Manage and export your product listings</p>
        </div>
        <a routerLink="/catalogs/new" style="background:#F26B23; color:#fff; border:none; border-radius:8px; padding:10px 18px; font-size:13px; font-weight:600; cursor:pointer; text-decoration:none; display:inline-flex; align-items:center; gap:6px;">
          + New Catalog
        </a>
      </div>

      <!-- KPI stat cards row -->
      <div style="display:grid; grid-template-columns:repeat(auto-fill,minmax(160px,1fr)); gap:16px; margin-bottom:24px;">
        <mee-stat-card
          label="Total Catalogs"
          value="24"
          icon="folder_open"
          color="orange"
          trendLabel="+3 this week"
          trend="up"
        ></mee-stat-card>
        <mee-stat-card
          label="Active"
          value="8"
          icon="check_circle"
          color="green"
          trendLabel="2 new"
          trend="up"
        ></mee-stat-card>
        <mee-stat-card
          label="Draft"
          value="14"
          icon="edit_note"
          color="blue"
        ></mee-stat-card>
        <mee-stat-card
          label="Exports"
          value="3"
          icon="download"
          color="purple"
          trendLabel="this month"
          trend="neutral"
        ></mee-stat-card>
      </div>

      <!-- Profile completeness banner -->
      @if (!profileComplete()) {
        <div class="mee-profile-banner" role="alert">
          {{ 'dashboard.profileBanner.message' | transloco }}
          <a routerLink="/profile" class="mee-profile-banner__link">
            {{ 'dashboard.profileBanner.link' | transloco }} →
          </a>
        </div>
      }

      <!-- Filter chips + search bar -->
      <div class="mee-dashboard-toolbar">
        <mat-chip-listbox
          class="mee-filter-chips"
          [attr.aria-label]="'dashboard.filter.all' | transloco"
          (change)="onStatusChange($event.value)"
        >
          <mat-chip-option
            value=""
            [selected]="!activeStatus()"
            class="mee-chip"
          >{{ 'dashboard.filter.all' | transloco }}</mat-chip-option>

          <mat-chip-option
            value="draft"
            [selected]="activeStatus() === 'draft'"
            class="mee-chip"
          >{{ 'dashboard.filter.draft' | transloco }}</mat-chip-option>

          <mat-chip-option
            value="ready"
            [selected]="activeStatus() === 'ready'"
            class="mee-chip"
          >{{ 'dashboard.filter.ready' | transloco }}</mat-chip-option>

          <mat-chip-option
            value="exported"
            [selected]="activeStatus() === 'exported'"
            class="mee-chip"
          >{{ 'dashboard.filter.exported' | transloco }}</mat-chip-option>
        </mat-chip-listbox>

        <mat-form-field class="mee-search-field" appearance="outline" subscriptSizing="dynamic">
          <mat-icon matPrefix>search</mat-icon>
          <input
            matInput
            [formControl]="searchCtrl"
            [placeholder]="'dashboard.search.placeholder' | transloco"
            autocomplete="off"
          />
        </mat-form-field>
      </div>

      <!-- Loading spinner -->
      @if (loading()) {
        <div class="mee-spinner-container" aria-label="Loading catalogs">
          <mat-spinner diameter="32"></mat-spinner>
        </div>
      }

      <!-- Content area (hidden while loading) -->
      @if (!loading()) {
        @if (hasProducts()) {
          <!-- Product table -->
          <table
            mat-table
            [dataSource]="products()"
            class="mee-product-table"
            aria-label="Product catalog list"
          >
            <!-- Name column -->
            <ng-container matColumnDef="name">
              <th mat-header-cell *matHeaderCellDef>
                {{ 'dashboard.table.name' | transloco }}
              </th>
              <td mat-cell *matCellDef="let row" class="mee-cell--name">
                {{ displayName(row) }}
              </td>
            </ng-container>

            <!-- Status column -->
            <ng-container matColumnDef="status">
              <th mat-header-cell *matHeaderCellDef>
                {{ 'dashboard.table.status' | transloco }}
              </th>
              <td mat-cell *matCellDef="let row" class="mee-cell--status">
                <mee-status-badge [status]="row.status"></mee-status-badge>
              </td>
            </ng-container>

            <!-- Updated at column -->
            <ng-container matColumnDef="updatedAt">
              <th mat-header-cell *matHeaderCellDef>
                {{ 'dashboard.table.updated' | transloco }}
              </th>
              <td mat-cell *matCellDef="let row" class="mee-cell--updated">
                {{ row.updated_at | relativeTime }}
              </td>
            </ng-container>

            <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
            <tr
              mat-row
              *matRowDef="let row; columns: displayedColumns"
              class="mee-product-row"
              (click)="navigateToEdit(row)"
              [attr.aria-label]="'Edit ' + (row.name ?? 'Untitled')"
              tabindex="0"
              (keydown.enter)="navigateToEdit(row)"
              (keydown.space)="$event.preventDefault(); navigateToEdit(row)"
            ></tr>
          </table>

          <mat-paginator
            class="mee-paginator"
            [length]="totalCount()"
            [pageSize]="pageSize()"
            [pageIndex]="currentPage() - 1"
            [pageSizeOptions]="[10, 20, 50]"
            [showFirstLastButtons]="false"
            (page)="onPageChange($event)"
            [attr.aria-label]="'Product catalog pagination'"
          ></mat-paginator>

        } @else if (isEmptyWithNoFilter()) {
          <!-- True empty state — no products at all -->
          <mee-empty-state
            icon="folder_open"
            [headline]="'dashboard.empty.headline' | transloco"
            [body]="'dashboard.empty.body' | transloco"
            [ctaLabel]="'dashboard.empty.cta' | transloco"
            (ctaClick)="navigateToCreate()"
          ></mee-empty-state>

        } @else {
          <!-- No results for current filter/search -->
          <p class="mee-no-results">
            {{ 'dashboard.noResults' | transloco }}
          </p>
        }
      }

    </div>
  `,
})
export class DashboardComponent implements OnInit {
  // ── DI ──
  private readonly dashboardApi = inject(DashboardApiService);
  private readonly errorService = inject(ErrorService);
  private readonly router = inject(Router);
  private readonly transloco = inject(TranslocoService);

  // ── Local signals ──
  readonly products = signal<ProductListItem[]>([]);
  readonly loading = signal(true);
  readonly totalCount = signal(0);
  readonly currentPage = signal(1);
  readonly pageSize = signal(20);
  readonly activeStatus = signal<StatusFilter | null>(null);
  readonly searchQuery = signal<string | null>(null);
  readonly profileCompleteness = signal<{ profile_complete: boolean } | null>(null);

  // ── Computed helpers ──
  readonly hasProducts = computed(() => this.products().length > 0);

  readonly isEmptyWithNoFilter = computed(
    () => this.totalCount() === 0 && !this.activeStatus() && !this.searchQuery(),
  );

  readonly profileComplete = computed(
    () => this.profileCompleteness()?.profile_complete ?? true,
  );

  // ── Form control for search (with debounce via RxJS) ──
  readonly searchCtrl = new FormControl<string>('', { nonNullable: true });

  // ── Table config ──
  readonly displayedColumns: string[] = ['name', 'status', 'updatedAt'];

  constructor() {
    // Wire search control with debounce — takeUntilDestroyed auto-unsubscribes
    this.searchCtrl.valueChanges
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        takeUntilDestroyed(),
      )
      .subscribe((value) => {
        this.searchQuery.set(value.trim() || null);
        this.currentPage.set(1);
        this.loadProducts();
      });
  }

  ngOnInit(): void {
    this.loadProducts();
  }

  // ── Event handlers ──

  onStatusChange(value: string | null | undefined): void {
    const status = (value as StatusFilter) || null;
    this.activeStatus.set(status);
    this.currentPage.set(1);
    this.loadProducts();
  }

  onPageChange(event: PageEvent): void {
    this.currentPage.set(event.pageIndex + 1);
    this.pageSize.set(event.pageSize);
    this.loadProducts();
  }

  /** Returns the display name for a product row, falling back to the i18n "Untitled" label. */
  displayName(row: ProductListItem): string {
    return row.name || this.transloco.translate('dashboard.table.untitled');
  }

  navigateToEdit(row: ProductListItem): void {
    this.router.navigate(['/catalogs', row.product_id, 'edit']);
  }

  navigateToCreate(): void {
    this.router.navigate(['/catalogs/new']);
  }

  // ── Data loading ──

  loadProducts(): void {
    this.loading.set(true);

    this.dashboardApi
      .listProducts({
        page: this.currentPage(),
        limit: this.pageSize(),
        status_filter: this.activeStatus(),
        search: this.searchQuery(),
      })
      .pipe(
        catchError((err) => {
          this.errorService.showError(err?.displayMessage ?? 'Failed to load products');
          this.loading.set(false);
          return EMPTY;
        }),
      )
      .subscribe((response) => {
        this.products.set(response.products);
        this.totalCount.set(response.total);
        this.profileCompleteness.set(response.profile_completeness);
        this.loading.set(false);
      });
  }
}
