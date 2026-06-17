// catalog-form.component.ts — Wizard Refactor (multi-step wizard)
// Route: /catalogs/:id/edit
// Replaces 3-accordion layout with a step_id-driven multi-step wizard.
//
// Spec items implemented:
//   A — groupIntoSteps() groups fields by step_id in STEP_ORDER, required-first within step
//   B — Basics step: "Required" block + collapsible "More details" for optional fields
//   C — mee-steps horizontal stepper, sticky bottom nav bar, 44px touch targets
//   D — Next gating: blocks only when current step has unfilled required fields
//   E — Dropdowns: lazy per-step enum load on stepEnter(); enumCache preserved
//   F — Photos step: ImageUploaderComponent (reused), non-blocking front-photo warning
//   G — Preserved: categoryIdMissing, GAP-1, getDraft, autosave (10s), autofill overlay, OnPush, a11y

import {
  AfterViewInit,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  ElementRef,
  inject,
  OnInit,
  signal,
  ViewChild,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject } from 'rxjs';
import { debounceTime } from 'rxjs/operators';

import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeSelectComponent,
  MeeTextareaComponent,
  MeeStepsComponent,
  MeeToastService,
} from '@mesell/ui-kit';
import type { MeeStep } from '@mesell/ui-kit';
import {
  LoadingSkeletonComponent,
  PageHeaderComponent,
  StatusBadgeComponent,
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
} from '@mesell/composites';

import { ImageUploaderComponent } from '../../images/image-uploader/image-uploader.component';

import type {
  FieldSchema,
  AutofillResponse,
  ProductDetailResponse,
} from '../services/catalog-form-api.service';
import { CatalogFormApiService } from '../services/catalog-form-api.service';
import type { EnumEntryDTO, FieldGroup } from '../services/catalog-form-api.service';
import type { WizardStep } from '../models/field-schema.model';
import { groupIntoSteps } from '../models/field-schema.model';
import {
  canAdvanceFromStep,
  hasPhotosStepFrontMissing,
  stepRequiredFieldErrors,
} from '../catalog-form.model';

