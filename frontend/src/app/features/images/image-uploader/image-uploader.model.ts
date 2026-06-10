// image-uploader.model.ts
// Pure TypeScript — NO Angular decorators. Vitest-testable without TestBed.

// ── Domain types ───────────────────────────────────────────────────────────────

export interface PrecheckResult {
  jpeg_format: boolean;
  color_space_rgb: boolean;  // false = CMYK detected
  min_resolution: boolean;   // >= 1500x1500 px
  white_bg: boolean;
  no_watermark: boolean;
}

export interface ProductImage {
  id: string;
  slot_index: number;          // 0-based, max 5
  gcs_url: string | null;
  status: 'pending' | 'pass' | 'fail';
  precheck: PrecheckResult | null;
}

export interface PrecheckItem {
  key: keyof PrecheckResult;
  label: string;
  pass: boolean;
  hint: string | null;
}

// ── Static lookup maps ────────────────────────────────────────────────────────

export const PRECHECK_HINTS: Record<keyof PrecheckResult, string> = {
  jpeg_format:     'Save the image as JPEG (.jpg) before uploading',
  color_space_rgb: 'Convert image to RGB mode before uploading (CMYK detected)',
  min_resolution:  'Image must be at least 1500×1500 pixels',
  white_bg:        'Use a plain white background for best results',
  no_watermark:    'Remove watermarks or logos before uploading',
};

export const PRECHECK_LABELS: Record<keyof PrecheckResult, string> = {
  jpeg_format:     'JPEG format',
  color_space_rgb: 'RGB color space',
  min_resolution:  'Min. resolution',
  white_bg:        'White background',
  no_watermark:    'No watermark',
};

// ── Pre-check gate 1: buildPrecheckItems ──────────────────────────────────────
// Returns the 5-item pre-check matrix for a resolved image.
// Returns [] for pending images (precheck is null).

export function buildPrecheckItems(image: ProductImage): PrecheckItem[] {
  if (!image.precheck) return [];
  const keys = Object.keys(image.precheck) as Array<keyof PrecheckResult>;
  return keys.map(key => ({
    key,
    label: PRECHECK_LABELS[key],
    pass:  image.precheck![key],
    hint:  image.precheck![key] ? null : PRECHECK_HINTS[key],
  }));
}

// ── Pre-check gate 2: slotProgress ───────────────────────────────────────────
// Returns 0 while pending, 100 when resolved (pass or fail).

export function slotProgress(image: ProductImage): number {
  if (image.status === 'pending') return 0;
  return 100;
}

// ── Gate 3: computeCanContinue ───────────────────────────────────────────────
// canContinue = at least one image AND all images passed.
// Slot 1 CMYK fail blocks this gate (journey step 7).

export function computeCanContinue(images: ProductImage[]): boolean {
  return images.length > 0 && images.every(img => img.status === 'pass');
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

// ── Gate 6: addSlots ──────────────────────────────────────────────────────────
// Enforces max 6 images. Returns new slots to append (does NOT mutate).

export function addSlots(
  currentImages: ProductImage[],
  fileNames: string[],  // abstracted from File[] for pure-function testability
  maxSlots = 6,
): ProductImage[] {
  const remaining = maxSlots - currentImages.length;
  if (remaining <= 0) return [];

  const toAdd = fileNames.slice(0, remaining);
  const startIndex = currentImages.length;

  return toAdd.map((name, i) => ({
    id:         `slot-${startIndex + i}-${name}`,
    slot_index: startIndex + i,
    gcs_url:    null,
    status:     'pending' as const,
    precheck:   null,
  }));
}

// ── resetSlot ────────────────────────────────────────────────────────────────
// Returns a new images array with the given slot reset to pending (for re-upload).

export function resetSlot(
  images: ProductImage[],
  slotIndex: number,
): ProductImage[] {
  return images.map(img =>
    img.slot_index === slotIndex
      ? { ...img, status: 'pending' as const, precheck: null }
      : img,
  );
}

// ── applySimulationResult ─────────────────────────────────────────────────────
// Returns a new images array with the simulation result applied to a given slot.

export function applySimulationResult(
  images: ProductImage[],
  slotIndex: number,
  precheck: PrecheckResult,
): ProductImage[] {
  const allPass = Object.values(precheck).every(Boolean);
  return images.map(img => {
    if (img.slot_index !== slotIndex) return img;
    return {
      ...img,
      precheck,
      status: allPass ? 'pass' as const : 'fail' as const,
    };
  });
}

// ── statusForMeeStatusBadge ───────────────────────────────────────────────────
// Maps image status to the ProductStatus union expected by mee-status-badge.

export type SlotDisplayStatus = 'ready' | 'failed' | 'pending';

export function statusForMeeStatusBadge(imageStatus: ProductImage['status']): SlotDisplayStatus {
  if (imageStatus === 'pass')    return 'ready';
  if (imageStatus === 'fail')    return 'failed';
  return 'pending';
}
