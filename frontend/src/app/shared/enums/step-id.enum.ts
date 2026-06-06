// shared/enums/step-id.enum.ts
// The 13 wizard step IDs from MVP §5.6.3 — drives the step composer

export type StepId =
  | 'basics'
  | 'pricing'
  | 'inventory'
  | 'sizing'
  | 'materials'
  | 'food'
  | 'tech_specs'
  | 'safety'
  | 'warranty'
  | 'compliance'
  | 'photos'
  | 'description'
  | 'advanced';

export const STEP_ID = {
  BASICS: 'basics',
  PRICING: 'pricing',
  INVENTORY: 'inventory',
  SIZING: 'sizing',
  MATERIALS: 'materials',
  FOOD: 'food',
  TECH_SPECS: 'tech_specs',
  SAFETY: 'safety',
  WARRANTY: 'warranty',
  COMPLIANCE: 'compliance',
  PHOTOS: 'photos',
  DESCRIPTION: 'description',
  ADVANCED: 'advanced',
} as const satisfies Record<string, StepId>;

/** Canonical step display order per MVP §5.6.3 */
export const STEP_ORDER: readonly StepId[] = [
  'basics', 'pricing', 'inventory', 'sizing', 'materials', 'food',
  'tech_specs', 'safety', 'warranty', 'compliance', 'photos',
  'description', 'advanced',
];
