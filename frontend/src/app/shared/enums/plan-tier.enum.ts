// shared/enums/plan-tier.enum.ts
// Plan tier values — free in V1, pro gates in V1.5

export type PlanTier = 'free' | 'pro';

export const PLAN_TIER = {
  FREE: 'free',
  PRO: 'pro',
} as const satisfies Record<string, PlanTier>;
