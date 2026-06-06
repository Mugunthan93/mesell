// core/models/ai-suggestion.model.ts
// Mirrors products.ai_suggestions_jsonb per DATABASE_ARCHITECTURE.md §4.5

export interface AiSuggestion {
  readonly value: string | number | string[];
  /** Confidence 0.0 – 1.0 */
  readonly confidence: number;
  /** e.g. 'gemini-2.5-flash' */
  readonly source: string;
  readonly accepted: boolean;
  readonly rejectedReason?: string;
}
