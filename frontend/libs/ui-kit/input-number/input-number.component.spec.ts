import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeInputNumberComponent } from './input-number.component';

describe('MeeInputNumberComponent', () => {
  let fixture: ComponentFixture<MeeInputNumberComponent>;
  let comp: MeeInputNumberComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeInputNumberComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeInputNumberComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default innerValue to null', () => {
    expect(comp.innerValue()).toBeNull();
  });

  it('should update innerValue via writeValue', () => {
    comp.writeValue(42);
    expect(comp.innerValue()).toBe(42);
  });

  it('should treat writeValue(null) as null', () => {
    comp.writeValue(null);
    expect(comp.innerValue()).toBeNull();
  });

  it('should call onChange when model changes', () => {
    let emitted: number | null = null;
    comp.registerOnChange((v: number | null) => { emitted = v; });
    comp.onModelChange(99);
    expect(comp.innerValue()).toBe(99);
    expect(emitted).toBe(99);
  });

  it('should emit value_change when model changes', () => {
    let emitted: number | null = null;
    comp.value_change.subscribe((v: number | null) => { emitted = v; });
    comp.onModelChange(7);
    expect(emitted).toBe(7);
  });

  it('should call onTouched on blur', () => {
    let touched = false;
    comp.registerOnTouched(() => { touched = true; });
    comp.onBlur();
    expect(touched).toBe(true);
  });

  it('should emit blur with current innerValue', () => {
    comp.writeValue(123);
    let emitted: number | null = undefined as unknown as number | null;
    comp.blur.subscribe((v: number | null) => { emitted = v; });
    comp.onBlur();
    expect(emitted).toBe(123);
  });

  it('should have showButtons=false (no spinner buttons)', () => {
    fixture.detectChanges();
    const spinnerBtns = fixture.nativeElement.querySelectorAll('.p-inputnumber-button');
    expect(spinnerBtns.length).toBe(0);
  });

  describe('tooltip icon', () => {
    it('should NOT render info icon when tooltip is not set', () => {
      fixture.detectChanges();
      const icon = fixture.nativeElement.querySelector('i.pi-info-circle');
      expect(icon).toBeNull();
    });

    it('should render info icon when tooltip is set', () => {
      fixture.componentRef.setInput('tooltip', 'Maximum retail price');
      fixture.detectChanges();
      const icon = fixture.nativeElement.querySelector('i.pi-info-circle');
      expect(icon).toBeTruthy();
    });
  });

  describe('label rendering', () => {
    it('should NOT render label when label input is not set', () => {
      fixture.detectChanges();
      const label = fixture.nativeElement.querySelector('label');
      expect(label).toBeNull();
    });

    it('should render label when label input is set', () => {
      fixture.componentRef.setInput('label', 'Selling Price');
      fixture.detectChanges();
      const label = fixture.nativeElement.querySelector('label');
      expect(label).toBeTruthy();
      expect(label.textContent).toContain('Selling Price');
    });
  });

  it('CVA round-trip: writeValue reflected in innerValue signal', () => {
    comp.writeValue(500);
    expect(comp.innerValue()).toBe(500);
    comp.writeValue(null);
    expect(comp.innerValue()).toBeNull();
  });
});
