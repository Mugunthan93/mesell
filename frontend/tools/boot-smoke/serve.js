/**
 * serve.js — SPA-aware static file server for browser-boot smoke gate.
 *
 * Key anti-false-pass guarantee:
 *   ANY path that does NOT resolve to a real file returns 200 + index.html,
 *   NOT a 404. This reproduces the prod Nginx/Traefik rewrite behaviour and
 *   is the difference between "ng serve" (which has the fallback) and a naive
 *   `python -m http.server` (which does NOT — the false-pass root cause).
 *
 * API reverse-proxy (added 2026-06-21, feature/dev-proxy/infra):
 *   The federated app runs in the shell origin (:4200) and makes RELATIVE API
 *   calls (every call is `${apiBase}/api/v1/...` with apiBase='', confirmed via
 *   libs/core/services/auth-api.service.ts + ApiClient.withBase). Without a
 *   proxy the static server answered those with index.html (the SPA fallback),
 *   so OTP login could not complete and every authenticated screen silently
 *   degraded (UI/UX audit PR #367). This mirrors what the ng-serve
 *   proxy.conf.json does and what the prod Ingress does: any request whose path
 *   begins with a PROXY_PREFIX is streamed to the backend, preserving
 *   method/headers/body; everything else keeps the unchanged static-SPA path.
 *
 * Usage:
 *   node serve.js <dist-dir> <port> [backend-target]
 *
 *   backend-target may also be supplied via the MEESELL_BACKEND env var. If
 *   neither is given, the proxy is DISABLED and behaviour is byte-identical to
 *   the original static-only server (so smoke-gate callers are unaffected).
 *
 * Example:
 *   node serve.js ../../dist/frontend/browser 4200 http://127.0.0.1:8000
 *   node serve.js ../../dist/mfe-auth/browser  4206          # no proxy, static only
 */

'use strict';

const http = require('http');
const fs   = require('fs');
const path = require('path');

const [, , distDir, portArg, backendArg] = process.argv;
if (!distDir || !portArg) {
  console.error('Usage: node serve.js <dist-dir> <port> [backend-target]');
  process.exit(1);
}

const ROOT = path.resolve(distDir);
const PORT = parseInt(portArg, 10);

// Reverse-proxy target. CLI arg wins over env; if neither set, proxy is off.
const BACKEND = backendArg || process.env.MEESELL_BACKEND || '';
// Path prefixes proxied to the backend. The app only calls /api/* relative to
// origin (verified); /health, /docs, /openapi.json are included so manual API
// probing in the browser works too. Non-matching paths keep static-SPA serving.
const PROXY_PREFIXES = ['/api', '/health', '/docs', '/openapi.json'];

let backendURL = null;
if (BACKEND) {
  try {
    backendURL = new URL(BACKEND);
  } catch (err) {
    console.error(`serve.js: invalid backend target '${BACKEND}': ${err.message}`);
    process.exit(1);
  }
}

function shouldProxy(urlPath) {
  if (!backendURL) return false;
  return PROXY_PREFIXES.some(
    (p) => urlPath === p || urlPath.startsWith(p + '/') || urlPath.startsWith(p + '?'),
  );
}

function proxy(req, res) {
  const opts = {
    protocol: backendURL.protocol,
    hostname: backendURL.hostname,
    port: backendURL.port || (backendURL.protocol === 'https:' ? 443 : 80),
    method: req.method,
    path: req.url,                 // includes the query string verbatim
    headers: { ...req.headers, host: backendURL.host },
  };
  const upstream = http.request(opts, (up) => {
    res.writeHead(up.statusCode || 502, up.headers);
    up.pipe(res);
  });
  upstream.on('error', (err) => {
    if (!res.headersSent) {
      res.writeHead(502, { 'Content-Type': 'application/json; charset=utf-8' });
    }
    res.end(JSON.stringify({ detail: `dev proxy upstream error: ${err.message}` }));
  });
  req.pipe(upstream);   // stream the request body (POST/PATCH) through unbuffered
}

if (!fs.existsSync(ROOT)) {
  console.error(`serve.js: dist dir does not exist: ${ROOT}`);
  process.exit(1);
}

const MIME = {
  '.js':    'text/javascript; charset=utf-8',
  '.mjs':   'text/javascript; charset=utf-8',
  '.json':  'application/json; charset=utf-8',
  '.css':   'text/css; charset=utf-8',
  '.html':  'text/html; charset=utf-8',
  '.ico':   'image/x-icon',
  '.png':   'image/png',
  '.svg':   'image/svg+xml',
  '.woff':  'font/woff',
  '.woff2': 'font/woff2',
  '.txt':   'text/plain; charset=utf-8',
  '.webmanifest': 'application/manifest+json; charset=utf-8',
};

const INDEX = path.join(ROOT, 'index.html');

function serve(req, res) {
  // Reverse-proxy FIRST: any /api|/health|/docs|/openapi.json request goes to the
  // backend (method/headers/body preserved, response streamed). This is what lets
  // OTP login + every authenticated screen work in the static dev shell. Only
  // active when a backend target was supplied (CLI arg or MEESELL_BACKEND env).
  const reqPath = req.url.split('?')[0];
  if (shouldProxy(reqPath)) {
    proxy(req, res);
    return;
  }

  // Handle CORS preflight — the federation client may send OPTIONS before GET.
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin':  '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end();
    return;
  }

  // Strip query string for file resolution only.
  const urlPath = req.url.split('?')[0];
  const candidate = path.join(ROOT, urlPath);

  // Security: reject any path that escapes ROOT.
  if (!candidate.startsWith(ROOT)) {
    res.writeHead(403);
    res.end('Forbidden');
    return;
  }

  // Try the exact file first.
  let filePath = candidate;
  if (fs.existsSync(filePath) && fs.statSync(filePath).isFile()) {
    // Exact file found — serve it.
  } else {
    // SPA fallback: ALL non-file GETs (including /login, /profile) → 200 + index.html.
    // This is THE assertion that prevents the false-pass: a naive server would return 404
    // here, Angular would never boot, and naive body-length checks would still pass on
    // the 404 page body.
    filePath = INDEX;
  }

  if (!fs.existsSync(filePath)) {
    res.writeHead(500);
    res.end(`serve.js: index.html not found at ${INDEX}`);
    return;
  }

  const ext = path.extname(filePath).toLowerCase();
  const mime = MIME[ext] || 'application/octet-stream';

  try {
    const data = fs.readFileSync(filePath);
    res.writeHead(200, {
      'Content-Type':             mime,
      'Cache-Control':            'no-cache',
      // CORS required: the shell (port 4200) fetches remoteEntry.json from the remote
      // ports (4201-4206) — a cross-origin fetch. Without this header the browser
      // blocks the request with "No 'Access-Control-Allow-Origin' header" and the
      // federation runtime falls back to RemoteFailureComponent for every remote.
      'Access-Control-Allow-Origin':  '*',
      'Access-Control-Allow-Methods': 'GET, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    });
    res.end(data);
  } catch (err) {
    res.writeHead(500);
    res.end(`serve.js read error: ${err.message}`);
  }
}

http.createServer(serve).listen(PORT, '127.0.0.1', () => {
  const proxyNote = backendURL
    ? `[proxy ${PROXY_PREFIXES.join('|')} → ${backendURL.origin}]`
    : '[proxy OFF — static only]';
  console.log(`serve.js: ${ROOT} → http://127.0.0.1:${PORT}  [SPA fallback ON] ${proxyNote}`);
});
