import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { MeeSideNavComponent } from './side-nav.component';
import type { MeeNavGroup } from '../chrome.types';

const GROUPS: readonly MeeNavGroup[] = [
  { label: 'Home', items: [{ label: 'Dashboard', route: '/dashboard', icon: 'dashboard' }] },
  {
    label: 'Catalogs',
    items: [
      { label: 'All Catalogs', route: '/catalogs', icon: 'catalog', exact: false },
      { label: 'New Catalog', route: '/catalogs/new', icon: 'add', accent: true },
    ],
  },
  { label: 'Empty', items: [] },
];

describe('MeeSideNavComponent', () => {
  let fixture: ComponentFixture<MeeSideNavComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeSideNavComponent, NoopAnimationsModule],
      // Wildcard route so clicking a real routerLink resolves cleanly (no
      // "cannot match" error reported after teardown → no NG0205 noise).
      providers: [provideRouter([{ path: '**', children: [] }])],
    }).compileComponents();

    fixture = TestBed.createComponent(MeeSideNavComponent);
    fixture.componentRef.setInput('groups', GROUPS);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render the brand (default MeeSell)', () => {
    expect(fixture.nativeElement.querySelector('.sidebar-brand')?.textContent).toContain('MeeSell');
  });

  it('should render a <nav aria-label="Main navigation"> landmark (a11y parity with Phase 3)', () => {
    const nav = fixture.nativeElement.querySelector('nav[aria-label="Main navigation"]');
    expect(nav).toBeTruthy();
  });

  it('should render one group label per non-empty group (empty groups dropped)', () => {
    const labels = Array.from(
      fixture.nativeElement.querySelectorAll('.nav-group__label'),
    ).map((el) => (el as HTMLElement).textContent?.trim());
    expect(labels).toEqual(['Home', 'Catalogs']);
  });

  it('should render one mee-nav-item per item', () => {
    expect(fixture.nativeElement.querySelectorAll('.nav-item').length).toBe(3);
  });

  it('should render the accent CTA', () => {
    const accent = fixture.nativeElement.querySelector('.nav-item--accent');
    expect(accent).toBeTruthy();
    expect(accent.textContent).toContain('New Catalog');
  });

  it('should re-emit navigated when a child nav item is clicked', () => {
    let emitted = false;
    fixture.componentInstance.navigated.subscribe(() => (emitted = true));
    fixture.nativeElement.querySelector('a.nav-item').click();
    expect(emitted).toBe(true);
  });
});