@Component({
  selector: 'app-catalog-form',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  providers: [CatalogFormApiService],
  imports: [
    MeeButtonComponent,
    MeeInputComponent,
    MeeSelectComponent,
    MeeTextareaComponent,
    MeeStepsComponent,
    LoadingSkeletonComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
    ImageUploaderComponent,
  ],
  styles: [`
    /* ── Host layout ──────────────────────────────────────────────────── */
    :host { display: block; }

    /* ── Wizard page wrapper: mobile-first 360px → desktop ────────────── */
    .mee-wizard-page {
      max-width: 100%;
      margin: 0 auto;
      padding: var(--mee-space-4);
      padding-bottom: 80px; /* reserve space for sticky bottom bar */
    }

    /* ── Sticky bottom navigation bar ─────────────────────────────────── */
    .mee-wizard-nav {
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 100;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--mee-space-3) var(--mee-space-4);
      background: var(--mee-color-surface);
      border-top: 1px solid var(--mee-color-outline);
      min-height: 64px;
    }
    .mee-wizard-nav__step-label {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
    }
    .mee-wizard-nav__actions {
      display: flex;
      gap: var(--mee-space-2);
      align-items: center;
    }

    /* ── Stepper header region ─────────────────────────────────────────── */
    .mee-stepper-region {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
      margin-bottom: var(--mee-space-5);
      /* Hide scrollbar but keep scroll functionality */
      scrollbar-width: none;
    }
    .mee-stepper-region::-webkit-scrollbar { display: none; }

    /* ── Step content card ─────────────────────────────────────────────── */
    .mee-step-content {
      background: var(--mee-color-surface);
      border-radius: var(--mee-radius-md);
      padding: var(--mee-space-5);
    }
    .mee-step-title {
      font-size: 1.0625rem;
      font-weight: 600;
      color: var(--mee-color-on-surface);
      margin-bottom: var(--mee-space-4);
    }

    /* ── Fields layout within a step ──────────────────────────────────── */
    .mee-step-fields {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }

    /* Full-width spanner: text_long (textarea) fields always occupy both columns */
    .mee-field--full {
      grid-column: 1 / -1;
    }

    /* ── "More details" sub-section (Basics step B) ───────────────────── */
    .mee-more-details-toggle {
      display: flex;
      width: 100%;
      align-items: center;
      justify-content: space-between;
      padding: 10px 0;
      margin-top: var(--mee-space-3);
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--mee-color-on-surface-muted);
      background: none;
      border: none;
      border-top: 1px solid var(--mee-color-outline);
      cursor: pointer;
      min-height: 44px;
      text-align: left;
    }
    .mee-more-details-toggle:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
    }
    .mee-more-details-fields {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding-top: var(--mee-space-3);
    }

    /* ── AI-suggested field highlight ─────────────────────────────────── */
    .field-wrapper {
      background-color: transparent;
      transition: background-color var(--mee-transition-fast);
    }
    .field-wrapper.mee-ai-suggested {
      padding: var(--mee-space-2);
      border-radius: var(--mee-radius-sm);
      outline: 1px solid var(--mee-color-warning);
      outline-offset: 2px;
      background-color: var(--mee-color-warning-light);
    }

    /* ── Autofill suggestion overlay ──────────────────────────────────── */
    .mee-autofill-overlay {
      background: var(--mee-color-warning-light);
      border: 1px solid var(--mee-color-warning);
      border-radius: var(--mee-radius-md);
      padding: var(--mee-space-3);
      margin-bottom: var(--mee-space-4);
    }
    .mee-autofill-overlay__heading {
      font-size: 0.875rem;
      font-weight: 500;
      color: var(--mee-color-on-surface);
      margin-bottom: var(--mee-space-2);
    }
    .suggestion-row {
      display: flex;
      align-items: center;
      gap: var(--mee-space-2);
      padding: 6px 0;
      border-bottom: 1px solid var(--mee-color-outline);
      min-height: 44px;
    }
    .suggestion-row:last-child { border-bottom: none; }
    .suggestion-row__canonical {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
      white-space: nowrap;
      flex-shrink: 0;
    }
    .suggestion-row__value {
      font-size: 0.875rem;
      font-weight: 500;
      flex: 1;
      padding: 0 var(--mee-space-2);
      color: var(--mee-color-on-surface);
      word-break: break-word;
    }
    .suggestion-row__actions {
      display: flex;
      gap: var(--mee-space-1);
      flex-shrink: 0;
    }

    /* ── Autosave status indicator ─────────────────────────────────────── */
    .mee-autosave-status {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
    }
    .mee-autosave-status--error { color: var(--mee-color-error); }

    /* ── Photos warning banner ─────────────────────────────────────────── */
    .mee-photos-warning {
      margin-bottom: var(--mee-space-3);
    }

    /* ── Error/missing-category banner ────────────────────────────────── */
    .mee-error-region {
      margin-top: var(--mee-space-4);
    }
    .mee-error-cta {
      display: flex;
      justify-content: center;
      margin-top: var(--mee-space-4);
    }

    /* ── Loading skeleton region ───────────────────────────────────────── */
    .mee-skeleton-region {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-5);
    }
    .mee-skeleton-section {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);
    }
    .mee-skeleton-heading {
      height: 44px;
      border-radius: var(--mee-radius-sm);
      background: var(--mee-color-outline);
      width: 40%;
      animation: mee-pulse 1.5s ease-in-out infinite;
    }

    @keyframes mee-pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.45; }
    }

    /* ── Tablet+ ───────────────────────────────────────────────────────── */
    @media (min-width: 768px) {
      .mee-wizard-page {
        max-width: 42rem;
        padding: var(--mee-space-6) var(--mee-space-8);
        padding-bottom: 88px;
      }

      /* Two-column field grid — required block and optional ("More details") block */
      .mee-step-fields,
      .mee-more-details-fields {
        display: grid;
        grid-template-columns: 1fr 1fr;
        column-gap: var(--mee-space-6);
        row-gap: var(--mee-space-4);
      }
    }

    /* ── Desktop ───────────────────────────────────────────────────────── */
    @media (min-width: 1280px) {
      .mee-wizard-page {
        max-width: 64rem;
        padding: var(--mee-space-8) var(--mee-space-10);
        padding-bottom: 88px;
      }
      .mee-wizard-layout {
        display: grid;
        grid-template-columns: 1fr 20rem;
        gap: var(--mee-space-8);
        align-items: start;
      }
      .mee-wizard-sidebar {
        position: sticky;
        top: var(--mee-space-4);
      }
    }
  `],
  template: `
    <!-- a11y: categoryIdMissing error banner ref for programmatic focus -->
    <div #errorRegionRef>

    <div class="mee-wizard-page">
      <mee-offline-banner />

      <!-- categoryIdMissing: critical error state — GAP-1 hard-reload path -->
      @if (categoryIdMissing()) {
        <div class="mee-error-region"
             role="alert"
             aria-live="assertive"
             aria-atomic="true"
             tabindex="-1">
          <mee-alert-banner
            variant="error"
            message="Cannot load form: product category not found. Return to the dashboard and try again." />
          <div class="mee-error-cta">
            <mee-button label="Return to dashboard" variant="secondary" (clicked)="onBack()" />
          </div>
        </div>
      }

      @if (!categoryIdMissing()) {
        <!-- Page header -->
        <mee-page-header [title]="productName()" [subtitle]="categoryPath()" />

        <!-- Inline error banner -->
        @if (errorMessage()) {
          <div class="mb-4"
               role="alert"
               aria-live="assertive"
               aria-atomic="true"
               tabindex="-1"
               #inlineErrorRef>
            <mee-alert-banner variant="error" [message]="errorMessage()!" />
            <div class="flex justify-end mt-2">
              <mee-button label="Retry" variant="ghost" (clicked)="onRetry()" />
            </div>
          </div>
        }

        <!-- Status bar + AI fill button -->
        <div class="flex items-center justify-between mt-3 mb-4">
          <mee-status-badge [status]="'draft'" />
          <mee-button
            label="AI fill"
            variant="secondary"
            icon="sparkles"
            [loading]="autofilling()"
            [disabled]="loading() || autofillUnavailable()"
            (clicked)="onAutofill()"
            aria-label="Fill fields with AI suggestions" />
        </div>

        <!-- Loading skeleton -->
        @if (loading()) {
          <div class="mee-skeleton-region"
               role="status"
               aria-live="polite"
               aria-label="Loading product form fields, please wait">
            <div class="mee-skeleton-section">
              <div class="mee-skeleton-heading" aria-hidden="true"></div>
              <mee-loading-skeleton variant="text" [lines]="4" />
            </div>
            <div class="mee-skeleton-section">
              <div class="mee-skeleton-heading" aria-hidden="true"></div>
              <mee-loading-skeleton variant="text" [lines]="3" />
            </div>
          </div>
        }

        @if (!loading()) {
          <!-- ── Stepper header (horizontally scrollable on mobile) ──── -->
          <div class="mee-stepper-region" aria-label="Form progress">
            <mee-steps
              [steps]="meeStepItems()"
              [active_index]="activeStepIndex()"
              (active_index_change)="onStepChange($event)"
            />
          </div>

          <!-- ── Desktop 2-col layout wrapper ──────────────────────────── -->
          <div class="mee-wizard-layout">

            <!-- Left: active step content -->
            <div>
              <!-- Photos step — special: render ImageUploaderComponent -->
              @if (isPhotosStep()) {
                <div class="mee-step-content">
                  <h2 class="mee-step-title">Photos</h2>
                  <!-- Non-blocking front-photo warning (spec §F) -->
                  @if (showPhotosWarning()) {
                    <div class="mee-photos-warning"
                         role="alert"
                         aria-live="polite">
                      <mee-alert-banner
                        variant="warning"
                        message="Add your main photo before exporting — the front image (slot 1) is required for export." />
                    </div>
                  }
                  <!-- Reuse the existing ImageUploaderComponent from /images page -->
                  <app-image-uploader />
                </div>
              }

              <!-- Generic field-renderer step -->
              @if (!isPhotosStep()) {
                <div class="mee-step-content"
                     [attr.aria-label]="activeStep()?.label + ' fields'"
                     role="region">
                  <h2 class="mee-step-title">{{ activeStep()?.label }}</h2>

                  <!-- enum loading state for this step -->
                  @if (stepEnumsLoading()) {
                    <div role="status" aria-live="polite" aria-label="Loading dropdown options" class="mb-4">
                      <mee-loading-skeleton variant="text" [lines]="2" />
                    </div>
                  }

                  <!-- Required fields block -->
                  @let requiredFields = activeStepRequiredFields();
                  @if (requiredFields.length > 0) {
                    <div class="mee-step-fields" aria-label="Required fields">
                      @for (field of requiredFields; track field.canonical_name) {
                        <div class="field-wrapper"
                             [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                             [class.mee-field--full]="field.primitive === 'text_long'">
                          @switch (field.primitive) {
                            @case ('text_long') {
                              <mee-textarea
                                [label]="field.display_name"
                                [required]="field.required"
                                [error]="getFieldError(field.canonical_name)"
                                [hint]="field.help_text"
                                [rows]="4"
                                (blur)="onFieldBlur(field.canonical_name, $any($event))" />
                            }
                            @case ('select') {
                              <mee-select
                                [label]="field.display_name"
                                [options]="getFieldOptions(field)"
                                [error]="getFieldError(field.canonical_name)"
                                (value_change)="onFieldChange(field.canonical_name, $event)" />
                            }
                            @default {
                              <mee-input
                                [label]="field.display_name"
                                [required]="field.required"
                                [error]="getFieldError(field.canonical_name)"
                                [hint]="field.help_text"
                                [type]="field.primitive === 'number' ? 'number' : 'text'"
                                (blur)="onFieldBlur(field.canonical_name, $any($event))" />
                            }
                          }
                        </div>
                      }
                    </div>
                  }

                  <!-- "More details" collapsible section (spec §B): optional fields -->
                  @let optionalFields = activeStepOptionalFields();
                  @if (optionalFields.length > 0) {
                    <button
                      type="button"
                      class="mee-more-details-toggle"
                      (click)="toggleMoreDetails()"
                      [attr.aria-expanded]="moreDetailsOpen()"
                      aria-controls="more-details-panel">
                      <span>{{ moreDetailsOpen() ? 'Hide' : 'More details' }} ({{ optionalFields.length }})</span>
                      <span aria-hidden="true">{{ moreDetailsOpen() ? '▲' : '▼' }}</span>
                    </button>
                    @if (moreDetailsOpen()) {
                      <div id="more-details-panel" class="mee-more-details-fields">
                        @for (field of optionalFields; track field.canonical_name) {
                          <div class="field-wrapper"
                               [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                               [class.mee-field--full]="field.primitive === 'text_long'">
                            @switch (field.primitive) {
                              @case ('text_long') {
                                <mee-textarea
                                  [label]="field.display_name"
                                  [required]="field.required"
                                  [error]="getFieldError(field.canonical_name)"
                                  [hint]="field.help_text"
                                  [rows]="4"
                                  (blur)="onFieldBlur(field.canonical_name, $any($event))" />
                              }
                              @case ('select') {
                                <mee-select
                                  [label]="field.display_name"
                                  [options]="getFieldOptions(field)"
                                  [error]="getFieldError(field.canonical_name)"
                                  (value_change)="onFieldChange(field.canonical_name, $event)" />
                              }
                              @default {
                                <mee-input
                                  [label]="field.display_name"
                                  [required]="field.required"
                                  [error]="getFieldError(field.canonical_name)"
                                  [hint]="field.help_text"
                                  [type]="field.primitive === 'number' ? 'number' : 'text'"
                                  (blur)="onFieldBlur(field.canonical_name, $any($event))" />
                              }
                            }
                          </div>
                        }
                      </div>
                    }
                  }
                </div>
              }
            </div>

            <!-- Right: autofill overlay + sidebar (desktop) -->
            <div class="mee-wizard-sidebar">
              <!-- Autofill suggestion overlay -->
              @if (!loading() && hasSuggestions()) {
                <div class="mee-autofill-overlay"
                     role="region"
                     aria-label="AI suggestions — review and apply or dismiss each field">
                  <p class="mee-autofill-overlay__heading">AI suggestions — review and apply</p>
                  @for (entry of suggestionEntries(); track entry.canonical) {
                    <div class="suggestion-row">
                      <span class="suggestion-row__canonical">{{ entry.canonical }}</span>
                      <span class="suggestion-row__value">{{ entry.value }}</span>
                      <div class="suggestion-row__actions">
                        <mee-button
                          label="Apply"
                          variant="secondary"
                          [attr.aria-label]="'Apply AI suggestion for ' + entry.canonical"
                          (clicked)="applySuggestion(entry.canonical)" />
                        <mee-button
                          label="Dismiss"
                          variant="ghost"
                          [attr.aria-label]="'Dismiss AI suggestion for ' + entry.canonical"
                          (clicked)="dismissSuggestion(entry.canonical)" />
                      </div>
                    </div>
                  }
                  <div class="flex justify-end mt-2">
                    <mee-button
                      label="Dismiss all"
                      variant="ghost"
                      aria-label="Dismiss all AI suggestions"
                      (clicked)="dismissAllSuggestions()" />
                  </div>
                </div>
              }

              <!-- AI autofill fallback -->
              @if (fallbackOffered()) {
                <div class="mb-3">
                  <mee-alert-banner
                    variant="warning"
                    message="AI couldn't fill — try adding more product details before using AI fill." />
                </div>
              }
            </div>

          </div><!-- /mee-wizard-layout -->
        }
      }
    </div><!-- /mee-wizard-page -->
    </div><!-- /#errorRegionRef -->

    <!-- ── Sticky bottom nav bar (spec §C) ───────────────────────────────── -->
    @if (!categoryIdMissing() && !loading()) {
      <nav class="mee-wizard-nav" aria-label="Step navigation">
        <!-- Step indicator + autosave status -->
        <div>
          <div class="mee-wizard-nav__step-label">
            Step {{ activeStepIndex() + 1 }} of {{ wizardSteps().length }}
          </div>
          <span
            role="status"
            aria-live="polite"
            aria-atomic="true"
            [class]="autosaveStatusClass()">
            {{ autosaveStatusLabel() }}
          </span>
        </div>
        <!-- Back / Next / Save & Finish actions -->
        <div class="mee-wizard-nav__actions">
          @if (activeStepIndex() > 0) {
            <mee-button
              label="Back"
              variant="ghost"
              (clicked)="onBack()"
              aria-label="Go to previous step" />
          } @else {
            <mee-button
              label="Dashboard"
              variant="ghost"
              (clicked)="onDashboard()"
              aria-label="Return to dashboard" />
          }
          @if (isLastStep()) {
            <mee-button
              label="Save & finish"
              variant="primary"
              (clicked)="onNext()"
              aria-label="Save and finish — navigate to images" />
          } @else {
            <mee-button
              label="Next"
              variant="primary"
              [disabled]="!canAdvance()"
              (clicked)="onNextStep()"
              [attr.aria-label]="canAdvance() ? 'Next step' : 'Fill required fields to continue'" />
          }
        </div>
      </nav>
    }
  `,
})
export class CatalogFormComponent implements OnInit, AfterViewInit {
  private readonly route      = inject(ActivatedRoute);
  private readonly router     = inject(Router);
  private readonly apiSvc     = inject(CatalogFormApiService);
  private readonly toast      = inject(MeeToastService);
  private readonly destroyRef = inject(DestroyRef);

