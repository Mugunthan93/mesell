// shared/pipes/locale-label.pipe.spec.ts

import { TestBed } from '@angular/core/testing';
import { provideExperimentalZonelessChangeDetection } from '@angular/core';
import { describe, expect, it, beforeEach } from 'vitest';
import { TranslocoService } from '@jsverse/transloco';
import { LocaleLabelPipe } from './locale-label.pipe';
import { LocaleMap } from '@core/models/locale-map.model';

function makeTransloco(lang: string): TranslocoService {
  return { getActiveLang: () => lang } as unknown as TranslocoService;
}

describe('LocaleLabelPipe', () => {
  function makePipe(lang = 'en'): LocaleLabelPipe {
    TestBed.configureTestingModule({
      providers: [
        provideExperimentalZonelessChangeDetection(),
        { provide: TranslocoService, useValue: makeTransloco(lang) },
      ],
    });
    return TestBed.runInInjectionContext(() => new LocaleLabelPipe());
  }

  beforeEach(() => TestBed.resetTestingModule());

  it('returns English label when lang=en', () => {
    const pipe = makePipe('en');
    const map: LocaleMap = { en: 'Color', ta: 'வண்ணம்' };
    expect(pipe.transform(map)).toBe('Color');
  });

  it('returns Tamil label when lang=ta and ta exists', () => {
    const pipe = makePipe('ta');
    const map: LocaleMap = { en: 'Color', ta: 'வண்ணம்' };
    expect(pipe.transform(map)).toBe('வண்ணம்');
  });

  it('falls back to en when lang=ta but ta is missing', () => {
    const pipe = makePipe('ta');
    const map: LocaleMap = { en: 'Size' };
    expect(pipe.transform(map)).toBe('Size');
  });

  it('returns empty string for null input', () => {
    const pipe = makePipe('en');
    expect(pipe.transform(null)).toBe('');
  });

  it('returns empty string for undefined input', () => {
    const pipe = makePipe('en');
    expect(pipe.transform(undefined)).toBe('');
  });

  it('returns empty string when map has no keys', () => {
    const pipe = makePipe('hi');
    expect(pipe.transform({} as LocaleMap)).toBe('');
  });
});
