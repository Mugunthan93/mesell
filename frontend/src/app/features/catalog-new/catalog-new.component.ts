import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
  OnInit,
} from '@angular/core';
import {
  FormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { of } from 'rxjs';
import { delay } from 'rxjs/operators';

import {
  MeeButtonComponent,
  MeeCardComponent,
  MeeProgressBarComponent,
  MeeTextareaComponent,
  MeeTreeSelectComponent,
} from '../../ui';
import type { MeeTreeNode } from '../../ui';
import { PageHeaderComponent, LoadingSkeletonComponent } from '../../shared';

import {
  SmartPickerApiService,
  CategorySuggestion,
} from './services/smart-picker-api.service';

// Simulated 2-level category tree for manual fallback browse
const SIMULATED_TREE: MeeTreeNode[] = [
  {
    label: 'Fashion',
    value: null,
    children: [
      {
        label: 'Women',
        value: null,
        children: [
          { label: 'Kurti', value: 'cat-kurti-uuid' },
          { label: 'Kurta Set', value: 'cat-kurta-set-uuid' },
        ],
      },
      {
        label: 'Men',
        value: null,
        children: [
          { label: 'Kurta', value: 'cat-kurta-men-uuid' },
          { label: 'Shirt', value: 'cat-shirt-uuid' },
        ],
      },
    ],
  },
  {
    label: 'Home & Kitchen',
    value: null,
    children: [
      {
        label: 'Bedding',
        value: null,
        children: [
          { label: 'Bedsheets', value: 'cat-bedsheet-uuid' },
          { label: 'Pillow Covers', value: 'cat-pillow-uuid' },
        ],
      },
      {
        label: 'Decor',
        value: null,
        children: [
          { label: 'Wall Art', value: 'cat-wallart-uuid' },
          { label: 'Candles', value: 'cat-candles-uuid' },
        ],
      },
    ],
  },
  {
    label: 'Electronics',
    value: null,
    children: [
      {
        label: 'Accessories',
        value: null,
        children: [
          { label: 'Phone Cases', value: 'cat-phonecase-uuid' },
          { label: 'Chargers', value: 'cat-charger-uuid' },
        ],
      },
    ],
  },
];

@Component({
  selector: 'app-catalog-new',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MeeButtonComponent,
    MeeCardComponent,
    MeeProgressBarComponent,
    MeeTextareaComponent,
    MeeTreeSelectComponent,
    PageHeaderComponent,
    LoadingSkeletonComponent,
  ],
  providers: [SmartPickerApiService],
  template: `
    <div class="p-4 sm:p-6 max-w-4xl mx-auto">

      <!-- Page title -->
      <mee-page-header [title]="'New Catalog'" />

      <!-- Description form -->
      <form [formGroup]="form" (ngSubmit)="onSuggest()" class="mt-6">
        <mee-textarea
          formControlName="description"
          [label]="'Describe your product'"
          [placeholder]="'e.g. Blue cotton kurti with mirror work for women, size M to XXL'"
          [rows]="4"
          [required]="true"
          [error]="descError()"
        />

        <div class="mt-4">
          <mee-button
            [label]="'Suggest categories'"
            [loading]="suggesting()"
            [disabled]="form.invalid || suggesting()"
            [fullWidth]="true"
            (clicked)="onSuggest()"
          />
        </div>
      </form>

      <!-- Error message -->
      @if (errorMessage()) {
        <div
          role="alert"
          class="mt-3 text-sm px-3 py-2 rounded"
          style="color: var(--mee-color-error); background: color-mix(in srgb, var(--mee-color-error) 8%, transparent);"
        >
          {{ errorMessage() }}
        </div>
      }

      <!-- Divider + manual fallback toggle -->
      <div class="mt-6 flex items-center gap-3">
        <div class="flex-1 h-px" style="background: var(--mee-color-outline);"></div>
        <span class="text-sm" style="color: var(--mee-color-on-surface-muted);">OR browse manually</span>
        <div class="flex-1 h-px" style="background: var(--mee-color-outline);"></div>
      </div>

      <div class="mt-3">
        @if (!showFallback()) {
          <button
            type="button"
            class="text-sm underline min-h-[44px] px-2"
            style="color: var(--mee-color-primary); cursor: pointer; background: none; border: none;"
            (click)="onShowFallback()"
          >
            Browse all categories
          </button>
        } @else {
          <mee-tree-select
            [nodes]="categoryTree()"
            [placeholder]="'Select category'"
            [loading]="treeLoading()"
            (value_change)="onTreePick($event)"
          />
        }
      </div>

      <!-- Loading state (skeleton cards while suggesting) -->
      @if (suggesting()) {
        <div class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          <mee-loading-skeleton variant="card" />
          <mee-loading-skeleton variant="card" />
          <mee-loading-skeleton variant="card" />
        </div>
      }

      <!-- Suggestion cards -->
      @if (!suggesting() && suggestions().length > 0) {
        <div class="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-3">
          @for (suggestion of suggestions(); track suggestion.id) {
            <mee-card>
              <div class="flex flex-col gap-3 p-1">
                <p
                  class="text-sm font-semibold leading-snug"
                  style="color: var(--mee-color-on-surface);"
                >
                  {{ suggestion.path }}
                </p>

                <p class="text-xs" style="color: var(--mee-color-on-surface-muted);">
                  Commission: {{ suggestion.commission_pct }}&nbsp;%
                </p>

                <mee-progress-bar
                  [value]="suggestion.confidence"
                  [label]="'Confidence'"
                  [show_value]="true"
                />

                <div class="flex justify-end">
                  <mee-button
                    [label]="'Pick this'"
                    variant="secondary"
                    size="sm"
                    [loading]="picking()"
                    [disabled]="picking()"
                    (clicked)="onPick(suggestion)"
                  />
                </div>
              </div>
            </mee-card>
          }
        </div>
      }

      <!-- Empty results (after suggest returned nothing) -->
      @if (!suggesting() && hasSearched() && suggestions().length === 0) {
        <div
          class="mt-6 p-4 rounded text-sm text-center"
          style="background: color-mix(in srgb, var(--mee-color-outline) 30%, transparent); color: var(--mee-color-on-surface-muted);"
        >
          No matches found — try a different description or browse manually above.
        </div>
      }

    </div>
  `,
})
export class CatalogNewComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly api = inject(SmartPickerApiService);
  private readonly destroyRef = inject(DestroyRef);

  // ── Form ──────────────────────────────────────────────────────────
  readonly form = this.fb.group({
    description: ['', [Validators.required, Validators.minLength(10)]],
  });

  // ── Local state signals ────────────────────────────────────────────
  readonly suggesting   = signal(false);
  readonly suggestions  = signal<CategorySuggestion[]>([]);
  readonly picking      = signal(false);
  readonly showFallback = signal(false);
  readonly errorMessage = signal<string | null>(null);
  readonly treeLoading  = signal(true);
  readonly categoryTree = signal<MeeTreeNode[]>([]);
  readonly hasSearched  = signal(false);

  // ── Computed ───────────────────────────────────────────────────────
  readonly descError = computed<string | undefined>(() => {
    const ctrl = this.form.get('description');
    if (!ctrl || !ctrl.touched || ctrl.valid) return undefined;
    if (ctrl.hasError('required')) return 'Please describe your product.';
    if (ctrl.hasError('minlength')) return 'Please enter at least 10 characters.';
    return undefined;
  });

  // ── Lifecycle ──────────────────────────────────────────────────────
  ngOnInit(): void {
    // Pre-load tree stub after 600ms so it is ready when user opens fallback
    of(SIMULATED_TREE)
      .pipe(delay(600), takeUntilDestroyed(this.destroyRef))
      .subscribe(tree => {
        this.categoryTree.set(tree);
        this.treeLoading.set(false);
      });
  }

  // ── Handlers ───────────────────────────────────────────────────────
  onSuggest(): void {
    if (this.form.invalid || this.suggesting()) return;

    const description = this.form.get('description')?.value ?? '';
    this.suggesting.set(true);
    this.errorMessage.set(null);
    this.hasSearched.set(false);

    this.api.suggest(description).subscribe({
      next: (results) => {
        this.suggestions.set(results);
        this.suggesting.set(false);
        this.hasSearched.set(true);
        if (results.length === 0) {
          this.showFallback.set(true);
        }
      },
      error: () => {
        this.suggesting.set(false);
        this.hasSearched.set(true);
        this.errorMessage.set('Could not fetch suggestions. Please try again.');
      },
    });
  }

  onPick(suggestion: CategorySuggestion): void {
    if (this.picking()) return;
    this.picking.set(true);
    this.errorMessage.set(null);

    this.api.createProduct({ category_id: suggestion.id }).subscribe({
      next: (product) => {
        this.picking.set(false);
        this.router.navigate(['/catalogs', product.id, 'edit']);
      },
      error: () => {
        this.picking.set(false);
        this.errorMessage.set('Could not create catalog. Please try again.');
      },
    });
  }

  onShowFallback(): void {
    this.showFallback.set(true);
  }

  onTreePick(node: MeeTreeNode): void {
    if (!node.value) return; // ignore group nodes with null value
    this.picking.set(true);
    this.errorMessage.set(null);

    this.api.createProduct({ category_id: node.value as string }).subscribe({
      next: (product) => {
        this.picking.set(false);
        this.router.navigate(['/catalogs', product.id, 'edit']);
      },
      error: () => {
        this.picking.set(false);
        this.errorMessage.set('Could not create catalog. Please try again.');
      },
    });
  }
}
