// features/catalog-form/catalog-form/catalog-form.component.ts
// Route: /catalogs/:id/edit
// Orchestrator: coordinates CatalogFormApiService, CatalogFormStateService,
// DraftRecoveryService, CategorySchemaService, WizardRendererComponent, StepComposerService.
// Does NOT render form fields directly — delegates to mee-wizard (WizardRendererComponent).

import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { debounceTime, Subject } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

import { CatalogFormApiService } from '../catalog-form-api.service';
import { CatalogFormStateService } from '../catalog-form-state.service';
import { DraftRecoveryService } from '../draft-recovery.service';
import { CategorySchemaService } from '../category-schema.service';
import { StepComposerService } from '../wizard-renderer/step-composer.service';
import { WizardRendererComponent } from '../wizard-renderer/wizard-renderer.component';
import { LoadingSpinnerComponent } from '@shared/components/loading-spinner/loading-spinner.component';
import { StatusBadgeComponent } from '@shared/components/status-badge/status-badge.component';
import { ErrorService } from '@core/services/error.service';
import { ApiError } from '@core/api/api-error';
import { ValueChange } from '../primitives/primitive.contract';

// AutosaveStatus type mirrors what we drive locally
type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error';

@Component({
  selector: 'mee-catalog-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [StepComposerService],
  imports: [
    MatButtonModule,
    MatProgressSpinnerModule,
    WizardRendererComponent,
    LoadingSpinnerComponent,
    StatusBadgeComponent,
  ],
  styles: [`
    :host {
      display: block;
      background: var(--mee-color-bg);
      min-height: 100vh;
      padding: 24px;
    }
    .catalog-form-page {
      max-width: 900px;
      margin: 0 auto;
    }
    .page-header {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 24px;
    }
    .page-header h1 {
      font-size: 22px;
      font-weight: 700;
      color: var(--mee-color-on-surface);
      margin: 0;
      flex: 1;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
    .error-banner {
      background: #FEF2F2;
      border: 1px solid #FECACA;
      border-radius: var(--mee-radius-md);
      padding: 12px 16px;
      color: #991B1B;
      font-size: 14px;
      margin-bottom: 16px;
    }
    .save-status {
      position: fixed;
      bottom: 16px;
      right: 16px;
      font-size: 12px;
      padding: 6px 12px;
      border-radius: var(--mee-radius-md);
      background: var(--mee-color-surface);
      border: 1px solid #E5E7EB;
      color: var(--mee-color-on-surface);
      pointer-events: none;
      opacity: 0;
      transition: opacity 0.2s ease;
    }
    .save-status[data-status='saving'],
    .save-status[data-status='saved'],
    .save-status[data-status='error'] {
      opacity: 1;
    }
    .save-status[data-status='error'] {
      border-color: #FECACA;
      color: #991B1B;
      background: #FEF2F2;
    }
    .save-status[data-status='saved'] {
      border-color: #BBF7D0;
      color: #166534;
      background: #F0FDF4;
    }
    .ai-fill-btn {
      min-height: 44px;
      min-width: 44px;
    }
  `],
  template: `
    <div class="catalog-form-page">

      <!-- Page header: product name + status badge + AI Fill button -->
      <div class="page-header">
        <h1>{{ productTitle() }}</h1>

        @if (state.product()) {
          <mee-status-badge [status]="state.product()!.status" />
        }

        <button
          mat-raised-button
          color="accent"
          class="ai-fill-btn"
          type="button"
          [disabled]="state.autofillLoading() || state.loading()"
          (click)="onRequestAutofill()"
          aria-label="Fill form fields using AI"
        >
          @if (state.autofillLoading()) {
            <mat-spinner diameter="16" />
          }
          AI Fill
        </button>
      </div>

      <!-- Loading state -->
      @if (state.loading()) {
        <mee-loading-spinner caption="Loading product..." />
      }

      <!-- Error state -->
      @if (state.error()) {
        <div class="error-banner" role="alert">{{ state.error() }}</div>
      }

      <!-- Wizard — only when schema + product are loaded -->
      @if (!state.loading() && state.schema() && state.product()) {
        <mee-wizard
          [steps]="wizardSteps()"
          [model]="state.fields()"
          [aiSuggestions]="state.aiSuggestions()"
          (valueChange)="onFieldChange($event)"
          (submit)="onSubmit()"
        />
      }

      <!-- Autosave status indicator -->
      <div class="save-status" [attr.data-status]="saveStatus()">
        @switch (saveStatus()) {
          @case ('saving') { <span>Saving...</span> }
          @case ('saved')  { <span>Saved</span> }
          @case ('error')  { <span>Save failed</span> }
        }
      </div>

    </div>
  `,
})
export class CatalogFormComponent implements OnInit {

