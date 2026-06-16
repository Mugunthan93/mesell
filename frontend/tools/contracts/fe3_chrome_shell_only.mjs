/**
 * fe3_chrome_shell_only.mjs — Contract FE-3
 *
 * Rule: MFEs (apps/mfe-*) must not import shell chrome primitives or ShellComponent.
 *
 * Scan set: .ts files under apps/mfe-* directories ONLY.
 * The shell (apps/shell/**) is EXEMPT — it OWNS the chrome.
 *
 * Match — import specifiers referencing chrome (either by symbol name or path segment):
 *   Symbol names:  ShellComponent, MeeAppBarComponent, mee-app-bar,
 *                  MeeSideNavComponent, mee-side-nav,
 *                  MeeNavItemComponent, mee-nav-item,
 *                  MeeUserMenuComponent, mee-user-menu
 *   Path segments: /shell/shell.component, @mesell/layout/chrome
 *
 * These are forward-compat seeds (none exist yet in Phase 0) so Phase 4 needs
 * no scanner edit when chrome primitives land.
 *
 * Phase-0 expectation: 0 violations (no MFE imports chrome today).
 * Becomes load-bearing after Phase 4.
 */

import { readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';
import { feRoot, walk, rel, readLines } from './_walk.mjs';

const CONTRACT = 'FE-3';
const DESCRIPTION = 'Chrome primitives and ShellComponent are shell-only — MFEs must not import them';

// Chrome symbol names (current + Phase 4 seeds).
const CHROME_SYMBOLS = [
  'ShellComponent',
  'MeeAppBarComponent',
  'mee-app-bar',
  'MeeSideNavComponent',
  'mee-side-nav',
  'MeeNavItemComponent',
  'mee-nav-item',
  'MeeUserMenuComponent',
  'mee-user-menu',
];

// Chrome path segments (in import specifiers).
const CHROME_PATH_SEGMENTS = [
  '/shell/shell.component',
  '@mesell/layout/chrome',
];

// Build a single regex that matches any chrome symbol or path segment.
// Escape special regex chars in each pattern part.
function escapeRe(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
const CHROME_PATTERN = new RegExp(
  '(?:' +
  [...CHROME_SYMBOLS, ...CHROME_PATH_SEGMENTS].map(escapeRe).join('|') +
  ')'
);

/**
 * scan(opts?) → { contract, description, violations }
 */
export function scan(_opts = {}) {
  const root = feRoot();
  const appsDir = join(root, 'apps');

  const violations = [];

  // Enumerate mfe-* directories (exclude shell)
  let mfeDirs = [];
  try {
    mfeDirs = readdirSync(appsDir)
      .filter(name => name.startsWith('mfe-'))
      .map(name => join(appsDir, name))
      .filter(d => {
        try { return statSync(d).isDirectory(); } catch { return false; }
      });
  } catch {
    // apps/ doesn't exist — return clean
    return { contract: CONTRACT, description: DESCRIPTION, violations };
  }

  for (const mfeDir of mfeDirs) {
    const files = walk(mfeDir, { exts: ['.ts'] });
    for (const absFile of files) {
      const lines = readLines(absFile);
      for (let i = 0; i < lines.length; i++) {
        const lineText = lines[i];
        // Only check lines containing the word 'import' (static + dynamic forms)
        if (!lineText.includes('import')) continue;
        if (CHROME_PATTERN.test(lineText)) {
          violations.push({
            file: rel(absFile),
            line: i + 1,
            snippet: lineText.trim().slice(0, 120),
            reason: `${CONTRACT}: chrome primitives and ShellComponent are shell-only — MFEs must not import them.`,
          });
        }
      }
    }
  }

  return { contract: CONTRACT, description: DESCRIPTION, violations };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('fe3_chrome_shell_only.mjs')) {
  const { violations } = scan();
  if (violations.length === 0) {
    console.log(`${CONTRACT}: 0 violations — no MFE imports chrome.`);
  } else {
    for (const v of violations) {
      console.log(`${v.file}:${v.line}: ${v.snippet}`);
      console.log(`  → ${v.reason}`);
    }
    console.log(`\n${CONTRACT}: ${violations.length} violation(s).`);
  }
}
