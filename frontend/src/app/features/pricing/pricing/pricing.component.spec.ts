// features/pricing/pricing/pricing.component.spec.ts
// Updated for Wave 4 PricingComponent — signal-based, API-driven

import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, input } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { of, throwError } from 'rxjs';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

import { PricingComponent } from './pricing.component';
import { PricingApiService, PricingCalc } from '../pricing-api.service';
import { MarginSliderComponent } from '../margin-slider/margin-slider.component';
import { PnlBreakdownComponent } from '../pnl-breakdown/pnl-breakdown.component';
import { PricingChartComponent } from '../pricing-chart/pricing-chart.component';

// Stubs for signal-input children to avoid NG0950
@Component({ selector: 'mee-margin-slider', standalone: true, template: '<div class="slider-stub"></div>' })
class MarginSliderStub {
  readonly mrp = input.required<number>();
  readonly minMrp = input<number>(50);
  readonly maxMrp = input<number>(10000);
}

@Component({ selector: 'mee-pnl-breakdown', standalone: true, template: '<div class="pnl-stub"></div>' })
class PnlBreakdownStub { readonly calc = input.required<PricingCalc>(); }

@Component({ selector: 'mee-pricing-chart', standalone: true, template: '<div class="chart-stub"></div>' })
class PricingChartStub { readonly calc = input.required<PricingCalc>(); }

const MOCK_CALC: PricingCalc = {
  mrp: 999,
  commission: 199,
  commission_pct: 20,
  gst: 150,
  gst_pct: 15,
  platform_fee: 50,
  platform_fee_pct: 5,
  logistics_deduction: 60,
  seller_payout: 540,
  net_margin: 40,
  net_margin_pct: 7.4,
};

const translocoOptions: TranslocoTestingOptions = {
  langs: {
    en: {
      'pricing.title': 'Set your price',
      'pricing.mrp.label': 'Maximum Retail Price (MRP)',
    },
  },
  translocoConfig: { availableLangs: ['en'], defaultLang: 'en' },
  preloadLangs: true,
};

const MOCK_ROUTE = {
  snapshot: {
    parent: { paramMap: { get: (_k: string) => 'product-abc' } },
    paramMap: { get: (_k: string) => null },
  },
};

async function createTestBed(apiValue: { calculate: ReturnType<typeof vi.fn> }) {
  await TestBed.configureTestingModule({
    imports: [
      PricingComponent,
      TranslocoTestingModule.forRoot(translocoOptions),
    ],
    providers: [
      provideAnimationsAsync('noop'),
      { provide: PricingApiService, useValue: apiValue },
      { provide: ActivatedRoute, useValue: MOCK_ROUTE },
    ],
  })
  .overrideComponent(PricingComponent, {
    remove: { imports: [MarginSliderComponent, PnlBreakdownComponent, PricingChartComponent] },
    add:    { imports: [MarginSliderStub, PnlBreakdownStub, PricingChartStub] },
  })
  .compileComponents();
}

describe('PricingComponent — success path', () => {
  let fixture: ComponentFixture<PricingComponent>;
  let component: PricingComponent;
  let mockPricingApi: { calculate: ReturnType<typeof vi.fn> };

  beforeEach(async () => {
    mockPricingApi = {
      calculate: vi.fn(() => of(MOCK_CALC)),
    };
    await createTestBed(mockPricingApi);
    fixture = TestBed.createComponent(PricingComponent);
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

  it('should show loading spinner initially (before API resolves)', () => {
    // A fresh component (before ngOnInit fires) starts with loading=true
    const freshComponent = TestBed.createComponent(PricingComponent).componentInstance;
    expect(freshComponent.loading()).toBe(true);
  });

  it('should render Next step button after data loads', () => {
    const el: HTMLElement = fixture.nativeElement;
    const nextBtn = el.querySelector('#next-step-btn');
    expect(nextBtn).toBeTruthy();
    expect(nextBtn!.textContent).toContain('Next');
  });

  it('should call pricingApi.calculate with correct productId and defaults on init', () => {
    expect(mockPricingApi.calculate).toHaveBeenCalledWith('product-abc', 999, 500);
  });

  it('localEstimate should recompute seller_payout when mrp signal changes', () => {
    // Verify API was called and ratesSnapshot is populated
    expect(component.calc()).toEqual(MOCK_CALC);

    // Update mrp signal — localEstimate recomputes via computed()
    component.onMrpChanged(1200);

    const estimate = component.localEstimate();
    // seller_payout = 1200 * (1 - 20/100 - 15/100 - 5/100) = 1200 * 0.60 = 720
    expect(estimate.seller_payout).toBeCloseTo(720, 0);
  });

  it('onMrpCommitted should call pricingApi.calculate with the new MRP', () => {
    component.onMrpCommitted(1500);
    expect(mockPricingApi.calculate).toHaveBeenCalledWith('product-abc', 1500, 500);
  });
});

describe('PricingComponent — API error path', () => {
  let component: PricingComponent;

  beforeEach(async () => {
    const errorApi = {
      calculate: vi.fn(() => throwError(() => ({ status: 500 }))),
    };
    await createTestBed(errorApi);
    const fixture = TestBed.createComponent(PricingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    TestBed.resetTestingModule();
  });

  it('should set loading to false and not set calc when API errors', () => {
    expect(component.loading()).toBe(false);
    expect(component.calc()).toBeNull();
  });
});
