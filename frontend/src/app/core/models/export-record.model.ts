// core/models/export-record.model.ts
// Export job record per BACKEND_ARCHITECTURE.md §14 (export module)

import { UUID } from '@core/auth/jwt-payload.model';
import { ExportStatus } from '@shared/enums/product-status.enum';

export interface ExportRecord {
  readonly id: UUID;
  readonly productId: UUID;
  readonly status: ExportStatus;
  /** Signed GCS URL (1h TTL) — present when status is 'ready' */
  readonly xlsxUrl: string | null;
  /** Signed GCS URL (1h TTL) — present when status is 'ready' */
  readonly imageZipUrl: string | null;
  /** Seller-facing error code — present when status is 'failed' */
  readonly errorCode: string | null;
  /** Seller-facing error message — present when status is 'failed' */
  readonly errorMessage: string | null;
  readonly createdAt: string;
  readonly updatedAt: string;
}