  /** Template ref for the error region — focused on mount when categoryIdMissing. */
  @ViewChild('errorRegionRef') private readonly errorRegionRef?: ElementRef<HTMLElement>;

  // ── State signals ──────────────────────────────────────────────────────────────
  readonly loading             = signal(true);
  readonly schema              = signal<FieldGroup[]>([]);
  readonly fieldValues         = signal<Record<string, unknown>>({});
  readonly aiSuggestions       = signal<AutofillResponse['suggestions']>({});
  readonly saveStatus          = signal<'idle' | 'saving' | 'saved' | 'error'>('idle');
  readonly autofilling         = signal(false);
  readonly autofillUnavailable = signal(false);
  readonly fallbackOffered     = signal(false);
  readonly productId           = signal<string>('');
  readonly categoryId          = signal<string | null>(null);
  readonly categoryIdMissing   = signal(false);
  readonly errorMessage        = signal<string | null>(null);
  readonly enumCache           = signal<Record<string, Array<{ label: string; value: string }>>>({});
  readonly stepEnumsLoading    = signal(false);
  /** Active wizard step index (0-based). */
  readonly activeStepIndex     = signal(0);
  /** Whether the "More details" collapsible section is open in the current step. */
  readonly moreDetailsOpen     = signal(false);
  /** Whether the front image (slot 1) has been uploaded — for photos warning. */
  readonly hasFrontImage       = signal(false);

