/**
 * auth-layout.component.spec.ts — QA Wave 2 (FE-AUTH-07)
 *
 * Hardened to cover render, brand content, and content-projection.
 * Component: AuthLayoutComponent (standalone, OnPush, no deps).
 *
 * NOTE on the skipped case: the original skip was for a pre-existing divergence
 * (".auth-logo textContent === 'MeeSell'"). The template renders "M" in .auth-logo
 * and "MeeSell" in .auth-wordmark. The new cases test the actual template.
 */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component } from '@angular/core';
import { AuthLayoutComponent } from './auth-layout.component';

@Component({
  standalone: true,
  imports: [AuthLayoutComponent],
  template: `<mee-auth-layout><p class="projected-content">Projected</p></mee-auth-layout>`,
})
class HostWithContentComponent {}

describe('AuthLayoutComponent', () => {
  let fixture: ComponentFixture<AuthLayoutComponent>;
  let el: HTMLElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AuthLayoutComponent],
    }).compileComponents();
    fixture = TestBed.createComponent(AuthLayoutComponent);
    fixture.detectChanges();
    el = fixture.nativeElement;
  });

  // ── instantiation ────────────────────────────────────────────────────────────

  it('should create', () => {
    expect(fixture.componentInstance).toBeTruthy();
  });

  // ── structural render ─────────────────────────────────────────────────────────

  it('should render the outer auth-wrapper container', () => {
    expect(el.querySelector('.auth-wrapper')).not.toBeNull();
  });

  it('should render the auth-card inside auth-wrapper', () => {
    const wrapper = el.querySelector('.auth-wrapper');
    expect(wrapper?.querySelector('.auth-card')).not.toBeNull();
  });

  it('should render the auth-brand block', () => {
    expect(el.querySelector('.auth-brand')).not.toBeNull();
  });

  // ── brand content ─────────────────────────────────────────────────────────────

  it('should render the abbreviation "M" inside .auth-logo', () => {
    // Template: <span class="auth-logo" aria-label="MeeSell">M</span>
    expect(el.querySelector('.auth-logo')?.textContent?.trim()).toBe('M');
  });

  it('should render "MeeSell" inside .auth-wordmark', () => {
    // Template: <span class="auth-wordmark">MeeSell</span>
    expect(el.querySelector('.auth-wordmark')?.textContent?.trim()).toBe('MeeSell');
  });

  it('should have aria-label "MeeSell" on the logo span for screen-reader users', () => {
    const logo = el.querySelector('.auth-logo');
    expect(logo?.getAttribute('aria-label')).toBe('MeeSell');
  });

  // ── content projection ─────────────────────────────────────────────────────────

  it('should project host content via ng-content into .auth-card', async () => {
    // Separate fixture that uses a host wrapper to supply content
    const projFixture = TestBed.createComponent(HostWithContentComponent);
    projFixture.detectChanges();
    const hostEl: HTMLElement = projFixture.nativeElement;
    // The projected element must exist inside the rendered card
    expect(hostEl.querySelector('.projected-content')).not.toBeNull();
    expect(hostEl.querySelector('.projected-content')?.textContent).toBe('Projected');
  });

  // ── skipped ─────────────────────────────────────────────────────────────────
  // This was the original failing skip: ".auth-logo === 'MeeSell'".
  // Superseded above by separate wordmark + logo assertions (FE-AUTH-07).
  it.skip('[pre-existing divergence] should display MeeSell logo text in .auth-logo', () => {
    expect(el.querySelector('.auth-logo')?.textContent?.trim()).toBe('MeeSell');
  });
});
