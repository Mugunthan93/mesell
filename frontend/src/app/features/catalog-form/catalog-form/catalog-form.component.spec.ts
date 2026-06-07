// features/catalog-form/catalog-form/catalog-form.component.spec.ts
// 4 required tests:
//   1. Creates component without errors
//   2. On init: calls getProduct then getSchema with product's leafCategoryId
//   3. onFieldChange: calls state.applyFieldChange with the correct ValueChange
//   4. onSubmit: on success, navigates to /catalogs/:id/images

import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { of, throwError } from 'rxjs';
import { signal, computed } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

import { CatalogFormComponent } from './catalog-form.component';
import { CatalogFormApiService, ProductDetail, AutofillResponse } from '../catalog-form-api.service';
import { CatalogFormStateService, ValueChange as StateValueChange } from '../catalog-form-state.service';
import { DraftRecoveryService, ProductDraft } from '../draft-recovery.service';
import { CategorySchemaService, CategorySchemaFull } from '../category-schema.service';
import { StepComposerService } from '../wizard-renderer/step-composer.service';
import { ErrorService } from '@core/services/error.service';
import { ApiError } from '@core/api/api-error';

// ─── Mock data ────────────────────────────────────────────────────────────────

const MOCK_PRODUCT: ProductDetail = {
  id: 'prod-uuid-001',
  leafCategoryId: 'cat-leaf-001',
  leafCategoryName: 'Cotton Kurtis',
  superCategoryId: 'cat-super-001',
  status: 'draft',
  fields: { title: 'Test Kurti', color: 'blue' },
  aiSuggestions: {},
  createdAt: '2026-06-07T00:00:00Z',
  updatedAt: '2026-06-07T00:00:00Z',
};

const MOCK_SCHEMA: CategorySchemaFull = {
  categoryId: 'cat-leaf-001',
  categoryName: 'Cotton Kurtis',
  fields: [
    {
      canonicalName: 'title',
      displayLabel: { en: 'Title' },
      primitive: 'text_short',
      stepId: 'basics',
      isMandatory: true,
      isHidden: false,
      validation: {},
    } as unknown as import('@core/models/field-schema.model').FieldSchema,
  ],
};

const MOCK_DRAFT: ProductDraft = {
  fields: { title: 'Draft Kurti' },
  lastUpdated: '2026-06-07T01:00:00Z',
  autosaveCount: 2,
};

const MOCK_AUTOFILL: AutofillResponse = {
  suggestions: { color: { suggested_value: 'red', confidence: 0.9 } },
  fieldsFilled: 1,
  fallbackOffered: false,
};

// ─── Service stubs ────────────────────────────────────────────────────────────

function createApiServiceStub() {
  return {
    getProduct: vi.fn(() => of(MOCK_PRODUCT)),
    saveProduct: vi.fn(() => of(MOCK_PRODUCT)),
    autosaveProduct: vi.fn(() => of(MOCK_PRODUCT)),
    requestAutofill: vi.fn(() => of(MOCK_AUTOFILL)),
  };
}

function createStateServiceStub() {
  return {
    productId: signal<string | null>(null),
    product: signal<ProductDetail | null>(null),
    schema: signal<unknown[] | null>(null),
    draft: signal<Record<string, unknown> | null>(null),
    aiSuggestions: signal<Record<string, unknown>>({}),
    loading: signal<boolean>(false),
    saving: signal<boolean>(false),
    autofillLoading: signal<boolean>(false),
    error: signal<string | null>(null),
    fields: computed(() => ({ title: 'Test Kurti' })),
    setProduct: vi.fn(),
    setSchema: vi.fn(),
    setDraft: vi.fn(),
    applyFieldChange: vi.fn(),
    applyAutofillSuggestions: vi.fn(),
    acceptAiSuggestion: vi.fn(),
    rejectAiSuggestion: vi.fn(),
  };
}

function createDraftServiceStub() {
  return { getDraft: vi.fn(() => of(MOCK_DRAFT)) };
}

function createSchemaServiceStub() {
  return { getSchema: vi.fn(() => of(MOCK_SCHEMA)) };
}

function createStepComposerStub() {
  return { compose: vi.fn(() => []) };
}

function createErrorServiceStub() {
  return { showError: vi.fn(), showWarning: vi.fn(), showInfo: vi.fn(), showSuccess: vi.fn() };
}

function createRouterStub() {
  return { navigate: vi.fn(() => Promise.resolve(true)) };
}

