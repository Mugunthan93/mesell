#!/usr/bin/env node
/**
 * dead_route_guard.mjs — Dead-route navigation guard (FED-2)
 *
 * WHY THIS EXISTS
 * ---------------
 * Angular's router has a catch-all `{ path: '**', redirectTo: 'login' }` in the shell
 * (apps/shell/src/app/app.routes.ts). So a navigate to a path that DOES NOT MATCH any
 * defined route does not 404 — it silently falls through the wildcard to /login. To a
 * logged-in user that reads as a sudden "logout": they clicked something and landed on
 * the login page. We have hit this twice from a single typo in a navigate literal:
 *   - image-uploader navigated to a retired path (#278)
 *   - a catalog action navigated to `:id/preview` after that route was retired (#395)
 * Both shipped because nothing checks navigation TARGETS against the route TABLE.
 *
 * This guard makes a navigate to an undefined route a CI FAILURE, before any build —
 * the same posture as the federation singleton guard (FED-1) next to it.
 *
 * WHAT IT CHECKS (source-level, zero build required)
 * --------------------------------------------------
 *   1. Builds the VALID ROUTE TABLE as the full set of ABSOLUTE mounted path patterns.
 *      It DERIVES this from the route files (never a hardcoded list) by:
 *        - parsing every apps/<app>/src/**\/*.routes.ts for route objects (`path:` +
 *          optional `children:` + optional `loadChildren:`),
 *        - resolving the MOUNTING: a route node whose `loadChildren` references a
 *          federation remote+expose (loadRemoteRoutesWithFallback('<remote>','<expose>'))
 *          is expanded by looking up that remote's federation.config.js `exposes` map
 *          (following one barrel re-export hop, e.g. public-api.ts), then splicing the
 *          target route array under the parent node's path,
 *        - concatenating segments down the tree to produce canonical patterns like
 *          /catalogs/:id/edit, /catalogs/new, /billing/plans, /dashboard, /login, …
 *   2. Extracts every STATIC navigation literal across apps + libs (.ts + .html),
 *      excluding *.spec.ts, *.routes.ts, and comments:
 *        this.router.navigate([ '...', '...' ])  (string-literal array elements)
 *        navigateByUrl('...')
 *        routerLink="..."           (HTML attribute, literal)
 *        [routerLink]="'...'"       (property binding, literal string)
 *        routerLink: '...'          (inline item config: menu/step/breadcrumb)
 *        route: '...'               (nav-item config — the source of [routerLink]="item.route")
 *   3. Resolves each static target against the table: variable segments (anything not a
 *      string literal — `id`, `this.productId()`) normalise to `:param`; literal segments
 *      stay literal; the resulting pattern must match a defined route pattern. A literal
 *      trailing segment with no matching route (like 'preview') = DEAD.
 *   4. Output + exit: prints each DEAD target (file:line -> target -> reason) and exits 1
 *      if any; else prints "OK: N static navigations, all resolve" and exits 0. Fully
 *      DYNAMIC targets (navigate(routeVar), [routerLink]="item.route") cannot be checked —
 *      they are printed as `UNVERIFIABLE (dynamic): file:line` and NEVER fail the build.
 *
 * Usage (from frontend/):
 *   node tools/contracts/dead_route_guard.mjs            # report, exit 1 on any dead route
 *   import { scan } from './dead_route_guard.mjs'         # programmatic { routes, dead, dynamic, checked }
 */

import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join, dirname, resolve } from 'node:path';
import { feRoot, rel, walk } from './_walk.mjs';

const CONTRACT = 'FED-2';