  private readonly autosaveTrigger$ = new Subject<void>();

  // ── Computed ───────────────────────────────────────────────────────────────────

  readonly productName = computed<string>(() => {
    const v = this.fieldValues()['product_name'];
    return (typeof v === 'string' && v) ? v : 'New Product';
  });

  readonly categoryPath = computed<string>(() => 'Fashion > Women > Ethnic > Kurti');

  /**
   * wizardSteps — all fields from the schema grouped by step_id into WizardStep[].
   * The 'photos' step is synthesised by ImageUploaderComponent (fields array is empty).
   * Only non-empty steps (or the photos step when it should appear) are included.
   */
  readonly wizardSteps = computed<WizardStep[]>(() => {
    const allFields: FieldSchema[] = this.schema().flatMap(g => g.fields);
    return groupIntoSteps(allFields);
  });

  /** Steps as MeeStep[] for the mee-steps component. */
  readonly meeStepItems = computed<MeeStep[]>(() =>
    this.wizardSteps().map(s => ({ label: s.label })),
  );

  /** The active WizardStep object. */
  readonly activeStep = computed<WizardStep | undefined>(() =>
    this.wizardSteps()[this.activeStepIndex()],
  );

  /** True when the current step is the 'photos' step (renders ImageUploaderComponent). */
  readonly isPhotosStep = computed<boolean>(() =>
    this.activeStep()?.id === 'photos',
  );

