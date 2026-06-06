// features/account/login/login.component.spec.ts

import { TestBed } from '@angular/core/testing';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render "Welcome back" heading', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('Welcome back');
  });

  it('should render phone input with +91 prefix', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    expect(compiled.textContent).toContain('+91');
    const input = compiled.querySelector('input[type="tel"]');
    expect(input).toBeTruthy();
  });

  it('should render Send OTP button', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    const btn = compiled.querySelector('button');
    expect(btn?.textContent?.trim()).toBe('Send OTP');
  });

  it('should render Create an account link pointing to /signup', () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    const compiled: HTMLElement = fixture.nativeElement;
    const link = compiled.querySelector<HTMLAnchorElement>('a[href="/signup"]');
    expect(link).toBeTruthy();
    expect(link?.textContent?.trim()).toBe('Create an account');
  });
});
