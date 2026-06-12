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

import type { FieldGroup, FieldSchema } from '../models/field-schema.model';
import type { AutofillResponse } from '../services/catalog-form-api.service';
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
    :host { display: block; }

    .mee-ai-suggested {
      background-color: var(--mee-color-warning-light, #fef9c3);
      border-color: var(--mee-color-warning, #ca8a04);
      border-radius: 4px;
    }
    .field-wrapper {
      background-color: transparent;
      transition: background-color 0.2s ease;
    }
    .field-wrapper.mee-ai-suggested {
      padding: 6px;
      outline: 1px solid var(--mee-color-warning, #ca8a04);
      outline-offset: 2px;
    }
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
      min-height: 44px;
      color: var(--mee-color-on-surface);
    }
    .section-toggle:focus-visible {
      outline: 2px solid var(--mee-color-primary);
      outline-offset: 2px;
    }
  `],
  template: `
    <div class="max-w-2xl mx-auto px-4 py-4">

      <!-- Page Header -->
      <mee-page-header
        [title]="productName()"
        [subtitle]="categoryPath()"
      />

      <!-- Status badge + AI fill row -->
      <div class="flex items-center justify-between mt-3 mb-5">
        <mee-status-badge [status]="'draft'" />
        <mee-button
          label="AI fill"
          variant="secondary"
          icon="auto_awesome"
          [loading]="autofilling()"
          [disabled]="loading()"
          (clicked)="onAutofill()"
        />
      </div>

      <!-- Loading skeleton -->
      @if (loading()) {
        <div class="flex flex-col gap-4">
          <mee-loading-skeleton variant="text" [lines]="3" />
          <mee-loading-skeleton variant="text" [lines]="3" />
          <mee-loading-skeleton variant="text" [lines]="2" />
        </div>
      }

      <!-- Schema field groups -->
      @if (!loading()) {

        <!-- Compulsory section -->
        <section aria-labelledby="compulsory-heading" class="mb-4">
          <button
            type="button"
            id="compulsory-heading"
            class="section-toggle"
            (click)="compulsoryOpen.set(!compulsoryOpen())"
            [attr.aria-expanded]="compulsoryOpen()"
          >
            <span>Compulsory ({{ compulsoryFields().length }})</span>
            <span class="text-sm font-normal" style="color: var(--mee-color-on-surface-muted);">
              {{ compulsoryOpen() ? 'Collapse' : 'Expand' }}
            </span>
          </button>

          @if (compulsoryOpen()) {
            <div class="flex flex-col gap-4 pt-4">
              @for (field of compulsoryFields(); track field.canonical_name) {
                <div
                  class="field-wrapper"
                  [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
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
        <section aria-labelledby="recommended-heading" class="mb-4">
          <button
            type="button"
            id="recommended-heading"
            class="section-toggle"
            (click)="recommendedOpen.set(!recommendedOpen())"
            [attr.aria-expanded]="recommendedOpen()"
          >
            <span>Recommended ({{ recommendedFields().length }})</span>
            <span class="text-sm font-normal" style="color: var(--mee-color-on-surface-muted);">
              {{ recommendedOpen() ? 'Collapse' : 'Expand' }}
            </span>
          </button>

          @if (recommendedOpen()) {
            <div class="flex flex-col gap-4 pt-4">
              @for (field of recommendedFields(); track field.canonical_name) {
                <div
                  class="field-wrapper"
                  [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
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
        <section aria-labelledby="optional-heading" class="mb-6">
          <button
            type="button"
            id="optional-heading"
            class="section-toggle"
            (click)="optionalOpen.set(!optionalOpen())"
            [attr.aria-expanded]="optionalOpen()"
          >
            <span>Optional ({{ optionalFields().length }})</span>
            <span class="text-sm font-normal" style="color: var(--mee-color-on-surface-muted);">
              {{ optionalOpen() ? 'Collapse' : 'Expand' }}
            </span>
          </button>

          @if (optionalOpen()) {
            <div class="flex flex-col gap-4 pt-4">
              @for (field of optionalFields(); track field.canonical_name) {
                <div
                  class="field-wrapper"
                  [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)"
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

        <!-- Footer: autosave indicator + navigation -->
        <div
          class="flex items-center justify-between pt-3 pb-4"
          style="border-top: 1px solid var(--mee-color-outline);"
        >
          <span class="text-sm" style="color: var(--mee-color-on-surface-muted);">
            @switch (saveStatus()) {
              @case ('saving') { Saving... }
              @case ('saved')  { Saved }
              @case ('error')  {
                <span style="color: var(--mee-color-error);">Save failed</span>
              }
              @default { &nbsp; }
            }
          </span>

          <div class="flex gap-2">
            <mee-button
              label="Back"
              variant="ghost"
              (clicked)="onBack()"
            />
            <mee-button
              label="Images"
              icon="arrow_forward"
              (clicked)="onNext()"
            />
          </div>
        </div>

      }
    </div>
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
   * categoryId — resolved from Router navigation state (GAP-1 interim, spec §4).
   * Set by smart-picker's selectCategory() call: router.navigate(['/catalogs', id, 'edit'], { state: { categoryId } }).
   * On hard-reload (nav-state absent), this is null → form shows an explicit error state.
   * TODO(builder-2): render error banner when categoryId is null after loading.
   */
  readonly categoryId      = signal<string | null>(null);
  /**
   * categoryIdMissing — true when hard-reload/deep-link arrived without nav-state.
   * TODO(builder-2): render an explicit error state / "return to dashboard" CTA.
   */
  readonly categoryIdMissing = signal(false);

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

    // GAP-1 resolution (spec §4): Resolve category_id from Router navigation state.
    // smart-picker navigates: router.navigate(['/catalogs', id, 'edit'], { state: { categoryId } })
    // On hard-reload the nav-state is absent → categoryIdMissing=true → form shows error state.
    // TODO(builder-2): wire categoryIdMissing to an error banner / "Return to dashboard" CTA.
    const navState = this.router.getCurrentNavigation()?.extras.state as
      | { categoryId?: string }
      | null
      | undefined;
    const catId = navState?.['categoryId'] as string | undefined;

    if (catId) {
      this.categoryId.set(catId);
    } else {
      // Hard-reload path — nav-state lost. Show explicit error state.
      this.categoryIdMissing.set(true);
      this.loading.set(false);
      this.toast.error('Cannot load form. Please return to the dashboard and try again.');
      return;
    }

    // Wire autosave pipeline (DestroyRef injected explicitly — not constructor).
    this.autosaveTrigger$
      .pipe(debounceTime(10_000), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.performAutosave());

    // #22 getDraft — pre-fill fieldValues with autosaved data for resume-on-reload.
    // Non-blocking: form renders even if draft fails (getDraft error matrix → null).
    this.apiSvc.getDraft(id).subscribe({
      next: (draft) => {
        if (draft?.fields && Object.keys(draft.fields).length > 0) {
          this.fieldValues.set(draft.fields);
        }
        // After draft recovery (or empty draft), load the schema.
        this.loadSchema(catId);
      },
      error: () => {
        // getDraft error matrix guarantees this is never reached (all errors → null).
        // Defensive: proceed to schema load.
        this.loadSchema(catId);
      },
    });
  }

  private loadSchema(categoryId: string): void {
    // #15 getSchema — load the category-specific field schema.
    // getSchema error matrix: non-401 errors return of([]) → loading=false + empty schema.
    this.apiSvc.getSchema(categoryId).subscribe({
      next: (groups) => {
        this.schema.set(groups);
        this.loading.set(false);
      },
      error: () => {
        // Only 401 reaches here (rethrown). All other errors return of([]) in the service.
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
    // Per spec §5.3 (GAP-1 autofill): description is REQUIRED by the backend (1..2000 chars).
    // Source: the product_title field value if filled; else block with a toast.
    const description = this.fieldValues()['product_title'];
    if (typeof description !== 'string' || !description.trim()) {
      this.toast.error('Add a product title first — autofill needs it.');
      return;
    }

    this.autofilling.set(true);
    this.apiSvc.autofill(this.productId(), description).subscribe({
      next: (resp: AutofillResponse) => {
        // Map AutofillResponse.suggestions {[k]:{value,confidence,source}} → flat {[k]:value}
        // for the aiSuggestions highlight signal (Record<string, unknown>).
        // TODO(builder-2): surface confidence as display hint (V1.5 spec §5.3).
        const flatSuggestions: Record<string, unknown> = {};
        for (const [key, suggestion] of Object.entries(resp.suggestions)) {
          flatSuggestions[key] = suggestion.value;
        }
        this.aiSuggestions.set(flatSuggestions);
        this.fieldValues.update(cur => ({ ...cur, ...flatSuggestions }));

        if (resp.fallback_offered && Object.keys(resp.suggestions).length === 0) {
          // AI couldn't fill — no suggestions returned
          this.toast.error("AI couldn't fill — try adding more product details.");
        }

        this.autofilling.set(false);
      },
      error: (err: { status?: number }) => {
        this.autofilling.set(false);
        if (err.status === 402) {
          this.toast.error('AI fill quota reached. Upgrade your plan to continue.');
        } else if (err.status === 404) {
          // FEATURE_AI_AUTOFILL_ENABLED=false — GAP-2 graceful
          this.toast.error('AI fill is not available in your current plan.');
        } else {
          this.toast.error('AI fill failed. Please try again.');
        }
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
