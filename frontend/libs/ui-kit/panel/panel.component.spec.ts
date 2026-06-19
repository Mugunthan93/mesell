import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeePanelComponent } from './panel.component';

function makeComp() {
  const fixture = TestBed.createComponent(MeePanelComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeePanelComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeePanelComponent, NoopAnimationsModule],
    });
  });

  it('(1) creates with header text — panelHeader() accessible via alias', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('header', 'Product Details');
    expect(comp.panelHeader()).toBe('Product Details');
    expect(comp.collapsed()).toBe(false);
    expect(comp.toggleable()).toBe(false);
  });

  it('(2) projected content — panel instantiates without error and model starts at false', () => {
    const { comp } = makeComp();
    expect(comp.collapsed()).toBe(false);
  });

  it('(3) toggleable=true + onCollapsedChange flips the collapsed model', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('toggleable', true);
    expect(comp.collapsed()).toBe(false);

    comp.onCollapsedChange(true);
    expect(comp.collapsed()).toBe(true);

    comp.onCollapsedChange(false);
    expect(comp.collapsed()).toBe(false);
  });

  it('(3b) onCollapsedChange normalises undefined to false', () => {
    const { comp } = makeComp();
    comp.onCollapsedChange(true);
    comp.onCollapsedChange(undefined);
    expect(comp.collapsed()).toBe(false);
  });
});