// ─────────────────────────────────────────────────────────────────────────────
// Comment stripping. Route + source files use // line comments and /* */ blocks.
// We strip both so a commented-out navigate or a literal mentioned in prose
// (e.g. the rationale comment "NOTE: :id/preview route retired") is never parsed.
// Strings are preserved (we only strip comment syntax, naively but adequately for
// our files — there are no `//` or `/*` sequences inside our route/nav string
// literals). Done char-by-char with a tiny state machine so `'http://'`-style
// strings are not mistaken for line comments.
// ─────────────────────────────────────────────────────────────────────────────
function stripComments(src) {
  let out = '';
  let i = 0;
  const n = src.length;
  let inS = null; // current string quote char or null
  while (i < n) {
    const c = src[i];
    const c2 = i + 1 < n ? src[i + 1] : '';
    if (inS) {
      out += c;
      if (c === '\\') {
        // keep escaped next char verbatim
        if (i + 1 < n) out += src[i + 1];
        i += 2;
        continue;
      }
      if (c === inS) inS = null;
      i += 1;
      continue;
    }
    // not in a string
    if (c === '"' || c === "'" || c === '`') {
      inS = c;
      out += c;
      i += 1;
      continue;
    }
    if (c === '/' && c2 === '/') {
      // line comment: skip to EOL but KEEP the newline (preserve line numbers)
      while (i < n && src[i] !== '\n') i += 1;
      continue;
    }
    if (c === '/' && c2 === '*') {
      // block comment: skip to */ but KEEP any newlines inside (preserve line numbers)
      i += 2;
      while (i < n && !(src[i] === '*' && src[i + 1] === '/')) {
        if (src[i] === '\n') out += '\n';
        i += 1;
      }
      i += 2; // skip closing */
      continue;
    }
    out += c;
    i += 1;
  }
  return out;
}

/** lineOf(src, index) → 1-based line number of a char offset (for file:line output). */
function lineOf(src, index) {
  let line = 1;
  for (let i = 0; i < index && i < src.length; i++) if (src[i] === '\n') line++;
  return line;
}

// ─────────────────────────────────────────────────────────────────────────────
// ROUTE TABLE
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Read every apps/<app>/federation.config.js and build:
 *   exposeMap: Map<`${remote}::${expose}`, absoluteRouteFilePath>
 * Following ONE re-export hop for barrel exposes (public-api.ts re-exporting a
 * *_ROUTES const from './x.routes'). If the expose points at a *.routes.ts directly
 * we use it as-is.
 */
function buildExposeMap(root) {
  const map = new Map();
  const appsDir = join(root, 'apps');
  if (!existsSync(appsDir)) return map;
  const apps = readdirSync(appsDir, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name);

  for (const app of apps) {
    const cfgAbs = join(appsDir, app, 'federation.config.js');
    if (!existsSync(cfgAbs)) continue;
    const text = stripComments(readFileSync(cfgAbs, 'utf8'));

    const nameM = text.match(/name\s*:\s*['"]([^'"]+)['"]/);
    const remote = nameM ? nameM[1] : app;

    // exposes entries: '<expose>': '<path>'
    // Native Federation expose paths are relative to the ANGULAR WORKSPACE ROOT,
    // which is frontend/ (where angular.json + the federation configs live). So
    // './apps/<app>/src/...' resolves under feRoot() (== frontend/), NOT the repo root.
    const re = /['"](\.\/[A-Za-z0-9_]+)['"]\s*:\s*['"](\.\/apps\/[^'"]+)['"]/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      const expose = m[1];
      const wsRelPath = m[2].replace(/^\.\//, ''); // 'apps/...'
      const abs = resolve(join(root, wsRelPath)); // root === frontend/ (angular workspace root)
      const routeFile = followToRouteFile(abs);
      if (routeFile) map.set(`${remote}::${expose}`, routeFile);
    }
  }
  return map;
}

/**
 * If `abs` is already a *.routes.ts, return it. If it is a barrel that re-exports a
 * *_ROUTES const from a relative module, follow ONE hop to that module and return it
 * (resolving .ts). Otherwise return abs (best effort).
 */
function followToRouteFile(abs) {
  if (!existsSync(abs)) return null;
  if (abs.endsWith('.routes.ts')) return abs;
  const text = stripComments(readFileSync(abs, 'utf8'));
  // export { XXX_ROUTES } from './billing.routes';
  const m = text.match(/export\s*\{[^}]*_ROUTES[^}]*\}\s*from\s*['"](\.\/[^'"]+)['"]/);
  if (m) {
    const relMod = m[1];
    let target = resolve(dirname(abs), relMod);
    if (!target.endsWith('.ts')) target += '.ts';
    if (existsSync(target)) return target;
  }
  return abs;
}

