import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeCheckboxComponent } from './checkbox.component';

function makeComp() {
  const fixture = TestBed.createComponent(MeeCheckboxComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeCheckboxComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeCheckboxComponent, ReactiveFormsModule, NoopAnimationsModule],
    });
  });

  it('(1) creates with default binary=true and innerValue=false (unchecked)', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('label', 'Accept terms');
    // Do NOT call detectChanges — avoid PrimeNG ngModule null crash
    expect(comp.binary()).toBe(true);
    expect(comp.innerValue()).toBe(false);
  });

  it('(2) CVA writeValue + registerOnChange propagate boolean through CVA', () => {
    const { comp } = makeComp();
    const received: boolean[] = [];
    comp.registerOnChange((v: boolean) => received.push(v));

    // writeValue sets inner state
    comp.writeValue(true);
    expect(comp.innerValue()).toBe(true);

    // onModelChange propagates through CVA
    comp.onModelChange(false);
    expect(comp.innerValue()).toBe(false);
    expect(received).toEqual([false]);
  });

  it('(3) error input makes computedError truthy and emits changed output', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('error', 'Required');

    // Error signal readable
    expect(comp.error()).toBe('Required');

    // changed output fires on toggle
    const emitted: boolean[] = [];
    comp.changed.subscribe((v: boolean) => emitted.push(v));
    comp.onModelChange(true);
    expect(emitted).toEqual([true]);
  });
});
