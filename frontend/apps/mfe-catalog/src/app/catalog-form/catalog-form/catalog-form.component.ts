// catalog-form.component.ts — Wave 6C builder-3 UI polish
// Route: /catalogs/:id/edit — dynamic field form, real HTTP, autosave, autofill overlay.
// Builder-3 changes (UI Styler):
//   - loading skeletons: 3-section skeleton matching real form shape
//   - error-state a11y: categoryIdMissing banner focus management + role="alert"
//   - autofill overlay: token-based colours (no hardcoded hex), 44px touch targets
//   - aria-live on autosave status + role="status" + aria-atomic="true"
//   - 360px section spacing via :host CSS; 1280px two-column grid via md:grid layout
//   - all interactive targets confirmed ≥44px (min-height in styles:[] + mee-button default)

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
  MeeToastService,
} from '@mesell/ui-kit';
import {
  LoadingSkeletonComponent,
  PageHeaderComponent,
  StatusBadgeComponent,
  MeeAlertBannerComponent,
  MeeOfflineBannerComponent,
} from '@mesell/composites';

import type {
  FieldGroup,
  FieldSchema,
  EnumEntryDTO,
  AutofillResponse,
} from '../services/catalog-form-api.service';
import { CatalogFormApiService } from '../services/catalog-form-api.service';

