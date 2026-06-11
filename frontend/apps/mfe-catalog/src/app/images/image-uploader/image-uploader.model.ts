// image-uploader.model.ts
// Pure TypeScript — NO Angular decorators. Vitest-testable without TestBed.

// ── Backend contract types (R-IP-B, 2026-06-11) ───────────────────────────────
// These types mirror the backend image/schemas.py on develop.
// One-way UI remap (R-IP-B authoritative, founder-ruled):
//   jpeg_valid        ← was jpeg_format
//   color_space       ← was color_space_rgb (bool — RGB pass/fail)
//   resolution_pass   ← was min_resolution
//   white_background  ← was white_bg
//   watermark_check   ← was no_watermark (semantics preserved: true = no watermark detected)

/**
 * precheck_jsonb keys — EXACT backend names (R-IP-B authoritative).
 * These are the 5 Celery-worker precheck keys in image/schemas.py PrecheckJsonb.
 */
export interface PrecheckJsonb {
  jpeg_valid: boolean;
  color_space: boolean;
  resolution_pass: boolean;
  white_background: boolean;
  watermark_check: boolean;
}

/** Single image summary as returned by GET /api/v1/products/{id}/images */
export interface ImageSummary {
  image_id: string;
  idx: number;                               // 1-based (1..4), D1-LOCKED CHECK constraint
  status: 'pending' | 'ready' | 'failed_precheck';
  signed_url: string;
  precheck_jsonb: PrecheckJsonb;
  is_front: boolean;                         // idx === 1
  width: number | null;
  height: number | null;
  color_space: string | null;                // e.g. "RGB", "CMYK"
  created_at: string;                        // ISO-8601 string
}

/**
 * Response shape for GET /api/v1/products/{id}/images.
 * Returns {images:[]} (200) when FEATURE_IMAGE_PRECHECK_ENABLED=false — NOT 404.
 */
export interface ImagesListResponse {
  images: ImageSummary[];
}

/**
 * Response shape for POST /api/v1/products/{id}/images (202 Accepted).
 * The image is queued; poll listImages until status !== 'pending'.
 */
export interface ImageUploadResponse {
  image_id: string;
  gcs_path: string;
  status: 'pending';
  idx: number;
  enqueued_task_id: string;
}

// ── UI domain type (mapped from ImageSummary) ─────────────────────────────────

/**
 * ProductImage — UI-layer representation of an uploaded image slot.
 * Derived from ImageSummary (backend) via mapImageSummaryToProductImage().
 * slot_index is the same as idx-1 (0-based) for @for track in the template.
 * status mirrors the backend enum exactly: 'pending' | 'ready' | 'failed_precheck'.
 */
export interface ProductImage {
  /** Backend image_id UUID */
  id: string;
  /** 0-based slot index (= ImageSummary.idx - 1) — used for @for track */
  slot_index: number;
  /** 1-based backend idx (1..4) */
  idx: number;
  /** Signed GCS URL for the thumbnail — null while still pending */
  gcs_url: string | null;
  /** Backend status enum — canonical (not the legacy pass/fail) */
  status: 'pending' | 'ready' | 'failed_precheck';
  /** 5-key precheck result object; null while still pending */
  precheck: PrecheckJsonb | null;
  /** true when idx === 1 (front image) */
  is_front: boolean;
}

export interface PrecheckItem {
  key: keyof PrecheckJsonb;
  label: string;
  pass: boolean;
  hint: string | null;
}

// ── Static lookup maps (backend keys — R-IP-B) ────────────────────────────────
// G3 FIX: keys are the BACKEND PrecheckJsonb names, NOT the legacy FE names.
// Canonical hint wording from FEATURE_PLAN.md §968 / §F5.

/**
 * Fix-hint copy per backend precheck key.
 * These are the §968 / §F5 canonical hints (founder-ruled R-IP-B as official source).
 */
export const PRECHECK_HINTS: Record<keyof PrecheckJsonb, string> = {
  jpeg_valid:       'Save the image as JPEG (.jpg) before uploading',
  color_space:      'Convert image to RGB mode before uploading (CMYK detected)',
  resolution_pass:  'Image must be at least 1500×1500 pixels',
  white_background: 'Use a plain white background for best results',
  watermark_check:  'Remove watermarks or logos before uploading',
};

