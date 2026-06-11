import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeOtpInputComponent } from './otp-input.component';

describe('MeeOtpInputComponent', () => {
  let fixture: ComponentFixture<MeeOtpInputComponent>;
  let comp: MeeOtpInputComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeOtpInputComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeOtpInputComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default length to 6', () => {
    expect(comp.length()).toBe(6);
  });

  it('should update innerValue on OTP change', () => {
    comp.onOtpChange('1234');
    expect(comp.innerValue()).toBe('1234');
  });

  it('should emit completed when full length is entered', () => {
    let emitted = '';
    comp.completed.subscribe((v: string) => { emitted = v; });
    comp.onOtpChange('123456');
    expect(emitted).toBe('123456');
  });

  it('should not emit completed for partial input', () => {
    let emitted = false;
    comp.completed.subscribe(() => { emitted = true; });
    comp.onOtpChange('123');
    expect(emitted).toBe(false);
  });

  it('should handle writeValue', () => {
    comp.writeValue('999999');
    expect(comp.innerValue()).toBe('999999');
  });
});
