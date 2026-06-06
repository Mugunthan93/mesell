// shared/enums/image-precheck-result.enum.ts
// Image precheck pipeline statuses per DATABASE_ARCHITECTURE.md §4.6

export type ImagePrecheckResult = 'pending' | 'processing' | 'ready' | 'failed';

export const IMAGE_PRECHECK_RESULT = {
  PENDING: 'pending',
  PROCESSING: 'processing',
  READY: 'ready',
  FAILED: 'failed',
} as const satisfies Record<string, ImagePrecheckResult>;
