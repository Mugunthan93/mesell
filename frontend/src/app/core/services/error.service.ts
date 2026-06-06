// core/services/error.service.ts
// MatSnackBar surface for user-facing errors per §4.F

import { inject, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiError } from '@core/api/api-error';

@Injectable({ providedIn: 'root' })
export class ErrorService {
  private readonly snackBar = inject(MatSnackBar);

  /**
   * Surfaces error.displayMessage (or .message) via MatSnackBar.
   * Duration: 6s for errors, swipe-to-dismiss on mobile.
   * Action button: "Details" if error.traceId exists → opens dialog with traceId.
   */
  showError(error: ApiError | Error | string): void {
    const message = error instanceof ApiError
      ? error.displayMessage
      : error instanceof Error
        ? error.message
        : error;

    const hasTraceId = error instanceof ApiError && !!error.traceId;
    const action = hasTraceId ? 'Details' : 'Dismiss';

    const ref = this.snackBar.open(message, action, {
      duration: 6000,
      panelClass: ['mee-snackbar', 'mee-snackbar--error'],
    });

    if (hasTraceId) {
      ref.onAction().subscribe(() => {
        const traceId = (error as ApiError).traceId;
        // V1: alert — V1.5 replaces with a MatDialog showing the traceId for support escalation
        alert(`Request ID for support: ${traceId}`);
      });
    }
  }

  /** Yellow snackbar, 4s. */
  showWarning(message: string): void {
    this.snackBar.open(message, 'Dismiss', {
      duration: 4000,
      panelClass: ['mee-snackbar', 'mee-snackbar--warning'],
    });
  }

  /** Blue snackbar, 3s. Used by PlanGuard upsell + autosave indicators. */
  showInfo(message: string): void {
    this.snackBar.open(message, 'Dismiss', {
      duration: 3000,
      panelClass: ['mee-snackbar', 'mee-snackbar--info'],
    });
  }

  /** Green snackbar, 3s. Used by feature success confirmations. */
  showSuccess(message: string): void {
    this.snackBar.open(message, 'Dismiss', {
      duration: 3000,
      panelClass: ['mee-snackbar', 'mee-snackbar--success'],
    });
  }
}
