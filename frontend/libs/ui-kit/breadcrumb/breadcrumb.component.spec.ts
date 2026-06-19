import { describe, it, expect, beforeEach } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { RouterTestingModule } from '@angular/router/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { MeeBreadcrumbComponent } from './breadcrumb.component';
import { MEE_ICONS } from '../icon/icon.registry';
import type { MeeMenuItem } from '../menu/menu.types';

const ITEMS: MeeMenuItem[] = [
  { label: 'Dashboard', routerLink: '/dashboard' },
  { label: 'Catalogs', routerLink: '/catalogs' },
  { label: 'Edit', routerLink: '/catalogs/1/edit' },
];

const HOME_ITEM: MeeMenuItem = { label: 'Home', icon: 'dashboard', routerLink: '/' };

function makeComp() {
  const fixture = TestBed.createComponent(MeeBreadcrumbComponent);
  return { fixture, comp: fixture.componentInstance };
}

describe('MeeBreadcrumbComponent', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [MeeBreadcrumbComponent, RouterTestingModule, NoopAnimationsModule],
    });
  });

  it('(1) creates with items only — pgItems() maps to the correct count', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('items', ITEMS);
    expect(comp.pgItems().length).toBe(3);
    expect(comp.pgItems()[0].label).toBe('Dashboard');
    expect(comp.pgHome()).toBeUndefined();
  });

  it('(2) MeeMenuItem.icon semantic name is resolved to pi pi-* class in pgItems()', () => {
    const { fixture, comp } = makeComp();
    const itemsWithIcon: MeeMenuItem[] = [
      { label: 'Back', icon: 'back', routerLink: '/dashboard' },
    ];
    fixture.componentRef.setInput('items', itemsWithIcon);
    const mapped = comp.pgItems();
    expect(mapped[0].icon).toBe(MEE_ICONS['back']);
  });

  it('(3) home input renders the home crumb via pgHome()', () => {
    const { fixture, comp } = makeComp();
    fixture.componentRef.setInput('items', ITEMS);
    fixture.componentRef.setInput('home', HOME_ITEM);
    const h = comp.pgHome();
    expect(h).toBeDefined();
    expect(h!.label).toBe('Home');
    expect(h!.icon).toBe(MEE_ICONS['dashboard']);
    expect(h!.routerLink).toBe('/');
  });
});
