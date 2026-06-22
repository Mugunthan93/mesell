/**
 * export.model.ts — typed contracts for the XLSX export feature.
 *
 * Wire DTOs: §1 of spec_w6c_export.md (Wave 6 Wave C Lane 2).
 *
 * Key decisions:
 * - ExportInitiatedResponse.status is LITERAL 'pending' (NOT 'processing') — backend constant.
 * - ExportResponseDTO has NO progress_pct field — wire shape confirmed in spec §1.
 * - SIMULATED_PASSING_CHECKS REMOVED — real readiness gate is the 422 failed_checks[]
 *   returned by POST export-xlsx (PR #291, R-W6-1). ExportFailedCheck + resolveCheckMessage
 *   replace the display-only checklist (GAP-1 Option A retired).
 * - ValidationChecks / buildCheckItems / allChecksPassed REMOVED — simulated checklist retired.
 * - canGenerate updated: gates only on status, not on simulated checks.
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

// ── Real failed-checks (PR #291 — replaces GAP-1 Option A simulated checklist) ──

/**
 * A single failed check emitted by POST export-xlsx 422 response body.
 * Backend emits this shape in the `failed_checks[]` array (PR #291).
 */
export interface ExportFailedCheck {
  check_id: string;    // e.g. "quality_status"
  message_key: string; // e.g. "export.check.quality_status"
}

/**
 * FE-local display strings for export failed-check message keys.
 * Unknown keys fall back to EXPORT_CHECK_FALLBACK — never blank, never the raw key.
 */
export const EXPORT_CHECK_MESSAGES: Record<string, string> = {
  'export.check.quality_status':
    "Your product isn't ready. Complete the required fields and resolve quality issues first.",
  'export.check.front_image_missing':
    'A front image is required. Upload an image in slot 1 before exporting with images.',
};

/** Fallback message for any check_id not in EXPORT_CHECK_MESSAGES. */
export const EXPORT_CHECK_FALLBACK = 'This item needs attention before you can export.';

/**
 * Resolves a human-readable message for a failed check.
 * Falls back to EXPORT_CHECK_FALLBACK for unknown message_keys.
 * Pure: no side-effects.
 */
export function resolveCheckMessage(check: ExportFailedCheck): string {
  return EXPORT_CHECK_MESSAGES[check.message_key] ?? EXPORT_CHECK_FALLBACK;
}

// ── Pure functions (exported for unit testing without TestBed) ──────────────────

/**
 * Returns true when the Generate Export button should be enabled.
 * Gates on status === 'idle' only — the real readiness gate is the backend 422.
 * Pure: no side-effects.
 */
export function canGenerate(status: ExportStatus): boolean {
  return status === 'idle';
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

/**
 * Resolves the product ID from an ActivatedRoute-style ParamMap.
 * Returns the id string when present and non-empty; null otherwise.
 * Pure helper — testable without TestBed or Angular DI.
 *
 * Usage in component:
 *   const productId = resolveExportProductId(this.route.snapshot.paramMap);
 *   if (!productId) { ... return; }
 */
export function resolveExportProductId(
  paramMap: { get(key: string): string | null }
): string | null {
  const id = paramMap.get('id');
  return id && id.length > 0 ? id : null;
}
