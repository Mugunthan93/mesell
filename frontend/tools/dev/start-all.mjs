/**
 * start-all.mjs — One-command dev boot for all 7 Native Federation servers.
 *
 * Spawns the 7 pnpm scripts that are already defined in frontend/package.json.
 * Ports are sourced from angular.json via those scripts — nothing is hardcoded here.
 *
 * Usage (from any directory):
 *   node tools/dev/start-all.mjs          (run from frontend/)
 *   pnpm run start:all                    (preferred — defined in package.json)
 *
 * Exit behaviour:
 *   Ctrl-C (SIGINT) or SIGTERM  → kills all 7 children, then exits 0.
 *   Any child exits non-zero    → prints which one died, kills the rest, exits 1.
 *
 * Dependencies: ZERO. Node built-ins only (node:child_process, node:process, node:path,
 * node:url). Do NOT add npm packages here.
 */

import { spawn } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
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

// One colour per server (cycles through the 7 bright colours).
const LABEL_COLOURS = [
  '\x1b[96m',  // bright cyan   — shell
  '\x1b[93m',  // bright yellow — mfe-pricing
  '\x1b[95m',  // bright magenta — mfe-export
  '\x1b[92m',  // bright green   — mfe-onboarding
  '\x1b[94m',  // bright blue    — mfe-dashboard
  '\x1b[91m',  // bright red     — mfe-catalog
  '\x1b[97m',  // bright white   — mfe-auth
];

// ─── Server definitions (reuse existing pnpm scripts) ────────────────────────

const SERVERS = [
  { label: 'shell',         script: 'start:shell'         },
  { label: 'mfe-pricing',   script: 'start:mfe-pricing'   },
  { label: 'mfe-export',    script: 'start:mfe-export'    },
  { label: 'mfe-onboarding',script: 'start:mfe-onboarding'},
  { label: 'mfe-dashboard', script: 'start:mfe-dashboard' },
  { label: 'mfe-catalog',   script: 'start:mfe-catalog'   },
  { label: 'mfe-auth',      script: 'start:mfe-auth'      },
];

// ─── Working directory: two levels up from this file = frontend/ ─────────────

const __filename = fileURLToPath(import.meta.url);
const __dirname  = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..', '..');

// ─── Startup banner ───────────────────────────────────────────────────────────

function printBanner() {
  const line = '─'.repeat(66);
  console.log(`\n${BOLD}${CYAN}${line}${RESET}`);
  console.log(`${BOLD}${WHITE}  MeeSell — Native Federation Dev Boot (FRONTEND ONLY)${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}`);

  console.log(`\n${BOLD}${YELLOW}  PORT MAP${RESET}`);
  console.log(`${GREEN}    4200${RESET}  shell        (host application)`);
  console.log(`${GREEN}    4201${RESET}  mfe-pricing`);
  console.log(`${GREEN}    4202${RESET}  mfe-export`);
  console.log(`${GREEN}    4203${RESET}  mfe-onboarding`);
  console.log(`${GREEN}    4204${RESET}  mfe-dashboard`);
  console.log(`${GREEN}    4205${RESET}  mfe-catalog`);
  console.log(`${GREEN}    4206${RESET}  mfe-auth`);

  console.log(`\n${BOLD}${YELLOW}  PREREQUISITES — still required for a working session:${RESET}`);
  console.log(`${RED}    (a)${RESET} Backend on ${BOLD}:8000${RESET}  (docker-compose or k3s)`);
  console.log(`${RED}    (b)${RESET} Dev proxy merged: PR #212 (${BOLD}frontend/proxy.conf.json${RESET} + angular.json proxyConfig)`);
  console.log(`${RED}    (c)${RESET} Real ${BOLD}MSG91_AUTH_KEY${RESET} in ${BOLD}backend/.env${RESET} (OTP is live-SMS-only — no test mode)`);

  console.log(`\n${DIM}  Ctrl-C kills all 7 servers cleanly.${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
}

// ─── Per-line prefix helper ───────────────────────────────────────────────────

function makeLineWriter(label, colour, targetStream) {
  let buf = '';
  return (chunk) => {
    buf += chunk.toString();
    let nl;
    while ((nl = buf.indexOf('\n')) !== -1) {
      const line = buf.slice(0, nl);
      buf = buf.slice(nl + 1);
      if (line.length > 0) {
        targetStream.write(`${colour}[${label}]${RESET} ${line}\n`);
      }
    }
  };
}

// ─── Teardown ─────────────────────────────────────────────────────────────────

let tearing = false;

function teardown(children, exitCode) {
  if (tearing) return;
  tearing = true;
  console.log(`\n${BOLD}${YELLOW}[start-all]${RESET} Stopping all dev servers…`);
  for (const { proc, label } of children) {
    if (!proc.exitCode === null && !proc.killed) {
      try {
        proc.kill('SIGTERM');
      } catch (_) {
        // already dead — fine
      }
    } else {
      try { proc.kill('SIGTERM'); } catch (_) { /* ignore */ }
    }
    console.log(`${DIM}[start-all] sent SIGTERM to [${label}]${RESET}`);
  }
  // Give them 3 s to die gracefully, then SIGKILL.
  setTimeout(() => {
    for (const { proc } of children) {
      try { proc.kill('SIGKILL'); } catch (_) { /* already dead */ }
    }
    process.exit(exitCode);
  }, 3000).unref();
}

// ─── Main ─────────────────────────────────────────────────────────────────────

printBanner();

const children = [];

for (let i = 0; i < SERVERS.length; i++) {
  const { label, script } = SERVERS[i];
  const colour = LABEL_COLOURS[i % LABEL_COLOURS.length];

  const proc = spawn('pnpm', ['run', script], {
    cwd:   FRONTEND_DIR,
    stdio: ['ignore', 'pipe', 'pipe'],
    // Pass through the inherited environment so ng CLI picks up PATH, NODE etc.
    env:   process.env,
  });

  const stdoutWriter = makeLineWriter(label, colour, process.stdout);
  const stderrWriter = makeLineWriter(label, colour, process.stderr);

  proc.stdout.on('data', stdoutWriter);
  proc.stderr.on('data', stderrWriter);

  proc.on('error', (err) => {
    process.stderr.write(
      `${RED}[start-all] FATAL: failed to spawn [${label}]: ${err.message}${RESET}\n`
    );
    teardown(children, 1);
  });

  proc.on('exit', (code, signal) => {
    if (tearing) return;  // we initiated the teardown — ignore cascading exits
    if (code !== 0 && code !== null) {
      process.stderr.write(
        `${RED}[start-all] ERROR: [${label}] exited with code ${code}. ` +
        `Tearing down remaining servers.${RESET}\n`
      );
      teardown(children, 1);
    } else if (signal && signal !== 'SIGTERM' && signal !== 'SIGKILL') {
      process.stderr.write(
        `${YELLOW}[start-all] WARN: [${label}] exited via signal ${signal}.${RESET}\n`
      );
    }
  });

  children.push({ label, proc });
  console.log(`${colour}[start-all]${RESET} Spawned ${BOLD}[${label}]${RESET} → pnpm run ${script}`);
}

console.log(`\n${DIM}[start-all] All 7 servers spawned. Waiting for output…${RESET}\n`);

// ─── Signal forwarding ────────────────────────────────────────────────────────

process.on('SIGINT',  () => teardown(children, 0));
process.on('SIGTERM', () => teardown(children, 0));
