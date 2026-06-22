/**
 * rate-limit.ts — dev-env reset harness for the OTP rate limit.
 *
 * WHY this exists (federation_quirks.md): the backend rate-limits OTP SEND to
 * 3/3600s PER IP (and verify 10/h) via a hardcoded `@rate_limit` decorator; the
 * counters live in Valkey DB0 under `meesell:rl:route:otp_*:ip:127.0.0.1:3600`.
 * The onboarding E2E suite legitimately needs several fresh-user logins (happy,
 * persist+resume, resume-incomplete, skip), which exceeds 3 sends in one run.
 *
 * This is an ENV RESET, deliberately kept OUT of every flow spec body: it clears
 * the OTP-send + verify rate-limit keys so a fresh login can send an OTP. It shells
 * out to the local `redis-cli` (the dev Valkey is on localhost:6379 DB0). If
 * redis-cli is unavailable (e.g. CI without it), the reset is a NO-OP and the suite
 * relies on the global pre-run clear + the dedicated per-flow phones instead.
 *
 * Override the Valkey location via MEESELL_VALKEY_HOST/PORT/DB if needed.
 */
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';

const execFileP = promisify(execFile);

const VALKEY_HOST = process.env.MEESELL_VALKEY_HOST ?? '127.0.0.1';
const VALKEY_PORT = process.env.MEESELL_VALKEY_PORT ?? '6379';
const VALKEY_DB = process.env.MEESELL_VALKEY_DB ?? '0';
const REDIS_CLI = process.env.MEESELL_REDIS_CLI ?? 'redis-cli';

/**
 * Clear all `meesell:rl:*` keys in Valkey DB0 (OTP send/verify, refresh, etc.).
 * Best-effort: any failure (no redis-cli, no Valkey) is swallowed so the suite can
 * still run on environments without a reachable dev Valkey.
 */
export async function resetRateLimits(): Promise<void> {
  try {
    // SCAN for the keys, then DEL them (avoids a blocking KEYS in case the DB grows).
    const { stdout } = await execFileP(REDIS_CLI, [
      '-h', VALKEY_HOST, '-p', VALKEY_PORT, '-n', VALKEY_DB,
      '--scan', '--pattern', 'meesell:rl:*',
    ]);
    const keys = stdout.split('\n').map((s) => s.trim()).filter(Boolean);
    if (keys.length === 0) return;
    await execFileP(REDIS_CLI, [
      '-h', VALKEY_HOST, '-p', VALKEY_PORT, '-n', VALKEY_DB, 'del', ...keys,
    ]);
  } catch {
    // No reachable Valkey / no redis-cli — best-effort env reset, not a test failure.
  }
}
