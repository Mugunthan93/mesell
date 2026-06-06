// shared/enums/product-status.enum.ts
// Product lifecycle status and export status — single source of truth

export type ProductStatus = 'draft' | 'ready' | 'exported' | 'live' | 'deleted';

export const PRODUCT_STATUS = {
  DRAFT: 'draft',
  READY: 'ready',
  EXPORTED: 'exported',
  LIVE: 'live',
  DELETED: 'deleted',
} as const satisfies Record<string, ProductStatus>;

export type ExportStatus = 'processing' | 'ready' | 'failed';

export const EXPORT_STATUS = {
  PROCESSING: 'processing',
  READY: 'ready',
  FAILED: 'failed',
} as const satisfies Record<string, ExportStatus>;
