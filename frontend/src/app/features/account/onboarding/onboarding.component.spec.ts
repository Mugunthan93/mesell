// features/account/onboarding/onboarding.component.spec.ts

import { TestBed } from '@angular/core/testing';
import { OnboardingWizardComponent } from './onboarding.component';

describe('OnboardingWizardComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OnboardingWizardComponent],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should start on step 1', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.currentStep()).toBe(1);
  });

  it('should render 4 step indicator dots', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.stepDots.length).toBe(4);
  });

  it('should show "Verify your number" heading on step 1', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Verify your number');
  });

  it('should show 6 OTP input boxes on step 1', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    const otpInputs = compiled.querySelectorAll('input[maxlength="1"]');
    expect(otpInputs.length).toBe(6);
  });

  it('should advance to step 2 on nextStep()', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    fixture.componentInstance.nextStep();
    fixture.detectChanges();
    expect(fixture.componentInstance.currentStep()).toBe(2);
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Tell us about your business');
  });

  it('should advance to step 3 and show category chips', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    fixture.componentInstance.nextStep();
    fixture.componentInstance.nextStep();
    fixture.detectChanges();
    expect(fixture.componentInstance.currentStep()).toBe(3);
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Kurtis');
    expect(compiled.textContent).toContain('Sarees');
  });

  it('should advance to step 4 and show consent text', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    fixture.componentInstance.nextStep();
    fixture.componentInstance.nextStep();
    fixture.componentInstance.nextStep();
    fixture.detectChanges();
    expect(fixture.componentInstance.currentStep()).toBe(4);
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Almost there!');
    const btn = compiled.querySelector('button:last-of-type');
    expect(btn?.textContent?.trim()).toBe('Get Started!');
  });

  it('should not advance past step 4', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    for (let i = 0; i < 5; i++) fixture.componentInstance.nextStep();
    expect(fixture.componentInstance.currentStep()).toBe(4);
  });

  it('should go back from step 2 to step 1 on prevStep()', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    fixture.componentInstance.nextStep();
    fixture.componentInstance.prevStep();
    expect(fixture.componentInstance.currentStep()).toBe(1);
  });

  it('should not go below step 1 on prevStep()', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    fixture.componentInstance.prevStep();
    expect(fixture.componentInstance.currentStep()).toBe(1);
  });

  it('should toggle category selection', () => {
    const fixture = TestBed.createComponent(OnboardingWizardComponent);
    fixture.detectChanges();
    const comp = fixture.componentInstance;
    expect(comp.isCategorySelected('Kurtis')).toBe(false);
    comp.toggleCategory('Kurtis');
    expect(comp.isCategorySelected('Kurtis')).toBe(true);
    comp.toggleCategory('Kurtis');
    expect(comp.isCategorySelected('Kurtis')).toBe(false);
  });
});
