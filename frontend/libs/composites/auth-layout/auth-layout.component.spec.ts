import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { AuthLayoutComponent } from './auth-layout.component';

// Host wrapper used by the content-projection test (FE-AUTH-07).
@Component({
  standalone: true,
  imports: [AuthLayoutComponent],
  template: `<mee-auth-layout><p class="projected-content">Projected</p></mee-auth-layout>`,
})
class HostWithContentComponent {}

describe('AuthLayoutComponent', () => {
  let fixture: ComponentFixture<AuthLayoutComponent>;

  beforeEach(async () => {
    // Import both the component under test AND the host wrapper for the
    // content-projection case (FE-AUTH-07) in the same module so we never
    // call configureTestingModule() a second time inside an it() block.
    await TestBed.configureTestingModule({
      imports: [AuthLayoutComponent, HostWithContentComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(AuthLayoutComponent);
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  // SKIP: logo text diverged from template — component now renders abbreviation.
  // Pre-existing gap (not introduced by billing wave). Tracked for realignment.
  it.skip('should display MeeSell logo text', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-logo')?.textContent?.trim()).toBe('MeeSell');
  });

  // ── FE-AUTH-07: structural render + brand content + content projection ────────
  //
  // Develop previously had only the thin "should create" case above.
  // The template structure (auth-wrapper > auth-card > auth-brand > ng-content)
  // is the load-bearing scaffolding of every auth page — verify it here.

  it('should render the outer auth-wrapper container when component is created', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-wrapper')).not.toBeNull();
  });

  it('should render the auth-card inside auth-wrapper when component is created', () => {
    const el: HTMLElement = fixture.nativeElement;
    const wrapper = el.querySelector('.auth-wrapper');
    expect(wrapper?.querySelector('.auth-card')).not.toBeNull();
  });

  it('should render the auth-brand block containing the logo and wordmark when component is created', () => {
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-brand')).not.toBeNull();
  });

  it('should render the abbreviation "M" inside .auth-logo when component is created', () => {
    // Template: <span class="auth-logo" aria-label="MeeSell">M</span>
    // The pre-existing skip tested for "MeeSell" here — that was wrong.
    // The actual text content of .auth-logo is the abbreviation "M".
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-logo')?.textContent?.trim()).toBe('M');
  });

  it('should render "MeeSell" inside .auth-wordmark when component is created', () => {
    // Template: <span class="auth-wordmark">MeeSell</span>
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-wordmark')?.textContent?.trim()).toBe('MeeSell');
  });

  it('should have aria-label "MeeSell" on the .auth-logo span for screen-reader accessibility when component is created', () => {
    const el: HTMLElement = fixture.nativeElement;
    const logo = el.querySelector('.auth-logo');
    expect(logo?.getAttribute('aria-label')).toBe('MeeSell');
  });

  it('should project host content via ng-content into the .auth-card when a host component provides child content', () => {
    // HostWithContentComponent is already compiled (imported in beforeEach's
    // configureTestingModule) — create it directly, no second configure call.
    const projFixture = TestBed.createComponent(HostWithContentComponent);
    projFixture.detectChanges();
    const hostEl: HTMLElement = projFixture.nativeElement;
    expect(hostEl.querySelector('.projected-content')).not.toBeNull();
    expect(hostEl.querySelector('.projected-content')?.textContent).toBe('Projected');
  });
});
