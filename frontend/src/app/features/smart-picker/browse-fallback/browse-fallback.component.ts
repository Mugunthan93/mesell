// features/smart-picker/browse-fallback/browse-fallback.component.ts
// Two-step manual browse: super-category select → leaf search with debounce
// Per AC-4: 500ms debounce, min 2 chars, emits BrowseSelection on leaf pick

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule, FormBuilder } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatInputModule } from '@angular/material/input';
import { MatListModule } from '@angular/material/list';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslocoModule } from '@jsverse/transloco';
import { output } from '@angular/core';
import { debounceTime, distinctUntilChanged, filter, switchMap, tap } from 'rxjs/operators';
import { SmartPickerApiService } from '../smart-picker-api.service';
import { SuperCategory, LeafCategory, BrowseSelection } from '../smart-picker.model';

@Component({
  selector: 'mee-browse-fallback',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    ReactiveFormsModule,
    MatFormFieldModule,
    MatSelectModule,
    MatInputModule,
    MatListModule,
    MatProgressSpinnerModule,
    TranslocoModule,
  ],
  template: `
    <div class="mee-browse-fallback flex flex-col gap-4 p-4 rounded-lg border border-gray-200 bg-gray-50">
      <h3 class="text-base font-semibold text-gray-800">
        {{ 'smartPicker.browse.superCategoryLabel' | transloco }}
      </h3>

      <!-- Step 1: super-category select -->
      <mat-form-field appearance="outline" class="w-full">
        <mat-label>{{ 'smartPicker.browse.superCategoryLabel' | transloco }}</mat-label>
        <mat-select [formControl]="superCtrl">
          @for (cat of superCategories(); track cat.id) {
            <mat-option [value]="cat.id">{{ cat.name }}</mat-option>
          }
        </mat-select>
      </mat-form-field>

      <!-- Step 2: leaf search — shown only after super-cat is picked -->
      @if (superCtrl.value) {
        <mat-form-field appearance="outline" class="w-full">
          <mat-label>{{ 'smartPicker.browse.leafSearchPlaceholder' | transloco }}</mat-label>
          <input
            matInput
            [formControl]="leafSearchCtrl"
            [placeholder]="'smartPicker.browse.leafSearchPlaceholder' | transloco"
          />
        </mat-form-field>

        @if (leafLoading()) {
          <div class="flex justify-center p-2">
            <mat-spinner diameter="24"></mat-spinner>
          </div>
        }

        @if (!leafLoading() && leafSearchCtrl.value && leafSearchCtrl.value.length >= 2) {
          @if (leaves().length === 0) {
            <p class="text-sm text-gray-500">
              {{ 'smartPicker.browse.noResults' | transloco }}
            </p>
          } @else {
            <mat-list class="bg-white rounded border border-gray-200 max-h-64 overflow-y-auto">
              @for (leaf of leaves(); track leaf.id) {
                <mat-list-item
                  class="cursor-pointer hover:bg-gray-50 min-h-[44px]"
                  (click)="selectLeaf(leaf)"
                  (keydown.enter)="selectLeaf(leaf)"
                  (keydown.space)="selectLeaf(leaf)"
                  tabindex="0"
                  role="option"
                  [attr.aria-label]="leaf.full_path"
                >
                  <span matListItemTitle>{{ leaf.name }}</span>
                  <span matListItemLine class="text-xs text-gray-500">{{ leaf.full_path }}</span>
                </mat-list-item>
              }
            </mat-list>
          }
        }
      }
    </div>
  `,
})
export class BrowseFallbackComponent implements OnInit {
  readonly categorySelected = output<BrowseSelection>();

  private readonly api = inject(SmartPickerApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  readonly superCategories = signal<SuperCategory[]>([]);
  readonly leaves = signal<LeafCategory[]>([]);
  readonly leafLoading = signal(false);

  readonly superCtrl = this.fb.control<string | null>(null);
  readonly leafSearchCtrl = this.fb.control('');

  ngOnInit(): void {
    // Load super categories on init
    this.api.getSuperCategories()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => this.superCategories.set(res.categories),
      });

    // When super-category changes, reset leaf search
    this.superCtrl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.leafSearchCtrl.reset('');
        this.leaves.set([]);
      });

    // Leaf search: debounce 500ms, min 2 chars
    this.leafSearchCtrl.valueChanges
      .pipe(
        debounceTime(500),
        distinctUntilChanged(),
        filter((v): v is string => !!v && v.length >= 2 && !!this.superCtrl.value),
        tap(() => this.leafLoading.set(true)),
        switchMap((search) =>
          this.api.searchLeaves(this.superCtrl.value!, search),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.leaves.set(res.leaves);
          this.leafLoading.set(false);
        },
        error: () => {
          this.leafLoading.set(false);
        },
      });
  }

  selectLeaf(leaf: LeafCategory): void {
    this.categorySelected.emit({
      leaf_id: leaf.id,
      leaf_name: leaf.name,
      full_path: leaf.full_path,
    });
  }
}
