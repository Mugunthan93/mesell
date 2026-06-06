// app.component.spec.ts
// Minimal smoke test for AppComponent — verifies the shell can be instantiated.
// Full template + interaction tests are deferred to meesell-angular-component-builder.

import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { describe, expect, it, beforeEach } from 'vitest';
import { AppComponent } from './app.component';
import { API_BASE_URL } from '@core/tokens/api-base-url.token';

describe('AppComponent (smoke)', () => {
  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        provideRouter([]),
        provideHttpClient(),
        { provide: API_BASE_URL, useValue: 'https://api.test/api/v1' },
      ],
      imports: [AppComponent],
    });
  });

  it('creates the root component', () => {
    const fixture = TestBed.createComponent(AppComponent);
    expect(fixture.componentInstance).toBeTruthy();
  });
});
