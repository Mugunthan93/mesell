import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeePasswordInputComponent } from './password-input.component';

describe('MeePasswordInputComponent', () => {
  let fixture: ComponentFixture<MeePasswordInputComponent>;
  let comp: MeePasswordInputComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeePasswordInputComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeePasswordInputComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default toggleMask to true', () => {
    expect(comp.toggleMask()).toBe(true);
  });

  it('should default feedback to false', () => {
    expect(comp.feedback()).toBe(false);
  });

  it('should update innerValue via writeValue', () => {
    comp.writeValue('secret123');
    expect(comp.innerValue()).toBe('secret123');
  });

  it('should call onChange when model changes', () => {
    let emitted = '';
    comp.registerOnChange((v: string) => { emitted = v; });
    comp.onModelChange('myPassword');
    expect(emitted).toBe('myPassword');
  });

  it('should handle null in writeValue', () => {
    comp.writeValue(null);
    expect(comp.innerValue()).toBe('');
  });
});
