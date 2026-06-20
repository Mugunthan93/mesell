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

  // Deep-link navigation
  'external-link': 'material-icons mi-open_in_new',  // My Live Listings sidebar nav

  // Shell / sidebar / topbar chrome (FE-2 migration — bottom-nav + grouped sidebar)
  home:        'material-icons mi-home',             // bottom-nav + sidebar "Home"
  list:        'material-icons mi-list',             // "Catalogs" / "My Catalogs"
  tag:         'material-icons mi-label',            // "Categories"
  calculator:  'material-icons mi-calculate',        // "Pricing"
  download:    'material-icons mi-download',         // "Export" + export-page download
  wallet:      'material-icons mi-account_balance_wallet', // "Plans" (billing — Wave 5 Razorpay)

  // Feature-page decorative icons (FE-2 migration — catalog-list + export states)
  image:        'material-icons mi-image',           // catalog-list card thumbnail
  spinner:      'material-icons mi-autorenew',        // export "Generating…" spinner
  'check-circle': 'material-icons mi-check_circle',  // export "ready" success mark
  'file-excel':  'material-icons mi-description',     // export "ready" XLSX file row
  'times-circle': 'material-icons mi-cancel',        // export "failed" error mark
  'file-export': 'material-icons mi-file_download',   // export "idle" empty-state icon

  // data-table
  'ellipsis-v': 'material-icons mi-more_vert',       // per-row kebab actions trigger

  // Stat-card / empty-state semantic icons (B01 fix — replacing raw Material Symbols tokens)
  'edit-note':    'material-icons mi-edit_note',        // stat-card "Draft"
  'inventory':    'material-icons mi-inventory_2',      // empty-state / stat-card "No catalogs"
  'cloud-off':    'material-icons mi-cloud_off',        // remote-failure empty-state
  'image-off':    'material-icons mi-image_not_supported', // image-uploader feature-disabled
  'category':     'material-icons mi-account_tree',     // category-related empty states
  'link':         'material-icons mi-link',             // link/external reference empty states
  'trending-up':  'material-icons mi-trending_up',      // stat-card positive trend
  'trending-down':'material-icons mi-trending_down',    // stat-card negative trend
} satisfies Record<MeeIconName, string>;
