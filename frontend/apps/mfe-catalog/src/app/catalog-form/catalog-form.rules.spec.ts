/**
 * catalog-form.rules.spec.ts — Conditional Field UX
 *
 * Pure-function tests for the dependency-rule evaluator.
 * Zero TestBed, zero Angular imports — safe to run with Vitest directly.
 *
 * Coverage:
 *   _predicateMet() — all 4 operators (eq, in, contains, any) + edge cases
 *   evaluateRules() — category_required, value_conditional, show action,
 *                     multi-rule accumulation, empty rules
 *   getSoftRules()  — soft filter, hard filter, mixed
 */

import { describe, it, expect } from 'vitest';
import { _predicateMet, evaluateRules, getSoftRules } from './catalog-form.rules';
import type { DependencyRule } from './catalog-form.rules';

// ── Fixtures ─────────────────────────────────────────────────────────────────

const BASE_RULE: DependencyRule = {
  id: 'test_rule',
  type: 'value_conditional',
  if_field: 'product_type',
  if_operator: 'eq',
  if_value: 'food',
  target_field: 'fssai_license_number',
  action: 'required',
  severity: 'hard',
  message_id: 'validation.cross_field.test_rule',
};

const CATEGORY_REQUIRED_RULE: DependencyRule = {
  id: 'country_origin',
  type: 'category_required',
  target_field: 'country_of_origin',
  action: 'required',
  severity: 'hard',
  message_id: 'validation.cross_field.country_origin',
};

const SHOW_RULE: DependencyRule = {
  id: 'show_battery_type',
  type: 'value_conditional',
  if_field: 'battery_required',
  if_operator: 'eq',
  if_value: 'Yes',
  target_field: 'battery_type',
  action: 'show',
  severity: 'soft',
  message_id: 'validation.cross_field.show_battery_type',
};

const SOFT_RULE: DependencyRule = {
  id: 'bis_advisory',
  type: 'value_conditional',
  if_field: 'product_type',
  if_operator: 'in',
  if_value: ['power bank', 'charger'],
  target_field: 'bis_isi_certification_number',
  action: 'required',
  severity: 'soft',
  message_id: 'validation.cross_field.bis_advisory',
};

// ── _predicateMet ─────────────────────────────────────────────────────────────

