import { ChangeDetectionStrategy, Component, inject, Injectable } from '@angular/core';
import { ConfirmDialog } from 'primeng/confirmdialog';
import { ConfirmationService } from 'primeng/api';

export interface MeeConfirmConfig {
  message: string;
  header?: string;
  accept: () => void;
  reject?: () => void;
}

@Injectable({ providedIn: 'root' })
export class MeeConfirmService {
  private readonly confirmSvc = inject(ConfirmationService);

  confirm(config: MeeConfirmConfig): void {
    this.confirmSvc.confirm({
      message: config.message,
      header: config.header ?? 'Confirm',
      icon: 'pi pi-exclamation-triangle',
      accept: config.accept,
      reject: config.reject,
    });
  }
}

/**
 * Host component — place ONCE in shell template.
 * Use MeeConfirmService.confirm() to trigger.
 */
@Component({
  selector: 'mee-confirm-dialog',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ConfirmDialog],
  template: `<p-confirmdialog />`,
})
export class MeeConfirmDialogComponent {}
