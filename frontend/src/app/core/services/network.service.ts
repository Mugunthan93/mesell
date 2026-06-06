// core/services/network.service.ts
// navigator.onLine signal per §4.G — drives offline banner + autosave queue

import { Injectable, signal, OnDestroy } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class NetworkService implements OnDestroy {
  /**
   * Binary online/offline signal. Updates on window 'online' + 'offline' events.
   * V1.5 may extend with navigator.connection.effectiveType for 2G/3G adaptations.
   */
  readonly online = signal<boolean>(typeof navigator !== 'undefined' ? navigator.onLine : true);

  private readonly onOnline = (): void => this.online.set(true);
  private readonly onOffline = (): void => this.online.set(false);

  constructor() {
    if (typeof window !== 'undefined') {
      window.addEventListener('online', this.onOnline);
      window.addEventListener('offline', this.onOffline);
    }
  }

  ngOnDestroy(): void {
    if (typeof window !== 'undefined') {
      window.removeEventListener('online', this.onOnline);
      window.removeEventListener('offline', this.onOffline);
    }
  }
}
