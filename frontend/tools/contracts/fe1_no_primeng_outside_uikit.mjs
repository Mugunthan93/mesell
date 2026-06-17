/**
 * fe1_no_primeng_outside_uikit.mjs — Contract FE-1
 *
 * Rule: no PrimeNG / PrimeUIX ES import outside frontend/libs/ui-kit/.
 *
 * Scan set: .ts + .html files under apps/**, libs/**, src/** (if present).
 * INCLUDES *.spec.ts — specs must also obey the seal.
 *
 * Allow-list: anything under libs/ui-kit/ is exempt (the sealed boundary).
 *
 * federation.config.js files are NOT scanned (only .ts/.html) — this is the
 * critical false-positive guard: 7 federation.config.js files reference
 * 'primeng' / '@primeuix' as share-config strings and a comment, NOT as imports.
 *
 * Match logic: line-based, real import forms only:
 *   - import ... from 'primeng/...' or '@primeuix/...'
 *   - import 'primeng/...' or '@primeuix/...'
 *   - dynamic import('primeng/...') or import('@primeuix/...')
 *   - require('primeng/...') or require('@primeuix/...')
 * The module specifier must appear inside quotes immediately after the keyword.
 * A comment mentioning 'primeng' is NOT flagged.
 *
 * Phase-0 expectation: 0 violations (seal already clean, PR #38).
 */

import { join } from 'node:path';
import { feRoot, walk, rel, readLines } from './_walk.mjs';

const CONTRACT = 'FE-1';
const DESCRIPTION = 'No PrimeNG/@primeuix import outside libs/ui-kit/';

// Real import forms — the specifier must start with primeng or @primeuix inside quotes.
// We test each line individually so multi-line imports require the specifier on one line
// (which is always true for `from '...'` and `import(...)` / `require(...)`).
const IMPORT_RE = /(?:import\s+[^'"]*from\s*|import\s*\(?\s*|require\s*\(\s*)(['"])(@primeuix|primeng)(?:\/[^'"]*)?(?:\1|\2)/;

/**
 * scan(opts?) → { contract, description, violations }
 * Each violation: { file, line, snippet, reason }
 */
export function scan(_opts = {}) {
  const root = feRoot();
  const allowPrefix = join(root, 'libs', 'ui-kit') + '/';

  const dirs = [
    join(root, 'apps'),
    join(root, 'libs'),
    join(root, 'src'),   // may not exist post-relocation — walk() tolerates absence
  ];

  const violations = [];

  for (const dir of dirs) {
    const files = walk(dir, { exts: ['.ts', '.html'] });
    for (const absFile of files) {
      // Allow-list: libs/ui-kit/** is the sealed boundary
      if (absFile.startsWith(allowPrefix)) continue;

      const lines = readLines(absFile);
      for (let i = 0; i < lines.length; i++) {
        const lineText = lines[i];
        if (IMPORT_RE.test(lineText)) {
          violations.push({
            file: rel(absFile),
            line: i + 1,
            snippet: lineText.trim().slice(0, 120),
            reason: `${CONTRACT}: PrimeNG/@primeuix may only be imported inside libs/ui-kit/.`,
          });
        }
      }
    }
  }

  return { contract: CONTRACT, description: DESCRIPTION, violations };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('fe1_no_primeng_outside_uikit.mjs')) {
  const { violations } = scan();
  if (violations.length === 0) {
    console.log(`${CONTRACT}: 0 violations — seal clean.`);
  } else {
    for (const v of violations) {
      console.log(`${v.file}:${v.line}: ${v.snippet}`);
      console.log(`  → ${v.reason}`);
    }
    console.log(`\n${CONTRACT}: ${violations.length} violation(s).`);
  }
}
