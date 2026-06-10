import { Component } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { StatusBadgeComponent } from './status-badge.component';
import type { ProductStatus } from './status-badge.component';
import { MeeBadgeComponent } from '../../ui';

// Stub mee-badge to avoid PrimeNG in tests
@Component({
  selector: 'mee-badge',
  standalone: true,
  template: '<span class="badge-stub">{{ value }}</span>',
})
class MeeBadgeStub {
  value = '';
  severity = '';
}

describe('StatusBadgeComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
    TestBed.overrideComponent(StatusBadgeComponent, {
      remove: { imports: [MeeBadgeComponent] },
      add:    { imports: [MeeBadgeStub] },
    });
  });

  function makeComp(status: ProductStatus) {
    const fixture = TestBed.createComponent(StatusBadgeComponent);
    fixture.componentRef.setInput('status', status);
    return fixture;
  }

  it('severity is neutral for draft', () => {
    const comp = makeComp('draft').componentInstance;
    expect(comp.severity()).toBe('neutral');
  });

  it('severity is info for ready', () => {
    const comp = makeComp('ready').componentInstance;
    expect(comp.severity()).toBe('info');
  });

  it('severity is warning for exported', () => {
    const comp = makeComp('exported').componentInstance;
    expect(comp.severity()).toBe('warning');
  });

  it('severity is success for live', () => {
    const comp = makeComp('live').componentInstance;
    expect(comp.severity()).toBe('success');
  });

  it('severity is danger for deleted', () => {
    const comp = makeComp('deleted').componentInstance;
    expect(comp.severity()).toBe('danger');
  });

  it('severity is info for processing', () => {
    const comp = makeComp('processing').componentInstance;
    expect(comp.severity()).toBe('info');
  });

  it('severity is neutral for pending', () => {
    const comp = makeComp('pending').componentInstance;
    expect(comp.severity()).toBe('neutral');
  });

  it('severity is danger for failed', () => {
    const comp = makeComp('failed').componentInstance;
    expect(comp.severity()).toBe('danger');
  });

  it('renders without error for all 8 valid statuses', () => {
    const statuses: ProductStatus[] = [
      'draft', 'ready', 'exported', 'live',
      'deleted', 'processing', 'pending', 'failed',
    ];
    for (const status of statuses) {
      expect(() => makeComp(status)).not.toThrow();
    }
  });
});
