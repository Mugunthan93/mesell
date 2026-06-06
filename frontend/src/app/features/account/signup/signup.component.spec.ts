// features/account/signup/signup.component.spec.ts

import { TestBed } from '@angular/core/testing';
import { SignupComponent } from './signup.component';

describe('SignupComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SignupComponent],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(SignupComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render "Create your account" heading', () => {
    const fixture = TestBed.createComponent(SignupComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Create your account');
  });

  it('should render Business Name input', () => {
    const fixture = TestBed.createComponent(SignupComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Business / Shop Name');
    const inputs = compiled.querySelectorAll('input[type="text"]');
    expect(inputs.length).toBeGreaterThanOrEqual(1);
  });

  it('should render phone input with +91 prefix', () => {
    const fixture = TestBed.createComponent(SignupComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('+91');
    const phoneInput = compiled.querySelector('input[type="tel"]');
    expect(phoneInput).toBeTruthy();
  });

  it('should render Continue button', () => {
    const fixture = TestBed.createComponent(SignupComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    const btn = compiled.querySelector('button');
    expect(btn?.textContent?.trim()).toBe('Continue');
  });

  it('should render Login link pointing to /login', () => {
    const fixture = TestBed.createComponent(SignupComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    const link = compiled.querySelector<HTMLAnchorElement>('a[href="/login"]');
    expect(link).toBeTruthy();
    expect(link?.textContent?.trim()).toBe('Login');
  });
});
