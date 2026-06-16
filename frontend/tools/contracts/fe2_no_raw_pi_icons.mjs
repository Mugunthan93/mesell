/**
 * fe2_no_raw_pi_icons.mjs — Contract FE-2
 *
 * Rule: no raw icon class string (the `pi pi-*` PrimeIcons convention) outside the
 * icon registry file.
 *
 * Scan set: .ts + .html under apps/**, libs/**, src/**.
 * INCLUDES *.spec.ts.
 *
 * Allow-list (Phase 1):
 *   - EXACTLY libs/ui-kit/icon/icon.registry.ts (the sole permitted raw-icon file).
 *     All other files must use MeeIconName semantic names + resolveIcon().
 *   ↳ Phase 0 used a broad allow for the whole libs/ui-kit/ tree; Phase 1 narrows it.
 *
 * Match: the literal token sequence `pi pi-` followed by a word character.
 * Catches both TS template strings (icon: 'pi pi-home') and HTML class attrs
 * (<i class="pi pi-bars">). Regex: /pi\s+pi-[a-z]/
 *
 * Phase-1 expectation: 0 violations (icon registry is the sole raw-icon file;
 * all former leaks migrated to MeeIconName in shell, smart-picker, and ui-kit).
 */

import { join } from 'node:path';
import { feRoot, walk, rel, readLines } from './_walk.mjs';

const CONTRACT = 'FE-2';
const DESCRIPTION = "No raw 'pi pi-*' icon class outside libs/ui-kit/icon/icon.registry.ts";

// Phase 1: allow ONLY the exact registry file (narrowed from Phase-0 broad ui-kit prefix).
const ALLOW_REGISTRY_FILE = 'libs/ui-kit/icon/icon.registry.ts';

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

      // Phase 1 allow: only the exact registry file
      if (relPath === ALLOW_REGISTRY_FILE) continue;

      const lines = readLines(absFile);
      for (let i = 0; i < lines.length; i++) {
        const lineText = lines[i];
        if (PI_RE.test(lineText)) {
          violations.push({
            file: relPath,
            line: i + 1,
            snippet: lineText.trim().slice(0, 120),
            reason: `${CONTRACT}: raw icon class is only allowed in ${ALLOW_REGISTRY_FILE} — use a MeeIconName semantic.`,
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
