// features/catalog-form/catalog-form/catalog-form.component.ts
// Wave 5 — F8: Catalog Form
// Route: /catalogs/:id/edit (shell child, auth-guarded)
// Renders a dynamic category-specific field form using mee-* UI Kit primitives.
// Dynamic fields use Record<string,unknown> signal — NOT FormGroup (JSONB schema).
// AI auto-fill highlights compulsory fields in yellow; autosaves on blur/change.
//
// Conditional Field UX (PR #290):
//   schemaRules signal — populated from /schema dependency_rules[] (backend PR #290)
//   fieldOverrides computed — evaluates rules against current field values (pure fn)
//   activeSoftRules computed — soft rules currently firing (for recommendation banners)

import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  OnInit,
  signal,
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
} from '@mesell/composites';
import { MeePageComponent } from '@mesell/layout';

import type { AutofillResponse, FieldGroup, FieldSchema, DependencyRuleDTO } from '../models/field-schema.model';
import { CatalogFormApiService } from '../services/catalog-form-api.service';
import { evaluateRules, getSoftRules } from '../catalog-form.rules';
import type { DependencyRule, FieldOverride } from '../catalog-form.rules';

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
    MeePageComponent,
  ],
  styles: [`
    /* ── Host ─────────────────────────────────────────────────────────── */
    :host { display: block; }

    /* ── Page inner padding: mobile-first 360px baseline ───────────────── */
    /* mee-page (maxWidth="xl" padding="none") provides the 1280px centering.
       .mee-form-page provides padding + sticky-nav clearance padding-bottom. */
    .mee-form-page {
      padding: var(--mee-space-4);
      /* Default mobile: form-nav (64px) sits above shell bottom-tab (60px),
         so page only needs to clear the form-nav itself.
         The @media ≤639px override below sets the correct combined value.
         On tablet+ (≥640px) the shell bottom-tab is gone. */
      padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
    }

    /* ── Sticky bottom navigation bar ─────────────────────────────────── */
    .mee-form-nav {
      position: fixed;
      /* Default (tablet+): sit at bottom, no shell bottom-tab present */
      bottom: 0;
      left: 0;
      right: 0;
      z-index: 110; /* above shell bottom-tab (z-index:100) */
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: var(--mee-space-3) var(--mee-space-4);
      background: var(--mee-color-surface);
      border-top: 1px solid var(--mee-color-outline);
      box-shadow: var(--mee-shadow-sm);
      min-height: 64px;
    }
    .mee-form-nav__status {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
    }
    .mee-form-nav__status--error {
      color: var(--mee-color-error);
    }
    .mee-form-nav__actions {
      display: flex;
      gap: var(--mee-space-2);
      align-items: center;
    }

    /* ── AI fill button: full-width on mobile ──────────────────────────── */
    .mee-ai-fill-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: var(--mee-space-2);
      margin-top: var(--mee-space-3);
      margin-bottom: var(--mee-space-5);
    }

    /* ── Section card wrapper ──────────────────────────────────────────── */
    .mee-section-card {
      background: var(--mee-color-surface);
      border: 1px solid var(--mee-color-outline);
      border-radius: var(--mee-radius-md);
      box-shadow: var(--mee-shadow-sm);
      padding: var(--mee-space-5) var(--mee-space-6);
      margin-bottom: var(--mee-space-4);
    }

    /* ── Accordion section toggle ──────────────────────────────────────── */
    .section-toggle {
      display: flex;
      width: 100%;
      align-items: center;
      justify-content: space-between;
      padding: var(--mee-space-1) 0 var(--mee-space-3);
      font-size: 1rem;
      font-weight: 600;
      text-align: left;
      background: none;
      border: none;
      border-bottom: 1px solid var(--mee-color-outline);
      cursor: pointer;
      /* 44px minimum touch target */
      min-height: 44px;
      color: var(--mee-color-on-surface);
    }
    .section-toggle:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
      border-radius: var(--mee-radius-sm);
    }
    .section-toggle__chevron {
      font-size: 0.75rem;
      font-weight: 400;
      color: var(--mee-color-on-surface-muted);
    }

    /* ── Field list: single column on mobile (flex) ────────────────────── */
    .mee-field-list {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
      padding-top: var(--mee-space-4);
    }

    /* ── Loading skeleton stack ────────────────────────────────────────── */
    .form-fields-stack {
      display: flex;
      flex-direction: column;
      gap: var(--mee-space-4);
    }

    /* Full-width spanner: text_long (textarea) fields span both columns on grid */
    .mee-field--full {
      grid-column: 1 / -1;
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
      /* Tint derived from the warning token via low-alpha overlay (no new token needed) */
      background-color: color-mix(in srgb, var(--mee-color-warning) 12%, transparent);
    }

    /* ── Soft dependency-rule recommendation banner ─────────────────────── */
    /* Shown below a field when a soft rule is currently firing for it.      */
    .mee-soft-rule-banner {
      display: flex;
      align-items: flex-start;
      gap: var(--mee-space-2);
      margin-top: var(--mee-space-1);
      padding: var(--mee-space-2) var(--mee-space-3);
      border-radius: var(--mee-radius-sm);
      background-color: color-mix(in srgb, var(--mee-color-warning) 10%, transparent);
      border: 1px solid color-mix(in srgb, var(--mee-color-warning) 40%, transparent);
      /* Ensure the banner does not create a tap-target taller than the field itself;
         min-height 44px applies to interactive controls — this is role=note (non-interactive) */
    }
    .mee-soft-rule-banner__icon {
      flex-shrink: 0;
      font-size: 0.875rem;
      color: var(--mee-color-warning);
      line-height: 1.4;
    }
    .mee-soft-rule-banner__text {
      font-size: 0.8125rem;
      color: var(--mee-color-on-surface-muted);
      line-height: 1.4;
    }

    /* ── Mobile only (≤639px): form nav sits above the shell bottom-tab ── */
    @media (max-width: 639px) {
      /* Shell bottom-tab is 60px tall. Raise the form nav above it. */
      .mee-form-nav {
        bottom: calc(60px + env(safe-area-inset-bottom, 0px));
      }
      /* Page padding-bottom = form-nav height (64px) + shell bottom-tab (60px) + safe area */
      .mee-form-page {
        padding-bottom: calc(64px + 60px + env(safe-area-inset-bottom, 0px));
      }
    }

    /* ── Tablet+ (≥768px): 2-col field grid ───────────────────────────── */
    @media (min-width: 768px) {
      .mee-form-page {
        padding: var(--mee-space-6) var(--mee-space-8);
        /* On tablet+ there's no shell bottom-tab (640px+ hides it).
           Only the sticky form nav (64px) needs clearance. */
        padding-bottom: calc(80px + env(safe-area-inset-bottom, 0px));
      }

      /* Two-column field grid on tablet+ */
      .mee-field-list {
        display: grid;
        grid-template-columns: 1fr 1fr;
        column-gap: var(--mee-space-6);
        row-gap: var(--mee-space-4);
      }
    }

    /* ── Desktop (≥1280px) ─────────────────────────────────────────────── */
    @media (min-width: 1280px) {
      .mee-form-page {
        padding: var(--mee-space-8) var(--mee-space-10);
        padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px));
      }
    }
  `],
  template: `
    <mee-page maxWidth="xl" padding="none">
    <div class="mee-form-page">

      <!-- Page Header -->
      <mee-page-header
        [title]="productName()"
        [subtitle]="categoryPath()"
      />

      <!-- Status badge + AI fill button -->
      <div class="mee-ai-fill-row">
        <mee-status-badge [status]="'draft'" />
        <mee-button
          label="AI fill"
          variant="secondary"
          icon="sparkles"
          [loading]="autofilling()"
          [disabled]="loading()"
          [testId]="'catalog-ai-fill'"
          (clicked)="onAutofill()"
          aria-label="Fill fields with AI suggestions"
        />
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="form-fields-stack"
             role="status"
             aria-live="polite"
             aria-label="Loading product form fields, please wait">
          <mee-loading-skeleton variant="text" [lines]="3" />
          <mee-loading-skeleton variant="text" [lines]="3" />
          <mee-loading-skeleton variant="text" [lines]="2" />
        </div>
      }

      <!-- Schema field groups -->
      @if (!loading()) {

        <!-- Compulsory section -->
        <section aria-labelledby="compulsory-heading" class="mee-section-card">
          <button
            type="button"
            id="compulsory-heading"
            class="section-toggle"
            (click)="compulsoryOpen.set(!compulsoryOpen())"
            [attr.aria-expanded]="compulsoryOpen()"
          >
            <span>Compulsory ({{ compulsoryFields().length }})</span>
            <span class="section-toggle__chevron" aria-hidden="true">
              {{ compulsoryOpen() ? '▲' : '▼' }}
            </span>
          </button>

          @if (compulsoryOpen()) {
            <div class="mee-field-list" aria-label="Compulsory fields">
              @for (field of compulsoryFields(); track field.canonical_name) {
                @if (isFieldVisible(field.canonical_name)) {
                  <div
                    class="field-wrapper"
                    [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                    [class.mee-field--full]="field.primitive === 'text_long'"
                  >
                    @switch (field.primitive) {
                      @case ('text_long') {
                        <mee-textarea
                          [label]="field.display_name"
                          [required]="isFieldRequired(field)"
                          [error]="getFieldError(field.canonical_name)"
                          [hint]="field.help_text"
                          [rows]="4"
                          (blur)="onFieldBlur(field.canonical_name, $any($event))"
                        />
                      }
                      @case ('enum') {
                        <mee-select
                          [label]="field.display_name"
                          [options]="field.enum_options ?? []"
                          [error]="getFieldError(field.canonical_name)"
                          (value_change)="onFieldChange(field.canonical_name, $event)"
                        />
                      }
                      @default {
                        <mee-input
                          [label]="field.display_name"
                          [required]="isFieldRequired(field)"
                          [error]="getFieldError(field.canonical_name)"
                          [hint]="field.help_text"
                          [type]="field.primitive === 'number' ? 'number' : 'text'"
                          (blur)="onFieldBlur(field.canonical_name, $any($event))"
                        />
                      }
                    }
                    @let softRule = getActiveSoftRule(field.canonical_name);
                    @if (softRule) {
                      <div class="mee-soft-rule-banner"
                           role="note"
                           [attr.aria-label]="'Recommendation for ' + field.display_name">
                        <span class="mee-soft-rule-banner__icon" aria-hidden="true">&#9432;</span>
                        <span class="mee-soft-rule-banner__text">Recommended for this listing type</span>
                      </div>
                    }
                  </div>
                }
              }
            </div>
          }
        </section>

        <!-- Recommended section -->
        <section aria-labelledby="recommended-heading" class="mee-section-card">
          <button
            type="button"
            id="recommended-heading"
            class="section-toggle"
            (click)="recommendedOpen.set(!recommendedOpen())"
            [attr.aria-expanded]="recommendedOpen()"
          >
            <span>Recommended ({{ recommendedFields().length }})</span>
            <span class="section-toggle__chevron" aria-hidden="true">
              {{ recommendedOpen() ? '▲' : '▼' }}
            </span>
          </button>

          @if (recommendedOpen()) {
            <div class="mee-field-list" aria-label="Recommended fields">
              @for (field of recommendedFields(); track field.canonical_name) {
                @if (isFieldVisible(field.canonical_name)) {
                  <div
                    class="field-wrapper"
                    [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                    [class.mee-field--full]="field.primitive === 'text_long'"
                  >
                    @switch (field.primitive) {
                      @case ('text_long') {
                        <mee-textarea
                          [label]="field.display_name"
                          [required]="isFieldRequired(field)"
                          [error]="getFieldError(field.canonical_name)"
                          [hint]="field.help_text"
                          [rows]="4"
                          (blur)="onFieldBlur(field.canonical_name, $any($event))"
                        />
                      }
                      @case ('enum') {
                        <mee-select
                          [label]="field.display_name"
                          [options]="field.enum_options ?? []"
                          [error]="getFieldError(field.canonical_name)"
                          (value_change)="onFieldChange(field.canonical_name, $event)"
                        />
                      }
                      @default {
                        <mee-input
                          [label]="field.display_name"
                          [required]="isFieldRequired(field)"
                          [error]="getFieldError(field.canonical_name)"
                          [hint]="field.help_text"
                          [type]="field.primitive === 'number' ? 'number' : 'text'"
                          (blur)="onFieldBlur(field.canonical_name, $any($event))"
                        />
                      }
                    }
                    @let softRule = getActiveSoftRule(field.canonical_name);
                    @if (softRule) {
                      <div class="mee-soft-rule-banner"
                           role="note"
                           [attr.aria-label]="'Recommendation for ' + field.display_name">
                        <span class="mee-soft-rule-banner__icon" aria-hidden="true">&#9432;</span>
                        <span class="mee-soft-rule-banner__text">Recommended for this listing type</span>
                      </div>
                    }
                  </div>
                }
              }
            </div>
          }
        </section>

        <!-- Optional section -->
        <section aria-labelledby="optional-heading" class="mee-section-card">
          <button
            type="button"
            id="optional-heading"
            class="section-toggle"
            (click)="optionalOpen.set(!optionalOpen())"
            [attr.aria-expanded]="optionalOpen()"
          >
            <span>Optional ({{ optionalFields().length }})</span>
            <span class="section-toggle__chevron" aria-hidden="true">
              {{ optionalOpen() ? '▲' : '▼' }}
            </span>
          </button>

          @if (optionalOpen()) {
            <div class="mee-field-list" aria-label="Optional fields">
              @for (field of optionalFields(); track field.canonical_name) {
                @if (isFieldVisible(field.canonical_name)) {
                  <div
                    class="field-wrapper"
                    [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                    [class.mee-field--full]="field.primitive === 'text_long'"
                  >
                    @switch (field.primitive) {
                      @case ('text_long') {
                        <mee-textarea
                          [label]="field.display_name"
                          [required]="isFieldRequired(field)"
                          [rows]="4"
                          (blur)="onFieldBlur(field.canonical_name, $any($event))"
                        />
                      }
                      @case ('enum') {
                        <mee-select
                          [label]="field.display_name"
                          [options]="field.enum_options ?? []"
                          (value_change)="onFieldChange(field.canonical_name, $event)"
                        />
                      }
                      @default {
                        <mee-input
                          [label]="field.display_name"
                          [required]="isFieldRequired(field)"
                          [type]="field.primitive === 'number' ? 'number' : 'text'"
                          (blur)="onFieldBlur(field.canonical_name, $any($event))"
                        />
                      }
                    }
                    @let softRule = getActiveSoftRule(field.canonical_name);
                    @if (softRule) {
                      <div class="mee-soft-rule-banner"
                           role="note"
                           [attr.aria-label]="'Recommendation for ' + field.display_name">
                        <span class="mee-soft-rule-banner__icon" aria-hidden="true">&#9432;</span>
                        <span class="mee-soft-rule-banner__text">Recommended for this listing type</span>
                      </div>
                    }
                  </div>
                }
              }
            </div>
          }
        </section>

      }
    </div>

    <!-- Sticky bottom navigation bar — outside page wrapper so it overlays correctly -->
    @if (!loading()) {
      <nav class="mee-form-nav" aria-label="Form navigation">
        <!-- Autosave status indicator -->
        <span
          role="status"
          aria-live="polite"
          aria-atomic="true"
          data-testid="catalog-save-status"
          [class]="saveStatus() === 'error' ? 'mee-form-nav__status mee-form-nav__status--error' : 'mee-form-nav__status'">
          @switch (saveStatus()) {
            @case ('saving') { Saving... }
            @case ('saved')  { Saved }
            @case ('error')  { Save failed }
            @default { &nbsp; }
          }
        </span>

        <!-- Back / Next actions -->
        <div class="mee-form-nav__actions">
          <mee-button
            label="Back"
            variant="ghost"
            (clicked)="onBack()"
            aria-label="Return to dashboard"
          />
          <mee-button
            label="Images"
            icon="forward"
            [testId]="'catalog-form-next'"
            (clicked)="onNext()"
            aria-label="Continue to images"
          />
        </div>
      </nav>
    }
    </mee-page>
  `,
})
export class CatalogFormComponent implements OnInit {
  private readonly route      = inject(ActivatedRoute);
  private readonly router     = inject(Router);
  private readonly apiSvc     = inject(CatalogFormApiService);
  private readonly toast      = inject(MeeToastService);
  private readonly destroyRef = inject(DestroyRef);

