// field-dispatcher.component.spec.ts — 2 tests per spec:
// Verifies the dispatcher component is correctly configured.
// Signal inputs can't be set via fixture.componentRef.setInput() in vitest+jsdom (NG0303).
// Tests verify the component class structure and imports rather than template rendering.

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { Component } from '@angular/core';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { describe, it, expect, beforeEach } from 'vitest';
import { FieldDispatcherComponent } from './field-dispatcher.component';
import { TranslocoTestingModule, TranslocoTestingOptions } from '@jsverse/transloco';

const translocoOptions: TranslocoTestingOptions = {
  langs: { en: {} },
  translocoConfig: { defaultLang: 'en', availableLangs: ['en'] },
};

describe('FieldDispatcherComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        FieldDispatcherComponent,
        TranslocoTestingModule.forRoot(translocoOptions),
      ],
      providers: [provideExperimentalZonelessChangeDetection(), provideAnimationsAsync('noop')],
    }).compileComponents();
  });

  it('should instantiate the FieldDispatcherComponent class', () => {
    const fixture = TestBed.createComponent(FieldDispatcherComponent);
    // Do NOT call schema() — it would throw NG0950 since setInput doesn't work
    // Verify the component instance exists
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('onChange() passes ValueChange through to valueChange output', () => {
    const fixture = TestBed.createComponent(FieldDispatcherComponent);
    const component = fixture.componentInstance;
    const emitSpy: unknown[] = [];
    component.valueChange.subscribe((v) => emitSpy.push(v));
    const change = { canonicalName: 'name', value: 'test', source: 'seller' as const };
    component.onChange(change);
    expect(emitSpy).toHaveLength(1);
    expect(emitSpy[0]).toEqual(change);
  });
});
