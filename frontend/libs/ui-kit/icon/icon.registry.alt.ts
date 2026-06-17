/**
 * icon.registry.alt.ts — MeeSell alternate icon registry (Material Icons)
 *
 * Alt icon set using Material Icons ligature class strings.
 * Key-parity with MEE_ICONS in icon.registry.ts — every semantic name maps
 * to a Material Icons equivalent.
 *
 * CRITICAL: This file MUST NOT contain any `pi pi-` string (FE-2 contract).
 * The FE-2 scanner allows ONLY libs/ui-kit/icon/icon.registry.ts to hold raw
 * PrimeIcons classes.
 *
 * SWAP NOTE: to activate this icon set, edit icon.selector.ts:
 *   export const ActiveIcons = MEE_ICONS;
 *   →
 *   export const ActiveIcons = MEE_ICONS_ALT;
 * (and swap the import). See SWAP_GUIDE.md for the full procedure.
 *
 * Material Icons usage: render as
 *   <span class="material-icons mi-<name>" aria-hidden="true">icon_ligature</span>
 * The class strings here are compatible with the Material Icons web font approach.
 */

import type { MeeIconName } from './icon.registry';

export const MEE_ICONS_ALT = {
  // Navigation / chrome (grouped sidebar)
  dashboard:  'material-icons mi-dashboard',        // overview grid
  catalog:    'material-icons mi-inventory_2',       // product box / catalog
  add:        'material-icons mi-add',               // new catalog CTA + page-header.cta "add"
  browse:     'material-icons mi-account_tree',      // browse categories (tree / sitemap)
  user:       'material-icons mi-person',            // profile nav + user menu
  logout:     'material-icons mi-logout',            // log out
  menu:       'material-icons mi-menu',              // hamburger

  // mee-button.icon semantic names
  sparkles:   'material-icons mi-auto_awesome',      // AI / autofill sparkle
  forward:    'material-icons mi-arrow_forward',     // next / forward
  back:       'material-icons mi-arrow_back',        // previous / back
  check:      'material-icons mi-check',             // confirm / done
  close:      'material-icons mi-close',             // dismiss / cancel
  delete:     'material-icons mi-delete',            // delete / remove
  send:       'material-icons mi-send',              // submit / send (smart-picker)

  // Internal ui-kit use
  warning:    'material-icons mi-warning',           // confirm-dialog warning icon
} satisfies Record<MeeIconName, string>;