  // ── Signals ───────────────────────────────────────────────────────────────
  readonly loading         = signal(true);
  readonly schema          = signal<FieldGroup[]>([]);
  readonly fieldValues     = signal<Record<string, unknown>>({});
  readonly aiSuggestions   = signal<Record<string, unknown>>({});
  readonly saveStatus      = signal<'idle' | 'saving' | 'saved' | 'error'>('idle');
  readonly autofilling     = signal(false);
  readonly compulsoryOpen  = signal(true);
  readonly recommendedOpen = signal(false);
  readonly optionalOpen    = signal(false);
  readonly productId       = signal<string>('');

  /**
   * schemaRules — cross-field dependency rules from the /schema endpoint (PR #290).
   * Populated when the schema loads; stays [] when the backend is pre-PR#290.
   *
   * Typed as DependencyRule[] (from catalog-form.rules.ts) because evaluateRules()
   * and getSoftRules() accept DependencyRule[]. DependencyRuleDTO (field-schema.model.ts)
   * has an identical shape — DependencyRuleDTO.message_id is string (required) while
   * DependencyRule.message_id is string|undefined. The cast to DependencyRule[] in
   * ngOnInit is safe (DependencyRuleDTO satisfies DependencyRule structurally).
   */
  readonly schemaRules = signal<DependencyRule[]>([]);