export const PRECHECK_LABELS: Record<keyof PrecheckJsonb, string> = {
  jpeg_valid:       'JPEG format',
  color_space:      'RGB color space',
  resolution_pass:  'Min. resolution',
  white_background: 'White background',
  watermark_check:  'No watermark',
};

// ── Ordered key list (backend order preserved from schemas.py) ─────────────────
export const PRECHECK_KEYS: ReadonlyArray<keyof PrecheckJsonb> = [
  'jpeg_valid',
  'color_space',
  'resolution_pass',
  'white_background',
  'watermark_check',
];

// ── Pre-check gate 1: buildPrecheckItems ──────────────────────────────────────
// Returns the 5-item pre-check matrix for a resolved image.
// Returns [] for pending images (precheck is null).

export function buildPrecheckItems(image: ProductImage): PrecheckItem[] {
  if (!image.precheck) return [];
  return PRECHECK_KEYS.map(key => ({
    key,
    label: PRECHECK_LABELS[key],
    pass:  image.precheck![key],
    hint:  image.precheck![key] ? null : PRECHECK_HINTS[key],
  }));
}

// ── Pre-check gate 2: slotProgress ───────────────────────────────────────────
// Returns 0 while pending, 100 when resolved (ready or failed_precheck).

export function slotProgress(image: ProductImage): number {
  if (image.status === 'pending') return 0;
  return 100;
}

// ── Gate 3: computeCanContinue ───────────────────────────────────────────────
// canContinue = at least one image AND all images have status 'ready'.
// Uses backend status enum: 'pending' | 'ready' | 'failed_precheck'.

export function computeCanContinue(images: ProductImage[]): boolean {
  return images.length > 0 && images.every(img => img.status === 'ready');
}

// ── Gate 4: computeActiveExpandedImage ───────────────────────────────────────
// Returns the image whose slot_index matches expandedSlot, or null.

export function computeActiveExpandedImage(
  images: ProductImage[],
  expandedSlot: number | null,
): ProductImage | null {
  if (expandedSlot === null) return null;
  return images.find(img => img.slot_index === expandedSlot) ?? null;
}

// ── Gate 5: toggleExpandedSlot ───────────────────────────────────────────────
// Toggles: same index → null (collapse); different index → new index.

export function toggleExpandedSlot(
  current: number | null,
  index: number,
): number | null {
  return current === index ? null : index;
}

// ── resetSlot ────────────────────────────────────────────────────────────────
// Returns a new images array with the given slot reset to pending (for re-upload).

export function resetSlot(
  images: ProductImage[],
  slotIndex: number,
): ProductImage[] {
  return images.map(img =>
    img.slot_index === slotIndex
      ? { ...img, status: 'pending' as const, precheck: null, gcs_url: null }
      : img,
  );
}

// ── mapImageSummaryToProductImage ────────────────────────────────────────────
// Maps the backend ImageSummary to the UI ProductImage type.
// slot_index = idx - 1 (0-based for @for track).

export function mapImageSummaryToProductImage(summary: ImageSummary): ProductImage {
  return {
    id:         summary.image_id,
    slot_index: summary.idx - 1,
    idx:        summary.idx,
    gcs_url:    summary.signed_url || null,
    status:     summary.status,
    precheck:   summary.precheck_jsonb ?? null,
    is_front:   summary.is_front,
  };
}

// ── statusForMeeStatusBadge ───────────────────────────────────────────────────
// Maps backend status enum to the ProductStatus union expected by mee-status-badge.
// Backend: 'pending' | 'ready' | 'failed_precheck'
// StatusBadge accepts: 'pending' | 'ready' | 'failed' (and others in the union)

export type SlotDisplayStatus = 'ready' | 'failed' | 'pending';

export function statusForMeeStatusBadge(
  imageStatus: ProductImage['status'],
): SlotDisplayStatus {
  if (imageStatus === 'ready')           return 'ready';
  if (imageStatus === 'failed_precheck') return 'failed';
  return 'pending';
}
