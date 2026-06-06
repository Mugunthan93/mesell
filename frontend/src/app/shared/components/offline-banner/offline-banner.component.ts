// shared/components/offline-banner/offline-banner.component.ts
// Stub — full implementation by meesell-angular-component-builder per §5.C.5
// Reads NetworkService.online() directly — exception to stateless rule documented in §5

import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { NetworkService } from '@core/services/network.service';

@Component({
  selector: 'mee-offline-banner',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (!network.online()) {
      <div class="mee-offline-banner" role="alert">
        You are offline. Changes will be saved when you reconnect.
      </div>
    }
  `,
})
export class OfflineBannerComponent {
  protected readonly network = inject(NetworkService);
}
