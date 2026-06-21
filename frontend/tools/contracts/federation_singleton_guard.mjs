#!/usr/bin/env node
/**
 * federation_singleton_guard.mjs — Federation auth-singleton config guard (FED-1)
 *
 * WHY THIS EXISTS
 * ---------------
 * `@mesell/core` owns AuthService and the IN-MEMORY access token. It MUST resolve to a
 * SINGLE shared instance across the shell + every Native Federation remote, or a remote
 * gets its own AuthService whose token is null → authGuard bounces the user to /login on
 * shell→remote navigation (the #328 "shell→remote logout" class).
 *
 * Native Federation 3.5.5 dedupes shared deps by the import-map key `packageName@version`
 * (see @softarc/native-federation-runtime getExternalKey()). For tsconfig-path-mapped libs
 * (`@mesell/*`), the emitted `version` is only populated when `features.mappingVersion: true`
 * is set on the remote AND the lib's package.json carries an explicit `version`. The
 * `...mesellShared` spread (singleton + the version pin) is INERT without `mappingVersion`.
 * (`requiredVersion`/`strictVersion` are NF-internal and dropped for path mappings; they do
 * NOT affect the version-keyed dedup — do not chase them.)
 *
 * The original drift (#328) and the mfe-billing regression both happened the same way: a new
 * remote's federation.config.js was authored WITHOUT the pin / WITHOUT mappingVersion, so its
 * remoteEntry.json emitted `@mesell/core version=''` → a distinct dedup key → a second
 * AuthService → logout. This guard makes that drift a CONFIG-REVIEW failure, before any build.
 *
 * WHAT IT CHECKS (source-level, zero build required)
 * --------------------------------------------------
 *   V1  shared.config.js pins every cross-boundary lib (singleton:true + a non-empty version)
 *       at one shared MESELL_SHARED_VERSION.
 *   V2  Every pinned @mesell/* lib has a package.json whose `version` === MESELL_SHARED_VERSION.
 *   V3  Every apps/<app>/federation.config.js (shell + all remotes) imports & spreads
 *       `...mesellShared` AFTER shareAll (so the pin wins).
 *   V4  Every apps/<app>/federation.config.js sets `features.mappingVersion: true` — the
 *       load-bearing flag that makes the version pin reach the emitted remoteEntry.json.
 *
 * Usage (from frontend/):
 *   node tools/contracts/federation_singleton_guard.mjs            # report, exit 1 on any violation
 *   import { scan } from './federation_singleton_guard.mjs'        # programmatic { contract, violations }
 */

