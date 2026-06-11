import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { LoginComponent } from './login.component';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  let comp: LoginComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LoginComponent, ReactiveFormsModule, RouterTestingModule, NoopAnimationsModule],
    }).compileComponents();
    fixture = TestBed.createComponent(LoginComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should render mee-auth-layout', () => {
    expect(fixture.nativeElement.querySelector('mee-auth-layout')).toBeTruthy();
  });

  it('should have form invalid when phone is empty', () => {
    comp.form.get('phone')!.setValue('');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should have form invalid when phone is less than 10 digits', () => {
    comp.form.get('phone')!.setValue('98765');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });
});
