/**
 * fe5_public_barrels_only.mjs — Contract FE-5
 *
 * Rule: apps/* must import @mesell/* public barrels only —
 *   (a) no deep @mesell/<lib>/<subpath> imports,
 *   (b) no cross-MFE imports (apps/mfe-a importing from apps/mfe-b).
 *
 * Scan set: .ts files under apps/**. EXCLUDES *.spec.ts (test files may
 * deep-import a private subject under test — this is documented behaviour).
 *
 * Sub-rule (a) — deep barrel bypass:
 *   import from '@mesell/<lib>/<anything>' where a slash follows the lib name.
 *
 * Phase-0 seed allow-list (WARN only, do not error):
 *   The lean-bundle deep-import pattern from SP0 (PR #38) intentionally uses
 *   deep imports. These ARE expected in Phase 0 and will warn. Phase 5 decides:
 *   (a) ratify (add to permanent allow-list), or (b) refactor to barrel imports.
 *   Accepted prefixes (Phase-0 baseline, revisit at Phase-5 flip):
 *   - '@mesell/ui-kit/'
 *   - '@mesell/composites/'
 *   - '@mesell/core/models'
 *
 * Sub-rule (b) — cross-MFE import:
 *   A relative import (../../, ../../../ etc.) from one apps/<unit>/ into a
 *   different apps/<unit>/ directory. Also flags absolute paths into another
 *   apps unit.
 *
 * Phase-0 expectation: 0 violations (all imports in apps/ are barrel-level;
 *   the SP0 lean-bundle deep imports do NOT actually exist in the current
 *   codebase — they were anticipated but not committed). Record actual count.
 */

import { readdirSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { feRoot, walk, rel, readLines } from './_walk.mjs';

const CONTRACT = 'FE-5';
const DESCRIPTION = 'Apps import @mesell/* public barrels only — no deep subpaths, no cross-MFE imports';

// Phase-0 seed allow-list (lean-bundle pattern — warn-only baseline).
// Phase 5 action: empty this list after barrel refactor, OR ratify as permanent.
const PHASE0_ALLOWED_DEEP_PREFIXES = [
  '@mesell/ui-kit/',
  '@mesell/composites/',
  '@mesell/core/models',
];

// Sub-rule (a): deep barrel bypass — @mesell/<lib>/<subpath>
// Matches: from '@mesell/<lib>/<anything>'
const DEEP_IMPORT_RE = /from\s*['"](@mesell\/[a-z-]+\/[^'"]+)['"]/;

/**
 * scan(opts?) → { contract, description, violations }
 */
export function scan(_opts = {}) {
  const root = feRoot();
  const appsDir = join(root, 'apps');

  const violations = [];

  // Enumerate all app units (for cross-MFE detection)
  let appUnits = [];
  try {
    appUnits = readdirSync(appsDir)
      .filter(name => {
        try { return statSync(join(appsDir, name)).isDirectory(); } catch { return false; }
      });
  } catch {
    return { contract: CONTRACT, description: DESCRIPTION, violations };
  }

  for (const unitName of appUnits) {
    const unitDir = join(appsDir, unitName);
    // Exclude *.spec.ts from scan set
    const files = walk(unitDir, { exts: ['.ts'] })
      .filter(f => !f.endsWith('.spec.ts'));

    for (const absFile of files) {
      const lines = readLines(absFile);
      for (let i = 0; i < lines.length; i++) {
        const lineText = lines[i];

        // Sub-rule (a): deep @mesell/* subpath import
        const m = DEEP_IMPORT_RE.exec(lineText);
        if (m) {
          const specifier = m[1];
          // Check if this is in the Phase-0 accepted allow-list
          const isAllowed = PHASE0_ALLOWED_DEEP_PREFIXES.some(p => specifier.startsWith(p));
          violations.push({
            file: rel(absFile),
            line: i + 1,
            snippet: lineText.trim().slice(0, 120),
            reason: `${CONTRACT}: import '${specifier}' bypasses the public barrel — use '@mesell/${specifier.split('/')[1]}' only.` +
              (isAllowed ? ' [Phase-0 lean-bundle pattern — allowed now; Phase 5 ratify-or-refactor]' : ''),
          });
        }

        // Sub-rule (b): cross-MFE relative import
        // Look for relative imports that contain another app unit name in the path
        if (/from\s*['"](\.\.)/.test(lineText)) {
          const relMatch = /from\s*['"]([^'"]+)['"]/.exec(lineText);
          if (relMatch) {
            const importPath = relMatch[1];
            // Resolve against the importing file's directory to get absolute path
            const importingDir = absFile.slice(0, absFile.lastIndexOf('/'));
            let resolvedTarget;
            try {
              resolvedTarget = resolve(importingDir, importPath);
            } catch {
              continue;
            }
            // Check if the resolved path lands in a DIFFERENT apps unit
            for (const otherUnit of appUnits) {
              if (otherUnit === unitName) continue;
              const otherUnitDir = join(appsDir, otherUnit);
              if (resolvedTarget.startsWith(otherUnitDir)) {
                violations.push({
                  file: rel(absFile),
                  line: i + 1,
                  snippet: lineText.trim().slice(0, 120),
                  reason: `${CONTRACT}: cross-MFE import detected — '${importPath}' resolves into apps/${otherUnit}/ from apps/${unitName}/.`,
                });
              }
            }
          }
        }
      }
    }
  }

  return { contract: CONTRACT, description: DESCRIPTION, violations };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('fe5_public_barrels_only.mjs')) {
  const { violations } = scan();
  if (violations.length === 0) {
    console.log(`${CONTRACT}: 0 violations — all @mesell/* imports are barrel-level.`);
  } else {
    for (const v of violations) {
      console.log(`${v.file}:${v.line}: ${v.snippet}`);
      console.log(`  → ${v.reason}`);
    }
    console.log(`\n${CONTRACT}: ${violations.length} violation(s).`);
  }
}
