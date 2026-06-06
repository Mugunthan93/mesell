// features/smart-picker/smart-picker/smart-picker.component.ts
// Page component for /catalogs/new — AI category suggestion + browse fallback
// Per AC-1, AC-8, AC-9: orchestrates description input, suggestion cards, browse fallback,
// 422 profile-incomplete modal, and navigation to /catalogs/:id/edit on success.

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
} from '@angular/core';
import { Router } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatExpansionModule } from '@angular/material/expansion';
import { TranslocoModule, TranslocoService } from '@jsverse/transloco';
import { catchError, EMPTY } from 'rxjs';

import { SmartPickerStateService } from '../smart-picker-state.service';
import { DescriptionInputComponent } from '../description-input/description-input.component';
import { CategoryCardComponent } from '../category-card/category-card.component';
import { BrowseFallbackComponent } from '../browse-fallback/browse-fallback.component';
import { ProfileIncompleteDialogComponent } from '../profile-incomplete-dialog/profile-incomplete-dialog.component';
import {
  CategorySuggestion,
  BrowseSelection,
  ProfileIncompleteError,
} from '../smart-picker.model';

@Component({
  selector: 'mee-smart-picker',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    MatProgressSpinnerModule,
    MatDialogModule,
    MatButtonModule,
    MatExpansionModule,
    TranslocoModule,
    DescriptionInputComponent,
    CategoryCardComponent,
    BrowseFallbackComponent,
  ],
  template: `
    <div class="mee-smart-picker max-w-2xl mx-auto px-4 py-8">
      <h1 class="text-2xl font-bold text-gray-900 mb-6">
        {{ 'smartPicker.title' | transloco }}
      </h1>

      <!-- Description input -->
      <mee-description-input
        [disabled]="state.loading()"
        (descriptionSubmit)="onDescriptionSubmit($event)"
        class="block mb-6"
      ></mee-description-input>

      <!-- Loading spinner while suggest in-flight -->
      @if (state.loading()) {
        <div class="flex justify-center py-8">
          <mat-spinner diameter="40"></mat-spinner>
        </div>
      }

      <!-- Rate limit message -->
      @if (state.rateLimitHit()) {
        <p class="text-sm text-amber-700 bg-amber-50 rounded px-3 py-2 mb-4">
          {{ 'smartPicker.rateLimitMessage' | transloco }}
        </p>
      }

      <!-- Suggestion cards (up to 3) -->
      @if (!state.loading() && suggestions().length > 0) {
        <div class="flex flex-col gap-3 mb-6">
          @for (suggestion of suggestions(); track suggestion.leaf_category_id) {
            <mee-category-card
              [suggestion]="suggestion"
              (categorySelected)="onCategorySelected($event)"
            ></mee-category-card>
          }
        </div>
      }

      <!-- Browse fallback — accordion, always present but collapsed unless triggered -->
      <mat-accordion>
        <mat-expansion-panel
          [expanded]="state.showBrowseFallback()"
          (opened)="state.openBrowseFallback()"
        >
          <mat-expansion-panel-header>
            <mat-panel-title>
              {{ 'smartPicker.browse.link' | transloco }}
            </mat-panel-title>
          </mat-expansion-panel-header>

          <mee-browse-fallback
            (categorySelected)="onBrowseSelection($event)"
          ></mee-browse-fallback>
        </mat-expansion-panel>
      </mat-accordion>
    </div>
  `,
})
export class SmartPickerComponent {
  readonly state = inject(SmartPickerStateService);
  private readonly router = inject(Router);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  private readonly transloco = inject(TranslocoService);

  /** Convert BehaviorSubject to signal for template binding */
  readonly suggestions = toSignal(this.state.suggestions$, {
    initialValue: [] as CategorySuggestion[],
  });

  onDescriptionSubmit(description: string): void {
    this.state.suggest(description);
  }

  onCategorySelected(suggestion: CategorySuggestion): void {
    this.selectAndNavigate(suggestion);
  }

  onBrowseSelection(selection: BrowseSelection): void {
    this.selectAndNavigate(selection);
  }

  private selectAndNavigate(
    selection: CategorySuggestion | BrowseSelection,
  ): void {
    this.state
      .selectCategory(selection)
      .pipe(
        catchError((err: unknown) => {
          this.handleSelectError(err);
          return EMPTY;
        }),
      )
      .subscribe(({ productId }) => {
        this.router.navigate(['/catalogs', productId, 'edit']);
      });
  }

  private handleSelectError(err: unknown): void {
    const status = (err as { status?: number })?.status;
    const raw = (err as { raw?: { error?: unknown } })?.raw?.error as
      | ProfileIncompleteError
      | null
      | undefined;

    if (status === 422 && raw?.detail === 'customer.profile_incomplete_for_category') {
      this.dialog.open(ProfileIncompleteDialogComponent, {
        data: raw,
        width: '480px',
      });
      return;
    }

    // All other errors are handled by ErrorInterceptor; show a generic snackbar fallback
    const message: string =
      (err as { displayMessage?: string })?.displayMessage ??
      (this.transloco.translate('common.error') as string);
    const dismiss: string = this.transloco.translate('common.dismiss') as string;
    this.snackBar.open(message, dismiss, { duration: 6000 });
  }
}
