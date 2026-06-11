import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeTextareaComponent } from './textarea.component';

describe('MeeTextareaComponent', () => {
  let fixture: ComponentFixture<MeeTextareaComponent>;
  let comp: MeeTextareaComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeTextareaComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeTextareaComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default rows to 4', () => {
    expect(comp.rows()).toBe(4);
  });

  it('should default autoResize to false', () => {
    expect(comp.autoResize()).toBe(false);
  });

  it('should update innerValue via writeValue', () => {
    comp.writeValue('description text');
    expect(comp.innerValue()).toBe('description text');
  });

  it('should call onChange when model changes', () => {
    let emitted = '';
    comp.registerOnChange((v: string) => { emitted = v; });
    comp.onModelChange('hello world');
    expect(emitted).toBe('hello world');
  });

  it('should call onTouched on blur', () => {
    let touched = false;
    comp.registerOnTouched(() => { touched = true; });
    comp.onTouched();
    expect(touched).toBe(true);
  });
});
