import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeRadioComponent } from './radio.component';
import type { MeeSelectOption } from '../select/select.types';

const OPTIONS: MeeSelectOption[] = [
  { label: 'Option A', value: 'a' },
  { label: 'Option B', value: 'b' },
  { label: 'Option C', value: 'c' },
];

function makeComp() {
  const fixture = TestBed.createComponent(MeeRadioComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeRadioComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeRadioComponent, ReactiveFormsModule, NoopAnimationsModule],
    });
  });

  it('(1) renders one radio per option — options() length matches', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('options', OPTIONS);
    // Verify options signal was set
    expect(comp.options().length).toBe(3);
    expect(comp.options()[0].label).toBe('Option A');
    expect(comp.options()[1].value).toBe('b');
  });

  it('(2) CVA: selecting an option propagates that value through registerOnChange', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('options', OPTIONS);

    const received: unknown[] = [];
    comp.registerOnChange((v: unknown) => received.push(v));

    comp.onModelChange('b');
    expect(comp.innerValue()).toBe('b');
    expect(received).toEqual(['b']);
  });

  it('(3) disabled input sets disabled() to true', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('options', OPTIONS);
    fixture.componentRef.setInput('disabled', true);
    expect(comp.disabled()).toBe(true);
  });
});
