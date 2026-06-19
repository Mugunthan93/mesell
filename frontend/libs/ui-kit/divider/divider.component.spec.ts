import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeDividerComponent } from './divider.component';

function makeComp() {
  const fixture = TestBed.createComponent(MeeDividerComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeDividerComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeDividerComponent, NoopAnimationsModule],
    });
  });

  it('(1) renders horizontal by default', () => {
    const { comp } = makeComp();
    expect(comp.layout()).toBe('horizontal');
    expect(comp.type()).toBe('solid');
    expect(comp.align()).toBeUndefined();
  });

  it('(2) layout="vertical" passes through correctly', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('layout', 'vertical');
    expect(comp.layout()).toBe('vertical');
  });

  it('(3) all inputs are bound via signal inputs — type and align accessible', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('type', 'dashed');
    fixture.componentRef.setInput('align', 'center');
    expect(comp.type()).toBe('dashed');
    expect(comp.align()).toBe('center');
  });
});
