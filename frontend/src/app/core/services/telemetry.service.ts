// core/services/telemetry.service.ts
// V1.5 analytics hook — stub in V1. No third-party analytics loaded in V1.

import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class TelemetryService {
  /** Stub — V1.5 will wire to a lightweight analytics provider */
  track(_event: string, _properties?: Record<string, unknown>): void {
    // no-op in V1
  }
}
