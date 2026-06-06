// shared/pipes/locale-label.pipe.ts
// Resolves a LocaleMap {en, ta?, hi?} to the active locale string, falling back to 'en'

import { inject, Pipe, PipeTransform } from '@angular/core';
import { TranslocoService } from '@jsverse/transloco';
import { LocaleMap } from '@core/models/locale-map.model';

@Pipe({
  name: 'localeLabel',
  standalone: true,
  pure: false, // impure because active locale can change at runtime
})
export class LocaleLabelPipe implements PipeTransform {
  private readonly transloco = inject(TranslocoService);

  /**
   * Resolves a LocaleMap to the active locale, falling back to 'en'.
   * Usage: {{ field.displayLabel | localeLabel }}
   */
  transform(value: LocaleMap | null | undefined): string {
    if (!value) return '';
    const lang = this.transloco.getActiveLang() as keyof LocaleMap ?? 'en';
    return value[lang] ?? value['en'] ?? '';
  }
}