describe('_predicateMet()', () => {
  describe('eq operator', () => {
    it('returns true when field value strictly equals if_value', () => {
      const rule: DependencyRule = { ...BASE_RULE, if_operator: 'eq', if_value: 'food' };
      expect(_predicateMet(rule, { product_type: 'food' })).toBe(true);
    });

    it('returns false when field value does not equal if_value', () => {
      const rule: DependencyRule = { ...BASE_RULE, if_operator: 'eq', if_value: 'food' };
      expect(_predicateMet(rule, { product_type: 'clothing' })).toBe(false);
    });

    it('returns false when field is absent from values', () => {
      const rule: DependencyRule = { ...BASE_RULE, if_operator: 'eq', if_value: 'food' };
      expect(_predicateMet(rule, {})).toBe(false);
    });

    it('is strict equality — "Food" !== "food"', () => {
      const rule: DependencyRule = { ...BASE_RULE, if_operator: 'eq', if_value: 'food' };
      expect(_predicateMet(rule, { product_type: 'Food' })).toBe(false);
    });
  });

  describe('in operator', () => {
    const rule: DependencyRule = {
      ...BASE_RULE,
      if_operator: 'in',
      if_value: ['food', 'grocery', 'snack'],
    };

    it('returns true when field value is in the array', () => {
      expect(_predicateMet(rule, { product_type: 'grocery' })).toBe(true);
    });

    it('returns false when field value is not in the array', () => {
      expect(_predicateMet(rule, { product_type: 'clothing' })).toBe(false);
    });

    it('returns false when if_value is not an array', () => {
      const badRule: DependencyRule = { ...BASE_RULE, if_operator: 'in', if_value: 'food' };
      expect(_predicateMet(badRule, { product_type: 'food' })).toBe(false);
    });

    it('returns false when field is absent', () => {
      expect(_predicateMet(rule, {})).toBe(false);
    });
  });

  describe('contains operator', () => {
    const rule: DependencyRule = {
      ...BASE_RULE,
      if_operator: 'contains',
      if_value: 'food',
    };

    it('returns true when field value contains the substring', () => {
      expect(_predicateMet(rule, { product_type: 'pet food' })).toBe(true);
    });

    it('returns false when field value does not contain the substring', () => {
      expect(_predicateMet(rule, { product_type: 'clothing' })).toBe(false);
    });

    it('returns false for absent field (empty string does not contain non-empty)', () => {
      expect(_predicateMet(rule, {})).toBe(false);
    });

    it('handles null field value gracefully (empty string)', () => {
      expect(_predicateMet(rule, { product_type: null })).toBe(false);
    });
  });

  describe('any operator', () => {
    const rule: DependencyRule = {
      ...BASE_RULE,
      if_operator: 'any',
      if_value: null,
    };

    it('returns true when field has a non-empty string value', () => {
      expect(_predicateMet(rule, { product_type: 'something' })).toBe(true);
    });

    it('returns false when field is absent', () => {
      expect(_predicateMet(rule, {})).toBe(false);
    });

    it('returns false when field is null', () => {
      expect(_predicateMet(rule, { product_type: null })).toBe(false);
    });

    it('returns false when field is empty string', () => {
      expect(_predicateMet(rule, { product_type: '' })).toBe(false);
    });

    it('returns true for numeric zero (zero is a valid value)', () => {
      // 0 != null && 0 !== '' → true
      expect(_predicateMet(rule, { product_type: 0 })).toBe(true);
    });
  });

  describe('edge cases', () => {
    it('returns false when if_field is null/undefined', () => {
      const rule: DependencyRule = { ...BASE_RULE, if_field: undefined };
      expect(_predicateMet(rule, { product_type: 'food' })).toBe(false);
    });

    it('returns false when if_operator is null/undefined', () => {
      const rule: DependencyRule = { ...BASE_RULE, if_operator: undefined };
      expect(_predicateMet(rule, { product_type: 'food' })).toBe(false);
    });

    it('returns false for unknown operator (forward-compat)', () => {
      const rule = { ...BASE_RULE, if_operator: 'unknown_op' } as unknown as DependencyRule;
      expect(_predicateMet(rule, { product_type: 'food' })).toBe(false);
    });
  });
});

// ── evaluateRules ─────────────────────────────────────────────────────────────

