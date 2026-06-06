// core/tokens/env-config.token.ts
// InjectionToken for the environment config per §4.H

import { InjectionToken } from '@angular/core';
import { EnvConfig } from './env-config.model';

export const ENV_CONFIG = new InjectionToken<EnvConfig>('ENV_CONFIG');
