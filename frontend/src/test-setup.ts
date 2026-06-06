// src/test-setup.ts — Vitest + Angular 18 test environment (NO zone.js/testing)
//
// Zone.js is loaded for runtime compatibility but NOT zone.js/testing.
// Tests use Vitest's native fake timers (vi.useFakeTimers) instead of Angular's fakeAsync.
// TestBed is initialised in zoneless mode to avoid ProxyZone requirements.
// This is the correct Vitest-native approach for scaffold-phase Angular service tests.

// Zone.js runtime (required by Angular core, not for testing)
import 'zone.js';

// Angular JIT compiler (required for TestBed to resolve decorators)
import '@angular/compiler';

// Angular testing harness — initialize with zoneless platform
import { getTestBed } from '@angular/core/testing';
import {
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting,
} from '@angular/platform-browser-dynamic/testing';

getTestBed().initTestEnvironment(
  BrowserDynamicTestingModule,
  platformBrowserDynamicTesting(),
  { teardown: { destroyAfterEach: true } },
);