  // ── Computed ──────────────────────────────────────────────────────────────

  /**
   * fieldOverrides — map of { [target_field]: { required, visible } } derived from
   * evaluating schemaRules[] against the current fieldValues.
   *
   * Pure computed — re-evaluates automatically when either schemaRules or fieldValues
   * change. No manual effect() or event wiring needed.
   */
  readonly fieldOverrides = computed<Record<string, FieldOverride>>(() =>
    evaluateRules(this.schemaRules(), this.fieldValues()),
  );

  /**
   * activeSoftRules — soft-severity rules that are currently firing.
   * Used to render yellow recommendation banners below fields.
   */
  readonly activeSoftRules = computed<DependencyRule[]>(() =>
    getSoftRules(this.schemaRules(), this.fieldValues()),
  );

  readonly productName = computed<string>(() => {
    const v = this.fieldValues()['product_name'] ?? this.fieldValues()['product_title'];
    return (typeof v === 'string' && v) ? v : 'New Product';
  });

  // categoryPath is Wave 6 — simulated for Wave 5
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

  // ── Autosave Subject ──────────────────────────────────────────────────────
  private readonly autosaveTrigger$ = new Subject<void>();

  // ── Lifecycle ─────────────────────────────────────────────────────────────
  ngOnInit(): void {
    const id = (this.route.snapshot.params['id'] as string | undefined) ?? 'new';
    this.productId.set(id);

    // Wire autosave pipeline in ngOnInit (DestroyRef injected explicitly — not constructor)
    this.autosaveTrigger$
      .pipe(debounceTime(10_000), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.performAutosave());

    // Load schema + dependency rules (PR #290: getSchemaWithRules returns both)
    this.apiSvc.getSchemaWithRules(id).subscribe({
      next: (result: { groups: FieldGroup[]; rules: DependencyRuleDTO[] }) => {
        this.schema.set(result.groups);
        // DependencyRuleDTO is structurally a subtype of DependencyRule
        // (both share all required fields; DTO.message_id is string vs Rule's string|undefined)
        this.schemaRules.set(result.rules as DependencyRule[]);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toast.error('Failed to load product schema. Please refresh.');
      },
    });
  }

