// shared/enums/primitive-kind.enum.ts
// The 11 primitive identifiers from MVP §4.1 — drives the catalog-form field dispatcher

export type PrimitiveKind =
  | 'text_short'
  | 'text_long'
  | 'number'
  | 'number_with_unit'
  | 'currency'
  | 'dropdown_small'
  | 'dropdown_medium'
  | 'dropdown_large'
  | 'dropdown_api_search'
  | 'image_upload'
  | 'address_group';

export const PRIMITIVE_KIND = {
  TEXT_SHORT: 'text_short',
  TEXT_LONG: 'text_long',
  NUMBER: 'number',
  NUMBER_WITH_UNIT: 'number_with_unit',
  CURRENCY: 'currency',
  DROPDOWN_SMALL: 'dropdown_small',
  DROPDOWN_MEDIUM: 'dropdown_medium',
  DROPDOWN_LARGE: 'dropdown_large',
  DROPDOWN_API_SEARCH: 'dropdown_api_search',
  IMAGE_UPLOAD: 'image_upload',
  ADDRESS_GROUP: 'address_group',
} as const satisfies Record<string, PrimitiveKind>;

export const ALL_PRIMITIVES: readonly PrimitiveKind[] = Object.values(PRIMITIVE_KIND);
