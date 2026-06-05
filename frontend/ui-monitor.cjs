/**
 * MeeSell UI Monitor — passive Chrome DevTools Protocol listener.
 * Connects to Chrome's remote debugging port and streams:
 *   - Console errors / warnings
 *   - Unhandled JS exceptions
 *   - Failed network requests (4xx / 5xx / net::ERR_*)
 *
 * Does NOT control or automate the browser. Read-only.
 *
 * Usage:
 *   1. Open Chrome with: open -a "Google Chrome" --args --remote-debugging-port=9222
 *   2. Navigate to http://localhost:5173
 *   3. Run: node /tmp/mesell-ui-monitor.js
 */

const http = require("http");
const WebSocket = require("ws");

const CDP_PORT = 9222;
const POLL_INTERVAL = 2000;

function getTargets() {
  return new Promise((resolve, reject) => {
    http.get(`http://localhost:${CDP_PORT}/json`, (res) => {
      let data = "";
      res.on("data", (c) => (data += c));
      res.on("end", () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(e); }
      });
    }).on("error", reject);
  });
}

function timestamp() {
  return new Date().toISOString().replace("T", " ").slice(0, 23);
}

function label(type) {
  const map = {
    error:   "[UI ERROR]  ",
    warning: "[UI WARN]   ",
    network: "[NET ERROR] ",
    exception: "[EXCEPTION] ",
  };
  return map[type] || "[UI]        ";
}

async function attachToTab(target) {
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  let msgId = 1;

  function send(method, params = {}) {
    ws.send(JSON.stringify({ id: msgId++, method, params }));
  }

  ws.on("open", () => {
    send("Runtime.enable");
    send("Log.enable");
    send("Network.enable");
    console.log(`[UI MONITOR] Attached → ${target.title || target.url}`);
  });

  ws.on("message", (raw) => {
    const msg = JSON.parse(raw);
    const method = msg.method;
    const p = msg.params || {};

    // Console API calls (console.error, console.warn)
    if (method === "Runtime.consoleAPICalled") {
      const type = p.type; // log, warning, error, etc.
      if (!["error", "warning"].includes(type)) return;
      const text = (p.args || [])
        .map((a) => a.value ?? a.description ?? JSON.stringify(a))
        .join(" ");
      console.log(`${timestamp()} ${label(type)}${text}`);
    }

    // Unhandled JS exceptions
    if (method === "Runtime.exceptionThrown") {
      const ex = p.exceptionDetails;
      const text = ex?.exception?.description || ex?.text || JSON.stringify(ex);
      console.log(`${timestamp()} ${label("exception")}${text}`);
    }

    // Browser-level log entries (includes CORS, CSP, etc.)
    if (method === "Log.entryAdded") {
      const entry = p.entry;
      if (!["error", "warning"].includes(entry.level)) return;
      console.log(`${timestamp()} ${label(entry.level)}[${entry.source}] ${entry.text}`);
    }

    // Failed network requests
    if (method === "Network.loadingFailed") {
      const { requestId, errorText, blockedReason } = p;
      console.log(`${timestamp()} ${label("network")}requestId=${requestId} ${errorText || blockedReason || "unknown"}`);
    }

    // HTTP responses — log 4xx/5xx
    if (method === "Network.responseReceived") {
      const { response } = p;
      if (response.status >= 400) {
        console.log(`${timestamp()} ${label("network")}HTTP ${response.status} — ${response.url}`);
      }
    }
  });

  ws.on("close", () => {
    console.log(`[UI MONITOR] Tab closed or detached — ${target.url}`);
  });

  ws.on("error", (e) => {
    console.log(`[UI MONITOR] WS error: ${e.message}`);
  });
}

async function findMeeSellTab(targets) {
  return targets.find(
    (t) => t.type === "page" && (t.url.includes("localhost:5173") || t.url.includes("localhost:5174"))
  );
}

let attached = false;

async function poll() {
  try {
    const targets = await getTargets();
    if (!attached) {
      const tab = await findMeeSellTab(targets);
      if (tab) {
        attached = true;
        await attachToTab(tab);
      } else {
        process.stdout.write(".");  // waiting for MeeSell tab
      }
    }
  } catch (e) {
    if (e.code === "ECONNREFUSED") {
      process.stdout.write("?");  // Chrome not started with --remote-debugging-port
    }
  }
}

console.log(`[UI MONITOR] Waiting for Chrome on port ${CDP_PORT}...`);
console.log(`[UI MONITOR] Open Chrome with:`);
console.log(`             open -a "Google Chrome" --args --remote-debugging-port=${CDP_PORT}`);
console.log(`[UI MONITOR] Then navigate to http://localhost:5173`);
console.log(`[UI MONITOR] Listening for: console.error, JS exceptions, 4xx/5xx, CORS, CSP\n`);

poll();
setInterval(poll, POLL_INTERVAL);
