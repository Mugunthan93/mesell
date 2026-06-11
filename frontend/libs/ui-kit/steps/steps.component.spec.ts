import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MeeStepsComponent } from './steps.component';
import type { MeeStep } from './steps.types';

const MOCK_STEPS: MeeStep[] = [
  { label: 'Step 1' },
  { label: 'Step 2' },
  { label: 'Step 3' },
];

describe('MeeStepsComponent', () => {
  let fixture: ComponentFixture<MeeStepsComponent>;
  let comp: MeeStepsComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeStepsComponent, NoopAnimationsModule],
      providers: [provideRouter([])],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeStepsComponent);
    comp = fixture.componentInstance;
    fixture.componentRef.setInput('steps', MOCK_STEPS);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(comp).toBeTruthy();
  });

  it('should convert MeeStep[] to MenuItem[]', () => {
    const items = comp.menuItems();
    expect(items.length).toBe(3);
    expect(items[0].label).toBe('Step 1');
  });

  it('should default active_index to 0', () => {
    expect(comp.active_index()).toBe(0);
  });

  it('should emit active_index_change', () => {
    let emitted: number | null = null;
    comp.active_index_change.subscribe((i: number) => { emitted = i; });
    comp.active_index_change.emit(2);
    expect(emitted).toBe(2);
  });
});