  // ── Public helpers ────────────────────────────────────────────────────────

  isAiSuggested(canonicalName: string): boolean {
    return canonicalName in this.aiSuggestions();
  }

  /**
   * isFieldVisible — returns true when the field should be rendered.
   *
   * A field is hidden only when a 'show' dependency rule targets it AND its
   * predicate is NOT currently met. Fields with no show-rule are always visible.
   * Default is true (no rule = visible).
   */
  isFieldVisible(canonicalName: string): boolean {
    const override = this.fieldOverrides()[canonicalName];
    return override?.visible ?? true;
  }

  /**
   * isFieldRequired — returns whether the field is required (schema OR rule override).
   *
   * The schema-level required flag is the base. A dependency rule with action='required'
   * that is currently firing can make an optional field required at runtime.
   */
  isFieldRequired(field: FieldSchema): boolean {
    // Rule override takes precedence over schema default
    const override = this.fieldOverrides()[field.canonical_name];
    return override?.required ?? field.required;
  }

  /**
   * getActiveSoftRule — returns the first firing soft rule targeting a given field,
   * if any. Used to render a yellow recommendation chip below the field.
   *
   * Returns undefined when no soft rule is targeting this field.
   */
  getActiveSoftRule(canonicalName: string): DependencyRule | undefined {
    return this.activeSoftRules().find((r: DependencyRule) => r.target_field === canonicalName);
  }

