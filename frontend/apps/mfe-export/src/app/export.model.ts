/**
 * export.model.ts — typed contracts for the XLSX export feature.
 *
 * Wire DTOs: §1 of spec_w6c_export.md (Wave 6 Wave C Lane 2).
 *
 * Key decisions:
 * - ExportInitiatedResponse.status is LITERAL 'pending' (NOT 'processing') — backend constant.
 * - ExportResponseDTO has NO progress_pct field — wire shape confirmed in spec §1.
 * - MOCK_DOWNLOAD_URL REMOVED — signed URL is read from ExportResponseDTO.xlsx_signed_url.
 * - SIMULATED_PASSING_CHECKS retained as DISPLAY-ONLY per GAP-1 Option A ruling;
 *   the real readiness gate is the 422 export.product_not_ready on initiate (R-W6-1).
 * - nextProgress / isProgressComplete REMOVED — no progress_pct on the wire.
 * - retryState adjusted — no progress field.
 * - isTerminalStatus added as a pure-function gate for the poll loop.
 */

// ── Wire formats ────────────────────────────────────────────────────────────────

/** Supported export formats (ExportRequest.format — backend extra=forbid). */
export type ExportFormat = 'xlsx_only' | 'xlsx_with_images';

/**
 * Request body for POST /api/v1/products/{product_id}/export-xlsx.
 * Backend enforces extra=forbid — only `format` is allowed.
 */
export interface ExportRequest {
  format: ExportFormat;
}

/**
 * Response from POST /api/v1/products/{product_id}/export-xlsx (HTTP 202).
 * status is ALWAYS the literal 'pending' (not 'processing').
 * Source: backend/app/modules/export/schemas.py:39
 */
export interface ExportInitiatedResponse {
  export_id: string;
  status: 'pending';
  enqueued_task_id: string;
  initiated_at: string; // ISO 8601 datetime
}

/**
 * Wire status values from GET /api/v1/exports/{export_id}.
 * Backend emits these three values only. 'pending' = job in Celery queue or running.
 */
export type ExportWireStatus = 'pending' | 'ready' | 'failed';

/**
 * Response from GET /api/v1/exports/{export_id} (HTTP 200, any status).
 * NO progress_pct field — status-based polling, no numeric progress on the wire.
 * Source: backend/app/modules/export/schemas.py:48
 */
export interface ExportResponseDTO {
  export_id: string;
  product_id: string;
  status: ExportWireStatus;
  format: ExportFormat;
  /** Populated when status = 'ready'. Fresh 1 h GCS signed URL. */
  xlsx_signed_url: string | null;
  /** Populated when status = 'ready' AND format = 'xlsx_with_images'. */
  zip_signed_url: string | null;
  /** Populated when status = 'failed'. */
  error_message: string | null;
  error_code: string | null;
  initiated_at: string; // ISO 8601 datetime
  /**
   * Always null in V1 — backend has no DDL column for this yet.
   * Retained per spec §1 to avoid future shape drift.
   */
  completed_at: string | null;
  /** true when status = 'ready' and round-trip XLSX validation passed. */
  round_trip_validated: boolean | null;
}

// ── UI-local types ──────────────────────────────────────────────────────────────

/**
 * UI-local export status enum.
 * 'idle'       — not yet triggered
 * 'processing' — initiate returned 202 + poll is running (wire status = 'pending')
 * 'ready'      — poll returned status = 'ready'; signed URL available
 * 'failed'     — poll returned status = 'failed'; or network/404 error
 *
 * Wire-to-UI mapping: 'pending' → 'processing' (template keeps its 4-state enum
 * without change; builder 2 owns the template render per §5 serial chain).
 */
export type ExportStatus = 'idle' | 'processing' | 'ready' | 'failed';

// ── GAP-1 Option A — display-only checklist ─────────────────────────────────────
// These checks are DISPLAY-ONLY constants, NOT backed by any backend endpoint.
// The authoritative readiness gate is the 422 `export.product_not_ready` /
// `export.front_image_missing` returned by POST export-xlsx (R-W6-1).

export interface ValidationChecks {
  title_ok: boolean;
  category_ok: boolean;
  fields_ok: boolean;
  images_ok: boolean;
}

/** Validation check display item for the checklist UI. */
export interface ValidationCheckItem {
  label: string;
  ok: boolean;
}

/**
 * All 4 checks set to true for V1 simulation.
 * DISPLAY-ONLY — not backed by a backend endpoint (GAP-1 Option A ruling).
 * The real gate is POST export-xlsx 422 response.
 */
export const SIMULATED_PASSING_CHECKS: ValidationChecks = {
  title_ok:    true,
  category_ok: true,
  fields_ok:   true,
  images_ok:   true,
};

// ── Pure functions (exported for unit testing without TestBed) ──────────────────

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
 * Returns true when the wire status is terminal (poll loop should stop).
 * 'ready' and 'failed' are terminal; 'pending' is not.
 * Pure: no side-effects.
 */
export function isTerminalStatus(status: ExportWireStatus): boolean {
  return status === 'ready' || status === 'failed';
}

/**
 * Returns reset state values for the Retry action.
 * No progress field — numeric progress was removed (no progress_pct on the wire).
 * Pure: no side-effects.
 */
export function retryState(): { status: ExportStatus; downloadUrl: null } {
  return { status: 'idle', downloadUrl: null };
}
