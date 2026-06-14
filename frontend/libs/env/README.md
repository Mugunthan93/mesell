# libs/env — Angular Environment Files

## Dev / Prod API mapping

| Environment | `apiBase` | How /api/v1 reaches the backend |
|---|---|---|
| `development` | `''` (empty) | ng-serve proxy (`proxy.conf.json`) forwards `/api/v1/*` → `http://localhost:8000` |
| `production` | `''` (empty) | K3s Traefik Ingress routes `/api` → `api` service on the same host |

Both environments use `apiBase: ''`, so all HTTP calls use relative `/api/v1/...` paths.
This means the URL shape is byte-identical in dev and prod — no risk of accidental cross-origin drift.

## fileReplacements (angular.json)

Each of the 7 apps (frontend, mfe-*) has a `fileReplacements` entry in its
`esbuild:production` configuration:

```json
"fileReplacements": [
  { "replace": "libs/env/environment.ts", "with": "libs/env/environment.prod.ts" }
]
```

The `development` configuration has NO `fileReplacements` — it uses `environment.ts` as-is.

## How to consume

```typescript
import { environment } from '@mesell/env';

// In a service:
private withBase(path: string): string {
  return `${environment.apiBase}${path}`;
}
```

## Sync rule: keep in lockstep with backend

When the backend `.env` changes, update this lib in the same PR:

| Backend env var | Frontend concern |
|---|---|
| `APP_ENV` | Matches `environment.name` |
| `COOKIE_SECURE` | If `false` (dev), `apiBase` must be same-origin |
| `COOKIE_DOMAIN` | If cross-origin `apiBase` is set, must span both origins |
| `CORS_ALLOWED_ORIGINS` | Must include FE origin if `apiBase` is cross-origin |

## Cross-origin apiBase (future)

If the FE and API are split onto different origins:

1. Set `apiBase: 'https://api.meesell.in'` in `environment.prod.ts`
2. Backend MUST change IN LOCKSTEP:
   - `CORS_ALLOWED_ORIGINS` includes the FE origin
   - `allow_credentials=True` (for the HttpOnly refresh cookie)
   - `COOKIE_DOMAIN='.meesell.in'` (spans both origins)
   - `COOKIE_SECURE=true`

**DO NOT change `apiBase` without those backend env-var changes in the same PR.**
