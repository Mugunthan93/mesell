// core/interceptors/error.interceptor.ts
// Interceptor #4 in chain — normalises 4xx/5xx → ApiError per §4.B.4

import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ErrorService } from '@core/services/error.service';
import { NetworkService } from '@core/services/network.service';
import { AuthService } from '@core/auth/auth.service';
import { ApiError, normaliseHttpError } from '@core/api/api-error';

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const errorService = inject(ErrorService);
  const networkService = inject(NetworkService);
  const auth = inject(AuthService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((err: unknown) => {
      if (!(err instanceof HttpErrorResponse) && !(err instanceof ApiError)) {
        return throwError(() => err);
      }

      const apiError = err instanceof ApiError ? err : normaliseHttpError(err as HttpErrorResponse);

      if (apiError.status === 401) {
        // Unrecoverable 401 — RefreshInterceptor already tried and failed
        auth.clear();
        router.navigate(['/login']);
        errorService.showWarning('Your session expired. Please log in again.');
        return throwError(() => apiError);
      }

      if (apiError.kind === 'network') {
        const msg = networkService.online()
          ? 'Cannot reach the server. Please try again.'
          : 'You appear to be offline.';
        errorService.showError(new ApiError({ ...apiError, displayMessage: msg }));
        return throwError(() => apiError);
      }

      // Surface to snackbar; re-throw so feature code can also catch (e.g., 422 field errors)
      errorService.showError(apiError);
      return throwError(() => apiError);
    }),
  );
};