describe('evaluateRules()', () => {
  it('returns empty map for empty rules[]', () => {
    const result = evaluateRules([], {});
    expect(result).toEqual({});
  });

  describe('category_required', () => {
    it('always fires — sets target required=true and visible=true', () => {
      const result = evaluateRules([CATEGORY_REQUIRED_RULE], {});
      expect(result['country_of_origin']).toEqual({ required: true, visible: true });
    });

    it('fires regardless of field values', () => {
      const result = evaluateRules([CATEGORY_REQUIRED_RULE], { country_of_origin: 'India' });
      expect(result['country_of_origin']?.required).toBe(true);
    });
  });

  describe('value_conditional — action=required', () => {
    it('fires when predicate is met — sets required=true', () => {
      const result = evaluateRules([BASE_RULE], { product_type: 'food' });
      expect(result['fssai_license_number']?.required).toBe(true);
    });

    it('does NOT set required when predicate is not met', () => {
      const result = evaluateRules([BASE_RULE], { product_type: 'clothing' });
      // Field appears in the result only if rule fires or has show-rule
      // Since predicate is not met, fssai_license_number should not be required
      expect(result['fssai_license_number']?.required ?? false).toBe(false);
    });

    it('default visible=true when field has no show-rule', () => {
      const result = evaluateRules([BASE_RULE], { product_type: 'food' });
      expect(result['fssai_license_number']?.visible).toBe(true);
    });
  });

  describe('value_conditional — action=show', () => {
    it('field is visible when predicate fires', () => {
      const result = evaluateRules([SHOW_RULE], { battery_required: 'Yes' });
      expect(result['battery_type']?.visible).toBe(true);
    });

    it('field is NOT visible when predicate does not fire', () => {
      const result = evaluateRules([SHOW_RULE], { battery_required: 'No' });
      expect(result['battery_type']?.visible).toBe(false);
    });

    it('show=true but required stays false (show action does not set required)', () => {
      const result = evaluateRules([SHOW_RULE], { battery_required: 'Yes' });
      expect(result['battery_type']?.required).toBe(false);
    });
  });

  describe('category_required — action=show', () => {
    it('always makes the field visible', () => {
      const showCatRule: DependencyRule = {
        ...CATEGORY_REQUIRED_RULE,
        target_field: 'compliance_label',
        action: 'show',
      };
      const result = evaluateRules([showCatRule], {});
      expect(result['compliance_label']?.visible).toBe(true);
    });
  });

  describe('multi-rule accumulation', () => {
    it('required=true wins when one rule fires and another does not', () => {
      const rule2: DependencyRule = {
        ...BASE_RULE,
        id: 'rule2',
        if_operator: 'eq',
        if_value: 'grocery',
      };
      // rule1: product_type === 'food' → fires
      // rule2: product_type === 'grocery' → does not fire
      const result = evaluateRules([BASE_RULE, rule2], { product_type: 'food' });
      expect(result['fssai_license_number']?.required).toBe(true);
    });

    it('multiple rules targeting the same field: required=true persists', () => {
      const rule2: DependencyRule = { ...BASE_RULE, id: 'rule2', if_value: 'grocery' };
      // Both fire
      const result = evaluateRules([BASE_RULE, rule2], { product_type: 'food' });
      expect(result['fssai_license_number']?.required).toBe(true);
    });

    it('show-rule + require-rule targeting same field: both accumulate independently', () => {
      const requireRule: DependencyRule = {
        ...SHOW_RULE,
        id: 'require_battery',
        action: 'required',
        target_field: 'battery_type',
      };
      // SHOW_RULE fires (battery_required=Yes) → visible=true
      // requireRule fires → required=true
      const result = evaluateRules([SHOW_RULE, requireRule], { battery_required: 'Yes' });
      expect(result['battery_type']?.visible).toBe(true);
      expect(result['battery_type']?.required).toBe(true);
    });
  });

  describe('action alias: "require" (spec alias)', () => {
    it('action="require" is treated same as "required"', () => {
      const aliasRule: DependencyRule = {
        ...BASE_RULE,
        action: 'require',
      };
      const result = evaluateRules([aliasRule], { product_type: 'food' });
      expect(result['fssai_license_number']?.required).toBe(true);
    });
  });
});

// ── getSoftRules ──────────────────────────────────────────────────────────────

describe('getSoftRules()', () => {
  it('returns empty array when no rules are present', () => {
    expect(getSoftRules([], {})).toEqual([]);
  });

  it('returns empty array when no soft rules fire', () => {
    const result = getSoftRules([BASE_RULE], { product_type: 'food' });
    // BASE_RULE is severity='hard', not soft
    expect(result).toEqual([]);
  });

  it('returns firing soft rules', () => {
    const result = getSoftRules([SOFT_RULE], { product_type: 'power bank' });
    expect(result).toHaveLength(1);
    expect(result[0]?.id).toBe('bis_advisory');
  });

  it('does not return non-firing soft rules', () => {
    const result = getSoftRules([SOFT_RULE], { product_type: 'clothing' });
    expect(result).toHaveLength(0);
  });

  it('category_required soft rule always fires', () => {
    const softCatRule: DependencyRule = {
      ...CATEGORY_REQUIRED_RULE,
      severity: 'soft',
    };
    const result = getSoftRules([softCatRule], {});
    expect(result).toHaveLength(1);
  });

  it('filters out hard rules even when they fire', () => {
    const rules = [BASE_RULE, SOFT_RULE];
    const result = getSoftRules(rules, { product_type: 'food' });
    // BASE_RULE fires but is hard; SOFT_RULE does not fire (product_type is 'food', not in list)
    expect(result.every(r => r.severity === 'soft')).toBe(true);
  });

  it('returns multiple firing soft rules', () => {
    const softRule2: DependencyRule = {
      id: 'bis_toys',
      type: 'value_conditional',
      if_field: 'product_type',
      if_operator: 'eq',
      if_value: 'power bank',
      target_field: 'second_soft_field',
      action: 'required',
      severity: 'soft',
      message_id: 'validation.cross_field.bis_toys',
    };
    const result = getSoftRules([SOFT_RULE, softRule2], { product_type: 'power bank' });
    expect(result).toHaveLength(2);
  });
});
