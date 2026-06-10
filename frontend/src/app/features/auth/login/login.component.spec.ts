// features/auth/login/login.component.spec.ts
// Unit tests for LoginComponent — 4 tests per dispatch acceptance criteria.
// Pattern: Vitest + Angular TestBed (zoneless) + vi.fn() mocks.

import { TestBed } from '@angular/core/testing';
import { Component, forwardRef } from '@angular/core';
import { ControlValueAccessor, NG_VALUE_ACCESSOR } from '@angular/forms';
import { provideRouter } from '@angular/router';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, expect, it, beforeEach, vi } from 'vitest';
import { of } from 'rxjs';

import { LoginComponent } from './login.component';
import { AuthApiService } from '../auth-api.service';
import { ErrorService } from '@core/services/error.service';
import { PhoneInputComponent } from '../components/phone-input/phone-input.component';
import { OtpVerifyComponent } from '../components/otp-verify/otp-verify.component';

// Stubs — isolate LoginComponent from child component DI requirements
// PhoneInputStub implements CVA so formControlName="phone" resolves correctly
@Component({
  selector: 'mee-phone-input',
  standalone: true,
  template: '<input class="mee-phone-stub" />',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => PhoneInputStub),
      multi: true,
    },
  ],
})
class PhoneInputStub implements ControlValueAccessor {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  writeValue(_v: unknown): void {}
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  registerOnChange(_fn: unknown): void {}
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  registerOnTouched(_fn: unknown): void {}
}

@Component({
  selector: 'mee-otp-verify',
  standalone: true,
  template: '<div class="mee-otp-verify-stub">OTP stub</div>',
})
class OtpVerifyStub {}

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'account.login.title': 'Welcome back',
      'account.login.phone_label': 'Mobile number',
      'auth.login.send_otp': 'Send OTP to log in',
      'auth.login.signup_link': 'New to MeeSell?',
      'account.otp.rate_limit': 'Too many attempts. Try again in {{minutes}} minutes.',
      'account.signup.title': 'Create your account',
      'common.error': 'Something went wrong. Please try again.',
      'landing.cta.signup': 'Get started free',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

describe('LoginComponent', () => {
  let sendOtpSpy: ReturnType<typeof vi.fn>;
  let showErrorSpy: ReturnType<typeof vi.fn>;

  beforeEach(async () => {
    sendOtpSpy = vi.fn();
    showErrorSpy = vi.fn();

    await TestBed.configureTestingModule({
      imports: [
        LoginComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        {
          provide: AuthApiService,
          useValue: {
            sendOtp: sendOtpSpy,
            verifyOtp: vi.fn(),
          },
        },
        {
          provide: ErrorService,
          useValue: { showError: showErrorSpy },
        },
      ],
    })
    .overrideComponent(LoginComponent, {
      remove: { imports: [PhoneInputComponent, OtpVerifyComponent] },
      add: { imports: [PhoneInputStub, OtpVerifyStub] },
    })
    .compileComponents();
  });

  // Test 1: renders title from transloco
  it('renders the login title from transloco', async () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const h1 = fixture.nativeElement.querySelector('h1');
    expect(h1?.textContent?.trim()).toContain('Welcome back');
  });

  // Test 2: renders mee-phone-input selector in DOM
  it('renders mee-phone-input in the DOM', async () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    const phoneInput = fixture.nativeElement.querySelector('mee-phone-input');
    expect(phoneInput).not.toBeNull();
  });

  // Test 3: Send OTP button is disabled when form is invalid (empty/pristine)
  it('"Send OTP" button is disabled when form is pristine/invalid', async () => {
    const fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const button = fixture.nativeElement.querySelector('button[type="submit"]');
    expect(button?.disabled).toBe(true);
  });

  // Test 4: on successful sendOtp, phase changes to 'otp_sent'
  it('transitions phase to otp_sent on successful sendOtp', async () => {
    sendOtpSpy.mockReturnValue(of({ request_id: 'req-456' }));

    const fixture = TestBed.createComponent(LoginComponent);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();

    // Set a valid phone value
    component.form.controls.phone.setValue('+919876543210');
    fixture.detectChanges();

    // Call onSubmit directly
    component.onSubmit();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(component.phase()).toBe('otp_sent');
    expect(component.requestId()).toBe('req-456');

    const otpStub = fixture.nativeElement.querySelector('mee-otp-verify');
    expect(otpStub).not.toBeNull();
  });
});
