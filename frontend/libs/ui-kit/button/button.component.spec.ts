import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeButtonComponent } from './button.component';
import { MEE_ICONS } from '../icon/icon.registry';
import type { MeeIconName } from '../icon/icon.registry';

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

  it('pgIcon "sparkles" resolves via registry to MEE_ICONS["sparkles"]', () => {
    const comp = makeComp('Test', { icon: 'sparkles' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['sparkles']);
  });

  it('pgIcon "forward" resolves via registry to MEE_ICONS["forward"]', () => {
    const comp = makeComp('Test', { icon: 'forward' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['forward']);
  });

  it('pgIcon "back" resolves via registry to MEE_ICONS["back"]', () => {
    const comp = makeComp('Test', { icon: 'back' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['back']);
  });

  it('pgIcon "check" resolves via registry to MEE_ICONS["check"]', () => {
    const comp = makeComp('Test', { icon: 'check' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['check']);
  });

  it('pgIcon "close" resolves via registry to MEE_ICONS["close"]', () => {
    const comp = makeComp('Test', { icon: 'close' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['close']);
  });

  it('pgIcon "delete" resolves via registry to MEE_ICONS["delete"]', () => {
    const comp = makeComp('Test', { icon: 'delete' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['delete']);
  });

  it('pgIcon "user" resolves via registry to MEE_ICONS["user"]', () => {
    const comp = makeComp('Test', { icon: 'user' satisfies MeeIconName });
    expect(comp.pgIcon()).toBe(MEE_ICONS['user']);
  });

  describe('testId passthrough', () => {
    it('returns the testId signal value when provided', () => {
      const comp = makeComp('Test', { testId: 'login-request-otp' });
      expect(comp.testId()).toBe('login-request-otp');
    });

    it('returns undefined when testId is not provided', () => {
      const comp = makeComp('Test');
      expect(comp.testId()).toBeUndefined();
    });
  });
});