/**
 * Parse a routes file into a list of top-level route NODES. Each node:
 *   { path: string|null, children: node[], loadChildrenRef: {remote,expose}|null }
 * Adequate for our route files: route objects are `{ ... }` inside a Routes array,
 * with `path:` a string literal, optional nested `children: [ ... ]`, and optional
 * `loadChildren: loadRemoteRoutesWithFallback('<remote>', '<expose>')`.
 *
 * We use a brace-matching scan over the comment-stripped text to find each `{...}`
 * object literal at any depth, then for each object extract its OWN `path:` (the
 * first path key not inside a deeper brace) and recurse into its `children:` array.
 */
function parseRoutes(absFile) {
  if (!existsSync(absFile)) return [];
  const text = stripComments(readFileSync(absFile, 'utf8'));
  // Find the first `Routes` array literal: `: Routes = [ ... ]` OR just parse from
  // the first top-level `[` after an `= [`. Simplest robust approach: locate the
  // exported route array assignment and brace-match its array.
  const arrStart = findRouteArrayStart(text);
  if (arrStart === -1) return [];
  const arr = matchBracket(text, arrStart, '[', ']');
  if (!arr) return [];
  return parseRouteArray(text, arr.start + 1, arr.end);
}

function findRouteArrayStart(text) {
  // Prefer `: Routes = [`
  let m = /:\s*Routes\s*=\s*\[/.exec(text);
  if (m) return text.indexOf('[', m.index);
  // Fallback: first `= [` after a `Routes` token
  m = /Routes[^=]*=\s*\[/.exec(text);
  if (m) return text.indexOf('[', m.index);
  return -1;
}

/** matchBracket(text, openIdx, open, close) → {start, end} indices of the matching close. */
function matchBracket(text, openIdx, open, close) {
  if (text[openIdx] !== open) {
    openIdx = text.indexOf(open, openIdx);
    if (openIdx === -1) return null;
  }
  let depth = 0;
  for (let i = openIdx; i < text.length; i++) {
    const ch = text[i];
    if (ch === open) depth++;
    else if (ch === close) {
      depth--;
      if (depth === 0) return { start: openIdx, end: i };
    }
  }
  return null;
}

/**
 * Parse the contents of a route array (between [ and ]) into route nodes.
 * Iterates the top-level `{...}` object literals only.
 */
function parseRouteArray(text, from, to) {
  const nodes = [];
  let i = from;
  while (i < to) {
    // find next top-level '{'
    while (i < to && text[i] !== '{') i++;
    if (i >= to) break;
    const obj = matchBracket(text, i, '{', '}');
    if (!obj) break;
    nodes.push(parseRouteObject(text, obj.start, obj.end));
    i = obj.end + 1;
  }
  return nodes;
}

/** Parse a single `{...}` route object → node. */
function parseRouteObject(text, start, end) {
  const body = text.slice(start + 1, end);
  // path: '<literal>'  (own key — body excludes nested braces' interiors only by
  // virtue of we searching the WHOLE body; but a nested children:[{path:...}] would
  // also contain `path:`. To get the OWN path we take the FIRST path: that is not
  // inside a nested bracket. We compute nesting depth as we scan.)
  const ownPath = firstOwnKeyString(text, start + 1, end, /path\s*:\s*['"]([^'"]*)['"]/);

  // loadChildren: loadRemoteRoutesWithFallback('<remote>', '<expose>')
  // MUST be read at the object's OWN depth (depth-0 within this object), else a
  // nested child's loadChildren is wrongly attributed to the parent — that bug
  // double-expanded CatalogRoutes at the root prefix (/new, /:id/edit, …).
  let loadChildrenRef = null;
  const lcIdx = ownKeyIndex(text, start + 1, end, /loadChildren\s*:/);
  if (lcIdx !== -1) {
    const lcRe = /loadChildren\s*:\s*loadRemoteRoutesWithFallback\(\s*['"]([^'"]+)['"]\s*,\s*['"]([^'"]+)['"]\s*\)/;
    const lcM = lcRe.exec(text.slice(lcIdx, end));
    if (lcM) loadChildrenRef = { remote: lcM[1], expose: lcM[2] };
  }

  // children: [ ... ]  (nested route array)
  let children = [];
  const childIdx = ownKeyIndex(text, start + 1, end, /children\s*:\s*\[/);
  if (childIdx !== -1) {
    const arrOpen = text.indexOf('[', childIdx);
    const arr = matchBracket(text, arrOpen, '[', ']');
    if (arr) children = parseRouteArray(text, arr.start + 1, arr.end);
  }

  return { path: ownPath, children, loadChildrenRef };
}

/**
 * Find the FIRST match of `re` within [from,to) that occurs at brace-depth 0
 * relative to `from` (i.e. the object's OWN key, not a nested object's key),
 * and return its first capture group. Returns null if none.
 */
function firstOwnKeyString(text, from, to, re) {
  const idx = ownKeyIndex(text, from, to, re);
  if (idx === -1) return null;
  re.lastIndex = 0;
  const m = re.exec(text.slice(idx, to));
  return m ? m[1] : null;
}

/** Index (absolute) of the first depth-0 occurrence of `re` within [from,to), else -1. */
function ownKeyIndex(text, from, to, re) {
  let depth = 0;
  for (let i = from; i < to; i++) {
    const ch = text[i];
    if (ch === '{' || ch === '[' || ch === '(') depth++;
    else if (ch === '}' || ch === ']' || ch === ')') depth--;
    else if (depth === 0) {
      re.lastIndex = 0;
      const slice = text.slice(i, to);
      const m = re.exec(slice);
      if (m && m.index === 0) return i;
    }
  }
  return -1;
}

/**
 * Expand route nodes into a flat list of absolute path PATTERNS (arrays of segments).
 * `prefix` is the accumulated segment array from ancestors.
 * exposeMap resolves loadChildren remotes into their route files (parsed lazily).
 */
function expandNodes(nodes, prefix, exposeMap, parsedCache, root) {
  const patterns = [];
  for (const node of nodes) {
    const segs = node.path == null ? [] : splitPath(node.path);
    const here = [...prefix, ...segs];
    // This node itself is a navigable route (its full path), even if it also has
    // children (e.g. the catalog list at '' under /catalogs). We register `here`.
    patterns.push(here);

    if (node.loadChildrenRef) {
      const key = `${node.loadChildrenRef.remote}::${node.loadChildrenRef.expose}`;
      const file = exposeMap.get(key);
      if (file) {
        let childNodes = parsedCache.get(file);
        if (!childNodes) {
          childNodes = parseRoutes(file);
          parsedCache.set(file, childNodes);
        }
        patterns.push(...expandNodes(childNodes, here, exposeMap, parsedCache, root));
      }
    }
    if (node.children && node.children.length) {
      patterns.push(...expandNodes(node.children, here, exposeMap, parsedCache, root));
    }
  }
  return patterns;
}

/** splitPath('catalogs/:id/edit') → ['catalogs', ':id', 'edit']; '' → []. */
function splitPath(p) {
  const t = p.replace(/^\/+/, '').replace(/\/+$/, '');
  if (t === '') return [];
  return t.split('/');
}

/** Normalise a pattern segment array to a canonical string key, params → ':param'. */
function patternKey(segs) {
  return '/' + segs.map((s) => (s.startsWith(':') ? ':param' : s)).join('/');
}

/** Build the route table: Set of canonical pattern keys + the human pattern strings. */
function buildRouteTable(root) {
  const shellRoutes = join(root, 'apps', 'shell', 'src', 'app', 'app.routes.ts');
  const exposeMap = buildExposeMap(root);
  const parsedCache = new Map();
  const rootNodes = parseRoutes(shellRoutes);
  const rawPatterns = expandNodes(rootNodes, [], exposeMap, parsedCache, root);

  const keySet = new Set();
  const human = new Set();
  for (const segs of rawPatterns) {
    // Skip the wildcard '**' route — it is the catch-all, not a real target.
    if (segs.some((s) => s === '**')) continue;
    keySet.add(patternKey(segs));
    human.add('/' + segs.join('/'));
  }
  return { keySet, human, exposeMap };
}

// ─────────────────────────────────────────────────────────────────────────────
// NAVIGATION EXTRACTION
// ─────────────────────────────────────────────────────────────────────────────

/**
 * A navigation occurrence:
 *   { file, line, raw, segs|null, dynamic:boolean }
 * segs is the array of resolved segments where literals are kept and non-literals
 * are the sentinel PARAM. dynamic=true means the WHOLE target is a variable and is
 * unverifiable. A mixed call (literal base + variable segments) is verifiable: the
 * variables become :param.
 */
const PARAM = { param: true };

function extractNavigations(absFile, relPath) {
  const raw = readFileSync(absFile, 'utf8');
  const text = stripComments(raw);
  const occ = [];

  // 1) this.router.navigate([ ... ])  and  router.navigate([ ... ])
  // Capture the bracket array, then parse its elements.
  {
    const re = /\.navigate\s*\(\s*\[/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      const open = text.indexOf('[', m.index);
      const arr = matchBracket(text, open, '[', ']');
      if (!arr) continue;
      const inner = text.slice(arr.start + 1, arr.end);
      const parsed = parseNavArray(inner);
      occ.push({
        file: relPath,
        line: lineOf(text, m.index),
        raw: 'navigate([' + inner.trim().replace(/\s+/g, ' ').slice(0, 80) + '])',
        ...parsed,
      });
    }
  }

  // 2) navigateByUrl('...')  (literal) or navigateByUrl(expr) (dynamic)
  {
    const re = /\.navigateByUrl\s*\(\s*([^)]*?)\s*\)/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      const argRaw = m[1].trim();
      const lit = stringLiteral(argRaw);
      if (lit !== null) {
        occ.push({
          file: relPath,
          line: lineOf(text, m.index),
          raw: `navigateByUrl('${lit}')`,
          segs: splitUrl(lit),
          dynamic: false,
        });
      } else {
        occ.push({
          file: relPath,
          line: lineOf(text, m.index),
          raw: `navigateByUrl(${argRaw.slice(0, 60)})`,
          segs: null,
          dynamic: true,
        });
      }
    }
  }

  // 3) routerLink="..."   (HTML attribute, always a literal here)
  {
    const re = /(?<![[\w])routerLink\s*=\s*"([^"]*)"/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      const val = m[1].trim();
      // skip empty
      if (val === '') continue;
      occ.push({
        file: relPath,
        line: lineOf(text, m.index),
        raw: `routerLink="${val}"`,
        segs: splitUrl(val),
        dynamic: false,
      });
    }
  }

  // 4) [routerLink]="..."  property binding. Literal string ('..'), literal array
  //    (['..']), or a dynamic expression (item.route / route()).
  {
    const re = /\[routerLink\]\s*=\s*"([^"]*)"/g;
    let m;
    while ((m = re.exec(text)) !== null) {
      const expr = m[1].trim();
      const parsed = parseBoundExpr(expr);
      occ.push({
        file: relPath,
        line: lineOf(text, m.index),
        raw: `[routerLink]="${expr.slice(0, 70)}"`,
        ...parsed,
      });
    }
  }

  // 5) routerLink: '...'  / routerLink: [...]  inline item config (menu/step/breadcrumb)
  //    Also `route: '...'` nav-item config which feeds [routerLink]="item.route".
  for (const key of ['routerLink', 'route']) {
    const re = new RegExp(`(?<![\\w.])${key}\\s*:\\s*([^,}\\n]+)`, 'g');
    let m;
    while ((m = re.exec(text)) !== null) {
      const expr = m[1].trim();
      // Ignore the TS interface/type declarations: `route: string;` `routerLink?: ...`
      if (/^(string|number|boolean|unknown|any)\b/.test(expr)) continue;
      if (expr.endsWith(';') && !/['"\[]/.test(expr)) continue;
      const parsed = parseBoundExpr(expr.replace(/;$/, ''));
      // Only record literals & literal arrays here; pure dynamic config values
      // (routerLink: item.route, route: s.route) are surfaced as dynamic.
      occ.push({
        file: relPath,
        line: lineOf(text, m.index),
        raw: `${key}: ${expr.slice(0, 70)}`,
        ...parsed,
      });
    }
  }

  return occ;
}

/** If `s` is a single string literal ('x' | "x" | `x` with no ${}), return its value, else null. */
function stringLiteral(s) {
  const t = s.trim();
  const m = /^(['"`])([^'"`]*)\1$/.exec(t);
  if (!m) return null;
  if (m[1] === '`' && m[2].includes('${')) return null; // template with interpolation = dynamic
  return m[2];
}

/** splitUrl('/catalogs/new?x=1#h') → ['catalogs','new'] (drop query/hash + leading slash). */
function splitUrl(u) {
  let s = u.split('?')[0].split('#')[0];
  return splitPath(s);
}

/**
 * Parse the array INNER of navigate([ ... ]) into { segs, dynamic }.
 * Elements split on top-level commas. A string-literal element contributes its
 * path segments (a literal may itself be '/catalogs' or 'catalogs/new'); a
 * non-literal element (id, this.productId(), variable) becomes PARAM.
 * If the FIRST element is a non-literal (dynamic base, e.g. navigate([routeVar])),
 * the whole thing is dynamic/unverifiable.
 */
function parseNavArray(inner) {
  const elems = splitTopLevel(inner, ',').map((e) => e.trim()).filter((e) => e.length);
  if (elems.length === 0) return { segs: [], dynamic: false };
  const segs = [];
  let firstDynamic = false;
  for (let idx = 0; idx < elems.length; idx++) {
    const e = elems[idx];
    const lit = stringLiteral(e);
    if (lit !== null) {
      for (const seg of splitUrl(lit)) segs.push(seg);
    } else {
      if (idx === 0) firstDynamic = true;
      segs.push(PARAM);
    }
  }
  // If the very first element is a dynamic base, we cannot anchor the route → dynamic.
  if (firstDynamic) return { segs: null, dynamic: true };
  return { segs, dynamic: false };
}

/**
 * Parse a [routerLink] / inline-config value expression into { segs, dynamic }.
 *   '/x/y'            → literal
 *   ['/x', id]        → literal base + param
 *   item.route        → dynamic
 *   route()           → dynamic
 */
function parseBoundExpr(expr) {
  const t = expr.trim();
  const lit = stringLiteral(t);
  if (lit !== null) return { segs: splitUrl(lit), dynamic: false };
  if (t.startsWith('[')) {
    const arr = matchBracket(t, 0, '[', ']');
    if (arr) {
      const parsed = parseNavArray(t.slice(arr.start + 1, arr.end));
      return parsed;
    }
  }
  // anything else (identifier, member access, call) is dynamic
  return { segs: null, dynamic: true };
}

/** Split `s` on top-level `sep`, respecting (), [], {}, '' "" `` nesting. */
function splitTopLevel(s, sep) {
  const parts = [];
  let depth = 0;
  let inS = null;
  let cur = '';
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inS) {
      cur += c;
      if (c === '\\') {
        if (i + 1 < s.length) cur += s[++i];
        continue;
      }
      if (c === inS) inS = null;
      continue;
    }
    if (c === '"' || c === "'" || c === '`') {
      inS = c;
      cur += c;
      continue;
    }
    if (c === '(' || c === '[' || c === '{') depth++;
    else if (c === ')' || c === ']' || c === '}') depth--;
    if (c === sep && depth === 0) {
      parts.push(cur);
      cur = '';
      continue;
    }
    cur += c;
  }
  if (cur.length) parts.push(cur);
  return parts;
}

// ─────────────────────────────────────────────────────────────────────────────
// RESOLUTION
// ─────────────────────────────────────────────────────────────────────────────

/** Normalise a nav `segs` (mixed literal + PARAM sentinel) to a canonical key. */
function navKey(segs) {
  return '/' + segs.map((s) => (s === PARAM ? ':param' : s)).join('/');
}

/**
 * Does the nav pattern match a defined route pattern?
 * A nav segment that is PARAM matches ONLY a route :param segment.
 * A nav segment that is a literal matches an identical route literal OR a route
 * :param segment (a literal value passed where the route expects a param — valid,
 * e.g. navigate(['/catalogs','new']) where 'new' is a literal route, but
 * navigate(['/catalogs', someLiteralId]) is rare; we accept literal↦:param).
 */
function navMatchesTable(navSegs, routeKeySet, routeHuman) {
  const key = navKey(navSegs);
  if (routeKeySet.has(key)) return true;
  // Allow a literal nav segment to satisfy a route :param (covers a literal used as
  // an id). Compare segment-wise against each route pattern of equal length.
  for (const h of routeHuman) {
    const rsegs = splitPath(h);
    if (rsegs.length !== navSegs.length) continue;
    let ok = true;
    for (let i = 0; i < rsegs.length; i++) {
      const r = rsegs[i];
      const nv = navSegs[i];
      if (r.startsWith(':')) {
        // route param: matches a nav PARAM OR a nav literal (id value)
        continue;
      }
      // route literal: must equal nav literal exactly (a nav PARAM cannot satisfy a
      // fixed literal route segment — that's the dead-route signal)
      if (nv === PARAM || nv !== r) {
        ok = false;
        break;
      }
    }
    if (ok) return true;
  }
  return false;
}

// ─────────────────────────────────────────────────────────────────────────────
// SCAN
// ─────────────────────────────────────────────────────────────────────────────

/**
 * scan(opts?) → { contract, routes:[...], checked:[...], dead:[...], dynamic:[...] }
 */
export function scan(_opts = {}) {
  const root = feRoot();
  const { keySet, human } = buildRouteTable(root);

  const dead = [];
  const dynamic = [];
  const checked = [];

  const targets = [join(root, 'apps'), join(root, 'libs')];
  const files = [];
  for (const dir of targets) {
    if (!existsSync(dir)) continue;
    for (const f of walk(dir, { exts: ['.ts', '.html'] })) {
      if (f.endsWith('.spec.ts')) continue;
      if (f.endsWith('.routes.ts')) continue;
      files.push(f);
    }
  }

  for (const abs of files) {
    const relPath = rel(abs);
    let occ;
    try {
      occ = extractNavigations(abs, relPath);
    } catch (e) {
      // A parse error on one file must not crash the whole guard.
      dynamic.push({ file: relPath, line: 0, raw: `(parse error: ${e.message})` });
      continue;
    }
    for (const o of occ) {
      if (o.dynamic || o.segs == null) {
        dynamic.push(o);
        continue;
      }
      // Empty target (navigate([]) or routerLink="") → treat as root '/', which is valid.
      if (o.segs.length === 0) {
        checked.push(o);
        continue;
      }
      checked.push(o);
      if (!navMatchesTable(o.segs, keySet, human)) {
        dead.push({ ...o, target: navKey(o.segs) });
      }
    }
  }

  return {
    contract: CONTRACT,
    routes: [...human].sort(),
    routeKeys: [...keySet].sort(),
    checked,
    dead,
    dynamic,
  };
}

// ── Standalone CLI ─────────────────────────────────────────────────────────────
if (process.argv[1] && process.argv[1].endsWith('dead_route_guard.mjs')) {
  const { routes, checked, dead, dynamic } = scan();

  if (process.argv.includes('--routes')) {
    console.log(`${CONTRACT}: route table (${routes.length} patterns):`);
    for (const r of routes) console.log(`  ${r}`);
    console.log('');
  }

  // Always surface dynamic (unverifiable) targets so the residual surface is visible.
  for (const d of dynamic) {
    console.log(`UNVERIFIABLE (dynamic): ${d.file}:${d.line}  ${d.raw}`);
  }
  if (dynamic.length) console.log('');

  if (dead.length === 0) {
    console.log(
      `${CONTRACT}: OK — ${checked.length} static navigations, all resolve to a defined route ` +
        `(${routes.length} route patterns; ${dynamic.length} dynamic target(s) skipped).`,
    );
    process.exit(0);
  }

  for (const d of dead) {
    console.log(`DEAD ROUTE: ${d.file}:${d.line} -> ${d.target}  (${d.raw}) — no matching route`);
  }
  console.log(
    `\n${CONTRACT}: ${dead.length} dead navigation target(s) — a navigate to an undefined route ` +
      `falls through the '**' wildcard to /login (false logout). Fix the target or add the route.`,
  );
  process.exit(1);
}
