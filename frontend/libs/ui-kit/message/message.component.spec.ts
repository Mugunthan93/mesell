import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeMessageComponent } from './message.component';

function makeComp() {
  const fixture = TestBed.createComponent(MeeMessageComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeMessageComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeMessageComponent, NoopAnimationsModule],
    });
  });

  it('(1) creates with default severity=info — pgSeverity() returns "info"', () => {
    const { comp } = makeComp();
    expect(comp.severity()).toBe('info');
    expect(comp.pgSeverity()).toBe('info');
    expect(comp.closable()).toBe(false);
  });

  it('(2) severity="error" maps to pgSeverity()="error" (1:1 passthrough)', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('severity', 'error');
    expect(comp.pgSeverity()).toBe('error');
  });

  it('(3) closable=true exposes the closed output for subscription', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('closable', true);
    expect(comp.closable()).toBe(true);

    // closed output fires on emit
    const fired: void[] = [];
    comp.closed.subscribe(() => fired.push());
    comp.closed.emit();
    expect(fired.length).toBe(1);
  });
});