  /** True when the active step is the last step in the wizard. */
  readonly isLastStep = computed<boolean>(() =>
    this.activeStepIndex() === this.wizardSteps().length - 1,
  );

  /** Required fields for the active step. */
  readonly activeStepRequiredFields = computed<FieldSchema[]>(() =>
    (this.activeStep()?.fields ?? []).filter((f: FieldSchema) => f.required),
  );

  /** Optional fields for the active step. */
  readonly activeStepOptionalFields = computed<FieldSchema[]>(() =>
    (this.activeStep()?.fields ?? []).filter((f: FieldSchema) => !f.required),
  );

  /**
   * canAdvance — whether the Next button is enabled.
   * Blocks only when current step has unfilled required fields.
   * Photos step never blocks (warn-only). Steps with requiredCount===0 are freely skippable.
   */
  readonly canAdvance = computed<boolean>(() =>
    canAdvanceFromStep(this.activeStep(), this.fieldValues()),
  );

  /**
   * showPhotosWarning — non-blocking warning when on photos step without front image.
   */
  readonly showPhotosWarning = computed<boolean>(() =>
    hasPhotosStepFrontMissing(this.activeStep()?.id ?? '', this.hasFrontImage()),
  );

  readonly suggestionEntries = computed<Array<{ canonical: string; value: unknown }>>(() =>
    Object.entries(this.aiSuggestions()).map(([canonical, s]) => ({ canonical, value: s.value })),
  );

