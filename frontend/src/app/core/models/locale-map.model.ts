// core/models/locale-map.model.ts
// Locale map — {en, ta?, hi?} per §4.I and Philosophy M9

export interface LocaleMap {
  readonly en: string;
  readonly ta?: string;
  readonly hi?: string;
}
