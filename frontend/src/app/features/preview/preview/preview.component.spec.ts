// features/preview/preview/preview.component.spec.ts

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of, throwError } from 'rxjs';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

import { PreviewComponent } from './preview.component';
import { PreviewApiService, PreviewData } from '../preview-api.service';
import { PreviewFeedComponent } from './preview-feed/preview-feed.component';
import { PreviewDetailComponent } from './preview-detail/preview-detail.component';

// Stubs for signal-input children to avoid NG0950
@Component({ selector: 'mee-preview-feed', standalone: true, template: '<div class="feed-stub"></div>' })
class PreviewFeedStub { readonly previewData = input.required<PreviewData>(); }

@Component({ selector: 'mee-preview-detail', standalone: true, template: '<div class="detail-stub"></div>' })
class PreviewDetailStub { readonly previewData = input.required<PreviewData>(); }

const MOCK_PREVIEW_DATA: PreviewData = {
  title: 'Cotton Kurti Blue',
  price: 599,
  image_urls: [],
  first_variant: 'Color: Blue',
  full_description: 'A beautiful cotton kurti.',
  quality_score: 87,
  category_path: 'Women > Kurtis & Suits > Kurtis',
};

const translocoOptions: TranslocoTestingOptions = {
  langs: {
    en: {
      'preview.title': 'Preview your listing',
      'preview.tab.feed': 'Feed view',
      'preview.tab.detail': 'Product page',
    },
  },
  translocoConfig: { availableLangs: ['en'], defaultLang: 'en' },
  preloadLangs: true,
};

const MOCK_ROUTE = {
  snapshot: {
    parent: { paramMap: { get: (_k: string) => 'product-123' } },
    paramMap: { get: (_k: string) => null },
  },
};

async function createTestBed(apiValue: { getPreview: ReturnType<typeof vi.fn> }) {
  await TestBed.configureTestingModule({
    imports: [
      PreviewComponent,
      TranslocoTestingModule.forRoot(translocoOptions),
    ],
    providers: [
      provideAnimationsAsync('noop'),
      { provide: PreviewApiService, useValue: apiValue },
      { provide: ActivatedRoute, useValue: MOCK_ROUTE },
    ],
  })
  .overrideComponent(PreviewComponent, {
    remove: { imports: [PreviewFeedComponent, PreviewDetailComponent] },
    add:    { imports: [PreviewFeedStub, PreviewDetailStub] },
  })
  .compileComponents();
}

describe('PreviewComponent — success path', () => {
  let fixture: ComponentFixture<PreviewComponent>;
  let component: PreviewComponent;
  let mockPreviewApi: { getPreview: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockPreviewApi = {
      getPreview: vi.fn(() => of(MOCK_PREVIEW_DATA)),
    };
    await createTestBed(mockPreviewApi);
    fixture = TestBed.createComponent(PreviewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    TestBed.resetTestingModule();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should show loading spinner before data arrives', () => {
    // A fresh instance (before ngOnInit sync-completes) starts with loading=true
    const freshComponent = TestBed.createComponent(PreviewComponent).componentInstance;
    expect(freshComponent.loading()).toBe(true);
  });

  it('should render Next step button after data loads', () => {
    const el: HTMLElement = fixture.nativeElement;
    const nextBtn = el.querySelector('#next-step-btn');
    expect(nextBtn).toBeTruthy();
    expect(nextBtn!.textContent).toContain('Next');
  });

  it('should call getPreview with the product id from route', () => {
    expect(mockPreviewApi.getPreview).toHaveBeenCalledWith('product-123');
  });

  it('should set previewData signal when API succeeds', () => {
    expect(component.previewData()).toEqual(MOCK_PREVIEW_DATA);
    expect(component.loading()).toBe(false);
  });
});

describe('PreviewComponent — 404 error path', () => {
  let component: PreviewComponent;

  beforeEach(async () => {
    const errorApi = {
      getPreview: vi.fn(() => throwError(() => ({ status: 404 }))),
    };
    await createTestBed(errorApi);
    const fixture = TestBed.createComponent(PreviewComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    TestBed.resetTestingModule();
  });

  it('should set loading to false and not set previewData when API returns 404', () => {
    expect(component.loading()).toBe(false);
    expect(component.previewData()).toBeNull();
  });
});
