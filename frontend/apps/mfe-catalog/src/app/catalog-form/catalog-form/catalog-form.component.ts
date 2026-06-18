// features/catalog-form/catalog-form/catalog-form.component.ts
// Wave 5 — F8: Catalog Form
// Route: /catalogs/:id/edit (shell child, auth-guarded)
// Renders a dynamic category-specific field form using mee-* UI Kit primitives.
// Dynamic fields use Record<string,unknown> signal — NOT FormGroup (JSONB schema).
// AI auto-fill highlights compulsory fields in yellow; autosaves on blur/change.

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

import type { AutofillResponse, FieldGroup, FieldSchema } from '../models/field-schema.model';
import { CatalogFormApiService } from '../services/catalog-form-api.service';

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
  ],
  styles: [`
    /* ── Host ─────────────────────────────────────────────────────────── */
    :host { display: block; }

    /* ── Page wrapper: mobile-first 360px baseline ─────────────────────── */
    .mee-form-page {
      max-width: 100%;
      margin: 0 auto;
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
        max-width: 42rem;
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
        max-width: 64rem;
        padding: var(--mee-space-8) var(--mee-space-10);
        padding-bottom: calc(88px + env(safe-area-inset-bottom, 0px));
      }
    }
  `],
  template: `
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
                <div
                  class="field-wrapper"
                  [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                  [class.mee-field--full]="field.primitive === 'text_long'"
                >
                  @switch (field.primitive) {
                    @case ('text_long') {
                      <mee-textarea
                        [label]="field.display_name"
                        [required]="field.required"
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
                        [required]="field.required"
                        [error]="getFieldError(field.canonical_name)"
                        [hint]="field.help_text"
                        [type]="field.primitive === 'number' ? 'number' : 'text'"
                        (blur)="onFieldBlur(field.canonical_name, $any($event))"
                      />
                    }
                  }
                </div>
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
                <div
                  class="field-wrapper"
                  [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                  [class.mee-field--full]="field.primitive === 'text_long'"
                >
                  @switch (field.primitive) {
                    @case ('text_long') {
                      <mee-textarea
                        [label]="field.display_name"
                        [required]="field.required"
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
                        [required]="field.required"
                        [error]="getFieldError(field.canonical_name)"
                        [hint]="field.help_text"
                        [type]="field.primitive === 'number' ? 'number' : 'text'"
                        (blur)="onFieldBlur(field.canonical_name, $any($event))"
                      />
                    }
                  }
                </div>
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
                <div
                  class="field-wrapper"
                  [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
                  [class.mee-field--full]="field.primitive === 'text_long'"
                >
                  @switch (field.primitive) {
                    @case ('text_long') {
                      <mee-textarea
                        [label]="field.display_name"
                        [required]="field.required"
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
                        [required]="field.required"
                        [type]="field.primitive === 'number' ? 'number' : 'text'"
                        (blur)="onFieldBlur(field.canonical_name, $any($event))"
                      />
                    }
                  }
                </div>
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
            (clicked)="onNext()"
            aria-label="Continue to images"
          />
        </div>
      </nav>
    }
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

  // ── Computed ──────────────────────────────────────────────────────────────
  readonly productName = computed<string>(() => {
    const v = this.fieldValues()['product_title'];
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

    // Load schema (simulated)
    this.apiSvc.getSchema(id).subscribe({
      next: (groups) => {
        this.schema.set(groups);
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

  getFieldError(canonicalName: string): string | undefined {
    const allFields = [
      ...this.compulsoryFields(),
      ...this.recommendedFields(),
      ...this.optionalFields(),
    ];
    const field = allFields.find(f => f.canonical_name === canonicalName);
    if (!field?.required) return undefined;
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
