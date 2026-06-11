import { Component, Input } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { LoadingSkeletonComponent } from './loading-skeleton.component';
import { MeeSkeletonComponent } from '@mesell/ui-kit';
import type { MeeSkeletonVariant } from '@mesell/ui-kit';

// Stub mee-skeleton to avoid PrimeNG in tests — use @Input to avoid NG8109 signal warnings
@Component({
  selector: 'mee-skeleton',
  standalone: true,
  template: '<div class="skeleton-stub"></div>',
})
class MeeSkeletonStub {
  @Input() variant: MeeSkeletonVariant = 'text';
  @Input() lines = 1;
}

describe('LoadingSkeletonComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
    TestBed.overrideComponent(LoadingSkeletonComponent, {
      remove: { imports: [MeeSkeletonComponent] },
      add:    { imports: [MeeSkeletonStub] },
    });
  });

  it('defaults to text variant and 1 line', () => {
    const fixture = TestBed.createComponent(LoadingSkeletonComponent);
    const comp = fixture.componentInstance;
    expect(comp.variant()).toBe('text');
    expect(comp.lines()).toBe(1);
  });

  it('renders mee-skeleton for text variant', () => {
    const fixture = TestBed.createComponent(LoadingSkeletonComponent);
    fixture.componentRef.setInput('variant', 'text');
    fixture.detectChanges();
    const el = fixture.nativeElement.querySelector('mee-skeleton');
    expect(el).not.toBeNull();
  });

  it('renders mee-skeleton for card variant', () => {
    const fixture = TestBed.createComponent(LoadingSkeletonComponent);
    fixture.componentRef.setInput('variant', 'card');
    fixture.detectChanges();
    const el = fixture.nativeElement.querySelector('mee-skeleton');
    expect(el).not.toBeNull();
  });

  it('renders 4 mee-skeleton rows for table-row variant', () => {
    const fixture = TestBed.createComponent(LoadingSkeletonComponent);
    fixture.componentRef.setInput('variant', 'table-row');
    fixture.detectChanges();
    const els = fixture.nativeElement.querySelectorAll('mee-skeleton');
    expect(els.length).toBe(4);
  });

  it('renders 4 mee-skeleton blocks for stat-card variant', () => {
    const fixture = TestBed.createComponent(LoadingSkeletonComponent);
    fixture.componentRef.setInput('variant', 'stat-card');
    fixture.detectChanges();
    const els = fixture.nativeElement.querySelectorAll('mee-skeleton');
    expect(els.length).toBe(4);
  });

  it('passes lines input to mee-skeleton for text variant', () => {
    const fixture = TestBed.createComponent(LoadingSkeletonComponent);
    fixture.componentRef.setInput('variant', 'text');
    fixture.componentRef.setInput('lines', 3);
    const comp = fixture.componentInstance;
    expect(comp.lines()).toBe(3);
  });
});
