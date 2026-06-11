import { Component, EventEmitter, Output, Input } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { describe, it, expect, beforeEach } from 'vitest';
import { PageHeaderComponent } from './page-header.component';
import { MeeButtonComponent } from '@mesell/ui-kit';

// Stub mee-button to avoid PrimeNG in tests
@Component({
  selector: 'mee-button',
  standalone: true,
  template: '<button class="btn-stub">{{ label }}</button>',
})
class MeeButtonStub {
  @Input() label = '';
  @Input() icon: string | undefined = undefined;
  @Input() variant = 'primary';
  @Output() clicked = new EventEmitter<void>();
}

describe('PageHeaderComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({});
    TestBed.overrideComponent(PageHeaderComponent, {
      remove: { imports: [MeeButtonComponent] },
      add:    { imports: [MeeButtonStub] },
    });
  });

  it('renders required title', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'My Catalogs');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('My Catalogs');
  });

  it('renders subtitle when provided', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'Dashboard');
    fixture.componentRef.setInput('subtitle', 'Manage your listings');
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Manage your listings');
  });

  it('does not render CTA button when cta_label is undefined', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'Title Only');
    fixture.detectChanges();
    const btn = fixture.nativeElement.querySelector('mee-button');
    expect(btn).toBeNull();
  });

  it('hasCta is false when cta_label is undefined', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'Title');
    expect(fixture.componentInstance.hasCta()).toBe(false);
  });

  it('hasCta is true when cta_label is provided', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'Title');
    fixture.componentRef.setInput('cta_label', 'New Catalog');
    expect(fixture.componentInstance.hasCta()).toBe(true);
  });

  it('renders CTA button when cta_label is provided', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'My Catalogs');
    fixture.componentRef.setInput('cta_label', '+ New Catalog');
    fixture.detectChanges();
    const btn = fixture.nativeElement.querySelector('mee-button');
    expect(btn).not.toBeNull();
  });

  it('cta_click output is defined on the component', () => {
    const fixture = TestBed.createComponent(PageHeaderComponent);
    fixture.componentRef.setInput('title', 'Title');
    fixture.componentRef.setInput('cta_label', 'New');
    const comp = fixture.componentInstance;
    // output() returns an OutputEmitterRef — verify it is defined
    expect(comp.cta_click).toBeDefined();
    expect(typeof comp.cta_click.emit).toBe('function');
  });
});
