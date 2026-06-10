// wizard-renderer.component.spec.ts — 3 tests per spec
// Signal inputs don't work with fixture.componentRef.setInput() in vitest+jsdom (NG0303).
// Tests verify component methods and outputs directly without accessing signal inputs.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { Component } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { WizardRendererComponent, WizardStep } from './wizard-renderer.component';
import { FieldSchema } from '@core/models/field-schema.model';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';
import { FieldDispatcherComponent } from './field-dispatcher.component';
import { ValueChange } from '../primitives/primitive.contract';

// Stub FieldDispatcherComponent to avoid pulling in all 11 primitives
@Component({
  selector: 'mee-field-dispatcher',
  standalone: true,
  template: '<div class="stub-dispatcher"></div>',
  inputs: ['schema', 'value', 'aiSuggestion', 'disabled'],
  outputs: ['valueChange'],
})
class FieldDispatcherStub {}

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

describe('WizardRendererComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        WizardRendererComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    })
      .overrideComponent(WizardRendererComponent, {
        remove: { imports: [FieldDispatcherComponent] },
        add: { imports: [FieldDispatcherStub] },
      })
      .compileComponents();
  });

  it('should instantiate WizardRendererComponent', () => {
    const fixture = TestBed.createComponent(WizardRendererComponent);
    // Cannot set signal inputs via setInput() in this test env — just verify instantiation
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('patch() emits valueChange output', () => {
    const fixture = TestBed.createComponent(WizardRendererComponent);
    const component = fixture.componentInstance;
    const emitSpy = vi.fn();
    component.valueChange.subscribe(emitSpy);
    const change: ValueChange = { canonicalName: 'name', value: 'Kurti', source: 'seller' };
    component.patch(change);
    expect(emitSpy).toHaveBeenCalledWith(change);
  });

  it('onSubmit() emits submit output', () => {
    const fixture = TestBed.createComponent(WizardRendererComponent);
    const component = fixture.componentInstance;
    const submitSpy = vi.fn();
    component.submit.subscribe(submitSpy);
    component.onSubmit();
    expect(submitSpy).toHaveBeenCalled();
  });
});
