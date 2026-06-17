#!/usr/bin/env node
/**
 * run-all.mjs — FE contract scanner orchestrator
 *
 * Runs the 5 frontend design-system boundary contracts and prints a per-contract
 * report. Mirrors the backend `check_*.py` + Gate 3 pattern (BACKEND_ARCHITECTURE.md §16.E).
 *
 * Usage (from frontend/):
 *   node tools/contracts/run-all.mjs              # warn-only, exits 0 always
 *   node tools/contracts/run-all.mjs --strict      # exits 1 if ANY violation exists
 *   node tools/contracts/run-all.mjs --strict=fe2,fe3  # exits 1 if FE-2 or FE-3 has violations
 *
 * Warn → strict roadmap:
 *   Phase 0: warn-only DEFAULT (CI runs without --strict).
 *   Phase 1: CI flips --strict=fe2 after icon migration.
 *   Phase 4: CI flips --strict=fe2,fe3 after chrome primitives land.
 *   Phase 5 (ACTIVE): CI flips --strict (ALL 5) and the FE Gate job becomes a
 *     REQUIRED status check on develop (founder wires it in branch protection).
 *     A violation of any of FE-1..FE-5 fails the gate and blocks merge.
 */

import { scan as fe1 } from './fe1_no_primeng_outside_uikit.mjs';
import { scan as fe2 } from './fe2_no_raw_pi_icons.mjs';
import { scan as fe3 } from './fe3_chrome_shell_only.mjs';
import { scan as fe4 } from './fe4_lib_dag.mjs';
import { scan as fe5 } from './fe5_public_barrels_only.mjs';

// ── Parse CLI flags ────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
let strictAll = false;
let strictContracts = new Set(); // populated when --strict=fe2,fe3 form is used

for (const arg of args) {
  if (arg === '--strict') {
    strictAll = true;
  } else if (arg.startsWith('--strict=')) {
    const ids = arg.slice('--strict='.length).split(',').map(s => s.trim().toLowerCase());
    for (const id of ids) strictContracts.add(id);
  }
}

const isStrictMode = strictAll || strictContracts.size > 0;

// ── Run all scanners ───────────────────────────────────────────────────────────
console.log('');
console.log('='.repeat(70));
console.log('  MeeSell FE Contract Scanners — Phase 5 (UI Design-System Decoupling — sealed)');
console.log('='.repeat(70));
console.log('');

const start = Date.now();

const results = [
  fe1(),
  fe2(),
  fe3(),
  fe4(),
  fe5(),
];

const elapsed = ((Date.now() - start) / 1000).toFixed(2);

// ── Print per-contract report ──────────────────────────────────────────────────
for (const result of results) {
  const { contract, description, violations } = result;
  const status = violations.length === 0 ? 'CLEAN' : 'WARN';
  const statusTag = violations.length === 0 ? '[CLEAN]' : `[WARN  ${violations.length} violation(s)]`;

  console.log(`── ${contract}: ${description}`);
  console.log(`   ${statusTag}`);

  if (violations.length > 0) {
    // Cap output at 50 lines per contract to avoid log flooding
    const shown = violations.slice(0, 50);
    for (const v of shown) {
      console.log(`   ${v.file}:${v.line}: ${v.snippet}`);
      console.log(`     → ${v.reason}`);
    }
    if (violations.length > 50) {
      console.log(`   ... and ${violations.length - 50} more (run scanner standalone to see all)`);
    }
  }
  console.log('');
}

// ── Summary table ──────────────────────────────────────────────────────────────
console.log('='.repeat(70));
console.log('  Summary');
console.log('='.repeat(70));
const totalViolations = results.reduce((sum, r) => sum + r.violations.length, 0);
for (const { contract, violations } of results) {
  const bar = violations.length === 0 ? 'OK ' : `${violations.length} warning(s)`;
  console.log(`  ${contract.padEnd(6)} → ${bar}`);
}
console.log('');
console.log(`  Total: ${totalViolations} warning(s) across ${results.length} contracts`);
console.log(`  Elapsed: ${elapsed}s`);
console.log('');

// ── Exit code logic ────────────────────────────────────────────────────────────
if (!isStrictMode) {
  // Warn-only default (no --strict flag): always exit 0 regardless of violations.
  console.log('WARN-ONLY MODE: violations reported, pipeline not failed.');
  console.log('Use --strict or --strict=<fe-id,...> to enable strict enforcement.');
  console.log('');
  process.exit(0);
}

// Strict mode: check which contracts have violations
let hasStrictViolation = false;

if (strictAll) {
  // --strict: fail if ANY contract has violations
  hasStrictViolation = totalViolations > 0;
} else {
  // --strict=fe2,fe3 comma-list: fail only if a listed contract has violations
  for (const { contract, violations } of results) {
    const contractId = contract.toLowerCase().replace('-', ''); // 'FE-2' → 'fe2'
    if (strictContracts.has(contractId) && violations.length > 0) {
      hasStrictViolation = true;
      console.log(`STRICT: contract ${contract} has ${violations.length} violation(s) — exit 1.`);
    }
  }
}

if (hasStrictViolation) {
  if (strictAll) {
    console.log(`STRICT MODE: ${totalViolations} total violation(s) — exit 1.`);
  }
  process.exit(1);
} else {
  if (strictContracts.size > 0) {
    const ids = [...strictContracts].join(',');
    console.log(`STRICT (${ids}): targeted contracts are clean — exit 0.`);
  } else {
    console.log('STRICT MODE: all contracts clean — exit 0.');
  }
  process.exit(0);
}
