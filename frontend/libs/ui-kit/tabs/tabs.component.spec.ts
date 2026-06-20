import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeTabsComponent } from './tabs.component';
import { MEE_ICONS } from '../icon/icon.registry';
import type { MeeTab } from './tabs.types';

const TABS: MeeTab[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'details',  label: 'Details', icon: 'catalog' },
  { value: 'images',   label: 'Images',  disabled: true },
];

function makeComp() {
  const fixture = TestBed.createComponent(MeeTabsComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeTabsComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeTabsComponent, NoopAnimationsModule],
    });
  });

  it('(1) renders one tab per entry in tabs() — count matches', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('tabs', TABS);
    expect(comp.tabs().length).toBe(3);
    expect(comp.tabs()[0].label).toBe('Overview');
    expect(comp.tabs()[2].disabled).toBe(true);
  });

  it('(2) default value is the model default (0); can be overridden via model set', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('tabs', TABS);
    // Default value from model initializer is 0
    expect(comp.value()).toBe(0);

    // onTabChange updates the model
    comp.onTabChange('details');
    expect(comp.value()).toBe('details');
  });

  it('(3) MeeTab.icon resolves to the registry pi pi-* class via resolveIcon()', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('tabs', TABS);
    const detailTab = comp.tabs().find(t => t.value === 'details');
    expect(detailTab?.icon).toBe('catalog');
    // resolveIcon('catalog') should return MEE_ICONS['catalog']
    expect(comp.resolveIcon('catalog')).toBe(MEE_ICONS['catalog']);
  });
});
