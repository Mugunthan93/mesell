/**
 * serve.js — SPA-aware static file server for browser-boot smoke gate.
 *
 * Key anti-false-pass guarantee:
 *   ANY path that does NOT resolve to a real file returns 200 + index.html,
 *   NOT a 404. This reproduces the prod Nginx/Traefik rewrite behaviour and
 *   is the difference between "ng serve" (which has the fallback) and a naive
 *   `python -m http.server` (which does NOT — the false-pass root cause).
 *
 * Usage:
 *   node serve.js <dist-dir> <port>
 *
 * Example:
 *   node serve.js ../../dist/frontend/browser 4200
 *   node serve.js ../../dist/mfe-auth/browser  4206
 */

'use strict';

const http = require('http');
const fs   = require('fs');
const path = require('path');

const [, , distDir, portArg] = process.argv;
if (!distDir || !portArg) {
  console.error('Usage: node serve.js <dist-dir> <port>');
  process.exit(1);
}

const ROOT = path.resolve(distDir);
const PORT = parseInt(portArg, 10);

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
  console.log(`serve.js: ${ROOT} → http://127.0.0.1:${PORT}  [SPA fallback ON]`);
});