  readonly hasSuggestions = computed<boolean>(() => this.suggestionEntries().length > 0);

  readonly autosaveStatusLabel = computed<string>(() => {
    switch (this.saveStatus()) {
      case 'saving': return 'Saving...';
      case 'saved':  return 'Saved';
      case 'error':  return 'Save failed';
      default:       return '';
    }
  });

  readonly autosaveStatusClass = computed<string>(() =>
    this.saveStatus() === 'error'
      ? 'mee-autosave-status mee-autosave-status--error'
      : 'mee-autosave-status',
  );

  // ── Lifecycle ──────────────────────────────────────────────────────────────────

  ngAfterViewInit(): void {
    // Focus management handled in ngOnInit callback (async — see Wave 2B notes).
  }

  /**
   * resolveInitOutcome — pure helper for ngOnInit() product-fetch resolution.
   * GAP-1: reads category_id from GET /products/{id} (not router nav state).
   */
  resolveInitOutcome(product: ProductDetailResponse | null): { categoryId: string | null; missing: boolean } {
    if (!product) return { categoryId: null, missing: true };
    const catId = product.category_id;
    if (!catId) return { categoryId: null, missing: true };
    return { categoryId: catId, missing: false };
  }

  ngOnInit(): void {
    const id = (this.route.snapshot.params['id'] as string | undefined) ?? 'new';
    this.productId.set(id);

    this.apiSvc.getProduct(id).subscribe({
      next: (product) => {
        const outcome = this.resolveInitOutcome(product);
        if (outcome.missing) {
          this.categoryIdMissing.set(true);
          this.loading.set(false);
          Promise.resolve().then(() => {
            this.errorRegionRef?.nativeElement?.focus();
          });
          return;
        }

        const catId = outcome.categoryId!;
        this.categoryId.set(catId);

        this.autosaveTrigger$
          .pipe(debounceTime(10_000), takeUntilDestroyed(this.destroyRef))
          .subscribe(() => this.performAutosave());

        this.apiSvc.getDraft(id).subscribe({
          next: (draft) => {
            if (draft?.fields && Object.keys(draft.fields).length > 0) {
              this.fieldValues.set(draft.fields);
            }
            this.loadSchema(catId);
          },
          error: () => this.loadSchema(catId),
        });
      },
      error: (err: { status?: number }) => {
        this.errorMessage.set(
          err.status === 401
            ? 'Session expired. Please log in again.'
            : 'Failed to load product. Please retry.',
        );
        this.loading.set(false);
      },
    });
  }

