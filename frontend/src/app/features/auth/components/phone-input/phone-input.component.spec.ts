// features/auth/components/phone-input/phone-input.component.spec.ts
// Unit tests for PhoneInputComponent (ControlValueAccessor)
// Pattern: Vitest + Angular TestBed (zoneless) — direct CVA method testing
// to avoid NG0950 from signal inputs + jsdom limitations.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { describe, expect, it, beforeEach } from 'vitest';

import { PhoneInputComponent } from './phone-input.component';

const TRANSLOCO_OPTIONS: TranslocoTestingOptions = {
  langs: {
    en: {
      'auth.phone.error.invalid': 'Please enter a valid 10-digit mobile number.',
    },
  },
  translocoConfig: {
    availableLangs: ['en'],
    defaultLang: 'en',
  },
};

describe('PhoneInputComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        PhoneInputComponent,
        TranslocoTestingModule.forRoot(TRANSLOCO_OPTIONS),
      ],
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideAnimationsAsync('noop'),
      ],
    }).compileComponents();
  });

  // Test 1: renders +91 prefix in template
  it('renders +91 prefix in the template', async () => {
    const fixture = TestBed.createComponent(PhoneInputComponent);
    fixture.componentInstance.label = 'Mobile number';
    fixture.detectChanges();
    await fixture.whenStable();

    const prefixEl = fixture.nativeElement.querySelector('span');
    expect(prefixEl?.textContent?.trim()).toBe('+91');
  });

  // Test 2: strips non-digit characters on input via onInput handler
  it('strips non-digit characters on input', () => {
    const fixture = TestBed.createComponent(PhoneInputComponent);
    const component = fixture.componentInstance;

    let emitted = '';
    component.registerOnChange((v: string) => { emitted = v; });

    // Simulate input event with non-digit chars
    const input = document.createElement('input');
    input.value = 'abc9876543210xyz';
    const event = new Event('input');
    Object.defineProperty(event, 'target', { value: input });
    component.onInput(event as Event);

    // displayValue should contain only digits (limited to 10)
    expect(component.displayValue()).toBe('9876543210');
    expect(emitted).toBe('+919876543210');
  });

  // Test 3: limits to 10 digits maximum
  it('limits input to 10 digits', () => {
    const fixture = TestBed.createComponent(PhoneInputComponent);
    const component = fixture.componentInstance;

    component.registerOnChange(() => {});

    const input = document.createElement('input');
    input.value = '12345678901234'; // 14 digits
    const event = new Event('input');
    Object.defineProperty(event, 'target', { value: input });
    component.onInput(event as Event);

    expect(component.displayValue()).toBe('1234567890'); // truncated to 10
  });

  // Test 4: formats valid 10-digit input to E.164 on value change
  it('formats valid 10-digit input to E.164 (+91XXXXXXXXXX)', () => {
    const fixture = TestBed.createComponent(PhoneInputComponent);
    const component = fixture.componentInstance;

    let emittedValue = '';
    component.registerOnChange((v: string) => { emittedValue = v; });

    const input = document.createElement('input');
    input.value = '9876543210';
    const event = new Event('input');
    Object.defineProperty(event, 'target', { value: input });
    component.onInput(event as Event);

    expect(emittedValue).toBe('+919876543210');
  });

  // Test 5: shows error message when touched + invalid (less than 10 digits)
  it('shows error message when touched and input is invalid', async () => {
    const fixture = TestBed.createComponent(PhoneInputComponent);
    const component = fixture.componentInstance;
    fixture.componentInstance.label = 'Mobile number';

    // Simulate partial input (5 digits — invalid)
    component.registerOnChange(() => {});
    const input = document.createElement('input');
    input.value = '98765';
    const event = new Event('input');
    Object.defineProperty(event, 'target', { value: input });
    component.onInput(event as Event);

    // Mark as touched
    component.onBlur();
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const errorEl = fixture.nativeElement.querySelector('.mee-phone-error');
    expect(errorEl).not.toBeNull();
    expect(errorEl?.textContent?.trim()).toContain('valid 10-digit');
  });

  // Test 6: does NOT show error when pristine (not yet touched)
  it('does NOT show error when pristine (not yet touched)', async () => {
    const fixture = TestBed.createComponent(PhoneInputComponent);
    fixture.componentInstance.label = 'Mobile number';
    fixture.detectChanges();
    await fixture.whenStable();

    // touched() is false by default — no onBlur() called
    const errorEl = fixture.nativeElement.querySelector('.mee-phone-error');
    expect(errorEl).toBeNull();
  });
});