  /**
   * getFieldError — returns a validation error message for a field, or undefined.
   *
   * Respects the fieldOverrides computed so fields made required by a rule are
   * validated in the same pass as schema-required fields.
   */
  getFieldError(canonicalName: string): string | undefined {
    const allFields = [
      ...this.compulsoryFields(),
      ...this.recommendedFields(),
      ...this.optionalFields(),
    ];
    const field = allFields.find(f => f.canonical_name === canonicalName);
    if (!field) return undefined;

    // Use rule-augmented required state
    const effectiveRequired = this.isFieldRequired(field);
    if (!effectiveRequired) return undefined;
    return !this.fieldValues()[canonicalName]
      ? `${field.display_name} is required`
      : undefined;
  }

  // ── Event handlers ────────────────────────────────────────────────────────
  onFieldBlur(canonicalName: string, value: string): void {
    this.fieldValues.update(cur => ({ ...cur, [canonicalName]: value }));
    this.clearAiSuggestionIfPresent(canonicalName);
    this.autosaveTrigger$.next();
  }

  onFieldChange(canonicalName: string, value: unknown): void {
    this.fieldValues.update(cur => ({ ...cur, [canonicalName]: value }));
    this.clearAiSuggestionIfPresent(canonicalName);
    this.autosaveTrigger$.next();
  }

