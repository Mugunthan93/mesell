import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeButtonComponent } from './button.component';

describe('MeeButtonComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NoopAnimationsModule],
    }).compileComponents();
  });

  function makeComp(label: string, overrides: Record<string, unknown> = {}): MeeButtonComponent {
    const fixture = TestBed.createComponent(MeeButtonComponent);
    fixture.componentRef.setInput('label', label);
    for (const [key, value] of Object.entries(overrides)) {
      fixture.componentRef.setInput(key, value);
    }
    // Do NOT call detectChanges — avoids PrimeNG jsdom rendering error for p-button inputs
    return fixture.componentInstance;
  }

  it('should create', () => {
    const comp = makeComp('Test');
    expect(comp).toBeTruthy();
  });

  it('should map primary variant to no severity', () => {
    const comp = makeComp('Test', { variant: 'primary' });
    expect(comp.pgSeverity()).toBeUndefined();
  });

  it('should map secondary variant correctly', () => {
    const comp = makeComp('Test', { variant: 'secondary' });
    expect(comp.pgSeverity()).toBe('secondary');
    expect(comp.pgVariant()).toBe('outlined');
  });

  it('should map danger variant correctly', () => {
    const comp = makeComp('Test', { variant: 'danger' });
    expect(comp.pgSeverity()).toBe('danger');
  });

  it('should map ghost variant to contrast', () => {
    const comp = makeComp('Test', { variant: 'ghost' });
    expect(comp.pgSeverity()).toBe('contrast');
    expect(comp.pgVariant()).toBe('text');
  });

  it('should map sm size to small', () => {
    const comp = makeComp('Test', { size: 'sm' });
    expect(comp.pgSize()).toBe('small');
  });

  it('should map lg size to large', () => {
    const comp = makeComp('Test', { size: 'lg' });
    expect(comp.pgSize()).toBe('large');
  });

  it('should emit clicked output', () => {
    const comp = makeComp('Test');
    let emitted = false;
    comp.clicked.subscribe(() => { emitted = true; });
    comp.clicked.emit();
    expect(emitted).toBe(true);
  });

  it('pgIcon should return undefined when no icon is provided', () => {
    const comp = makeComp('Test');
    expect(comp.pgIcon()).toBeUndefined();
  });

  it('pgIcon should map auto_awesome to pi pi-sparkles', () => {
    const comp = makeComp('Test', { icon: 'auto_awesome' });
    expect(comp.pgIcon()).toBe('pi pi-sparkles');
  });

  it('pgIcon should map arrow_forward to pi pi-arrow-right', () => {
    const comp = makeComp('Test', { icon: 'arrow_forward' });
    expect(comp.pgIcon()).toBe('pi pi-arrow-right');
  });

  it('pgIcon should map arrow_back to pi pi-arrow-left', () => {
    const comp = makeComp('Test', { icon: 'arrow_back' });
    expect(comp.pgIcon()).toBe('pi pi-arrow-left');
  });

  it('pgIcon should map check to pi pi-check', () => {
    const comp = makeComp('Test', { icon: 'check' });
    expect(comp.pgIcon()).toBe('pi pi-check');
  });

  it('pgIcon should map close to pi pi-times', () => {
    const comp = makeComp('Test', { icon: 'close' });
    expect(comp.pgIcon()).toBe('pi pi-times');
  });

  it('pgIcon should map delete to pi pi-trash', () => {
    const comp = makeComp('Test', { icon: 'delete' });
    expect(comp.pgIcon()).toBe('pi pi-trash');
  });

  it('pgIcon should pass through unmapped icon names unchanged', () => {
    const comp = makeComp('Test', { icon: 'pi pi-user' });
    expect(comp.pgIcon()).toBe('pi pi-user');
  });
});
