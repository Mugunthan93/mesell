/**
 * build-static.mjs — Watchdog-build all 8 Native Federation apps (dev config), one at a time.
 *
 * WHY THIS EXISTS (low-RAM local dev):
 *   Running all 8 `ng serve` dev servers concurrently (`pnpm run start:all`) exhausts an
 *   8 GB machine — each ng serve holds a Node+esbuild watcher (~0.4–0.8 GB), so 8 of them
 *   = 3–5 GB on top of VS Code + Claude, the swap fills, and the machine HANGS. The
 *   sustainable path is: build each app ONCE here, then serve the static
 *   `dist/<app>/browser` output with `tools/dev/serve-static.mjs` (8 static servers ≈ 147 MB
 *   total). See tools/dev/STATIC_DEV.md for the full diagnosis + numbers.
 *
 * THE dev:true WATCHDOG FINDING:
 *   `ng build <app> --configuration development` sets `dev: true` on the native-federation
 *   builder. It writes the full browser bundle + remoteEntry.json in ~3.5s, but then NEVER
 *   EXITS — it drops into an incremental watch mode (this is the historical "build hung at
 *   90m" symptom). Workaround: start the build, poll until both `index.html` AND
 *   `remoteEntry.json` exist, settle ~3s for trailing chunk writes, then kill the build
 *   process tree and move on. ONE build at a time keeps it memory-safe.
 *
 * Usage (from any directory; run resolves to frontend/):
 *   node tools/dev/build-static.mjs                 # build all 8 apps
 *   node tools/dev/build-static.mjs mfe-auth        # build a subset
 *   node tools/dev/build-static.mjs frontend mfe-pricing
 *   pnpm run dev:build-static                        # preferred (package.json)
 *
 * Exit behaviour:
 *   All requested apps READY → exit 0.
 *   Any app FAILED (missing artifacts after timeout) → exit 1.
 *
 * Dependencies: ZERO. Node built-ins only. Do NOT add npm packages here.
 */

import { spawn } from 'node:child_process';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { existsSync, rmSync } from 'node:fs';
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

// ─── App list (angular.json project names; 'frontend' IS the shell) ──────────

const ALL_APPS = [
  'frontend',        // shell (host) — served on :4200
  'mfe-pricing',
  'mfe-export',
  'mfe-onboarding',
  'mfe-dashboard',
  'mfe-catalog',
  'mfe-auth',
  'mfe-billing',
];

// Poll up to this long for both artifacts to appear (ms).
const BUILD_TIMEOUT_MS = 180_000;
const POLL_INTERVAL_MS = 2_000;
const SETTLE_MS        = 3_000;   // let trailing chunk writes flush before kill

// ─── Working directory: two levels up from this file = frontend/ ─────────────

const __filename = fileURLToPath(import.meta.url);
const __dirname  = dirname(__filename);
const FRONTEND_DIR = resolve(__dirname, '..', '..');

// ─── Helpers ──────────────────────────────────────────────────────────────────

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

function artifactPaths(app) {
  const browserDir = join(FRONTEND_DIR, 'dist', app, 'browser');
  return {
    browserDir,
    index: join(browserDir, 'index.html'),
    remoteEntry: join(browserDir, 'remoteEntry.json'),
  };
}

function bothExist(app) {
  const { index, remoteEntry } = artifactPaths(app);
  return existsSync(index) && existsSync(remoteEntry);
}

/**
 * Build a single app with the dev:true watchdog. Resolves true on READY, false on FAILED.
 */
async function buildOne(app) {
  const { index, remoteEntry } = artifactPaths(app);

  // Clear stale markers so we detect THIS build's fresh write, not last run's.
  for (const p of [index, remoteEntry]) {
    try { rmSync(p, { force: true }); } catch (_) { /* ignore */ }
  }

  console.log(`\n${BOLD}${CYAN}=== building ${app} ===${RESET}`);
  console.log(`${DIM}    pnpm exec ng build ${app} --configuration development${RESET}`);

  const proc = spawn('pnpm', ['exec', 'ng', 'build', app, '--configuration', 'development'], {
    cwd:      FRONTEND_DIR,
    stdio:    ['ignore', 'ignore', 'pipe'],   // discard noisy stdout; keep stderr for real errors
    env:      process.env,
    detached: true,                           // own process group so killTree reaches the watcher
  });

  let stderrTail = '';
  proc.stderr.on('data', (c) => { stderrTail = (stderrTail + c.toString()).slice(-2000); });

  let diedEarly = false;
  proc.on('exit', () => { diedEarly = true; });

  // Poll for both artifacts.
  const started = Date.now();
  let ready = false;
  while (Date.now() - started < BUILD_TIMEOUT_MS) {
    if (bothExist(app)) { ready = true; break; }
    // If the build process died on its own before artifacts appeared, it's a real error.
    if (diedEarly && !bothExist(app)) break;
    await sleep(POLL_INTERVAL_MS);
  }

  // Settle: let any trailing chunk writes flush before we kill the watcher.
  await sleep(SETTLE_MS);

  // Kill the (likely still-watching) build process tree.
  killTree(proc, app);
  await sleep(800);

  const elapsed = Math.round((Date.now() - started) / 1000);
  if (bothExist(app)) {
    console.log(`${GREEN}    ${app} READY${RESET}  ${DIM}(index + remoteEntry, ~${elapsed}s)${RESET}`);
    return true;
  }
  console.log(`${RED}    ${app} FAILED${RESET}  ${DIM}(missing artifacts after ${elapsed}s)${RESET}`);
  if (stderrTail.trim()) {
    console.log(`${DIM}    --- last build stderr ---${RESET}`);
    for (const line of stderrTail.trim().split('\n').slice(-12)) {
      console.log(`${DIM}    ${line}${RESET}`);
    }
  }
  return false;
}

