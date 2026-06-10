import { inject, Injectable } from '@angular/core';
import { MessageService } from 'primeng/api';

@Injectable({ providedIn: 'root' })
export class MeeToastService {
  private readonly msgSvc = inject(MessageService);

  success(detail: string, summary = 'Success'): void {
    this.msgSvc.add({ severity: 'success', summary, detail, life: 4000 });
  }

  error(detail: string, summary = 'Error'): void {
    this.msgSvc.add({ severity: 'error', summary, detail, life: 4000 });
  }

  warn(detail: string, summary = 'Warning'): void {
    this.msgSvc.add({ severity: 'warn', summary, detail, life: 4000 });
  }

  info(detail: string, summary = 'Info'): void {
    this.msgSvc.add({ severity: 'info', summary, detail, life: 4000 });
  }
}