  private loadSchema(categoryId: string): void {
    this.apiSvc.getSchema(categoryId).subscribe({
      next: (groups) => {
        if (groups.length === 0) {
          this.errorMessage.set('Could not load form fields. Check connection and retry.');
        }
        this.schema.set(groups);
        this.loading.set(false);
        // Spec §E: load enums for the first step lazily on schema load
        this.loadStepEnums(categoryId, 0);
      },
      error: () => {
        this.errorMessage.set('Failed to load product fields. Please retry.');
        this.loading.set(false);
      },
    });
  }

  /**
   * loadStepEnums — lazily loads API enum options for all needs_api_enum fields
   * in the given step. Called when a step becomes active.
   * Spec §E: lazy per-step loading; enumCache deduplicates repeat visits.
   */
  private loadStepEnums(categoryId: string, stepIndex: number): void {
    const steps = this.wizardSteps();
    const step = steps[stepIndex];
    if (!step) return;

    const fieldsNeedingEnum = step.fields.filter(
      (f: FieldSchema) => f.needs_api_enum && f.api_enum_field_name && !this.enumCache()[f.canonical_name],
    );

    if (fieldsNeedingEnum.length === 0) return;

    this.stepEnumsLoading.set(true);
    let pending = fieldsNeedingEnum.length;

    for (const field of fieldsNeedingEnum) {
      this.apiSvc
        .getFieldEnum(categoryId, field.api_enum_field_name!)
        .pipe(takeUntilDestroyed(this.destroyRef))
        .subscribe(entries => {
          const opts = entries.map((e: EnumEntryDTO) => ({
            label: e.meesho || e.canonical,
            value: e.canonical,
          }));
          this.enumCache.update(cache => ({ ...cache, [field.canonical_name]: opts }));
          pending--;
          if (pending === 0) this.stepEnumsLoading.set(false);
        });
    }
  }

  // ── Step navigation ───────────────────────────────────────────────────────────

  /**
   * onStepChange — called when the user clicks a stepper header item.
   * Allows free navigation (clicking any step header); canAdvance is only
   * enforced by the Next button.
   */
  onStepChange(index: number): void {
    const catId = this.categoryId();
    this.activeStepIndex.set(index);
    this.moreDetailsOpen.set(false);
    if (catId) this.loadStepEnums(catId, index);
  }

  onNextStep(): void {
    const nextIndex = this.activeStepIndex() + 1;
    if (nextIndex >= this.wizardSteps().length) return;
    this.onStepChange(nextIndex);
  }

  toggleMoreDetails(): void {
    this.moreDetailsOpen.update(v => !v);
  }

  // ── Public helpers ────────────────────────────────────────────────────────────

