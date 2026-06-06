// core/interceptors/locale.interceptor.ts
// Interceptor #2 in chain — attaches Accept-Language per §4.B.2

import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { TranslocoService } from '@jsverse/transloco';

export const localeInterceptor: HttpInterceptorFn = (req, next) => {
  let locale = 'en';
  try {
    locale = inject(TranslocoService).getActiveLang() ?? 'en';
  } catch {
    // TranslocoService may not be available in early bootstrap — fall back to 'en'
  }

  return next(req.clone({
    setHeaders: { 'Accept-Language': locale },
  }));
};