  // ── DI ─────────────────────────────────────────────────────────────────────

  protected readonly state = inject(CatalogFormStateService);
  private readonly catalogFormApi = inject(CatalogFormApiService);
  private readonly draftRecovery = inject(DraftRecoveryService);
  private readonly categorySchema = inject(CategorySchemaService);
  private readonly stepComposer = inject(StepComposerService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly errorService = inject(ErrorService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  // ── Local state ─────────────────────────────────────────────────────────────

  /** Autosave status driven by the Subject+debounce autosave pipeline */
  readonly saveStatus = signal<AutosaveStatus>('idle');

  /**
   * Autosave pipeline: Subject+debounce(10s) + takeUntilDestroyed.
   * This is functionally equivalent to the meeAutosave directive.
   * The directive requires a FormGroup via meeAutosaveControl; since this
   * component uses signals (no FormGroup), we implement autosave directly.
   * Pattern: emit on each onFieldChange call → debounce 10s → call autosaveProduct.
   */
  private readonly autosaveTrigger$ = new Subject<void>();

  /** The product UUID from the route param :id */
  private productId = '';

  // ── Computed ────────────────────────────────────────────────────────────────

  /** Wizard steps computed from schema via StepComposerService */
  readonly wizardSteps = computed(() =>
    this.stepComposer.compose(this.state.schema() ?? []),
  );

  /** Product title derived from fields for the page header */
  readonly productTitle = computed<string>(() => {
    const fields = this.state.fields();
    return (fields['title'] as string) || (fields['name'] as string) || 'Untitled product';
  });

  // ── Lifecycle ────────────────────────────────────────────────────────────────

  ngOnInit(): void {
    // Wire up the autosave Subject pipeline (constructor-equivalent injection context)
    this.autosaveTrigger$.pipe(
      debounceTime(10_000),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(() => {
      const pid = this.productId;
      if (!pid) return;
      this.saveStatus.set('saving');
      this.catalogFormApi.autosaveProduct(pid, this.state.fields()).subscribe({
        next: () => {
          this.saveStatus.set('saved');
          // Auto-reset to idle after 3s
          setTimeout(() => {
            if (this.saveStatus() === 'saved') this.saveStatus.set('idle');
          }, 3000);
        },
        error: () => {
          this.saveStatus.set('error');
        },
      });
    });

    // 1. Read route param :id
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      // No product ID — navigate to dashboard
      void this.router.navigate(['/dashboard']);
      return;
    }
    this.productId = id;
    this.state.loading.set(true);
    this.state.error.set(null);

    // 2a. Fetch product first — schema requires leafCategoryId from product response
    this.catalogFormApi.getProduct(id).subscribe({
      next: (product) => {
        this.state.setProduct(product);
        this.state.productId.set(id);

        // 2b. Fetch schema (requires leafCategoryId) + draft recovery in parallel
        let schemaResolved = false;
        let draftResolved = false;

        const tryFinish = () => {
          if (schemaResolved && draftResolved) {
            this.state.loading.set(false);
          }
        };

        // Fetch category schema
        this.categorySchema.getSchema(product.leafCategoryId).subscribe({
          next: (schema) => {
            this.state.setSchema(schema.fields);
            schemaResolved = true;
            tryFinish();
          },
          error: (err: unknown) => {
            this.state.error.set('Failed to load category fields. Please refresh.');
            this.errorService.showError(err instanceof Error ? err : new Error('Schema load failed'));
            schemaResolved = true;
            this.state.loading.set(false);
          },
        });

        // Fetch draft (in parallel with schema)
        this.draftRecovery.getDraft(id).subscribe({
          next: (draft) => {
            // null = no draft (204), non-null = draft exists
            this.state.setDraft(draft ? draft.fields : null);
            draftResolved = true;
            tryFinish();
          },
          error: () => {
            // Draft fetch failure is non-fatal — log and continue
            draftResolved = true;
            tryFinish();
          },
        });
      },
      error: (err: unknown) => {
        this.state.loading.set(false);
        if (err instanceof ApiError && err.status === 404) {
          // catalog.product_not_found → navigate to /dashboard
          void this.router.navigate(['/dashboard']);
          return;
        }
        if (err instanceof ApiError && err.status === 429) {
          // Rate limit exceeded — use Retry-After header if available
          const retryAfter = err.raw?.headers?.get('Retry-After');
          const message = retryAfter
            ? `Pausing a moment, please try again in ${retryAfter} seconds`
            : 'Too many requests. Please wait before trying again.';
          this.snackBar.open(message, 'Dismiss', { duration: 6000 });
          return;
        }
        this.state.error.set('Failed to load product. Please try again.');
        this.errorService.showError(err instanceof ApiError ? err : new Error('Load failed'));
      },
    });
  }

  // ── Event handlers ──────────────────────────────────────────────────────────

  /**
   * Called on each field change from WizardRendererComponent.
   * Applies the change to state and triggers debounced autosave.
   */
  onFieldChange(change: ValueChange): void {
    this.state.applyFieldChange(change);
    // Trigger the 10s-debounced autosave pipeline
    this.autosaveTrigger$.next();
  }

  /**
   * Triggered by the AI Fill button.
   * Calls requestAutofill and applies suggestions to state.
   * Handles fallback_offered + 429 rate limit per §11.A.1.
   */
  onRequestAutofill(): void {
    const pid = this.productId;
    if (!pid) return;

    this.state.autofillLoading.set(true);
    this.catalogFormApi.requestAutofill(pid).subscribe({
      next: (response) => {
        this.state.applyAutofillSuggestions(response.suggestions);
        if (response.fallbackOffered) {
          this.snackBar.open('AI suggestions may not be complete', 'Dismiss', { duration: 4000 });
        }
        this.state.autofillLoading.set(false);
      },
      error: (err: unknown) => {
        this.state.autofillLoading.set(false);
        if (err instanceof ApiError && err.status === 429) {
          this.snackBar.open('Daily AI fill limit reached. Try again tomorrow.', 'Dismiss', { duration: 6000 });
          return;
        }
        this.errorService.showError(err instanceof ApiError ? err : new Error('Autofill failed'));
      },
    });
  }

  /**
   * Called when the seller accepts an AI suggestion for a field.
   * Accepts the suggestion in state and persists it via saveProduct.
   */
  onAutofillAccepted(event: { canonicalName: string; value: unknown }): void {
    this.state.acceptAiSuggestion(event.canonicalName);
    const pid = this.productId;
    if (!pid) return;
    // Persist the accepted field value immediately (no debounce)
    this.catalogFormApi.saveProduct(pid, this.state.fields()).subscribe({
      error: (err: unknown) => {
        this.errorService.showError(err instanceof ApiError ? err : new Error('Save failed'));
      },
    });
  }

  /**
   * Called when the seller rejects an AI suggestion for a field.
   * Removes the suggestion from state and persists rejection metadata.
   */
  onAutofillRejected(event: { canonicalName: string; rejectedReason: string }): void {
    this.state.rejectAiSuggestion(event.canonicalName);
    const pid = this.productId;
    if (!pid) return;
    // Persist rejection note — backend merges ai_suggestions_jsonb on receipt
    const rejectionPayload = {
      ...this.state.fields(),
      ai_suggestions: {
        [event.canonicalName]: { rejected_reason: 'user_rejected' },
      },
    };
    this.catalogFormApi.saveProduct(pid, rejectionPayload).subscribe({
      error: (err: unknown) => {
        this.errorService.showError(err instanceof ApiError ? err : new Error('Save failed'));
      },
    });
  }

  /**
   * Manual save triggered by wizard submit button.
   * On success: navigate to /catalogs/:id/images.
   */
  onSubmit(): void {
    const pid = this.productId;
    if (!pid) return;

    this.state.saving.set(true);
    this.catalogFormApi.saveProduct(pid, this.state.fields()).subscribe({
      next: () => {
        this.state.saving.set(false);
        void this.router.navigate(['/catalogs', pid, 'images']);
      },
      error: (err: unknown) => {
        this.state.saving.set(false);
        this.errorService.showError(err instanceof ApiError ? err : new Error('Save failed'));
      },
    });
  }
}
