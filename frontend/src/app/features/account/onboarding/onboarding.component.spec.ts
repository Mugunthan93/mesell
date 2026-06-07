// features/account/onboarding/onboarding.component.spec.ts
//
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks.
// TranslocoTestingModule.forRoot() is in imports[] (not providers[]).
// provideAnimationsAsync('noop') suppresses animation overhead in tests.
// vi.useFakeTimers() / vi.advanceTimersByTime() for setTimeout navigation test.
// Tests 5-7 use overrideComponent to stub SuperCategoryChipsComponent +
// ComplianceStepComponent (avoids NG0950 from @Input({ required: true }) on the real children).

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { By } from '@angular/platform-browser';
import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideRouter, Router } from '@angular/router';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, it, expect, afterEach, vi } from 'vitest';

import { OnboardingWizardComponent } from './onboarding.component';
import { SuperCategoryChipsComponent } from '../components/super-category-chips/super-category-chips.component';
import { ComplianceStepComponent } from '../components/compliance-step/compliance-step.component';

// ── Stub components (avoid NG0950 from required @Input decorators on real children) ──

@Component({ selector: 'mee-super-category-chips', standalone: true, template: '' })
class SuperCategoryChipsStub {
  @Output() selectionChange = new EventEmitter<string[]>();
}

@Component({ selector: 'mee-compliance-step', standalone: true, template: '' })
class ComplianceStepStub {
  @Input() superCategoryId = '';
  @Input() fields: unknown[] = [];
  @Input() saving = false;
  @Output() formSubmit = new EventEmitter<Record<string, string | null>>();
  @Output() formBack = new EventEmitter<void>();
}

// ── i18n fixture ──

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'onboarding.title': 'Set Up Your Seller Profile',
      'onboarding.steps.businessDetails': 'Business Details',
      'onboarding.steps.productCategories': 'Product Categories',
      'onboarding.steps.compliance': 'Compliance',
      'onboarding.actions.next': 'Next',
      'onboarding.actions.back': 'Back',
      'onboarding.actions.completeSetup': 'Complete Setup',
      'onboarding.phase1.title': 'Enter your manufacturer and packer details',
      'onboarding.phase1.help': 'These details appear on your product labels as required by Meesho.',
      'onboarding.phase1.placeholder': 'Business detail fields coming soon',
      'onboarding.phase2.title': 'Which product categories do you sell in?',
      'onboarding.phase2.help': 'Choose all that apply. This determines your compliance requirements.',
      'onboarding.phase2.placeholder': 'Category chip selector coming soon',
      'onboarding.phase3.title': 'Complete your compliance information',
      'onboarding.phase3.help': 'Required by government regulations for the categories you selected.',
      'onboarding.phase3.placeholder': 'Compliance fields coming soon',
      'onboarding.phase3.noCategories': 'Select product categories in Step 2 to see compliance requirements.',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Tests ──

describe('OnboardingWizardComponent', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  // Test 1: Component instantiates
  it('should create', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  // Test 2: 3 stepper steps are rendered
  it('should render 3 stepper steps', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    // mat-step renders .mat-step-header elements in the stepper
    const stepHeaders = fixture.nativeElement.querySelectorAll('.mat-step-header');
    expect(stepHeaders.length).toBe(3);
  });

  // Test 3: onPhase1Next() sets phase1Submitted to true
  it('should set phase1Submitted to true when Phase 1 Next is clicked', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    expect(component.phase1Submitted()).toBe(false);

    component.onPhase1Next();

    expect(component.phase1Submitted()).toBe(true);
  });

  // Test 4: onSubmit() navigates to /dashboard after 300ms timeout
  it('should navigate to /dashboard after submit', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([{ path: 'dashboard', redirectTo: '' }]),
      ],
    }).compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);

    vi.useFakeTimers();

    component.onSubmit();
    expect(component.saving()).toBe(true);

    vi.advanceTimersByTime(300);

    expect(component.saving()).toBe(false);
    expect(navigateSpy).toHaveBeenCalledWith('/dashboard');
  });

  // Test 5: mee-super-category-chips is rendered in Phase 2
  it('should render mee-super-category-chips in phase 2', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    })
      .overrideComponent(OnboardingWizardComponent, {
        remove: { imports: [SuperCategoryChipsComponent, ComplianceStepComponent] },
        add:    { imports: [SuperCategoryChipsStub, ComplianceStepStub] },
      })
      .compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    const chipsEl = fixture.debugElement.query(By.css('mee-super-category-chips'));
    expect(chipsEl).not.toBeNull();
  });

  // Test 6: selectionChange from chips updates selectedSuperCategories signal
  it('should update selectedSuperCategories when selectionChange fires', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    })
      .overrideComponent(OnboardingWizardComponent, {
        remove: { imports: [SuperCategoryChipsComponent, ComplianceStepComponent] },
        add:    { imports: [SuperCategoryChipsStub, ComplianceStepStub] },
      })
      .compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    const chipsDebug = fixture.debugElement.query(By.directive(SuperCategoryChipsStub));
    chipsDebug.componentInstance.selectionChange.emit(['26', '16']);
    fixture.detectChanges();

    expect(component.selectedSuperCategories()).toEqual(['26', '16']);
  });

  // Test 7: compliance steps rendered per selected super-category
  it('should render compliance steps for each selected super-category', async () => {
    await TestBed.configureTestingModule({
      imports: [
        OnboardingWizardComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
      ],
    })
      .overrideComponent(OnboardingWizardComponent, {
        remove: { imports: [SuperCategoryChipsComponent, ComplianceStepComponent] },
        add:    { imports: [SuperCategoryChipsStub, ComplianceStepStub] },
      })
      .compileComponents();

    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    component.selectedSuperCategories.set(['26', '13']);
    fixture.detectChanges();

    const complianceEls = fixture.debugElement.queryAll(By.css('mee-compliance-step'));
    expect(complianceEls.length).toBe(2);
  });
});
