// shared/pipes/relative-time.pipe.ts
// "2 hours ago", "yesterday", "last week" using Intl.RelativeTimeFormat

import { inject, Pipe, PipeTransform } from '@angular/core';
import { TranslocoService } from '@jsverse/transloco';

@Pipe({
  name: 'relativeTime',
  standalone: true,
  pure: false, // impure because relative time changes with the current time
})
export class RelativeTimePipe implements PipeTransform {
  private readonly transloco = inject(TranslocoService);

  transform(value: string | Date | null | undefined): string {
    if (!value) return '';
    const date = typeof value === 'string' ? new Date(value) : value;
    if (isNaN(date.getTime())) return '';

    const locale = this.transloco.getActiveLang() ?? 'en';
    const now = Date.now();
    const diffMs = date.getTime() - now;
    const diffSec = Math.round(diffMs / 1000);
    const diffMin = Math.round(diffSec / 60);
    const diffHour = Math.round(diffMin / 60);
    const diffDay = Math.round(diffHour / 24);
    const diffWeek = Math.round(diffDay / 7);
    const diffMonth = Math.round(diffDay / 30);
    const diffYear = Math.round(diffDay / 365);

    const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });

    if (Math.abs(diffSec) < 60) return rtf.format(diffSec, 'second');
    if (Math.abs(diffMin) < 60) return rtf.format(diffMin, 'minute');
    if (Math.abs(diffHour) < 24) return rtf.format(diffHour, 'hour');
    if (Math.abs(diffDay) < 7) return rtf.format(diffDay, 'day');
    if (Math.abs(diffWeek) < 4) return rtf.format(diffWeek, 'week');
    if (Math.abs(diffMonth) < 12) return rtf.format(diffMonth, 'month');
    return rtf.format(diffYear, 'year');
  }
}