function createSnackBarStub() {
  return { open: vi.fn(() => ({ onAction: () => of(undefined) })) };
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function createActivatedRoute(productId: string) {
  return {
    snapshot: {
      paramMap: {
        get: (key: string) => (key === 'id' ? productId : null),
      },
    },
  };
}

async function createComponent(
  productId = 'prod-uuid-001',
  overrides: Partial<{
    apiService: ReturnType<typeof createApiServiceStub>;
    stateService: ReturnType<typeof createStateServiceStub>;
    draftService: ReturnType<typeof createDraftServiceStub>;
    schemaService: ReturnType<typeof createSchemaServiceStub>;
  }> = {},
) {
  const apiService = overrides.apiService ?? createApiServiceStub();
  const stateService = overrides.stateService ?? createStateServiceStub();
  const draftService = overrides.draftService ?? createDraftServiceStub();
  const schemaService = overrides.schemaService ?? createSchemaServiceStub();
  const stepComposer = createStepComposerStub();
  const errorService = createErrorServiceStub();
  const router = createRouterStub();
  const snackBar = createSnackBarStub();

  await TestBed.configureTestingModule({
    imports: [CatalogFormComponent],
    providers: [
      provideAnimations(),
      { provide: CatalogFormApiService, useValue: apiService },
      { provide: CatalogFormStateService, useValue: stateService },
      { provide: DraftRecoveryService, useValue: draftService },
      { provide: CategorySchemaService, useValue: schemaService },
      { provide: StepComposerService, useValue: stepComposer },
      { provide: ErrorService, useValue: errorService },
      { provide: Router, useValue: router },
      { provide: MatSnackBar, useValue: snackBar },
      { provide: ActivatedRoute, useValue: createActivatedRoute(productId) },
    ],
  }).compileComponents();

  const fixture = TestBed.createComponent(CatalogFormComponent);
  const component = fixture.componentInstance;

  return { fixture, component, apiService, stateService, draftService, schemaService, stepComposer, errorService, router, snackBar };
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe('CatalogFormComponent', () => {
  afterEach(() => {
    vi.clearAllMocks();
    TestBed.resetTestingModule();
  });

  // ── Test 1: creates component ───────────────────────────────────────────────

  it('creates the component without errors', async () => {
    const { component } = await createComponent();
    expect(component).toBeTruthy();
  });

  // ── Test 2: ngOnInit calls getProduct then getSchema with leafCategoryId ────

  it('ngOnInit: calls getProduct then getSchema with the product leafCategoryId', async () => {
    const { component, apiService, stateService, draftService, schemaService } = await createComponent('prod-uuid-001');

    component.ngOnInit();

    // getProduct called with productId from route
    expect(apiService.getProduct).toHaveBeenCalledWith('prod-uuid-001');

    // getSchema called with the product's leafCategoryId
    expect(schemaService.getSchema).toHaveBeenCalledWith('cat-leaf-001');

    // getDraft called in parallel for draft recovery
    expect(draftService.getDraft).toHaveBeenCalledWith('prod-uuid-001');

    // State mutations called with correct data
    expect(stateService.setProduct).toHaveBeenCalledWith(MOCK_PRODUCT);
    expect(stateService.setSchema).toHaveBeenCalledWith(MOCK_SCHEMA.fields);
    expect(stateService.setDraft).toHaveBeenCalledWith(MOCK_DRAFT.fields);
  });

  // ── Test 3: onFieldChange delegates to state.applyFieldChange ───────────────

  it('onFieldChange: calls state.applyFieldChange with the correct ValueChange', async () => {
    const { component, stateService } = await createComponent();

    const change = { canonicalName: 'color', value: 'green', source: 'seller' as const };
    component.onFieldChange(change);

    expect(stateService.applyFieldChange).toHaveBeenCalledWith(change);
  });

  // ── Test 4: onSubmit on success navigates to /catalogs/:id/images ───────────

  it('onSubmit: on success navigates to /catalogs/:id/images', async () => {
    const { component, router } = await createComponent('prod-uuid-001');

    // Ensure productId is set (mirrors ngOnInit side-effect)
    (component as unknown as { productId: string }).productId = 'prod-uuid-001';

    component.onSubmit();

    expect(router.navigate).toHaveBeenCalledWith(['/catalogs', 'prod-uuid-001', 'images']);
  });

  // ── Test 5: getProduct 404 navigates to /dashboard ──────────────────────────

  it('ngOnInit: when getProduct returns 404, navigates to /dashboard', async () => {
    const apiService = createApiServiceStub();
    apiService.getProduct = vi.fn(() =>
      throwError(() => new ApiError({ kind: 'http', status: 404, displayMessage: 'Not found', code: 'catalog.product_not_found' })),
    );

    const { component, router } = await createComponent('prod-uuid-001', { apiService });

    component.ngOnInit();

    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);
  });

  // ── Test 6: onRequestAutofill calls requestAutofill and applies suggestions ─

  it('onRequestAutofill: calls requestAutofill and applies suggestions to state', async () => {
    const { component, apiService, stateService } = await createComponent();
    (component as unknown as { productId: string }).productId = 'prod-uuid-001';

    component.onRequestAutofill();

    expect(apiService.requestAutofill).toHaveBeenCalledWith('prod-uuid-001');
    expect(stateService.applyAutofillSuggestions).toHaveBeenCalledWith(MOCK_AUTOFILL.suggestions);
  });
});
