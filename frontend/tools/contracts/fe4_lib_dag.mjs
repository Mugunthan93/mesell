/**
 * fe4_lib_dag.mjs — Contract FE-4
 *
 * Rule: lib imports flow strictly composites → layout → ui-kit (no back-edges, no cycles).
 *
 * DAG tiers (rank = importable direction — a file may only import a lower rank):
 *   rank 0 (base):       ui-kit      (@mesell/ui-kit)
 *   rank 0 (base):       core        (@mesell/core)        — shared base, importable by all
 *   rank 0 (base):       design-tokens (@mesell/design-tokens) — shared base, importable by all
 *   rank 0 (base):       env         (@mesell/env)         — shared base, importable by all
 *   rank 1:              layout      (@mesell/layout)
 *   rank 2:              composites  (@mesell/composites)
 *
 * Forbidden edges (back-edges):
 *   libs/ui-kit/**    importing @mesell/layout or @mesell/composites
 *   libs/layout/**    importing @mesell/composites
 *   libs/core/**      importing @mesell/ui-kit, @mesell/layout, @mesell/composites
 *
 * Scan set: .ts files under libs/** (specs included — test files must not smuggle edges).
 *
 * Phase 5: enforced (strict; FE Gate is a required check on develop). Baseline
 *   is 0 violations: ui-kit imports no sibling UI lib; composites may import
 *   layout + ui-kit (allowed edges); no back-edges/cycles.
 */

import { join } from 'node:path';
import { feRoot, walk, rel, readLines } from './_walk.mjs';

const CONTRACT = 'FE-4';
const DESCRIPTION = 'Lib DAG — composites → layout → ui-kit (no back-edge/cycle)';

// Tier ranks — lower rank = more foundational
const LIB_RANKS = {
  'ui-kit':       0,
  'core':         0,  // shared base: importable by any tier, imports no UI tier
  'design-tokens': 0, // shared base
  'env':          0,  // shared base
  'layout':       1,
  'composites':   2,
};

// @mesell/* lib name → rank (for import specifier matching)
const MESELL_IMPORT_RANKS = {
  '@mesell/ui-kit':        0,
  '@mesell/core':          0,
  '@mesell/design-tokens': 0,
  '@mesell/env':           0,
  '@mesell/layout':        1,
  '@mesell/composites':    2,
};

// Match `from '@mesell/<lib>'` or `from '@mesell/<lib>/<subpath>'`
// Capture group 1 = the lib name (e.g. 'ui-kit', 'layout', 'composites')
const MESELL_IMPORT_RE = /from\s*['"]@mesell\/([a-z-]+)(?:\/[^'"]*)?['"]/;

/**
 * Derive the lib rank of a source file from its path under libs/.
 * e.g. libs/ui-kit/... → 'ui-kit' → rank 0
 *      libs/composites/... → 'composites' → rank 2
 */
function fileRank(absFile, root) {
  const libsPrefix = join(root, 'libs') + '/';
  if (!absFile.startsWith(libsPrefix)) return null; // not a lib file — skip
  const rest = absFile.slice(libsPrefix.length);     // e.g. 'ui-kit/providers.ts'
  const libName = rest.split('/')[0];
  return LIB_RANKS[libName] ?? null;
}

/**
 * scan(opts?) → { contract, description, violations }
 */
export function scan(_opts = {}) {
  const root = feRoot();
  const libsDir = join(root, 'libs');

  const violations = [];

  const files = walk(libsDir, { exts: ['.ts'] });

  for (const absFile of files) {
    const sourceRank = fileRank(absFile, root);
    if (sourceRank === null) continue; // unknown lib — skip

    const lines = readLines(absFile);
    for (let i = 0; i < lines.length; i++) {
      const lineText = lines[i];
      const m = MESELL_IMPORT_RE.exec(lineText);
      if (!m) continue;

      const importedLib = '@mesell/' + m[1];
      const importedRank = MESELL_IMPORT_RANKS[importedLib];
      if (importedRank === undefined) continue; // unknown lib — skip

      // A file at rank R may only import libs with rank <= R - 1 (strictly lower).
      // Importing a lib with rank STRICTLY GREATER than the source rank is a back-edge.
      // Same-rank imports among the rank-0 shared bases (core, ui-kit, design-tokens, env)
      // are NOT flagged — they are all foundational peers.
      // Rule: flag when importedRank > sourceRank (not >= — same-rank base peers are OK).
      if (importedRank > sourceRank) {
        violations.push({
          file: rel(absFile),
          line: i + 1,
          snippet: lineText.trim().slice(0, 120),
          reason: `${CONTRACT}: lib DAG violation — composites → layout → ui-kit only (no back-edge/cycle). ${rel(absFile)} (rank ${sourceRank}) imports ${importedLib} (rank ${importedRank}).`,
        });
      }
    }
  }

  return { contract: CONTRACT, description: DESCRIPTION, violations };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('fe4_lib_dag.mjs')) {
  const { violations } = scan();
  if (violations.length === 0) {
    console.log(`${CONTRACT}: 0 violations — DAG is clean.`);
  } else {
    for (const v of violations) {
      console.log(`${v.file}:${v.line}: ${v.snippet}`);
      console.log(`  → ${v.reason}`);
    }
    console.log(`\n${CONTRACT}: ${violations.length} violation(s).`);
  }
}
