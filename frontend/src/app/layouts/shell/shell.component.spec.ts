// layouts/shell/shell.component.spec.ts

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideAnimations } from '@angular/platform-browser/animations';
import { signal } from '@angular/core';
import { MeeShellComponent } from './shell.component';
import { AuthService } from '@core/auth/auth.service';
import { BreakpointObserver } from '@angular/cdk/layout';
import { of } from 'rxjs';

const mockBreakpointObserver = {
  observe: jasmine.createSpy('observe').and.returnValue(of({ matches: false })),
};

const mockAuthService = {
  userId: signal<string | null>(null),
  isAuthenticated: signal(false),
  logout: jasmine.createSpy('logout').and.returnValue(of(undefined)),
};

describe('MeeShellComponent', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MeeShellComponent],
      providers: [
        provideRouter([]),
        provideAnimations(),
        { provide: AuthService, useValue: mockAuthService },
        { provide: BreakpointObserver, useValue: mockBreakpointObserver },
      ],
    }).compileComponents();
  });

  it('should create the shell component', () => {
    const fixture = TestBed.createComponent(MeeShellComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });

  it('should default to desktop (isMobile = false)', () => {
    const fixture = TestBed.createComponent(MeeShellComponent);
    fixture.detectChanges();
    expect(fixture.componentInstance.isMobile()).toBe(false);
  });

  it('should default to sidebarCollapsed = false', () => {
    const fixture = TestBed.createComponent(MeeShellComponent);
    expect(fixture.componentInstance.sidebarCollapsed()).toBe(false);
  });

  it('should have 4 nav items defined', () => {
    const fixture = TestBed.createComponent(MeeShellComponent);
    expect(fixture.componentInstance.navItems.length).toBe(4);
  });

  it('should return "?" for userInitials when userId is null', () => {
    mockAuthService.userId = signal<string | null>(null);
    const fixture = TestBed.createComponent(MeeShellComponent);
    expect(fixture.componentInstance.userInitials()).toBe('?');
  });

  it('should call auth.logout() when logout() is invoked', () => {
    const fixture = TestBed.createComponent(MeeShellComponent);
    fixture.componentInstance.logout();
    expect(mockAuthService.logout).toHaveBeenCalled();
  });
});
