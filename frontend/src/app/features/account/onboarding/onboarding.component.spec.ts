import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, forwardRef, Input } from '@angular/core';
import {
  ControlValueAccessor,
  NG_VALUE_ACCESSOR,
  ReactiveFormsModule,
} from '@angular/forms';
import { Router } from '@angular/router';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { OnboardingComponent, optionalGstValidator } from './onboarding.component';
import {
  MeeButtonComponent,
  MeeInputComponent,
  MeeStepsComponent,
} from '../../../ui';
import type { MeeStep } from '../../../ui';
import type { MeeButtonVariant } from '../../../ui';

// Stubs for mee-* children to avoid PrimeNG rendering in jsdom

@Component({
  selector: 'mee-steps',
  standalone: true,
  template: '<div class="mee-steps-stub"></div>',
})
class MeeStepsStub {
  @Input() steps: MeeStep[] = [];
  @Input() active_index = 0;
}

/** MeeInputStub must implement CVA so formControlName binding works without NG01203. */
@Component({
  selector: 'mee-input',
  standalone: true,
  template: '<input class="mee-input-stub" />',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => MeeInputStub),
      multi: true,
    },
  ],
})
class MeeInputStub implements ControlValueAccessor {
  @Input() label: string | undefined = undefined;
  @Input() required = false;
  @Input() error: string | undefined = undefined;
  writeValue(_v: unknown): void {}
  registerOnChange(_fn: (_: unknown) => void): void {}
  registerOnTouched(_fn: () => void): void {}
  setDisabledState?(_isDisabled: boolean): void {}
}

@Component({
  selector: 'mee-button',
  standalone: true,
  template: '<button class="mee-button-stub" [disabled]="disabled">{{ label }}</button>',
})
class MeeButtonStub {
  @Input() label = '';
  @Input() loading = false;
  @Input() disabled = false;
  @Input() fullWidth = false;
  @Input() variant: MeeButtonVariant = 'primary';
}

describe('OnboardingComponent', () => {
  let fixture: ComponentFixture<OnboardingComponent>;
  let component: OnboardingComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OnboardingComponent, ReactiveFormsModule],
      providers: [
        provideRouter([]),
        provideAnimationsAsync('noop'),
      ],
    })
      .overrideComponent(OnboardingComponent, {
        remove: { imports: [MeeStepsComponent, MeeInputComponent, MeeButtonComponent] },
        add: { imports: [MeeStepsStub, MeeInputStub, MeeButtonStub] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(OnboardingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // Gate spec 1: mee-auth-layout is present in the rendered output
  it('should render inside mee-auth-layout', () => {
    const authLayout = fixture.nativeElement.querySelector('mee-auth-layout');
    expect(authLayout).not.toBeNull();
  });

  // Gate spec 2: Submit button disabled when businessName is empty
  it('should disable the submit button when businessName is empty', () => {
    component.form.get('businessName')!.setValue('');
    fixture.detectChanges();
    // form.invalid is true → mee-button receives [disabled]="true"
    expect(component.form.invalid).toBeTruthy();
    const buttonEl = fixture.nativeElement.querySelector('.mee-button-stub');
    expect(buttonEl?.getAttribute('disabled')).not.toBeNull();
  });

  // Gate spec 3: city control default value is 'Tirupur'
  it('should pre-fill city with Tirupur', () => {
    expect(component.form.get('city')!.value).toBe('Tirupur');
  });

  // Gate spec 4: form is valid when gstNumber is empty and required fields are filled
  it('should be valid when GST is empty and required fields are filled', () => {
    component.form.setValue({
      businessName: 'My Textile Shop',
      city: 'Tirupur',
      gstNumber: '',
    });
    expect(component.form.valid).toBeTruthy();
  });

  // Extra: form invalid when businessName too short
  it('should be invalid when businessName is shorter than 2 characters', () => {
    component.form.setValue({
      businessName: 'A',
      city: 'Tirupur',
      gstNumber: '',
    });
    expect(component.form.get('businessName')!.hasError('minlength')).toBeTruthy();
    expect(component.form.valid).toBeFalsy();
  });

  // Extra: gstNumber field rejects invalid GSTIN when non-empty
  it('should show gst error when GST format is invalid', () => {
    component.form.setValue({
      businessName: 'Shop',
      city: 'Tirupur',
      gstNumber: 'INVALID123',
    });
    expect(component.form.get('gstNumber')!.hasError('gstPattern')).toBeTruthy();
  });

  // Extra: valid GSTIN passes the optional validator
  it('should accept a correctly formatted GSTIN', () => {
    component.form.setValue({
      businessName: 'Shop',
      city: 'Tirupur',
      gstNumber: '29ABCDE1234F1Z5',
    });
    expect(component.form.get('gstNumber')!.valid).toBeTruthy();
    expect(component.form.valid).toBeTruthy();
  });

  // Extra: loading starts false; onSubmit sets it true then navigates
  it('should set loading to true on submit and navigate after timeout', () => {
    vi.useFakeTimers();
    const router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);

    component.form.setValue({
      businessName: 'My Shop',
      city: 'Tirupur',
      gstNumber: '',
    });

    component.onSubmit();
    expect(component.loading()).toBeTruthy();

    vi.advanceTimersByTime(1500);
    expect(component.loading()).toBeFalsy();
    expect(router.navigate).toHaveBeenCalledWith(['/dashboard']);

    vi.useRealTimers();
  });
});

describe('optionalGstValidator', () => {
  const validator = optionalGstValidator();

  it('should return null when value is empty', () => {
    const result = validator({ value: '' } as never);
    expect(result).toBeNull();
  });

  it('should return null when value is whitespace-only', () => {
    const result = validator({ value: '   ' } as never);
    expect(result).toBeNull();
  });

  it('should return gstPattern error for invalid GSTIN', () => {
    const result = validator({ value: 'BADGSTIN' } as never);
    expect(result).toEqual({ gstPattern: true });
  });

  it('should return null for a valid GSTIN', () => {
    const result = validator({ value: '29ABCDE1234F1Z5' } as never);
    expect(result).toBeNull();
  });
});
