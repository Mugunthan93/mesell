// features/auth/components/otp-verify/otp-verify.component.spec.ts
// Unit tests for OtpVerifyComponent
// Pattern: Vitest + Angular TestBed (zoneless) + TranslocoTestingModule
// Reference: landing.component.spec.ts

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { EMPTY } from 'rxjs';
import { describe, expect, it, beforeEach } from 'vitest';

import { OtpVerifyComponent } from './otp-verify.component';
import { AuthApiService } from '../../auth-api.service';
import { ApiClient } from '@core/api/api-client.service';
import { ErrorService } from '@core/services/error.service';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';

// ── i18n test translations ──
const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'account.otp.title': 'Enter OTP',
      'account.otp.sent_to': 'OTP sent to {{phone}}',
      'account.otp.resend_in': 'Resend in {{seconds}}s',
      'account.otp.resend': 'Resend OTP',
      'account.otp.verify': 'Verify',
      'account.otp.rate_limit': 'Too many attempts. Try again in {{minutes}} minutes.',
      'common.error': 'Something went wrong. Please try again.',
      'auth.otp_invalid': "That code doesn't match. Try again.",
      'auth.otp_attempts_exceeded': 'Too many attempts. Request a new code.',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

// ── Test Suite ──

describe('OtpVerifyComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        OtpVerifyComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
        provideRouter([]),
        { provide: AuthApiService, useValue: { sendOtp: () => EMPTY, verifyOtp: () => EMPTY } },
        { provide: ApiClient, useValue: { get: () => EMPTY } },
        { provide: ErrorService, useValue: { showError: () => {} } },
        { provide: API_BASE_URL, useValue: 'http://localhost:8000/api/v1' },
      ],
    }).compileComponents();
  });

  // ── Test 1: Renders OTP title ──

  it('renders the OTP title from transloco', async () => {
    const fixture = TestBed.createComponent(OtpVerifyComponent);
    fixture.componentInstance.phone = '+919876543210';
    fixture.componentInstance.requestId = 'req-123';
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const heading = el.querySelector('h2');
    expect(heading?.textContent?.trim()).toBe('Enter OTP');
  });

  // ── Test 2: Renders sent-to subtitle ──

  it('renders sent-to subtitle with phone stripped of +91', async () => {
    const fixture = TestBed.createComponent(OtpVerifyComponent);
    fixture.componentInstance.phone = '+919876543210';
    fixture.componentInstance.requestId = 'req-123';
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const subtitle = el.querySelector('p[aria-live="polite"]');
    expect(subtitle?.textContent).toContain('9876543210');
  });

  // ── Test 3: Renders ng-otp-input element ──

  it('renders the ng-otp-input element', async () => {
    const fixture = TestBed.createComponent(OtpVerifyComponent);
    fixture.componentInstance.phone = '+919876543210';
    fixture.componentInstance.requestId = 'req-123';
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const otpWidget = el.querySelector('ng-otp-input');
    expect(otpWidget).not.toBeNull();
  });

  // ── Test 4: Verify button is disabled when otpValue < 6 chars ──

  it('verify button is disabled initially when otpValue is empty', async () => {
    const fixture = TestBed.createComponent(OtpVerifyComponent);
    fixture.componentInstance.phone = '+919876543210';
    fixture.componentInstance.requestId = 'req-123';
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const verifyBtn = el.querySelector<HTMLButtonElement>('button[aria-label="Verify OTP"]');
    expect(verifyBtn).not.toBeNull();
    expect(verifyBtn?.disabled).toBe(true);
  });

  // ── Test 5: Timer shows resend countdown ──

  it('shows resend countdown "Resend in 60s" on initial render', async () => {
    const fixture = TestBed.createComponent(OtpVerifyComponent);
    fixture.componentInstance.phone = '+919876543210';
    fixture.componentInstance.requestId = 'req-123';
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    // timeLeft starts at 60 — "Resend in 60s" should appear
    const resendSection = el.querySelector('.text-center');
    expect(resendSection?.textContent).toContain('60');
  });

  // ── Test 6: Error message renders ──

  it('renders error message in role="alert" element when errorMsg is set', async () => {
    const fixture = TestBed.createComponent(OtpVerifyComponent);
    fixture.componentInstance.phone = '+919876543210';
    fixture.componentInstance.requestId = 'req-123';
    fixture.detectChanges();
    await fixture.whenStable();

    fixture.componentInstance.errorMsg.set("That code doesn't match. Try again.");
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const el: HTMLElement = fixture.nativeElement;
    const alert = el.querySelector('[role="alert"]');
    expect(alert).not.toBeNull();
    expect(alert?.textContent).toContain("That code doesn't match. Try again.");
  });
});
