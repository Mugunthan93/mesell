import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { SignupComponent } from './signup.component';

describe('SignupComponent', () => {
  let fixture: ComponentFixture<SignupComponent>;
  let comp: SignupComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SignupComponent, ReactiveFormsModule, RouterTestingModule, NoopAnimationsModule],
    }).compileComponents();
    fixture = TestBed.createComponent(SignupComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should render mee-auth-layout', () => {
    expect(fixture.nativeElement.querySelector('mee-auth-layout')).toBeTruthy();
  });

  it('should be invalid when name is empty', () => {
    comp.form.get('name')!.setValue('');
    comp.form.get('phone')!.setValue('9876543210');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });

  it('should be invalid when phone is invalid', () => {
    comp.form.get('name')!.setValue('Test');
    comp.form.get('phone')!.setValue('12345');
    fixture.detectChanges();
    expect(comp.form.invalid).toBeTruthy();
  });
});
