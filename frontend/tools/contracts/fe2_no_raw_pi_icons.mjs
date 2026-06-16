/**
 * fe2_no_raw_pi_icons.mjs — Contract FE-2
 *
 * Rule: no raw `pi pi-*` icon class outside the icon registry file.
 *
 * Scan set: .ts + .html under apps/**, libs/**, src/**.
 * INCLUDES *.spec.ts.
 *
 * Allow-list (Phase 0):
 *   - libs/ui-kit/icon/icon.registry.ts (the one permitted file; may not exist yet
 *     in Phase 0 — allow-listed so Phase 1 needs no scanner edit).
 *   - ANY file under libs/ui-kit/ (Phase 0 broad allow — covers mee-button's
 *     MATERIAL_TO_PI map and any future ui-kit internal use).
 *     ↳ Phase 1 NARROWS this to just libs/ui-kit/icon/icon.registry.ts.
 *     ↳ See README §Phase-1-tighten for the exact constant to update.
 *
 * Match: the literal token sequence `pi pi-` followed by a word character.
 * Catches both TS template strings (icon: 'pi pi-home') and HTML class attrs
 * (<i class="pi pi-bars">). Regex: /pi\s+pi-[a-z]/
 *
 * Phase-0 expectation: 3 files warn (the known leaks committed before Phase 0):
 *   apps/shell/src/app/layouts/shell/shell.component.ts
 *   apps/shell/src/app/layouts/shell/shell.component.html
 *   apps/mfe-catalog/src/app/smart-picker/smart-picker.component.ts
 *
 * These are NOT fixed in Phase 0 — Phase 1 migrates them to MeeIconName semantics.
 */

import { join } from 'node:path';
import { feRoot, walk, rel, readLines } from './_walk.mjs';

const CONTRACT = 'FE-2';
const DESCRIPTION = "No raw 'pi pi-*' icon class outside libs/ui-kit/";

// Phase-0 allow prefix (the whole ui-kit tree).
// TODO(Phase 1): narrow to ALLOW_REGISTRY_FILE = 'libs/ui-kit/icon/icon.registry.ts'
const ALLOW_PREFIX_PHASE0 = 'libs/ui-kit/';

// Match `pi pi-` followed by at least one word character (letter, digit, or dash via [a-z])
const PI_RE = /pi\s+pi-[a-z]/;

/**
 * scan(opts?) → { contract, description, violations }
 * Each violation: { file, line, snippet, reason }
 */
export function scan(_opts = {}) {
  const root = feRoot();

  const dirs = [
    join(root, 'apps'),
    join(root, 'libs'),
    join(root, 'src'),
  ];

  const violations = [];

  for (const dir of dirs) {
    const files = walk(dir, { exts: ['.ts', '.html'] });
    for (const absFile of files) {
      const relPath = rel(absFile);

      // Phase-0 allow: entire libs/ui-kit/ tree
      if (relPath.startsWith(ALLOW_PREFIX_PHASE0)) continue;

      const lines = readLines(absFile);
      for (let i = 0; i < lines.length; i++) {
        const lineText = lines[i];
        if (PI_RE.test(lineText)) {
          violations.push({
            file: relPath,
            line: i + 1,
            snippet: lineText.trim().slice(0, 120),
            reason: `${CONTRACT}: raw 'pi pi-*' is only allowed in libs/ui-kit/icon/icon.registry.ts — use a MeeIconName semantic.`,
          });
        }
      }
    }
  }

  return { contract: CONTRACT, description: DESCRIPTION, violations };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('fe2_no_raw_pi_icons.mjs')) {
  const { violations } = scan();
  if (violations.length === 0) {
    console.log(`${CONTRACT}: 0 violations.`);
  } else {
    // Group by file for readability
    const byFile = new Map();
    for (const v of violations) {
      if (!byFile.has(v.file)) byFile.set(v.file, []);
      byFile.get(v.file).push(v);
    }
    for (const [file, viols] of byFile) {
      for (const v of viols) {
        console.log(`${file}:${v.line}: ${v.snippet}`);
        console.log(`  → ${v.reason}`);
      }
    }
    console.log(`\n${CONTRACT}: ${violations.length} violation(s) in ${byFile.size} file(s).`);
  }
}
