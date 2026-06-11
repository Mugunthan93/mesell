import { ComponentFixture, TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { OtpVerifyComponent } from './otp-verify.component';
import { AuthService } from '@mesell/core';

describe('OtpVerifyComponent', () => {
  let fixture: ComponentFixture<OtpVerifyComponent>;
  let comp: OtpVerifyComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [OtpVerifyComponent, RouterTestingModule, NoopAnimationsModule],
    }).compileComponents();
    fixture = TestBed.createComponent(OtpVerifyComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  afterEach(() => {
    // destroy component to clear interval
    fixture.destroy();
  });

  it('should render mee-auth-layout', () => {
    expect(fixture.nativeElement.querySelector('mee-auth-layout')).toBeTruthy();
  });

  it('should initialise countdown at 30', () => {
    expect(comp.countdown()).toBe(30);
  });

  it('should not call auth.setSession on init', () => {
    const authSvc = TestBed.inject(AuthService);
    expect(authSvc.isAuthenticated()).toBeFalsy();
  });

  it('should initialise otpValue as empty string', () => {
    expect(comp.otpValue()).toBe('');
  });

  it('should set otpValue when onOtpCompleted is called', () => {
    comp.onOtpCompleted('123456');
    expect(comp.otpValue()).toBe('123456');
  });
});
