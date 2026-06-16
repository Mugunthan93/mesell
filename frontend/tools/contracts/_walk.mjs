/**
 * _walk.mjs — shared recursive directory walker + utilities for FE contract scanners.
 *
 * Zero dependencies: node:fs + node:path only.
 * Used by all 5 contract scanners (fe1–fe5) so the walk logic lives in one place.
 *
 * CWD assumption: scanners are invoked from `frontend/` but this module computes
 * REPO_FE from its own import.meta.url so it works regardless of CWD.
 */

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

// ── Directory pruning (never descend into these) ──────────────────────────────
const PRUNE_DIRS = new Set([
  'node_modules',
  'dist',
  'out-tsc',
  '.angular',
  '.git',
  'coverage',
]);

/**
 * feRoot() → absolute path to `frontend/` (two levels up from tools/contracts/).
 * tools/contracts/_walk.mjs → tools/contracts/ → tools/ → frontend/
 */
export function feRoot() {
  const thisFile = fileURLToPath(import.meta.url);        // .../frontend/tools/contracts/_walk.mjs
  const toolsContracts = resolve(thisFile, '..', '..');   // .../frontend/tools/
  const tools = resolve(toolsContracts, '..');             // .../frontend/
  return tools;
}

/**
 * rel(absPath) → path relative to frontend/ with POSIX separators.
 * Stable cross-platform output for consistent CI log lines.
 */
export function rel(absPath) {
  const root = feRoot();
  return relative(root, absPath).split(sep).join('/');
}

/**
 * readLines(absPath) → string[] (one entry per source line, no trailing newline issues).
 */
export function readLines(absPath) {
  return readFileSync(absPath, 'utf8').split('\n');
}

/**
 * walk(absDir, { exts }) → string[] of absolute paths matching any of `exts`.
 *
 * Prunes: node_modules, dist, out-tsc, .angular, .git, coverage.
 * `exts` must include the leading dot, e.g. ['.ts', '.html'].
 *
 * @param {string} absDir
 * @param {{ exts: string[] }} opts
 * @returns {string[]}
 */
export function walk(absDir, { exts }) {
  const results = [];
  _walkDir(absDir, exts, results);
  return results;
}

function _walkDir(dir, exts, results) {
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    // Directory may not exist (e.g. frontend/src/ after relocation) — skip silently.
    return;
  }

  for (const name of entries) {
    if (PRUNE_DIRS.has(name)) continue;

    const full = join(dir, name);
    let stat;
    try {
      stat = statSync(full);
    } catch {
      continue;
    }

    if (stat.isDirectory()) {
      _walkDir(full, exts, results);
    } else if (stat.isFile()) {
      const ext = name.slice(name.lastIndexOf('.'));
      if (exts.includes(ext)) {
        results.push(full);
      }
    }
  }
}
