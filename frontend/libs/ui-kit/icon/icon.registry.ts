/**
 * icon.registry.ts — MeeSell icon registry
 *
 * This is the ONLY file permitted to contain raw `pi pi-` classes (FE-2 allow-list).
 * Swap the icon set by editing the right-hand values here.
 *
 * All other files reference icons by their MeeIconName semantic key and call resolveIcon().
 */

// ── Navigation / chrome (shell navItems, userMenu, hamburger) ──
// ── mee-button.icon (folded from MATERIAL_TO_PI + the unmapped 'add' + raw send) ──
// ── Internal ui-kit use ──

export const MEE_ICONS = {
  // Navigation / chrome (grouped sidebar — sidebar-grouping PR icons)
  dashboard:  'pi pi-th-large',         // shell navGroups Dashboard (th-large = overview grid)
  catalog:    'pi pi-box',              // shell navGroups "All Catalogs"
  add:        'pi pi-plus',             // shell "New Catalog" CTA + page-header.cta "add"
  browse:     'pi pi-sitemap',          // shell navGroups "Browse Categories"
  user:       'pi pi-user',             // shell Profile nav + userMenu "My Profile"
  logout:     'pi pi-sign-out',         // shell userMenu "Log out"
  menu:       'pi pi-bars',             // shell hamburger

  // mee-button.icon semantic names (folded from MATERIAL_TO_PI)
  sparkles:   'pi pi-sparkles',         // was MATERIAL_TO_PI['auto_awesome']
  forward:    'pi pi-arrow-right',      // was MATERIAL_TO_PI['arrow_forward']
  back:       'pi pi-arrow-left',       // was MATERIAL_TO_PI['arrow_back']
  check:      'pi pi-check',            // was MATERIAL_TO_PI['check']
  close:      'pi pi-times',            // was MATERIAL_TO_PI['close']
  delete:     'pi pi-trash',            // was MATERIAL_TO_PI['delete']
  send:       'pi pi-send',             // was raw 'pi pi-send' (smart-picker)

  // Internal ui-kit use
  warning:    'pi pi-exclamation-triangle', // confirm-dialog ConfirmationService icon

  // Deep-link navigation
  'external-link': 'pi pi-external-link',  // My Live Listings sidebar nav (live Meesho links)
} as const;

export type MeeIconName = keyof typeof MEE_ICONS;

/**
 * Resolve a semantic MeeIconName to its PrimeIcons CSS class string.
 * Used by mee-icon, mee-button, mee-menu, and confirm-dialog.
 */
export function resolveIcon(name: MeeIconName): string {
  return MEE_ICONS[name];
}
