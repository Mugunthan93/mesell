// layouts/auth/auth-layout.component.spec.ts

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MeeAuthLayoutComponent } from './auth-layout.component';

describe('MeeAuthLayoutComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeAuthLayoutComponent],
      providers: [provideRouter([])],
    }).compileComponents();
  });

  it('should create', () => {
    const fixture = TestBed.createComponent(MeeAuthLayoutComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should render the MeeSell brand name', () => {
    const fixture = TestBed.createComponent(MeeAuthLayoutComponent);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-brand-name')?.textContent).toContain('MeeSell');
  });

  it('should render a router-outlet inside the auth-card', () => {
    const fixture = TestBed.createComponent(MeeAuthLayoutComponent);
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.auth-card router-outlet')).toBeTruthy();
  });
});
