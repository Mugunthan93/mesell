/**
 * serve-static.mjs — Launch the 8 zero-dep static servers for the federated dist builds.
 *
 * Memory-safe alternative to `pnpm run start:all`. Each server is the existing
 * `tools/boot-smoke/serve.js` (a zero-dep Node http server with SPA fallback + CORS,
 * ~15 MB RSS). Eight of them together hold ~147 MB steady state — versus 3–5 GB for eight
 * concurrent `ng serve` watchers, which hang an 8 GB machine. See tools/dev/STATIC_DEV.md.
 *
 * Prerequisite: the apps must already be built — run `pnpm run dev:build-static` first.
 * This script fails fast with a helpful message if any `dist/<app>/browser/index.html`
 * is missing.
 *
 * Usage (from any directory; run resolves to frontend/):
 *   node tools/dev/serve-static.mjs        # serve all 8 on 4200–4207
 *   pnpm run dev:serve-static              # preferred (package.json)
 *
 * Exit behaviour:
 *   Ctrl-C (SIGINT) / SIGTERM   → SIGTERM all 8, then SIGKILL after 3s, exit 0.
 *   Any child exits non-zero    → prints which one died, kills the rest, exits 1.
 *   Missing dist for any app    → prints the fix, exits 1 (nothing started).
 *
 * Dependencies: ZERO. Node built-ins only. Do NOT add npm packages here.
 */

import { spawn } from 'node:child_process';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync } from 'node:fs';
import process from 'node:process';

// ─── ANSI colour codes (no chalk — zero deps) ────────────────────────────────

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const DIM    = '\x1b[2m';
const RED    = '\x1b[31m';
const GREEN  = '\x1b[32m';
const YELLOW = '\x1b[33m';
const CYAN   = '\x1b[36m';
const WHITE  = '\x1b[37m';

// One colour per server (matches start-all.mjs SORTED-CANONICAL ordering).
const LABEL_COLOURS = [
  '\x1b[96m',  // bright cyan    — shell (frontend)
  '\x1b[97m',  // bright white   — mfe-auth
  '\x1b[33m',  // yellow         — mfe-billing
  '\x1b[91m',  // bright red     — mfe-catalog
  '\x1b[94m',  // bright blue    — mfe-dashboard
  '\x1b[95m',  // bright magenta — mfe-export
  '\x1b[92m',  // bright green   — mfe-onboarding
  '\x1b[93m',  // bright yellow  — mfe-pricing
];

// ─── Server definitions — port map MUST match federation.manifest.json ────────
// SORTED-CANONICAL (alphabetical by remote name) — identical to angular.json
// serve ports, the committed federation.manifest.json, and meesell_env.py slot-0.
// 'frontend' is the shell project (angular.json) and serves on :4200.

const SERVERS = [
  { label: 'shell',          app: 'frontend',       port: 4200 },
  { label: 'mfe-auth',       app: 'mfe-auth',       port: 4201 },
  { label: 'mfe-billing',    app: 'mfe-billing',    port: 4202 },
  { label: 'mfe-catalog',    app: 'mfe-catalog',    port: 4203 },
  { label: 'mfe-dashboard',  app: 'mfe-dashboard',  port: 4204 },
  { label: 'mfe-export',     app: 'mfe-export',     port: 4205 },
  { label: 'mfe-onboarding', app: 'mfe-onboarding', port: 4206 },
  { label: 'mfe-pricing',    app: 'mfe-pricing',    port: 4207 },
];

// ─── Working directory: two levels up from this file = frontend/ ─────────────

const __filename = fileURLToPath(import.meta.url);
const __dirname  = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..', '..');
const SERVE_JS     = join(FRONTEND_DIR, 'tools', 'boot-smoke', 'serve.js');

// ─── Pre-flight: every app must have a built browser/index.html ──────────────

function distFor(app) {
  return join('dist', app, 'browser');           // relative to FRONTEND_DIR (serve.js cwd)
}

