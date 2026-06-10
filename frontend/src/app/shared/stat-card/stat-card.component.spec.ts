import { Component, input } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { StatCardComponent } from './stat-card.component';
import { MeeCardComponent } from '../../ui';

// Stub mee-card to avoid PrimeNG in tests
@Component({ selector: 'mee-card', standalone: true, template: '<ng-content />' })
class MeeCardStub {}

describe('StatCardComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
    TestBed.overrideComponent(StatCardComponent, {
      remove: { imports: [MeeCardComponent] },
      add:    { imports: [MeeCardStub] },
    });
  });

  function makeComp(overrides?: {
    trend?: number;
    trend_label?: string;
    color?: 'orange' | 'blue' | 'green' | 'purple';
  }) {
    const fixture = TestBed.createComponent(StatCardComponent);
    fixture.componentRef.setInput('label', 'Total Products');
    fixture.componentRef.setInput('value', '1,234');
    fixture.componentRef.setInput('icon', 'inventory_2');
    if (overrides?.trend !== undefined) {
      fixture.componentRef.setInput('trend', overrides.trend);
    }
    if (overrides?.trend_label !== undefined) {
      fixture.componentRef.setInput('trend_label', overrides.trend_label);
    }
    if (overrides?.color !== undefined) {
      fixture.componentRef.setInput('color', overrides.color);
    }
    return fixture;
  }

  it('renders label and value', () => {
    const fixture = makeComp();
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('Total Products');
    expect(el.textContent).toContain('1,234');
  });

  it('trendPositive is true when trend > 0', () => {
    const fixture = makeComp({ trend: 12.5 });
    const comp = fixture.componentInstance;
    expect(comp.trendPositive()).toBe(true);
  });

  it('trendPositive is false when trend < 0', () => {
    const fixture = makeComp({ trend: -3.2 });
    const comp = fixture.componentInstance;
    expect(comp.trendPositive()).toBe(false);
  });

  it('trendPositive defaults to false when trend is undefined', () => {
    const fixture = makeComp();
    const comp = fixture.componentInstance;
    expect(comp.trendPositive()).toBe(false);
  });

  it('accentColor maps orange to primary CSS var', () => {
    const fixture = makeComp({ color: 'orange' });
    const comp = fixture.componentInstance;
    expect(comp.accentColor()).toBe('var(--mee-color-primary)');
  });

  it('accentColor maps blue to info CSS var', () => {
    const fixture = makeComp({ color: 'blue' });
    const comp = fixture.componentInstance;
    expect(comp.accentColor()).toBe('var(--mee-color-info)');
  });

  it('accentColor maps green to success CSS var', () => {
    const fixture = makeComp({ color: 'green' });
    const comp = fixture.componentInstance;
    expect(comp.accentColor()).toBe('var(--mee-color-success)');
  });

  it('does not render trend element when trend is undefined', () => {
    const fixture = makeComp();
    fixture.detectChanges();
    const trendEl = fixture.nativeElement.querySelector('[aria-label="trend"]');
    expect(trendEl).toBeNull();
  });

  it('renders trend label text when provided', () => {
    const fixture = makeComp({ trend: 5, trend_label: 'vs last month' });
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('vs last month');
  });
});
