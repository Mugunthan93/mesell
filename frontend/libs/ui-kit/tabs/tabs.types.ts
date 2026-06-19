import type { MeeIconName } from '../icon/icon.registry';

/**
 * Header definition for a single tab within mee-tabs.
 * Content body is supplied via consumer-projected p-tabpanel elements.
 */
export interface MeeTab {
  /** Stable key matching the p-tabpanel [value] on the projected body. */
  value: string | number;
  /** Visible header label. */
  label: string;
  /** Optional semantic icon for the tab header. */
  icon?: MeeIconName;
  /** Disable the tab header (prevents selection). */
  disabled?: boolean;
}