function preflight() {
  const missing = SERVERS.filter((s) => !existsSync(join(FRONTEND_DIR, distFor(s.app), 'index.html')));
  if (missing.length) {
    console.error(`\n${BOLD}${RED}  serve-static: ${missing.length} app(s) not built:${RESET}`);
    for (const m of missing) console.error(`${RED}    - ${m.app}${RESET} ${DIM}(missing ${distFor(m.app)}/index.html)${RESET}`);
    console.error(`\n${YELLOW}  Build them first:${RESET}`);
    console.error(`${BOLD}    pnpm run dev:build-static${RESET}` +
      (missing.length < SERVERS.length ? `  ${DIM}(or: pnpm run dev:build-static ${missing.map((m) => m.app).join(' ')})${RESET}` : ''));
    console.error('');
    process.exit(1);
  }
}

// ─── Banner ─────────────────────────────────────────────────────────────────

function printBanner() {
  const line = '─'.repeat(66);
  console.log(`\n${BOLD}${CYAN}${line}${RESET}`);
  console.log(`${BOLD}${WHITE}  MeeSell — Static Dev Serve (8 zero-dep servers, ~147 MB total)${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}`);
  console.log(`\n${BOLD}${YELLOW}  PORT MAP${RESET}`);
  for (const s of SERVERS) {
    console.log(`${GREEN}    ${s.port}${RESET}  ${s.label}${s.label === 'shell' ? ' (host application)' : ''}`);
  }
  console.log(`\n${DIM}  Serving built dist/<app>/browser. Open http://localhost:4200${RESET}`);
  console.log(`${DIM}  Ctrl-C stops all 7 servers cleanly.${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
}

// ─── Per-line prefix helper (matches start-all.mjs) ──────────────────────────

function makeLineWriter(label, colour, targetStream) {
  let buf = '';
  return (chunk) => {
    buf += chunk.toString();
    let nl;
    while ((nl = buf.indexOf('\n')) !== -1) {
      const line = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      if (line.length > 0) targetStream.write(`${colour}[${label}]${RESET} ${line}\n`);
    }
  };
}

// ─── Teardown ─────────────────────────────────────────────────────────────────

let tearing = false;

function teardown(children, exitCode) {
  if (tearing) return;
  tearing = true;
  console.log(`\n${BOLD}${YELLOW}[serve-static]${RESET} Stopping all static servers…`);
  for (const { proc, label } of children) {
    try { proc.kill('SIGTERM'); } catch (_) { /* already dead */ }
    console.log(`${DIM}[serve-static] sent SIGTERM to [${label}]${RESET}`);
  }
  setTimeout(() => {
    for (const { proc } of children) {
      try { proc.kill('SIGKILL'); } catch (_) { /* already dead */ }
    }
    process.exit(exitCode);
  }, 3000).unref();
}

// ─── Main ─────────────────────────────────────────────────────────────────────

preflight();
printBanner();

const children = [];

for (let i = 0; i < SERVERS.length; i++) {
  const { label, app, port } = SERVERS[i];
  const colour = LABEL_COLOURS[i % LABEL_COLOURS.length];

  const proc = spawn('node', [SERVE_JS, distFor(app), String(port)], {
    cwd:   FRONTEND_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    env:   process.env,
  });

  proc.stdout.on('data', makeLineWriter(label, colour, process.stdout));
  proc.stderr.on('data', makeLineWriter(label, colour, process.stderr));

  proc.on('error', (err) => {
    process.stderr.write(`${RED}[serve-static] FATAL: failed to spawn [${label}]: ${err.message}${RESET}\n`);
    teardown(children, 1);
  });

  proc.on('exit', (code, signal) => {
    if (tearing) return;
    if (code !== 0 && code !== null) {
      process.stderr.write(
        `${RED}[serve-static] ERROR: [${label}] exited with code ${code} ` +
        `(port ${port} in use?). Tearing down.${RESET}\n`
      );
      teardown(children, 1);
    }
  });

  children.push({ label, proc });
  console.log(`${colour}[serve-static]${RESET} Spawned ${BOLD}[${label}]${RESET} → :${port}  ${DIM}(${distFor(app)})${RESET}`);
}

console.log(`\n${DIM}[serve-static] All 8 servers spawned. Open http://localhost:4200${RESET}\n`);

process.on('SIGINT',  () => teardown(children, 0));
process.on('SIGTERM', () => teardown(children, 0));