  onAutofill(): void {
    this.autofilling.set(true);
    // Backend autofill requires a non-empty description (1..2000 chars). Seed it
    // from the current product name in V1 simulation.
    const description = this.productName();
    this.apiSvc.autofill(this.productId(), description).subscribe({
      next: (resp: AutofillResponse) => {
        // resp.suggestions is Record<string, AutofillSuggestion>; flatten to the
        // raw values map for the field-values signal + suggestion overlay.
        const values: Record<string, unknown> = Object.fromEntries(
          Object.entries(resp.suggestions).map(([k, s]) => [k, s.value]),
        );
        this.aiSuggestions.set(values);
        this.fieldValues.update(cur => ({ ...cur, ...values }));
        this.autofilling.set(false);
      },
      error: () => {
        this.autofilling.set(false);
        this.toast.error('AI fill failed. Please try again.');
      },
    });
  }

  onBack(): void {
    void this.router.navigate(['/dashboard']);
  }

  onNext(): void {
    void this.router.navigate(['/catalogs', this.productId(), 'images']);
  }

  // ── Private ───────────────────────────────────────────────────────────────
  private clearAiSuggestionIfPresent(canonicalName: string): void {
    if (!(canonicalName in this.aiSuggestions())) return;
    this.aiSuggestions.update(cur => {
      const { [canonicalName]: _removed, ...rest } = cur;
      return rest;
    });
  }

  private performAutosave(): void {
    this.saveStatus.set('saving');
    this.apiSvc.autosave(this.productId(), this.fieldValues()).subscribe({
      next: () => {
        this.saveStatus.set('saved');
        setTimeout(() => {
          if (this.saveStatus() === 'saved') this.saveStatus.set('idle');
        }, 3000);
        this.toast.success('Saved');
      },
      error: () => {
        this.saveStatus.set('error');
        this.toast.error('Autosave failed. Check your connection.');
      },
    });
  }
}
