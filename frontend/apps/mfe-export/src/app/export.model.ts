export interface ValidationChecks {
  title_ok: boolean;
  category_ok: boolean;
  fields_ok: boolean;
  images_ok: boolean;
}

export interface ExportJob {
  id: string;
  status: 'processing' | 'ready' | 'failed';
  progress_pct: number;
  download_url: string | null;
  created_at: string;
}

export interface ExportTriggerResponse {
  export_id: string;
}

export type ExportStatus = 'idle' | 'processing' | 'ready' | 'failed';

/** Validation check display item for the checklist UI. */
export interface ValidationCheckItem {
  label: string;
  ok: boolean;
}

/** All 4 checks pass in V1 simulation (journey step 10). */
export const SIMULATED_PASSING_CHECKS: ValidationChecks = {
  title_ok:    true,
  category_ok: true,
  fields_ok:   true,
  images_ok:   true,
};

/** Mock download URL returned after simulated XLSX generation. */
export const MOCK_DOWNLOAD_URL =
  'https://storage.googleapis.com/mee-exports/mock-kurti-catalog.xlsx';

// ── Pure functions (exported for unit testing without TestBed) ─────────────────

/**
 * Returns the 4 validation check items for display in the checklist table.
 * Pure: no side-effects, always same output for same input.
 */
export function buildCheckItems(checks: ValidationChecks): ValidationCheckItem[] {
  return [
    { label: 'Title filled',            ok: checks.title_ok },
    { label: 'Category selected',       ok: checks.category_ok },
    { label: 'Compulsory fields',       ok: checks.fields_ok },
    { label: 'At least 1 image (pass)', ok: checks.images_ok },
  ];
}

/**
 * Returns true when ALL 4 validation checks pass.
 * Pure: no side-effects.
 */
export function allChecksPassed(checks: ValidationChecks): boolean {
  return checks.title_ok && checks.category_ok && checks.fields_ok && checks.images_ok;
}

/**
 * Returns true when the Generate Export button should be enabled.
 * Requires status === 'idle' AND all checks passing.
 * Pure: no side-effects.
 */
export function canGenerate(status: ExportStatus, checks: ValidationChecks): boolean {
  return status === 'idle' && allChecksPassed(checks);
}

/**
 * Derives the next progress value after one tick, capped at 100.
 * Pure: no side-effects.
 */
export function nextProgress(current: number, tick: number): number {
  return Math.min(current + tick, 100);
}

/**
 * Returns true when progress has reached 100 and the export should become 'ready'.
 * Pure: no side-effects.
 */
export function isProgressComplete(progress: number): boolean {
  return progress >= 100;
}

/**
 * Returns reset state values for the Retry action.
 * Pure: no side-effects.
 */
export function retryState(): { status: ExportStatus; progress: number; downloadUrl: null } {
  return { status: 'idle', progress: 0, downloadUrl: null };
}