import { readFileSync, existsSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';
import { feRoot, rel } from './_walk.mjs';

// `require` is not defined in an ESM module by default; create one bound to this file
// so we can load the CJS shared.config.js and read its actual exported values.
const require = createRequire(import.meta.url);

const CONTRACT = 'FED-1';
const DESCRIPTION = 'Federation @mesell/* shared-singleton config is uniform (mappingVersion + version pin on shell + every remote)';

/**
 * scan(opts?) → { contract, description, violations }
 * Each violation: { file, line, snippet, reason }
 */
export function scan(_opts = {}) {
  const root = feRoot();
  const violations = [];

  const push = (file, reason, snippet = '') =>
    violations.push({ file, line: 0, snippet: snippet.slice(0, 120), reason: `${CONTRACT}: ${reason}` });

  // ── V1: read the canonical shared.config.js ──────────────────────────────────
  const sharedConfigAbs = join(root, 'libs', 'federation', 'shared.config.js');
  if (!existsSync(sharedConfigAbs)) {
    push(rel(sharedConfigAbs), 'shared.config.js (the single source of truth for the @mesell/* pin) is MISSING.');
    return { contract: CONTRACT, description: DESCRIPTION, violations };
  }

  // Require the config in-process to read the actual values (it is a plain CJS module).
  let MESELL_SHARED_VERSION;
  let mesellShared;
  try {
    const mod = require(sharedConfigAbs);
    MESELL_SHARED_VERSION = mod.MESELL_SHARED_VERSION;
    mesellShared = mod.mesellShared;
  } catch (e) {
    push(rel(sharedConfigAbs), `shared.config.js failed to load: ${e.message}`);
    return { contract: CONTRACT, description: DESCRIPTION, violations };
  }

  if (!MESELL_SHARED_VERSION || typeof MESELL_SHARED_VERSION !== 'string') {
    push(rel(sharedConfigAbs), 'MESELL_SHARED_VERSION export missing or not a string.');
  }
  if (!mesellShared || typeof mesellShared !== 'object') {
    push(rel(sharedConfigAbs), 'mesellShared export missing or not an object.');
    return { contract: CONTRACT, description: DESCRIPTION, violations };
  }

  const pinnedLibs = Object.keys(mesellShared);
  if (pinnedLibs.length === 0) {
    push(rel(sharedConfigAbs), 'mesellShared is empty — at least @mesell/core must be pinned.');
  }
  if (!pinnedLibs.includes('@mesell/core')) {
    push(rel(sharedConfigAbs), '@mesell/core is NOT in mesellShared — the AuthService singleton pin is the load-bearing one.');
  }
  for (const lib of pinnedLibs) {
    const cfg = mesellShared[lib];
    if (!cfg || cfg.singleton !== true) {
      push(rel(sharedConfigAbs), `${lib} must be singleton:true.`);
    }
    if (!cfg || !cfg.version || cfg.version !== MESELL_SHARED_VERSION) {
      push(rel(sharedConfigAbs), `${lib} must pin version:'${MESELL_SHARED_VERSION}' (got ${JSON.stringify(cfg && cfg.version)}). version is the NF dedup key.`);
    }

    // ── V2: the lib's package.json version must match the pin (mappingVersion reads it). ──
    const libDirName = lib.replace('@mesell/', '');
    const pkgAbs = join(root, 'libs', libDirName, 'package.json');
    if (!existsSync(pkgAbs)) {
      push(rel(pkgAbs), `${lib} is pinned in mesellShared but libs/${libDirName}/package.json is MISSING — mappingVersion has no version to emit → remoteEntry version='' → singleton drift.`);
      continue;
    }
    let pkg;
    try {
      pkg = JSON.parse(readFileSync(pkgAbs, 'utf-8'));
    } catch (e) {
      push(rel(pkgAbs), `${lib} package.json failed to parse: ${e.message}`);
      continue;
    }
    if (!pkg.version || pkg.version !== MESELL_SHARED_VERSION) {
      push(rel(pkgAbs), `${lib} package.json version is ${JSON.stringify(pkg.version)} but must be '${MESELL_SHARED_VERSION}' (the value NF emits into remoteEntry via mappingVersion).`);
    }
  }

  // ── V3 + V4: every apps/<app>/federation.config.js spreads mesellShared + mappingVersion. ──
  const appsDir = join(root, 'apps');
  if (!existsSync(appsDir)) {
    push(rel(appsDir), 'apps/ directory missing — cannot validate per-app federation configs.');
    return { contract: CONTRACT, description: DESCRIPTION, violations };
  }

  const appNames = readdirSync(appsDir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  for (const app of appNames) {
    const cfgAbs = join(appsDir, app, 'federation.config.js');
    if (!existsSync(cfgAbs)) {
      // An app folder without a federation.config.js is not a federation participant — skip.
      continue;
    }
    const rawText = readFileSync(cfgAbs, 'utf-8');
    // Strip `//` line comments so a commented mention (e.g. the rationale comment that
    // literally says "mappingVersion: true") is never mistaken for a live setting.
    // Block comments (/* */) are not used for these settings in our configs.
    const text = rawText
      .split('\n')
      .map((line) => {
        const idx = line.indexOf('//');
        return idx === -1 ? line : line.slice(0, idx);
      })
      .join('\n');

    // V3: must require + spread mesellShared (the pin), after shareAll.
    const importsShared = /require\(\s*['"][^'"]*shared\.config['"]\s*\)/.test(text)
      && /mesellShared/.test(text);
    const spreadsShared = /\.\.\.\s*mesellShared/.test(text);
    if (!importsShared || !spreadsShared) {
      push(rel(cfgAbs), `${app}: federation.config.js must import and spread \`...mesellShared\` from libs/federation/shared.config.js so the @mesell/* version pin is applied.`);
    } else {
      // Ordering check: the ...mesellShared spread must come AFTER the shareAll(...) spread
      // (otherwise shareAll's strictVersion:false/version:auto would overwrite the pin).
      const shareAllIdx = text.indexOf('shareAll(');
      const pinIdx = text.search(/\.\.\.\s*mesellShared/);
      if (shareAllIdx !== -1 && pinIdx !== -1 && pinIdx < shareAllIdx) {
        push(rel(cfgAbs), `${app}: \`...mesellShared\` is spread BEFORE shareAll(...) — the pin must come AFTER shareAll so it wins.`);
      }
    }

    // V4: mappingVersion: true must be set (the load-bearing flag for path-mapped libs).
    const hasMappingVersion = /mappingVersion\s*:\s*true/.test(text);
    if (!hasMappingVersion) {
      push(rel(cfgAbs), `${app}: federation.config.js is missing \`features.mappingVersion: true\` — without it NF emits version='' for @mesell/* → the shareAll/mesellShared pin is INERT → shell→remote logout.`);
    }
  }

  return { contract: CONTRACT, description: DESCRIPTION, violations };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('federation_singleton_guard.mjs')) {
  const { violations } = scan();
  if (violations.length === 0) {
    console.log(`${CONTRACT}: 0 violations — @mesell/* federation singleton config is uniform across shell + all remotes.`);
    process.exit(0);
  }
  for (const v of violations) {
    console.log(`${v.file}: ${v.reason}`);
  }
  console.log(`\n${CONTRACT}: ${violations.length} violation(s) — federation singleton config drift detected.`);
  process.exit(1);
}
