/**
 * dev-static.mjs — Orchestrator for the memory-safe static dev loop (low-RAM machines).
 *
 * Wraps the three building blocks so the founder has one entry point:
 *   build-static.mjs   → build all 7 apps (watchdog, dev config, one at a time)
 *   serve-static.mjs   → serve dist/<app>/browser on 4200–4206 (7 zero-dep servers)
 *   route-check.mjs    → drive the 11 shell routes through federation, assert 11/11 clean
 *
 * WHY (see tools/dev/STATIC_DEV.md for the full diagnosis): running all 7 `ng serve` dev
 * servers at once (start:all) needs 3–5 GB and hangs an 8 GB machine. Building once + serving
 * the static output holds ~129 MB and is the sustainable local-dev path.
 *
 * Subcommands:
 *   build [apps...]   build all 7 apps (or a named subset)            → build-static.mjs
 *   serve             serve the built apps (foreground, Ctrl-C stops) → serve-static.mjs
 *   check [engine]    route-check the running shell (chromium|webkit) → route-check.mjs
 *   up                build, then serve in the foreground             (build + serve)
 *   all               build, serve in background, check, report, stop (one-shot CI-style)
 *
 * Usage:
 *   node tools/dev/dev-static.mjs all
 *   node tools/dev/dev-static.mjs build mfe-auth
 *   node tools/dev/dev-static.mjs check webkit
 *   pnpm run dev:static all          # preferred (package.json)
 *
 * Exit codes mirror the underlying step: 0 on success, non-zero on failure. `all` exits 0
 * only if the route-check reports 11/11 clean.
 *
 * Dependencies: ZERO new ones. Node built-ins + the sibling scripts (route-check uses the
 * already-present `playwright` devDependency). Do NOT add npm packages here.
 */

import { spawn } from 'node:child_process';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import process from 'node:process';

// ─── ANSI colour codes ───────────────────────────────────────────────────────

const RESET  = '\x1b[0m';
const BOLD   = '\x1b[1m';
const DIM    = '\x1b[2m';
const RED    = '\x1b[31m';
const GREEN  = '\x1b[32m';
const YELLOW = '\x1b[33m';
const CYAN   = '\x1b[36m';
const WHITE  = '\x1b[37m';

const __filename = fileURLToPath(import.meta.url);
const __dirname  = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..', '..');

const BUILD = join(__dirname, 'build-static.mjs');
const SERVE = join(__dirname, 'serve-static.mjs');
const CHECK = join(__dirname, 'route-check.mjs');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ─── Run a child to completion, inheriting stdio. Resolves its exit code. ─────

function runToEnd(scriptPath, args = []) {
  return new Promise((res) => {
    const proc = spawn('node', [scriptPath, ...args], {
      cwd:   FRONTEND_DIR,
      stdio: 'inherit',
      env:   process.env,
    });
    proc.on('exit', (code) => res(code ?? 1));
    proc.on('error', (err) => {
      console.error(`${RED}dev-static: failed to spawn ${scriptPath}: ${err.message}${RESET}`);
      res(1);
    });
  });
}

// ─── Help ─────────────────────────────────────────────────────────────────────

