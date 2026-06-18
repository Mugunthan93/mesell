// Components
export { MeeIconComponent }            from './icon/icon.component';
export { MeeButtonComponent }          from './button/button.component';
export { MeeInputComponent }           from './input/input.component';
export { MeeOtpInputComponent }        from './otp-input/otp-input.component';
export { MeeBadgeComponent }           from './badge/badge.component';
export { MeeCardComponent }            from './card/card.component';
export { MeeTableComponent }           from './table/table.component';
export { MeeDialogComponent }          from './dialog/dialog.component';
export { MeeFileUploadComponent }      from './file-upload/file-upload.component';
export { MeeStepsComponent }           from './steps/steps.component';
export { MeeSelectComponent }          from './select/select.component';
export { MeeTreeSelectComponent }      from './tree-select/tree-select.component';
export { MeeSkeletonComponent }        from './skeleton/skeleton.component';
export { MeeProgressBarComponent }     from './progress-bar/progress-bar.component';
export { MeeSpinnerComponent }         from './spinner/spinner.component';
export { MeeToastComponent }           from './toast/toast.component';
export { MeeToastService }             from './toast/toast.service';
export { MeeConfirmDialogComponent }   from './confirm-dialog/confirm-dialog.component';
export { MeeConfirmService }           from './confirm-dialog/confirm-dialog.component';
export { MeePasswordInputComponent }   from './password-input/password-input.component';
export { MeeTextareaComponent }        from './textarea/textarea.component';
export { MeeDrawerComponent }          from './drawer/drawer.component';
export { MeeMenuComponent }            from './menu/menu.component';
export { MeeMultiselectComponent }     from './multiselect/multiselect.component';
export type { MeeShowErrorOn }         from './multiselect/multiselect.component';

// Root bootstrap (PrimeNG providers + theme — sealed behind @mee/ui)
export { provideMeeUi }                from './providers';
export { MeeSellPreset }               from './theme';

// Types
export type { MeeMenuItem }                                              from './menu/menu.types';
export type { MeeButtonVariant, MeeButtonSize }                         from './button/button.types';
export type { MeeSelectOption }                                          from './select/select.types';
export type { MeeColumn, MeeTablePageEvent, MeeTableSortEvent }         from './table/table.types';
export type { MeeStep }                                                  from './steps/steps.types';
export type { MeeBadgeSeverity }                                         from './badge/badge.types';
export type { MeeSkeletonVariant }                                       from './skeleton/skeleton.types';
export type { MeeFileUploadEvent }                                       from './file-upload/file-upload.types';
export type { MeeTreeNode }                                              from './tree-select/tree-select.component';
export type { MeeConfirmConfig }                                         from './confirm-dialog/confirm-dialog.component';
export type { MeeIconName }                                              from './icon/icon.registry';

// Aggregators (for component imports — NOT providers)
// Use MEE_FORM / MEE_OVERLAY / etc. in a standalone component's imports:[].
// MeeToastService + MeeConfirmService are providers — they live in provideMeeUi().
export { MEE_FORM, MEE_OVERLAY, MEE_FEEDBACK, MEE_DATA, MEE_COMMON, MEE_FILE, MEE_UI_ALL } from './aggregators';

// Phase 7 — swap-proof seam (alt preset + alt icon registry + selector)
// These are additive exports — live defaults (MeeSellPreset, MEE_ICONS) remain unchanged.
export { MeeSellAltPreset } from './theme.alt';
export { MEE_ICONS_ALT }    from './icon/icon.registry.alt';
export { ActiveIcons }      from './icon/icon.selector';