/** Section descriptor — drives @for over 3 sections without template repetition. */
interface SectionDef {
  id: string;
  label: string;
  open: boolean;
  fields: FieldSchema[];
}

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
    LoadingSkeletonComponent,
    PageHeaderComponent,
    StatusBadgeComponent,
    MeeAlertBannerComponent,
    MeeOfflineBannerComponent,
  ],
  styles: [`
    /* ── Host layout ────────────────────────────────────────────────── */
    :host { display: block; }

    /* ── Form page wrapper: 360px baseline → 1280px two-column ──────── */
    .mee-form-page {
      /* Mobile: single column, 16px side padding */
      max-width: 100%;
      margin: 0 auto;
      padding: var(--mee-space-4);           /* 16px — fits 360px without overflow */
    }

    /* Loading skeleton region */
    .mee-skeleton-region {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-5);               /* 20px between skeleton blocks */
    }

    /* Skeleton section block that mirrors the real 3-section layout */
    .mee-skeleton-section {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-3);               /* 12px between skeleton rows */
    }
    .mee-skeleton-heading {
      height: 44px;                          /* mirrors section-toggle min-height */
      border-radius: var(--mee-radius-sm);
      background: var(--mee-color-outline);
      width: 40%;
      animation: mee-pulse 1.5s ease-in-out infinite;
    }

    /* ── Section accordion toggle ────────────────────────────────────── */
    .section-toggle {
      display: flex;
      width: 100%;
      align-items: center;
      justify-content: space-between;
      padding: 10px 0;
      font-weight: 500;
      text-align: left;
      background: none;
      border: none;
      border-bottom: 1px solid var(--mee-color-outline);
      cursor: pointer;
      min-height: 44px;                      /* WCAG 2.5.8 — 44px touch target */
      color: var(--mee-color-on-surface);
    }
    .section-toggle:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
    }
    .section-toggle__label { font-size: 0.9375rem; }
    .section-toggle__hint  {
      font-size: 0.8125rem;
      font-weight: 400;
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Field section spacing: 360px single-col ─────────────────────── */
    .mee-form-sections {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-2);               /* 8px between sections at 360px */
    }
    .mee-section-fields {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);               /* 16px between fields at 360px */
      padding-top: var(--mee-space-4);
    }

    /* ── AI-suggested field highlight ───────────────────────────────── */
    .field-wrapper {
      background-color: transparent;
      transition: background-color var(--mee-transition-fast);
    }
    .field-wrapper.mee-ai-suggested {
      padding: var(--mee-space-2);           /* 8px */
      border-radius: var(--mee-radius-sm);
      outline: 1px solid var(--mee-color-warning);
      outline-offset: 2px;
      background-color: var(--mee-color-warning-light);
    }

    /* ── Autofill suggestion overlay ────────────────────────────────── */
    .mee-autofill-overlay {
      /* Token-based — no hardcoded hex (builder-3 fix). */
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
      gap: var(--mee-space-2);               /* 8px */
      padding: 6px 0;
      border-bottom: 1px solid var(--mee-color-outline);
      /* 44px min-height — inherited from flex items (buttons ≥44px by mee-button) */
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

    /* ── Autosave status indicator ───────────────────────────────────── */
    .mee-autosave-status {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
    }
    .mee-autosave-status--error { color: var(--mee-color-error); }

    /* ── Footer bar ──────────────────────────────────────────────────── */
    .mee-form-footer {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding-top: var(--mee-space-3);
      padding-bottom: var(--mee-space-4);
      border-top: 1px solid var(--mee-color-outline);
      margin-top: var(--mee-space-4);
    }

    /* ── Error/missing-category banner wrapper ───────────────────────── */
    .mee-error-region {
      margin-top: var(--mee-space-4);
    }
    .mee-error-cta {
      display: flex;
      justify-content: center;
      margin-top: var(--mee-space-4);
    }

    /* ── Skeleton pulse animation ────────────────────────────────────── */
    @keyframes mee-pulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.45; }
    }

    /* ── 768px+ (tablet): increase form width, more breathing room ───── */
    @media (min-width: 768px) {
      .mee-form-page {
        max-width: 42rem;                    /* ~672px — md:max-w-2xl equivalent */
        padding: var(--mee-space-6) var(--mee-space-8);
      }
      .mee-form-sections {
        gap: var(--mee-space-3);             /* 12px between sections */
      }
      .mee-section-fields {
        gap: var(--mee-space-5);             /* 20px between fields */
      }
    }

    /* ── 1280px+ (desktop): two-column layout per spec ───────────────── */
    @media (min-width: 1280px) {
      .mee-form-page {
        max-width: 64rem;                    /* ~1024px max on xl screens */
        padding: var(--mee-space-8) var(--mee-space-10);
      }
      /* Two-column grid: form sections on left, overlay/status on right */
      .mee-form-layout {
        display: grid;
        grid-template-columns: 1fr 20rem;  /* main form | sidebar */
        gap: var(--mee-space-8);
        align-items: start;
      }
      /* Sidebar column: autofill overlay + autosave status pinned to top */
      .mee-form-sidebar {
        position: sticky;
        top: var(--mee-space-4);
      }
    }
  `],
  template: `
    <!-- a11y: categoryIdMissing error banner ref for programmatic focus -->
    <div #errorRegionRef>

    <div class="mee-form-page">
      <mee-offline-banner />

      <!-- categoryIdMissing: critical error state — GAP-1 (spec §4) hard-reload path -->
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
        <!-- Page header: product name + category breadcrumb -->
        <mee-page-header [title]="productName()" [subtitle]="categoryPath()" />

        <!-- Inline error banner: schema load failure / flag-OFF -->
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
        <div class="flex items-center justify-between mt-3 mb-5">
          <mee-status-badge [status]="'draft'" />
          <mee-button
            label="AI fill"
            variant="secondary"
            icon="auto_awesome"
            [loading]="autofilling()"
            [disabled]="loading() || autofillUnavailable()"
            (clicked)="onAutofill()"
            aria-label="Fill fields with AI suggestions" />
        </div>

        <!-- ── 1280px two-column layout wrapper ──────────────────────── -->
        <div class="mee-form-layout">

          <!-- Left: form sections -->
          <div>
            <!-- Loading skeleton: mirrors 3-section real form layout -->
            @if (loading()) {
              <div class="mee-skeleton-region"
                   role="status"
                   aria-live="polite"
                   aria-label="Loading product form fields, please wait">
                <!-- Skeleton section 1: Compulsory (5 fields) -->
                <div class="mee-skeleton-section">
                  <div class="mee-skeleton-heading" aria-hidden="true"></div>
                  <mee-loading-skeleton variant="text" [lines]="4" />
                </div>
                <!-- Skeleton section 2: Recommended (3 fields) -->
                <div class="mee-skeleton-section">
                  <div class="mee-skeleton-heading" aria-hidden="true"></div>
                  <mee-loading-skeleton variant="text" [lines]="3" />
                </div>
                <!-- Skeleton section 3: Optional / Advanced (2 fields) -->
                <div class="mee-skeleton-section">
                  <div class="mee-skeleton-heading" aria-hidden="true"></div>
                  <mee-loading-skeleton variant="text" [lines]="2" />
                </div>
              </div>
            }

            @if (!loading()) {
              <div class="mee-form-sections">
                @for (sec of sections(); track sec.id) {
                  <section [attr.aria-labelledby]="sec.id + '-heading'">
                    <button
                      type="button"
                      [id]="sec.id + '-heading'"
                      class="section-toggle"
                      (click)="toggleSection(sec.id)"
                      [attr.aria-expanded]="sec.open">
                      <span class="section-toggle__label">{{ sec.label }} ({{ sec.fields.length }})</span>
                      <span class="section-toggle__hint" aria-hidden="true">
                        {{ sec.open ? 'Collapse' : 'Expand' }}
                      </span>
                    </button>
                    @if (sec.open) {
                      <div class="mee-section-fields">
                        @for (field of sec.fields; track field.canonical_name) {
                          <div class="field-wrapper"
                               [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)">
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
                  </section>
                }
              </div>
            }
          </div><!-- /Left column -->

          <!-- Right: autofill overlay + AI fallback (sidebar at 1280px; stacked below at <1280px) -->
          <div class="mee-form-sidebar">
            <!-- Autofill suggestion overlay — token-based colours, 44px touch targets -->
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

            <!-- AI autofill fallback: shown when AI ran but returned no suggestions -->
            @if (fallbackOffered()) {
              <div class="mb-3">
                <mee-alert-banner
                  variant="warning"
                  message="AI couldn't fill — try adding more product details before using AI fill." />
              </div>
            }
          </div><!-- /Right column / sidebar -->

        </div><!-- /mee-form-layout -->

        <!-- Footer: autosave status + navigation — below both columns -->
        @if (!loading()) {
          <div class="mee-form-footer">
            <!-- Autosave status: aria-live="polite" + role="status" + aria-atomic="true"
                 so screen readers announce status changes without interrupting editing. -->
            <span
              role="status"
              aria-live="polite"
              aria-atomic="true"
              [class]="autosaveStatusClass()">
              {{ autosaveStatusLabel() }}
            </span>
            <div class="flex gap-2">
              <mee-button label="Back" variant="ghost" (clicked)="onBack()" />
              <mee-button label="Images" icon="arrow_forward" (clicked)="onNext()" />
            </div>
          </div>
        }
      }
    </div><!-- /mee-form-page -->
    </div><!-- /#errorRegionRef -->
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

  // Signals
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
  private readonly sectionOpen = signal<Record<string, boolean>>({ compulsory: true, recommended: false, optional: false });
  private readonly autosaveTrigger$ = new Subject<void>();

  // Computed
  readonly productName = computed<string>(() => {
    const v = this.fieldValues()['product_title'];
    return (typeof v === 'string' && v) ? v : 'New Product';
  });
  readonly categoryPath = computed<string>(() => 'Fashion > Women > Ethnic > Kurti');
  readonly compulsoryFields = computed<FieldSchema[]>(() =>
    this.schema().find(g => g.group === 'compulsory')?.fields ?? []
  );
  readonly recommendedFields = computed<FieldSchema[]>(() =>
    this.schema().find(g => g.group === 'recommended')?.fields ?? []
  );
  readonly optionalFields = computed<FieldSchema[]>(() =>
    this.schema().find(g => g.group === 'optional')?.fields ?? []
  );
  readonly isFormComplete = computed<boolean>(() =>
    this.compulsoryFields().every(f => !!this.fieldValues()[f.canonical_name])
  );
  readonly sections = computed<SectionDef[]>(() => {
    const open = this.sectionOpen();
    return [
      { id: 'compulsory',  label: 'Compulsory',  open: !!open['compulsory'],  fields: this.compulsoryFields() },
      { id: 'recommended', label: 'Recommended', open: !!open['recommended'], fields: this.recommendedFields() },
      { id: 'optional',    label: 'Optional',    open: !!open['optional'],    fields: this.optionalFields() },
    ];
  });
  readonly suggestionEntries = computed<Array<{ canonical: string; value: unknown }>>(() =>
    Object.entries(this.aiSuggestions()).map(([canonical, s]) => ({ canonical, value: s.value }))
  );
  readonly hasSuggestions = computed<boolean>(() => this.suggestionEntries().length > 0);

  /**
   * autosaveStatusLabel — human-readable autosave status for the footer indicator.
   * The aria-live="polite" span announces this via screen-readers on change.
   * Empty string on 'idle' so screen readers don't announce a meaningless initial state.
   */
  readonly autosaveStatusLabel = computed<string>(() => {
    switch (this.saveStatus()) {
      case 'saving': return 'Saving...';
      case 'saved':  return 'Saved';
      case 'error':  return 'Save failed';
      default:       return '';
    }
  });

  /**
   * autosaveStatusClass — CSS class driving the colour of the autosave status span.
   * Uses :host-scoped BEM class names defined in styles:[].
   */
  readonly autosaveStatusClass = computed<string>(() =>
    this.saveStatus() === 'error'
      ? 'mee-autosave-status mee-autosave-status--error'
      : 'mee-autosave-status'
  );

  ngAfterViewInit(): void {
    // A11y: when categoryIdMissing is set on init, programmatically focus the error
    // region so screen-readers announce it immediately. Deferred microtask avoids
    // calling focus() during Angular's change detection cycle (Wave 6A pattern).
    if (this.categoryIdMissing()) {
      Promise.resolve().then(() => {
        this.errorRegionRef?.nativeElement?.focus();
      });
    }
  }

  ngOnInit(): void {
    const id = (this.route.snapshot.params['id'] as string | undefined) ?? 'new';
    this.productId.set(id);

    // GAP-1 (spec §4): category_id from Router navigation state; explicit error on hard-reload.
    const navState = this.router.getCurrentNavigation()?.extras.state as
      | { categoryId?: string } | null | undefined;
    const catId = navState?.['categoryId'] as string | undefined;

    if (!catId) {
      this.categoryIdMissing.set(true);
      this.loading.set(false);
      return;
    }

    this.categoryId.set(catId);

    this.autosaveTrigger$
      .pipe(debounceTime(10_000), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.performAutosave());

    // #22 getDraft — pre-fill fieldValues on resume. Non-blocking: proceeds to loadSchema on success OR error.
    this.apiSvc.getDraft(id).subscribe({
      next: (draft) => {
        if (draft?.fields && Object.keys(draft.fields).length > 0) {
          this.fieldValues.set(draft.fields);
        }
        this.loadSchema(catId);
      },
      error: () => this.loadSchema(catId),
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
        // Pre-load enum options for needs_api_enum fields (#16) at schema-load time.
        // V1 strategy: MeeSelectComponent has no dropdown-open event — pre-load eagerly.
        this.preloadApiEnums(categoryId, groups);
      },
      error: () => {
        this.errorMessage.set('Failed to load product fields. Please retry.');
        this.loading.set(false);
      },
    });
  }

  private preloadApiEnums(categoryId: string, groups: FieldGroup[]): void {
    groups.flatMap(g => g.fields)
      .filter(f => f.needs_api_enum && f.api_enum_field_name)
      .forEach(field => {
        this.apiSvc
          .getFieldEnum(categoryId, field.api_enum_field_name!)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe(entries => {
            const opts = entries.map((e: EnumEntryDTO) => ({ label: e.meesho || e.canonical, value: e.canonical }));
            this.enumCache.update(cache => ({ ...cache, [field.canonical_name]: opts }));
          });
      });
  }

  // Public helpers
  toggleSection(id: string): void {
    this.sectionOpen.update(s => ({ ...s, [id]: !s[id] }));
  }

  getFieldOptions(field: FieldSchema): Array<{ label: string; value: string }> {
    return field.needs_api_enum ? (this.enumCache()[field.canonical_name] ?? []) : (field.enum_options ?? []);
  }

  isAiSuggested(canonicalName: string): boolean {
    return canonicalName in this.aiSuggestions();
  }

  getFieldError(canonicalName: string): string | undefined {
    const allFields = [...this.compulsoryFields(), ...this.recommendedFields(), ...this.optionalFields()];
    const field = allFields.find(f => f.canonical_name === canonicalName);
    if (!field?.required) return undefined;
    return !this.fieldValues()[canonicalName] ? `${field.display_name} is required` : undefined;
  }

  // Autofill overlay handlers
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
  // Event handlers
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
    const description = this.fieldValues()['product_title'];
    if (typeof description !== 'string' || !description.trim()) {
      this.toast.error('Add a product title first — autofill needs it.');
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
    if (!catId) return;
    this.errorMessage.set(null);
    this.loading.set(true);
    this.loadSchema(catId);
  }

  onBack(): void {
    void this.router.navigate(['/dashboard']);
  }

  onNext(): void {
    void this.router.navigate(['/catalogs', this.productId(), 'images']);
  }

  // Private
  private performAutosave(): void {
    this.saveStatus.set('saving');
    this.apiSvc.autosave(this.productId(), this.fieldValues()).subscribe({
      next: () => this.saveStatus.set('saved'),
      error: () => {
        this.saveStatus.set('error');
        this.toast.error('Autosave failed. Check your connection.');
      },
    });
  }
}
