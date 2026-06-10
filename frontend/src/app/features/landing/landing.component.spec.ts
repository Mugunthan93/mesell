import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { LandingComponent } from './landing.component';

describe('LandingComponent', () => {
  let fixture: ComponentFixture<LandingComponent>;
  let comp: LandingComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [LandingComponent],
      providers: [provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(LandingComponent);
    comp = fixture.componentInstance;
    fixture.detectChanges();
  });

  // Gate test 1 — component creates without errors
  it('should create without errors', () => {
    expect(comp).toBeTruthy();
  });

  // Gate test 2 — "Start free" has routerLink → /signup
  it('should have a "Start free" anchor with routerLink pointing to /signup', () => {
    const startFreeLinks: NodeListOf<HTMLAnchorElement> =
      fixture.nativeElement.querySelectorAll('a[routerLink="/signup"], a[ng-reflect-router-link="/signup"]');
    // At minimum one "Start free" link must exist (hero CTA)
    expect(startFreeLinks.length).toBeGreaterThanOrEqual(1);
    const firstLink = startFreeLinks[0];
    expect(firstLink).toBeTruthy();
    const routerLinkAttr = firstLink.getAttribute('routerLink') ?? firstLink.getAttribute('ng-reflect-router-link');
    expect(routerLinkAttr).toBe('/signup');
  });

  // Gate test 3 — "Log in" has routerLink → /login
  it('should have a "Log in" anchor with routerLink pointing to /login', () => {
    const loginLinks: NodeListOf<HTMLAnchorElement> =
      fixture.nativeElement.querySelectorAll('a[routerLink="/login"], a[ng-reflect-router-link="/login"]');
    expect(loginLinks.length).toBeGreaterThanOrEqual(1);
    const firstLink = loginLinks[0];
    const routerLinkAttr = firstLink.getAttribute('routerLink') ?? firstLink.getAttribute('ng-reflect-router-link');
    expect(routerLinkAttr).toBe('/login');
  });

  it('should render the hero headline containing "3 minutes"', () => {
    const h1: HTMLElement = fixture.nativeElement.querySelector('h1');
    expect(h1).toBeTruthy();
    expect(h1.textContent).toContain('3 minutes');
  });

  it('should render the how-it-works section with id="how"', () => {
    const section: HTMLElement = fixture.nativeElement.querySelector('#how');
    expect(section).toBeTruthy();
  });

  it('should render 3 step items in the how-it-works section', () => {
    const steps: NodeListOf<Element> =
      fixture.nativeElement.querySelectorAll('.step-item');
    expect(steps.length).toBe(3);
  });

  it('should render the current year in the footer copyright', () => {
    const footer: HTMLElement = fixture.nativeElement.querySelector('footer');
    expect(footer).toBeTruthy();
    const year = new Date().getFullYear().toString();
    expect(footer.textContent).toContain(year);
  });

  it('should expose currentYear signal with the current year', () => {
    expect(comp.currentYear()).toBe(new Date().getFullYear());
  });
});
