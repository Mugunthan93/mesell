// catalog-form.component.ts — Wave 6C builder-2 wiring
// Route: /catalogs/:id/edit — dynamic field form, real HTTP, autosave, autofill overlay.

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
    :host { display: block; }
    .field-wrapper { background-color:transparent; transition:background-color 0.2s ease; }
    .field-wrapper.mee-ai-suggested { padding:6px; outline:1px solid var(--mee-color-warning,#ca8a04); outline-offset:2px; }
    .section-toggle { display:flex; width:100%; align-items:center; justify-content:space-between; padding:10px 0; font-weight:500; text-align:left; background:none; border:none; border-bottom:1px solid var(--mee-color-outline); cursor:pointer; min-height:44px; color:var(--mee-color-on-surface); }
    .section-toggle:focus-visible { outline:2px solid var(--mee-color-primary); outline-offset:2px; }
    .suggestion-row { display:flex; align-items:center; gap:8px; padding:6px 0; border-bottom:1px solid var(--mee-color-outline); }
    .suggestion-row:last-child { border-bottom:none; }
  `],
  template: `
    <div class="max-w-2xl mx-auto px-4 py-4">
      <mee-offline-banner />
      @if (categoryIdMissing()) {
        <div class="mt-4">
          <mee-alert-banner variant="error" message="Cannot load form: category not found. Please return to the dashboard." />
          <div class="flex justify-center mt-4">
            <mee-button label="Return to dashboard" variant="secondary" (clicked)="onBack()" />
          </div>
        </div>
      }
      @if (!categoryIdMissing()) {
        <mee-page-header [title]="productName()" [subtitle]="categoryPath()" />
        @if (errorMessage()) {
          <div class="mb-4">
            <mee-alert-banner variant="error" [message]="errorMessage()!" />
            <div class="flex justify-end mt-2">
              <mee-button label="Retry" variant="ghost" (clicked)="onRetry()" />
            </div>
          </div>
        }
        <div class="flex items-center justify-between mt-3 mb-5">
          <mee-status-badge [status]="'draft'" />
          <mee-button label="AI fill" variant="secondary" icon="auto_awesome"
            [loading]="autofilling()" [disabled]="loading() || autofillUnavailable()"
            (clicked)="onAutofill()" />
        </div>
        @if (loading()) {
          <div class="flex flex-col gap-4" aria-busy="true" aria-label="Loading form fields">
            <mee-loading-skeleton variant="text" [lines]="3" />
            <mee-loading-skeleton variant="text" [lines]="3" />
            <mee-loading-skeleton variant="text" [lines]="2" />
          </div>
        }
        @if (!loading() && hasSuggestions()) {
          <div class="mb-4 p-3 rounded" style="background:var(--mee-color-warning-light,#fef9c3);border:1px solid var(--mee-color-warning,#ca8a04);" role="region" aria-label="AI suggestions">
            <p class="text-sm font-medium mb-2" style="color:var(--mee-color-on-surface);">AI suggestions — review and apply</p>
            @for (entry of suggestionEntries(); track entry.canonical) {
              <div class="suggestion-row">
                <span class="text-sm" style="color:var(--mee-color-on-surface-muted);">{{ entry.canonical }}</span>
                <span class="text-sm font-medium flex-1 px-2">{{ entry.value }}</span>
                <mee-button label="Apply" variant="secondary" (clicked)="applySuggestion(entry.canonical)" />
                <mee-button label="Dismiss" variant="ghost" (clicked)="dismissSuggestion(entry.canonical)" />
              </div>
            }
            <div class="flex justify-end mt-2">
              <mee-button label="Dismiss all" variant="ghost" (clicked)="dismissAllSuggestions()" />
            </div>
          </div>
        }
        @if (fallbackOffered()) {
          <div class="mb-3">
            <mee-alert-banner variant="warning" message="AI couldn't fill — try adding more product details." />
          </div>
        }
        @if (!loading()) {
          @for (sec of sections(); track sec.id) {
            <section [attr.aria-labelledby]="sec.id + '-heading'" class="mb-4">
              <button type="button" [id]="sec.id + '-heading'" class="section-toggle"
                (click)="toggleSection(sec.id)" [attr.aria-expanded]="sec.open">
                <span>{{ sec.label }} ({{ sec.fields.length }})</span>
                <span class="text-sm font-normal" style="color:var(--mee-color-on-surface-muted);">{{ sec.open ? 'Collapse' : 'Expand' }}</span>
              </button>
              @if (sec.open) {
                <div class="flex flex-col gap-4 pt-4">
                  @for (field of sec.fields; track field.canonical_name) {
                    <div class="field-wrapper" [class.mee-ai-suggested]="isAiSuggested(field.canonical_name)">
                      @switch (field.primitive) {
                        @case ('text_long') {
                          <mee-textarea [label]="field.display_name" [required]="field.required"
                            [error]="getFieldError(field.canonical_name)" [hint]="field.help_text"
                            [rows]="4" (blur)="onFieldBlur(field.canonical_name, $any($event))" />
                        }
                        @case ('select') {
                          <mee-select [label]="field.display_name" [options]="getFieldOptions(field)"
                            [error]="getFieldError(field.canonical_name)"
                            (value_change)="onFieldChange(field.canonical_name, $event)" />
                        }
                        @default {
                          <mee-input [label]="field.display_name" [required]="field.required"
                            [error]="getFieldError(field.canonical_name)" [hint]="field.help_text"
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

          <!-- Footer: autosave status indicator + nav -->
          <div class="flex items-center justify-between pt-3 pb-4" style="border-top:1px solid var(--mee-color-outline);">
            <span class="text-sm" style="color:var(--mee-color-on-surface-muted);" aria-live="polite">
              @switch (saveStatus()) {
                @case ('saving') { Saving... }
                @case ('saved')  { Saved }
                @case ('error')  { <span style="color:var(--mee-color-error);">Save failed</span> }
                @default { &nbsp; }
              }
            </span>
            <div class="flex gap-2">
              <mee-button label="Back" variant="ghost" (clicked)="onBack()" />
              <mee-button label="Images" icon="arrow_forward" (clicked)="onNext()" />
            </div>
          </div>
        }
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
  readonly productName = computed<string>(() => { const v = this.fieldValues()['product_title']; return (typeof v === 'string' && v) ? v : 'New Product'; });
  readonly categoryPath = computed<string>(() => 'Fashion > Women > Ethnic > Kurti');
  readonly compulsoryFields = computed<FieldSchema[]>(() => this.schema().find(g => g.group === 'compulsory')?.fields ?? []);
  readonly recommendedFields = computed<FieldSchema[]>(() => this.schema().find(g => g.group === 'recommended')?.fields ?? []);
  readonly optionalFields = computed<FieldSchema[]>(() => this.schema().find(g => g.group === 'optional')?.fields ?? []);
  readonly isFormComplete = computed<boolean>(() => this.compulsoryFields().every(f => !!this.fieldValues()[f.canonical_name]));
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
