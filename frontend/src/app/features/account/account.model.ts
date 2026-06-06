// features/account/account.model.ts
// Feature-private types for the account feature per §3.D

export type OnboardingPhase = 'base' | 'super-category' | 'conditional-compliance';

export interface OtpFlowState {
  readonly phone: string;
  readonly requestId: string;
  readonly resendAt: number; // epoch ms when resend becomes available (30s timer)
}
