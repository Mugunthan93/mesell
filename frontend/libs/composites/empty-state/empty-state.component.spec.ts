import { Component, EventEmitter, Output, Input } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { EmptyStateComponent } from './empty-state.component';
import { MeeButtonComponent } from '@mesell/ui-kit';

// Stub mee-button to avoid PrimeNG in tests
@Component({
  selector: 'mee-button',
  standalone: true,
  template: '<button class="btn-stub">{{ label }}</button>',
})
class MeeButtonStub {
  @Input() label = '';
  @Input() variant = 'primary';
  @Output() clicked = new EventEmitter<void>();
}

describe('EmptyStateComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
    TestBed.overrideComponent(EmptyStateComponent, {
      remove: { imports: [MeeButtonComponent] },
      add:    { imports: [MeeButtonStub] },
    });
  });

  it('renders icon and message', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'No products yet');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.textContent).toContain('inventory');
    expect(el.textContent).toContain('No products yet');
  });

  it('does not render CTA button when cta_label is undefined', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'Nothing here');
    fixture.detectChanges();
    const btn = fixture.nativeElement.querySelector('mee-button');
    expect(btn).toBeNull();
  });

  it('hasCta is false when cta_label is undefined', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'Empty');
    expect(fixture.componentInstance.hasCta()).toBe(false);
  });

  it('hasCta is true when cta_label is provided', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'Empty');
    fixture.componentRef.setInput('cta_label', 'Create Catalog');
    expect(fixture.componentInstance.hasCta()).toBe(true);
  });

  it('renders CTA button when cta_label is provided', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'No products yet');
    fixture.componentRef.setInput('cta_label', '+ Create Catalog');
    fixture.detectChanges();
    const btn = fixture.nativeElement.querySelector('mee-button');
    expect(btn).not.toBeNull();
  });

  it('cta_click output is defined on the component', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'Empty');
    fixture.componentRef.setInput('cta_label', 'Create');
    const comp = fixture.componentInstance;
    // output() returns an OutputEmitterRef — verify it is defined and emittable
    expect(comp.cta_click).toBeDefined();
    expect(typeof comp.cta_click.emit).toBe('function');
  });

  it('has role="status" for accessibility', () => {
    const fixture = TestBed.createComponent(EmptyStateComponent);
    fixture.componentRef.setInput('icon', 'inventory');
    fixture.componentRef.setInput('message', 'Empty state');
    fixture.detectChanges();
    const container = fixture.nativeElement.querySelector('[role="status"]');
    expect(container).not.toBeNull();
  });
});