  getFieldOptions(field: FieldSchema): Array<{ label: string; value: string }> {
    return field.needs_api_enum
      ? (this.enumCache()[field.canonical_name] ?? [])
      : (field.enum_options ?? []);
  }

  isAiSuggested(canonicalName: string): boolean {
    return canonicalName in this.aiSuggestions();
  }

  getFieldError(canonicalName: string): string | undefined {
    const allFields: FieldSchema[] = this.schema().flatMap(g => g.fields);
    const field = allFields.find(f => f.canonical_name === canonicalName);
    if (!field?.required) return undefined;
    return !this.fieldValues()[canonicalName] ? `${field.display_name} is required` : undefined;
  }

  // ── Autofill overlay handlers ─────────────────────────────────────────────────

  applySuggestion(canonical: string): void {
    const suggestion = this.aiSuggestions()[canonical];
    if (suggestion) this.fieldValues.update(cur => ({ ...cur, [canonical]: suggestion.value }));
    this.dismissSuggestion(canonical);
  }

  dismissSuggestion(canonical: string): void {
    this.aiSuggestions.update(cur => { const { [canonical]: _, ...rest } = cur; return rest; });
  }

  dismissAllSuggestions(): void {
    this.aiSuggestions.set({});
    this.fallbackOffered.set(false);
  }

  // ── Event handlers ────────────────────────────────────────────────────────────

  onFieldBlur(canonicalName: string, value: string): void {
    this.fieldValues.update(cur => ({ ...cur, [canonicalName]: value }));
    if (canonicalName in this.aiSuggestions()) this.dismissSuggestion(canonicalName);
    this.autosaveTrigger$.next();
  }

  onFieldChange(canonicalName: string, value: unknown): void {
    this.fieldValues.update(cur => ({ ...cur, [canonicalName]: value }));
    if (canonicalName in this.aiSuggestions()) this.dismissSuggestion(canonicalName);
    this.autosaveTrigger$.next();
  }

  onAutofill(): void {
    const description = this.fieldValues()['product_name'];
    if (typeof description !== 'string' || !description.trim()) {
      this.toast.error('Add a product name first — autofill needs it.');
      return;
    }
    this.autofilling.set(true);
    this.fallbackOffered.set(false);
    this.aiSuggestions.set({});
    this.apiSvc.autofill(this.productId(), description).subscribe({
      next: (resp: AutofillResponse) => {
        this.aiSuggestions.set(resp.suggestions);
        if (resp.fallback_offered && Object.keys(resp.suggestions).length === 0) {
          this.fallbackOffered.set(true);
        }
        this.autofilling.set(false);
      },
      error: (err: { status?: number }) => {
        this.autofilling.set(false);
        if (err.status === 402) {
          this.toast.error('AI fill quota reached. Upgrade your plan to continue.');
        } else if (err.status === 404) {
          this.autofillUnavailable.set(true);
          this.toast.error('AI fill is not available in your current plan.');
        } else {
          this.toast.error('AI fill failed. Please try again.');
        }
      },
    });
  }

  onRetry(): void {
    const catId = this.categoryId();
    if (!catId) {
      this.categoryIdMissing.set(false);
      this.errorMessage.set(null);
      this.loading.set(true);
      this.ngOnInit();
      return;
    }
    this.errorMessage.set(null);
    this.loading.set(true);
    this.loadSchema(catId);
  }

  onBack(): void {
    const prevIndex = this.activeStepIndex() - 1;
    if (prevIndex >= 0) {
      this.onStepChange(prevIndex);
    }
  }

  onDashboard(): void {
    void this.router.navigate(['/dashboard']);
  }

  /** Last step primary action: navigate to /images (existing behaviour). */
  onNext(): void {
    void this.router.navigate(['/catalogs', this.productId(), 'images']);
  }

  // ── Private ───────────────────────────────────────────────────────────────────

  private performAutosave(): void {
    this.saveStatus.set('saving');
    this.apiSvc.autosave(this.productId(), this.fieldValues()).subscribe({
      next: () => {
        this.saveStatus.set('saved');
        setTimeout(() => {
          if (this.saveStatus() === 'saved') this.saveStatus.set('idle');
        }, 3000);
      },
      error: () => {
        this.saveStatus.set('error');
        this.toast.error('Autosave failed. Check your connection.');
      },
    });
  }
}
