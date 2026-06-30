import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeInputComponent } from './input.component';

describe('MeeInputComponent', () => {
  let fixture: ComponentFixture<MeeInputComponent>;
  let comp: MeeInputComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeInputComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeInputComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should update innerValue via writeValue', () => {
    comp.writeValue('test-val');
    expect(comp.innerValue()).toBe('test-val');
  });

  it('should call onChange when model changes', () => {
    let emitted = '';
    comp.registerOnChange((v: string) => { emitted = v; });
    comp.onModelChange('hello');
    expect(emitted).toBe('hello');
    expect(comp.innerValue()).toBe('hello');
  });

  it('should call onTouched on blur', () => {
    let touched = false;
    comp.registerOnTouched(() => { touched = true; });
    comp.onTouched();
    expect(touched).toBe(true);
  });

  it('should accept null in writeValue', () => {
    comp.writeValue(null);
    expect(comp.innerValue()).toBe('');
  });

  it('onBlur should emit the current innerValue as a string on the blur output', () => {
    comp.onModelChange('hello');
    let emitted: string | undefined;
    comp.blur.subscribe((v: string) => { emitted = v; });
    comp.onBlur();
    expect(typeof emitted).toBe('string');
    expect(emitted).toBe('hello');
  });

  it('onBlur should invoke the registered onTouched callback', () => {
    let touched = false;
    comp.registerOnTouched(() => { touched = true; });
    comp.onBlur();
    expect(touched).toBe(true);
  });

  describe('tooltip icon', () => {
    it('should NOT render info icon when tooltip is not set', () => {
      fixture.detectChanges();
      const icon = fixture.nativeElement.querySelector('i.pi-info-circle');
      expect(icon).toBeNull();
    });

    it('should render info icon when tooltip is set', () => {
      fixture.componentRef.setInput('tooltip', 'Help text for this field');
      fixture.componentRef.setInput('label', 'Product Name');
      fixture.detectChanges();
      const icon = fixture.nativeElement.querySelector('i.pi-info-circle');
      expect(icon).toBeTruthy();
    });
  });

  describe('testId passthrough', () => {
    it('sets data-testid on the inner input when testId is provided', () => {
      fixture.componentRef.setInput('testId', 'login-phone-input');
      fixture.detectChanges();
      const input = fixture.nativeElement.querySelector('input[data-testid="login-phone-input"]');
      expect(input).toBeTruthy();
    });

    it('does not set data-testid when testId is not provided', () => {
      fixture.detectChanges();
      const input = fixture.nativeElement.querySelector('input[data-testid]');
      expect(input).toBeNull();
    });
  });
});