function printHelp() {
  const line = '─'.repeat(66);
  console.log(`\n${BOLD}${CYAN}${line}${RESET}`);
  console.log(`${BOLD}${WHITE}  MeeSell — Static Dev (memory-safe local loop for low-RAM machines)${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
  console.log(`${BOLD}  Usage:${RESET} node tools/dev/dev-static.mjs <command> [args]\n`);
  console.log(`${BOLD}${YELLOW}  Commands${RESET}`);
  console.log(`    ${GREEN}build${RESET} [apps...]   build all 7 apps (or a named subset)`);
  console.log(`    ${GREEN}serve${RESET}             serve the built apps (foreground; Ctrl-C stops)`);
  console.log(`    ${GREEN}check${RESET} [engine]    route-check the running shell (chromium|webkit)`);
  console.log(`    ${GREEN}up${RESET}                build, then serve in the foreground`);
  console.log(`    ${GREEN}all${RESET}               build, serve in background, check, report, stop`);
  console.log(`\n${BOLD}${YELLOW}  Examples${RESET}`);
  console.log(`${DIM}    pnpm run dev:static all`);
  console.log(`    pnpm run dev:static build mfe-auth`);
  console.log(`    pnpm run dev:static check webkit${RESET}`);
  console.log(`\n${DIM}  Full diagnosis + numbers: tools/dev/STATIC_DEV.md${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
}

// ─── 'all' — build, serve (background), check, teardown ──────────────────────

async function runAll(passThrough) {
  // 1. Build.
  console.log(`\n${BOLD}${CYAN}[dev-static all] step 1/3 — build${RESET}`);
  const buildCode = await runToEnd(BUILD, passThrough);
  if (buildCode !== 0) {
    console.error(`${RED}[dev-static all] build failed (exit ${buildCode}). Aborting.${RESET}`);
    process.exit(buildCode);
  }

  // 2. Serve in the background.
  console.log(`\n${BOLD}${CYAN}[dev-static all] step 2/3 — serve (background)${RESET}`);
  const serveProc = spawn('node', [SERVE], {
    cwd:   FRONTEND_DIR,
    stdio: ['ignore', 'inherit', 'inherit'],
    env:   process.env,
  });

  let serveExited = false;
  serveProc.on('exit', (code) => {
    serveExited = true;
    if (!tearing && code !== 0 && code !== null) {
      console.error(`${RED}[dev-static all] serve exited early (code ${code}).${RESET}`);
    }
  });

  // Give the 7 servers a moment to bind before the harness hits :4200.
  await sleep(2500);
  if (serveExited) {
    console.error(`${RED}[dev-static all] serve did not stay up — check ports 4200–4206.${RESET}`);
    process.exit(1);
  }

  // 3. Check.
  console.log(`\n${BOLD}${CYAN}[dev-static all] step 3/3 — route-check${RESET}`);
  const checkCode = await runToEnd(CHECK, passThrough);

  // Teardown the background serve.
  teardown(serveProc);
  await sleep(500);

  const line = '─'.repeat(66);
  console.log(`\n${BOLD}${CYAN}${line}${RESET}`);
  if (checkCode === 0) {
    console.log(`${BOLD}${GREEN}  DEV-STATIC ALL — route-check clean. Servers stopped.${RESET}`);
  } else {
    console.log(`${BOLD}${RED}  DEV-STATIC ALL — route-check reported failures (exit ${checkCode}). Servers stopped.${RESET}`);
  }
  console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
  process.exit(checkCode);
}

let tearing = false;
function teardown(proc) {
  if (tearing) return;
  tearing = true;
  try { proc.kill('SIGTERM'); } catch (_) { /* already dead */ }
  setTimeout(() => { try { proc.kill('SIGKILL'); } catch (_) { /* ignore */ } }, 3000).unref();
}

// ─── Dispatch ─────────────────────────────────────────────────────────────────

async function main() {
  const [cmd, ...rest] = process.argv.slice(2);

  switch (cmd) {
    case 'build':
      process.exit(await runToEnd(BUILD, rest));
      break;
    case 'serve':
      process.exit(await runToEnd(SERVE, rest));
      break;
    case 'check':
      process.exit(await runToEnd(CHECK, rest));
      break;
    case 'up': {
      const buildCode = await runToEnd(BUILD, rest);
      if (buildCode !== 0) process.exit(buildCode);
      process.exit(await runToEnd(SERVE, []));
      break;
    }
    case 'all':
      await runAll(rest);
      break;
    case undefined:
    case '-h':
    case '--help':
    case 'help':
      printHelp();
      process.exit(cmd === undefined ? 1 : 0);
      break;
    default:
      console.error(`${RED}dev-static: unknown command '${cmd}'${RESET}`);
      printHelp();
      process.exit(2);
  }
}

main().catch((e) => { console.error(`${RED}dev-static crash:${RESET}`, e); process.exit(1); });
