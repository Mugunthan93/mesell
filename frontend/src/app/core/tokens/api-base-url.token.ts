// core/tokens/api-base-url.token.ts
// InjectionToken for the API base URL per §4.H

import { InjectionToken } from '@angular/core';

export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL');
