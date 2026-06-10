import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeSelectComponent } from './select.component';
import type { MeeSelectOption } from './select.types';

const MOCK_OPTIONS: MeeSelectOption[] = [
  { label: 'Option A', value: 'a' },
  { label: 'Option B', value: 'b' },
];

describe('MeeSelectComponent', () => {
  let fixture: ComponentFixture<MeeSelectComponent>;
  let comp: MeeSelectComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeSelectComponent, NoopAnimationsModule],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeSelectComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('options', MOCK_OPTIONS);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should default placeholder to Select', () => {
    expect(comp.placeholder()).toBe('Select');
  });

  it('should update innerValue and call onChange', () => {
    let emitted: unknown = null;
    comp.registerOnChange((v: unknown) => { emitted = v; });
    comp.onSelectChange('a');
    expect(comp.innerValue()).toBe('a');
    expect(emitted).toBe('a');
  });

  it('should emit value_change', () => {
    let emitted: unknown = null;
    comp.value_change.subscribe((v: unknown) => { emitted = v; });
    comp.onSelectChange('b');
    expect(emitted).toBe('b');
  });

  it('should handle writeValue', () => {
    comp.writeValue('a');
    expect(comp.innerValue()).toBe('a');
  });

  it('should default innerValue to null on writeValue(null)', () => {
    comp.writeValue(null);
    expect(comp.innerValue()).toBeNull();
  });
});
