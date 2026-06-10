// features/preview/preview/preview.component.ts
// Selector: mee-preview
// Route: /catalogs/:id/preview — pure presentation, read-only per §13

import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { EMPTY } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { MatTabsModule } from '@angular/material/tabs';
import { MatButtonModule } from '@angular/material/button';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslocoModule } from '@jsverse/transloco';

import { PreviewApiService, PreviewData } from '../preview-api.service';
import { LoadingSpinnerComponent } from '@shared/components/loading-spinner/loading-spinner.component';
import { EmptyStateComponent } from '@shared/components/empty-state/empty-state.component';
import { PreviewFeedComponent } from './preview-feed/preview-feed.component';
import { PreviewDetailComponent } from './preview-detail/preview-detail.component';

@Component({
  selector: 'mee-preview',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    MatTabsModule,
    MatButtonModule,
    MatSnackBarModule,
    TranslocoModule,
    LoadingSpinnerComponent,
    EmptyStateComponent,
    PreviewFeedComponent,
    PreviewDetailComponent,
  ],
  styles: [`
    :host { display: block; }
    .preview-page {
      max-width: 960px;
      margin: 0 auto;
      padding: 24px 16px;
    }
    .preview-header {
      margin-bottom: 24px;
    }
    .preview-header h1 {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0 0 4px;
    }
    .preview-header p {
      font-size: 13px;
      color: #6B7280;
      margin: 0;
    }
    .preview-tab-content {
      padding: 24px 0;
      display: flex;
      justify-content: center;
    }
    .preview-actions {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-top: 32px;
      gap: 12px;
    }
    .loading-wrap {
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 300px;
    }
    @media (max-width: 480px) {
      .preview-actions {
        flex-direction: column;
      }
      .preview-actions button, .preview-actions a {
        width: 100%;
      }
    }
  `],
  template: `
    <div class="preview-page">
      <!-- Page header -->
      <div class="preview-header">
        <h1>{{ 'preview.title' | transloco }}</h1>
        <p>See how your listing will appear on Meesho</p>
      </div>

      <!-- Loading state -->
      @if (loading()) {
        <div class="loading-wrap">
          <mee-loading-spinner [diameter]="40" caption="Loading preview..." />
        </div>
      }

      <!-- Error / missing data state -->
      @if (!loading() && !previewData()) {
        <mee-empty-state
          icon="preview"
          headline="Some fields are missing. Go back to edit your product."
          ctaLabel="Go to Edit"
          (ctaClick)="navigateToEdit()"
        />
      }

      <!-- Preview tabs -->
      @if (!loading() && previewData()) {
        <mat-tab-group animationDuration="150ms" aria-label="Preview tabs">
          <!-- Feed view tab -->
          <mat-tab [label]="'preview.tab.feed' | transloco">
            <div class="preview-tab-content">
              <mee-preview-feed [previewData]="previewData()!" />
            </div>
          </mat-tab>

          <!-- Detail view tab -->
          <mat-tab [label]="'preview.tab.detail' | transloco">
            <div class="preview-tab-content">
              <mee-preview-detail [previewData]="previewData()!" />
            </div>
          </mat-tab>
        </mat-tab-group>

        <!-- Navigation actions -->
        <div class="preview-actions">
          <button
            mat-stroked-button
            (click)="navigateBack()"
            class="min-h-[44px]"
            aria-label="Go back to images"
          >
            Back to Images
          </button>

          <button
            mat-flat-button
            color="primary"
            (click)="navigateNext()"
            class="min-h-[44px]"
            aria-label="Go to pricing"
            id="next-step-btn"
          >
            Next: Set Pricing
          </button>
        </div>
      }
    </div>
  `,
})
export class PreviewComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly previewApi = inject(PreviewApiService);
  private readonly snackBar = inject(MatSnackBar);

  readonly loading = signal<boolean>(true);
  readonly previewData = signal<PreviewData | null>(null);

  private get productId(): string {
    return this.route.snapshot.parent?.paramMap.get('id') ??
           this.route.snapshot.paramMap.get('id') ?? '';
  }

  ngOnInit(): void {
    const id = this.productId;
    if (!id) {
      this.loading.set(false);
      return;
    }

    this.previewApi.getPreview(id).pipe(
      catchError((err: unknown) => {
        this.loading.set(false);
        const status = (err as { status?: number })?.status;
        if (status !== 404) {
          this.snackBar.open('Failed to load preview. Please try again.', 'Dismiss', {
            duration: 4000,
            panelClass: ['mee-snackbar-error'],
          });
        }
        return EMPTY;
      }),
    ).subscribe((data) => {
      this.previewData.set(data);
      this.loading.set(false);
    });
  }

  navigateToEdit(): void {
    const id = this.productId;
    void this.router.navigate(['/catalogs', id, 'edit']);
  }

  navigateBack(): void {
    const id = this.productId;
    void this.router.navigate(['/catalogs', id, 'images']);
  }

  navigateNext(): void {
    const id = this.productId;
    void this.router.navigate(['/catalogs', id, 'pricing']);
  }
}