/**
 * Kill a process and its descendants. The native-federation watch build spawns workers;
 * killing only the parent can orphan the esbuild watcher. Because we spawn detached, the
 * child is a process-group leader — a negative PID signals the whole group. We also kill
 * by pattern as a belt-and-braces fallback.
 */
function killTree(proc, app) {
  if (proc && proc.pid != null) {
    try { process.kill(-proc.pid, 'SIGTERM'); } catch (_) { /* fall through */ }
    try { proc.kill('SIGTERM'); } catch (_) { /* already dead */ }
    setTimeout(() => {
      try { process.kill(-proc.pid, 'SIGKILL'); } catch (_) { /* ignore */ }
      try { proc.kill('SIGKILL'); } catch (_) { /* ignore */ }
    }, 1500).unref();
  }
  // Belt-and-braces: sweep any lingering watcher for this app.
  try {
    spawn('pkill', ['-f', `ng build ${app}`], { stdio: 'ignore' });
  } catch (_) { /* pkill unavailable — fine */ }
}

// ─── Banner ─────────────────────────────────────────────────────────────────

function printBanner(apps) {
  const line = '─'.repeat(66);
  console.log(`\n${BOLD}${CYAN}${line}${RESET}`);
  console.log(`${BOLD}${WHITE}  MeeSell — Static Dev Build (watchdog, dev config, one at a time)${RESET}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}`);
  console.log(`${DIM}  Memory-safe alternative to start:all on low-RAM machines.${RESET}`);
  console.log(`${DIM}  Builds → dist/<app>/browser, then serve with: pnpm run dev:serve-static${RESET}`);
  console.log(`\n${BOLD}${YELLOW}  Building ${apps.length} app(s):${RESET} ${apps.join(', ')}`);
  console.log(`${BOLD}${CYAN}${line}${RESET}`);
}

// ─── Arg parsing ──────────────────────────────────────────────────────────────

function resolveApps(argv) {
  const requested = argv.slice(2).filter((a) => !a.startsWith('-'));
  if (requested.length === 0) return ALL_APPS;
  const unknown = requested.filter((a) => !ALL_APPS.includes(a));
  if (unknown.length) {
    console.error(`${RED}Unknown app(s): ${unknown.join(', ')}${RESET}`);
    console.error(`${DIM}Valid apps: ${ALL_APPS.join(', ')}${RESET}`);
    process.exit(2);
  }
  // Preserve canonical order.
  return ALL_APPS.filter((a) => requested.includes(a));
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  const apps = resolveApps(process.argv);
  printBanner(apps);

  const failures = [];
  for (const app of apps) {
    const ok = await buildOne(app);
    if (!ok) failures.push(app);
  }

  const line = '─'.repeat(66);
  console.log(`\n${BOLD}${CYAN}${line}${RESET}`);
  if (failures.length === 0) {
    console.log(`${BOLD}${GREEN}  BUILD COMPLETE — ${apps.length}/${apps.length} apps READY${RESET}`);
    console.log(`${DIM}  Next: pnpm run dev:serve-static   (then pnpm run dev:check-routes)${RESET}`);
    console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
    process.exit(0);
  } else {
    console.log(`${BOLD}${RED}  BUILD FAILED — ${failures.length} app(s) missing artifacts: ${failures.join(', ')}${RESET}`);
    console.log(`${BOLD}${CYAN}${line}${RESET}\n`);
    process.exit(1);
  }
}

main().catch((e) => { console.error(`${RED}build-static crash:${RESET}`, e); process.exit(1); });
