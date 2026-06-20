import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeScrollPanelComponent } from './scroll-panel.component';

function makeComp() {
  const fixture = TestBed.createComponent(MeeScrollPanelComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeScrollPanelComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeScrollPanelComponent, NoopAnimationsModule],
    });
  });

  it('(1) renders with default maxHeight="100%"', () => {
    const { comp } = makeComp();
    expect(comp.maxHeight()).toBe('100%');
    expect(comp.styleClass()).toBeUndefined();
  });

  it('(2) maxHeight="300px" is reflected in hostStyle() computed', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('maxHeight', '300px');
    const style = comp.hostStyle();
    expect(style['height']).toBe('300px');
    expect(style['maxHeight']).toBe('300px');
    expect(style['width']).toBe('100%');
  });

  it('(3) styleClass input is forwarded to the component', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('styleClass', 'my-custom-scroll');
    expect(comp.styleClass()).toBe('my-custom-scroll');
  });
});
