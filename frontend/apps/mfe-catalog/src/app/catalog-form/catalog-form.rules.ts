/**
 * catalog-form.rules.ts — Conditional Field UX
 *
 * Pure-function rule evaluator for the catalog-form dependency_rules[] contract.
 * Decorator-free — safe to import in Vitest without TestBed.
 *
 * The backend's /schema endpoint returns a dependency_rules[] array that the
 * frontend uses to show/require fields in real-time as the seller fills the form.
 * This file evaluates those rules against the current field values and returns
 * a map of per-field overrides.
 *
 * Wire-shape note (PR #290 contract):
 *   - Backend JSON uses action: "required" (not "require") — the TypeScript type
 *     accepts both for safety, but evaluation checks both spellings.
 *   - The field "message_id" is the backend wire key (not "error_message_key") —
 *     this module re-exports error_message_key as an alias for spec compatibility.
 *
 * Import type: import type { DependencyRule } from './catalog-form.rules';
 * Companion model: DependencyRule is ALSO re-exported from catalog-form.model.ts
 *   (added in the same PR) so consumers have a single import point.
 */

/**
 * DependencyRule — frontend projection of one backend cross-field rule.
 *
 * Wire keys from backend/app/modules/category/service.py _project_dependency_rules:
 *   id, type, if_field, if_operator, if_value, target_field, action, severity, message_id
 *
 * Note on action values:
 *   Backend JSON uses "required" and "show" — NOT "require".
 *   The type accepts both "require" and "required" for spec compatibility,
 *   but evaluateRules handles both spellings internally.
 */
export interface DependencyRule {
  id: string;
  type: 'category_required' | 'value_conditional';
  if_field?: string | null;
  if_operator?: 'eq' | 'in' | 'contains' | 'any' | null;
  if_value?: unknown;
  target_field: string;
  /** "required" (backend wire) or "require" (spec alias) or "show" */
  action: 'required' | 'require' | 'show';
  severity: 'hard' | 'soft';
  /**
   * Backend wire key: "message_id" (format: "validation.cross_field.{rule_id}").
   * Required on the wire (backend always computes it). Optional only in test fixtures.
   */
  message_id?: string;
  /** Alias for message_id — kept for spec/test compatibility */
  error_message_key?: string;
  // NOTE: message_id is optional here to allow lightweight test fixtures.
  // DependencyRuleDTO (field-schema.model.ts) has message_id: string (required wire type).
}

/**
 * FieldOverride — the resolved required/visible state for a single field.
 * Produced by evaluateRules() and consumed by the CatalogFormComponent template.
 */
export interface FieldOverride {
  required: boolean;
  visible: boolean;
}

// ── Internal predicate helpers ─────────────────────────────────────────────

/**
 * _predicateMet — evaluates a value_conditional rule's if_field/if_operator/if_value
 * against the current field values.
 *
 * Operators:
 *   eq      — fieldValues[if_field] === if_value (strict equality)
 *   in      — if_value is an array containing fieldValues[if_field]
 *   contains — String(fieldValues[if_field] ?? '').includes(String(if_value))
 *   any     — fieldValues[if_field] != null && fieldValues[if_field] !== ''
 *
 * Returns false when if_field is absent (no field to check).
 * Returns false when if_operator is absent or unknown.
 */
export function _predicateMet(
  rule: DependencyRule,
  values: Record<string, unknown>,
): boolean {
  const { if_field, if_operator, if_value } = rule;

  if (!if_field) return false;
  if (!if_operator) return false;

  const fieldVal = values[if_field];

  switch (if_operator) {
    case 'eq':
      return fieldVal === if_value;

    case 'in':
      if (!Array.isArray(if_value)) return false;
      return if_value.includes(fieldVal);

    case 'contains':
      return String(fieldVal ?? '').includes(String(if_value ?? ''));

    case 'any':
      return fieldVal != null && fieldVal !== '';

    default:
      return false;
  }
}

// ── Main evaluator ────────────────────────────────────────────────────────

/**
 * evaluateRules — evaluates all dependency_rules[] against the current
 * field values and returns a map of per-field overrides.
 *
 * Return shape: { [target_field]: { required: boolean; visible: boolean } }
 *
 * Algorithm:
 *   1. For each rule where action = 'required' | 'require':
 *      - category_required: always fires → target_field.required = true
 *      - value_conditional: fires when _predicateMet(rule, values) = true
 *        → target_field.required = true
 *   2. For each rule where action = 'show':
 *      - category_required: always shows → target_field.visible = true
 *      - value_conditional: fires when predicate met → target_field.visible = true
 *   3. required=true wins over required=false across multiple rules targeting
 *      the same field (accumulation).
 *   4. visible defaults to true when not explicitly set by any 'show' rule.
 *      A field is only hidden when there is at least one 'show' rule that targets
 *      it AND that rule's predicate is NOT met.
 *
 * Called as a computed:
 *   readonly fieldOverrides = computed(() =>
 *     evaluateRules(this.schemaRules(), this.fieldValues())
 *   );
 *
 * Pure function — no Angular, no side effects.
 */
export function evaluateRules(
  rules: DependencyRule[],
  values: Record<string, unknown>,
): Record<string, FieldOverride> {
  // Phase 1: accumulate overrides from all rules
  const overrides = new Map<string, { required: boolean; hasShowRule: boolean; showActive: boolean }>();

  const getOrCreate = (target: string) => {
    if (!overrides.has(target)) {
      overrides.set(target, { required: false, hasShowRule: false, showActive: false });
    }
    return overrides.get(target)!;
  };

  for (const rule of rules) {
    const { action, type, target_field } = rule;

    // Determine whether the rule fires
    let fires: boolean;
    if (type === 'category_required') {
      fires = true;
    } else {
      // value_conditional
      fires = _predicateMet(rule, values);
    }

    if (action === 'required' || action === 'require') {
      const entry = getOrCreate(target_field);
      // required=true accumulates — once true, stays true
      if (fires) entry.required = true;
    } else if (action === 'show') {
      const entry = getOrCreate(target_field);
      entry.hasShowRule = true;
      // show=active: if any show-rule fires, the field is visible
      if (fires) entry.showActive = true;
    }
  }

  // Phase 2: convert to FieldOverride map
  const result: Record<string, FieldOverride> = {};
  for (const [target, state] of overrides.entries()) {
    result[target] = {
      required: state.required,
      // visible = true unless the field has a 'show' rule and NONE of them fire
      visible: !state.hasShowRule || state.showActive,
    };
  }

  return result;
}

/**
 * getSoftRules — returns all soft-severity rules from the set that are currently
 * firing (predicate met). Used by the component to render recommendation banners.
 *
 * Returns the list of firing soft rules so the template can show contextual
 * yellow chips like "Recommended for [product type] listings".
 */
export function getSoftRules(
  rules: DependencyRule[],
  values: Record<string, unknown>,
): DependencyRule[] {
  return rules.filter(rule => {
    if (rule.severity !== 'soft') return false;

    if (rule.type === 'category_required') return true;

    return _predicateMet(rule, values);
  });
}
