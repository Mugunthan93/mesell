#!/usr/bin/env python3
"""
meesell_env.py — dynamic, RAM-budgeted, port-isolated dev-environment manager.

Why this exists
---------------
The dev machine has 8 GB RAM. It cannot run several `ng serve` / `ng build`
processes at once: esbuild deadlocks and the box thrashes swap. The key insight
is that *serving* a built Angular app (static `serve.js`) is cheap, but
*building* one is the RAM spike. So this tool:

  * STATICALLY reserves a deterministic port block per worktree (slot model),
  * runs processes DYNAMICALLY inside a conservative RAM budget,
  * SERIALIZES all builds behind a single machine-wide lock (one build at a time),
  * REUSES untouched MFEs from a shared baseline (slot 0) via a per-env runtime
    federation manifest — so a worktree only rebuilds the shell-if-touched plus
    the MFEs it actually changed.

The shell loads `federation.manifest.json` at RUNTIME (origin-relative fetch via
`initFederation(...)`). That is the linchpin: we can reuse a SINGLE baseline
shell build and only overwrite the manifest at the served dist root per-env.
A worktree therefore never needs to rebuild the shell unless it touched the
shell itself.

Standard library only. We shell out to `ng` / `node` / `uvicorn` for the real
build and serve work.

Port scheme (deterministic, persisted in .nexus/env-ports.json)
---------------------------------------------------------------
Each worktree is assigned a SLOT (int, 0-9). Slot 0 is the baseline (develop).
For slot N (stride 10):

    backend = 8000 + N*10
    shell   = 4200 + N*10
    mfe[i]  = 4201 + N*10 + i   (i = index of the MFE in sorted app order)

Sorted app order = sorted names of `frontend/apps/mfe-*` directories. There are
~7 MFEs, so a slot uses ports 420(1..7)+N*10 — well within the stride of 10.

Commands
--------
    up <worktree> [--mfe a,b,...]   bring an env up (budget-checked, serialized build)
    down <worktree>                 stop the env's processes, keep the slot reserved
    baseline up|refresh             build develop's shell + ALL MFEs (the fallback), slot 0
    status                          running envs + live free RAM + swap%
    gc                              stop orphaned processes; prune dead slot reservations
    ports <worktree>                print the assigned port block
    --help                          this help; each subcommand has --help too

Files (all gitignored, never committed)
---------------------------------------
    .nexus/env-ports.json     worktree -> slot index (persisted, reclaimable)
    .nexus/env-state.json     running env -> {pids, ports, dist roots}
    .nexus/.build.lock        flock target — global build mutex
    <served-dist>/federation.manifest.json   per-env runtime manifest (generated)
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Constants / layout discovery
# ---------------------------------------------------------------------------

# This file lives at <repo>/tools/meesell_env.py. The TREE it sits in is wherever
# it was invoked from; that is NOT necessarily the baseline. The BASELINE (slot 0)
# is the worktree checked out on `develop` (the main tree), discovered dynamically
# from `git worktree list` so the tool behaves identically regardless of which
# worktree copy is invoked. All shared state (.nexus/, registries, lock) lives in
# the baseline tree so every worktree shares ONE registry and ONE build lock.
THIS_FILE = Path(__file__).resolve()
_INVOKED_FROM = THIS_FILE.parent.parent  # the tree this script copy lives in


def _discover_master_root() -> Path:
    """The baseline tree = the worktree on branch 'develop'. Fallback: the main
    (first) worktree from `git worktree list`, else the invoking tree."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(_INVOKED_FROM), "worktree", "list", "--porcelain"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError):
        return _INVOKED_FROM
    entries = []  # (path, branch)
    cur_path = None
    for line in out.splitlines():
        if line.startswith("worktree "):
            cur_path = line[len("worktree "):]
        elif line.startswith("branch ") and cur_path:
            br = line[len("branch "):].replace("refs/heads/", "")
            entries.append((cur_path, br))
            cur_path = None
        elif line == "" and cur_path:
            entries.append((cur_path, None))
            cur_path = None
    if cur_path:
        entries.append((cur_path, None))
    for path, br in entries:
        if br == "develop":
            return Path(path)
    return Path(entries[0][0]) if entries else _INVOKED_FROM


MASTER_ROOT = _discover_master_root()

NEXUS_DIR = MASTER_ROOT / ".nexus"
PORTS_REGISTRY = NEXUS_DIR / "env-ports.json"
STATE_FILE = NEXUS_DIR / "env-state.json"
BUILD_LOCK = NEXUS_DIR / ".build.lock"
BUILD_HISTORY = NEXUS_DIR / "build-history.jsonl"  # append-only build log (jsonl)


def build_log_path(slot: int | None, project: str) -> Path:
    """Per-ENV build log path: `.nexus/build-slot<N>-<project>.log`.

    Keyed by slot so concurrent worktrees building the SAME project (e.g. three
    slots each building mfe-catalog) never clobber one shared log. `slot=None`
    (slot unknown) degrades to slot 0 so a build still records somewhere
    deterministic. The writer (`ng_build`) and the `/api/log` tail handler both
    compute the path through this one helper so they always agree.
    """
    return NEXUS_DIR / f"build-slot{0 if slot is None else slot}-{project}.log"

# Default dashboard port. 7700 sits OUTSIDE every slot range (slots 0-9 use
# backend 8000-8090, shell 4200-4290, mfe 4201-4297) so the monitor never
# collides with a served env.
DASHBOARD_PORT = 7700

# Conservative RAM guard (founder-locked): refuse up/build if either trips.
MIN_FREE_MB = 1500
MAX_SWAP_PCT = 70.0

PORT_STRIDE = 10          # ports per slot
MAX_SLOTS = 10            # slots 0..9 (stride 10 keeps each slot's ports distinct)
BACKEND_BASE = 8000
SHELL_BASE = 4200
MFE_BASE = 4201

# The shell's Angular *project* name is "frontend" (its dist is dist/frontend),
# but its app directory is apps/shell. MFE project names == their dir names.
SHELL_APP_DIR = "shell"
SHELL_DIST_NAME = "frontend"

SERVE_JS_REL = "frontend/tools/boot-smoke/serve.js"


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------

def die(msg: str, code: int = 1) -> None:
    print(f"meesell_env: error: {msg}", file=sys.stderr)
    sys.exit(code)


def info(msg: str) -> None:
    print(f"[env] {msg}")


def _read_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        die(f"could not read {path}: {exc}")


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    tmp.replace(path)


# ---------------------------------------------------------------------------
# RAM / swap stats (macOS: vm_stat + sysctl vm.swapusage)
# ---------------------------------------------------------------------------

def ram_stats() -> tuple[int, float]:
    """Return (free_mb, swap_pct).

    free_mb  : pages free + inactive + speculative, * page size.
               (inactive/speculative are reclaimable, so they count as 'free'
               for a conservative-but-realistic dev budget.)
    swap_pct : used / total * 100 from `sysctl vm.swapusage`. 0.0 if no swap.
    """
    free_mb = _free_mb_from_vm_stat()
    swap_pct = _swap_pct_from_sysctl()
    return free_mb, swap_pct


def _free_mb_from_vm_stat() -> int:
    try:
        out = subprocess.check_output(["vm_stat"], text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"could not run vm_stat (macOS only): {exc}")

    # Header: "Mach Virtual Memory Statistics: (page size of 16384 bytes)"
    m = re.search(r"page size of (\d+) bytes", out)
    page_size = int(m.group(1)) if m else 4096

    def pages(label: str) -> int:
        mm = re.search(rf"{re.escape(label)}:\s+(\d+)\.", out)
        return int(mm.group(1)) if mm else 0

    reclaimable = (
        pages("Pages free")
        + pages("Pages inactive")
        + pages("Pages speculative")
    )
    return (reclaimable * page_size) // (1024 * 1024)


def _swap_pct_from_sysctl() -> float:
    try:
        out = subprocess.check_output(["sysctl", "vm.swapusage"], text=True)
    except (OSError, subprocess.CalledProcessError):
        return 0.0
    # "vm.swapusage: total = 2048.00M  used = 411.88M  free = 1636.12M"
    total = re.search(r"total\s*=\s*([\d.]+)M", out)
    used = re.search(r"used\s*=\s*([\d.]+)M", out)
    if not total or not used:
        return 0.0
    t = float(total.group(1))
    u = float(used.group(1))
    return (u / t * 100.0) if t > 0 else 0.0


def budget_ok() -> tuple[bool, str]:
    free_mb, swap_pct = ram_stats()
    reasons = []
    if free_mb < MIN_FREE_MB:
        reasons.append(f"free RAM {free_mb} MB < {MIN_FREE_MB} MB floor")
    if swap_pct > MAX_SWAP_PCT:
        reasons.append(f"swap used {swap_pct:.1f}% > {MAX_SWAP_PCT:.0f}% ceiling")
    if reasons:
        return False, "; ".join(reasons)
    return True, f"free RAM {free_mb} MB, swap {swap_pct:.1f}%"


# ---------------------------------------------------------------------------
# App discovery (dynamic — never hardcode the MFE list)
# ---------------------------------------------------------------------------

def discover_mfes(root: Path) -> list[str]:
    """Sorted list of mfe-* app directory names under frontend/apps/."""
    apps_dir = root / "frontend" / "apps"
    if not apps_dir.is_dir():
        die(f"frontend/apps not found under {root}")
    mfes = sorted(
        p.name for p in apps_dir.iterdir()
        if p.is_dir() and p.name.startswith("mfe-")
    )
    return mfes


# ---------------------------------------------------------------------------
# Worktree resolution
# ---------------------------------------------------------------------------

def git_worktrees() -> dict[str, dict]:
    """name -> {path, branch}. The master tree is keyed by its basename too."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(MASTER_ROOT), "worktree", "list", "--porcelain"],
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        die(f"git worktree list failed: {exc}")

    result: dict[str, dict] = {}
    cur: dict = {}
    for line in out.splitlines():
        if line.startswith("worktree "):
            if cur:
                result[Path(cur["path"]).name] = cur
            cur = {"path": line[len("worktree "):], "branch": None}
        elif line.startswith("branch "):
            cur["branch"] = line[len("branch "):].replace("refs/heads/", "")
        elif line.startswith("detached"):
            cur["branch"] = "(detached)"
    if cur:
        result[Path(cur["path"]).name] = cur
    return result


def resolve_worktree(name: str) -> dict:
    wts = git_worktrees()
    if name not in wts:
        avail = ", ".join(sorted(wts)) or "(none)"
        die(f"unknown worktree '{name}'. Known: {avail}")
    return wts[name]


def baseline_name() -> str:
    """The basename of the master tree — its slot is forced to 0."""
    return MASTER_ROOT.name


# ---------------------------------------------------------------------------
# Slot allocation (persisted, reclaimable)
# ---------------------------------------------------------------------------

def load_ports() -> dict[str, int]:
    return _read_json(PORTS_REGISTRY, {})


def save_ports(reg: dict[str, int]) -> None:
    _write_json(PORTS_REGISTRY, reg)


def assign_slot(worktree: str) -> int:
    """Return the slot for a worktree, assigning the lowest free slot if new.

    The baseline (master tree) is pinned to slot 0.
    """
    reg = load_ports()
    base = baseline_name()
    # Always pin baseline to 0.
    if reg.get(base) != 0:
        reg[base] = 0
        save_ports(reg)

    if worktree in reg:
        return reg[worktree]

    if worktree == base:
        return 0

    used = set(reg.values())
    for slot in range(1, MAX_SLOTS):  # slot 0 reserved for baseline
        if slot not in used:
            reg[worktree] = slot
            save_ports(reg)
            info(f"assigned slot {slot} to worktree '{worktree}'")
            return slot
    die(f"no free slot (max {MAX_SLOTS}). Run `gc` to prune dead reservations.")


def ports_for_slot(slot: int, mfes: list[str]) -> dict:
    base = slot * PORT_STRIDE
    mfe_ports = {name: MFE_BASE + base + i for i, name in enumerate(mfes)}
    return {
        "slot": slot,
        "backend": BACKEND_BASE + base,
        "shell": SHELL_BASE + base,
        "mfes": mfe_ports,
    }


# ---------------------------------------------------------------------------
# Build lock (global, machine-wide)
# ---------------------------------------------------------------------------

class BuildLock:
    """Exclusive flock — only one build runs across the whole machine."""

    def __init__(self) -> None:
        NEXUS_DIR.mkdir(parents=True, exist_ok=True)
        self._fh = None

    def __enter__(self):
        self._fh = open(BUILD_LOCK, "w")
        info("acquiring global build lock (one build at a time)...")
        fcntl.flock(self._fh, fcntl.LOCK_EX)
        info("build lock acquired")
        return self

    def __exit__(self, *exc):
        if self._fh:
            fcntl.flock(self._fh, fcntl.LOCK_UN)
            self._fh.close()
        info("build lock released")


def kill_esbuild() -> None:
    """Best-effort kill of stray esbuild processes between builds."""
    subprocess.run(["pkill", "-f", "esbuild"], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


# ---------------------------------------------------------------------------
# State tracking (PIDs for status/down/gc)
# ---------------------------------------------------------------------------

def load_state() -> dict:
    return _read_json(STATE_FILE, {})


def save_state(state: dict) -> None:
    _write_json(STATE_FILE, state)


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# ---------------------------------------------------------------------------
# Dashboard state model (read-only) — ONE code path shared by `status` and the
# `dashboard` HTTP server. This NEVER acquires the build lock and NEVER triggers
# a build; it only reads registries, probes liveness, and (optionally) probes
# health over HTTP with a short, cached timeout.
# ---------------------------------------------------------------------------

# Health-probe cache: port -> (epoch_checked, "up"|"down"). Shared across the
# dashboard's worker threads so a mid-build slot never blocks the page.
_HEALTH_CACHE: dict[int, tuple[float, str]] = {}
_HEALTH_CACHE_TTL = 3.0   # seconds — re-probe at most this often per port
_HEALTH_TIMEOUT = 1.0     # seconds — per-probe urllib timeout
_HEALTH_LOCK = threading.Lock()


def build_lock_held() -> bool:
    """True if a build is in progress (the global flock is held elsewhere).

    Read-only probe: open the lock file and try a NON-BLOCKING exclusive flock.
    If we get it, no build is running -> release immediately and report free.
    If it would block, a build holds it. Opened read-only so we never need write
    permission on the (possibly root-owned) lock file.
    """
    if not BUILD_LOCK.exists():
        return False
    try:
        fh = open(BUILD_LOCK, "r")
    except OSError:
        return False
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(fh, fcntl.LOCK_UN)
        return False
    except OSError:
        return True
    finally:
        fh.close()


def probe_health(port: int) -> str:
    """Return 'up' or 'down' for a TCP/HTTP service on 127.0.0.1:<port>.

    Cached for _HEALTH_CACHE_TTL seconds. 'up' means the port answered an HTTP
    request with ANY status (even 404 — a live FastAPI/serve.js answers 404 for
    '/'). 'down' means connection refused / timeout / no listener.
    """
    now = time.monotonic()
    with _HEALTH_LOCK:
        cached = _HEALTH_CACHE.get(port)
        if cached and (now - cached[0]) < _HEALTH_CACHE_TTL:
            return cached[1]
    result = "down"
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
        urllib.request.urlopen(req, timeout=_HEALTH_TIMEOUT).close()
        result = "up"
    except urllib.error.HTTPError:
        result = "up"  # answered HTTP (e.g. 404) => the process is alive
    except (urllib.error.URLError, OSError, ValueError):
        result = "down"
    with _HEALTH_LOCK:
        _HEALTH_CACHE[port] = (time.monotonic(), result)
    return result


def _service_health(pid: int | None, alive: bool, port: int) -> str:
    """Map (live port probe, pid liveness) to a single dot state.

    The verdict is a LIVE HTTP PORT PROBE first — NOT pid trust. A port that
    answers any HTTP status is `up` regardless of whether the recorded pid still
    matches the process actually serving it. This is what keeps the dashboard
    honest when a service is killed+relaunched OUTSIDE the tool (a common
    workflow): the recorded pid in env-state.json goes stale, but the port is
    still serving, so the dot must stay green. (The recorded `pid`/`alive` are
    still surfaced in the payload for info — only the up/down verdict moved to
    the live probe.)

    up   : the port answers HTTP (any status) — live, regardless of recorded pid.
    dead : the probe is inconclusive (port unknown) AND a pid was tracked but is
           gone (crashed/exited).
    down : the probe is inconclusive (port unknown) and no live pid, OR a known
           port that is not answering (connection refused / nothing listening).
    """
    # Primary verdict: live port probe. A serving port is `up` even if the
    # recorded pid is stale/wrong; a known port with nothing listening is `down`.
    if port:
        return probe_health(port)
    # Fallback ONLY when the probe is inconclusive (no port known for this role).
    if pid and not alive:
        return "dead"
    return "down"


def _row_slot(row: dict) -> int:
    """Normalise a history row's slot for keying/joining.

    Rows written before per-env keying lack `slot` (and `worktree`); treat a
    missing/None/unparseable slot as slot 0 so old history still attaches to the
    baseline card rather than vanishing.
    """
    slot = row.get("slot")
    try:
        return int(slot)
    except (TypeError, ValueError):
        return 0


def load_build_history(limit_per_project: int = 5) -> dict[tuple[int, str], list[dict]]:
    """Read .nexus/build-history.jsonl -> {(slot, project): [most-recent-first rows]}.

    Keyed by `(slot, project)` so the dashboard joins a build onto ITS OWN env
    card (a build done by slot 1 never shows on slot 0's or slot 2's card even
    when all three built the same project). Returns at most `limit_per_project`
    newest rows per `(slot, project)`. Tolerant of a missing file, a partially
    written final line, and OLD rows lacking `slot`/`worktree` (those normalise
    to slot 0 via `_row_slot`).
    """
    if not BUILD_HISTORY.exists():
        return {}
    by_key: dict[tuple[int, str], list[dict]] = {}
    try:
        lines = BUILD_HISTORY.read_text(errors="replace").splitlines()
    except OSError:
        return {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # skip a torn/partial trailing line
        proj = row.get("project")
        if not proj:
            continue
        by_key.setdefault((_row_slot(row), proj), []).append(row)
    # Newest first; cap per (slot, project).
    for key in by_key:
        by_key[key] = by_key[key][::-1][:limit_per_project]
    return by_key


def collect_dashboard_state(*, probe: bool = True) -> dict:
    """The single JSON model shared by CLI `status` and the dashboard `/api/state`.

    Read-only. Builds the union of `git_worktrees()` and `load_ports()` so a
    worktree that has a reserved slot but no live processes still shows up.

    With probe=False, the health field is reported as 'unknown' (no HTTP probes)
    — used by the CLI so `status` stays instant and never blocks on a port.
    """
    free_mb, swap_pct = ram_stats()
    state = load_state()
    reg = load_ports()
    worktrees = git_worktrees()
    history = load_build_history()

    # State is keyed by worktree basename; map basename -> running env entry.
    running_by_name = dict(state)

    # Union of every worktree we know about (live or just reserved).
    names = set(worktrees) | set(reg) | set(running_by_name)

    envs = []
    for name in sorted(names):
        wt = worktrees.get(name)
        path = wt["path"] if wt else (
            running_by_name.get(name, {}).get("path", ""))
        branch = wt["branch"] if wt else (
            running_by_name.get(name, {}).get("branch"))
        slot = reg.get(name, running_by_name.get(name, {}).get("slot"))

        # Port block for this slot (needs the MFE list from the worktree root).
        ports = {"backend": None, "shell": None, "mfes": {}}
        mfes: list[str] = []
        if slot is not None and path and Path(path).is_dir():
            try:
                mfes = discover_mfes(Path(path))
                block = ports_for_slot(slot, mfes)
                ports = {"backend": block["backend"], "shell": block["shell"],
                         "mfes": block["mfes"]}
            except SystemExit:
                pass  # frontend/apps missing in this tree — leave ports empty

        # Per-service status from the tracked procs.
        procs = running_by_name.get(name, {}).get("procs", {})
        services = []
        for role in sorted(procs):
            meta = procs[role]
            pid = meta.get("pid")
            port = meta.get("port")
            alive = bool(pid and pid_alive(pid))
            health = _service_health(pid, alive, port) if probe else "unknown"
            services.append({
                "role": role, "pid": pid, "port": port,
                "alive": alive, "health": health,
            })

        # Build rows for THIS env only: join history by (slot, project) so a
        # card shows only its own builds. An unreserved worktree (slot None)
        # normalises to slot 0 — same rule the reader uses for old rows. The
        # emitted row carries `slot` so the log viewer can tail the right
        # per-env log via /api/log?project=<p>&slot=<N>.
        builds = []
        join_slot = 0 if slot is None else slot
        proj_names = ["frontend"] + mfes
        for proj in proj_names:
            for row in history.get((join_slot, proj), []):
                builds.append({
                    "project": proj,
                    "slot": join_slot,
                    "status": row.get("status"),
                    "when": row.get("end_iso") or row.get("start_iso"),
                    "duration_s": row.get("duration_s"),
                })
        builds.sort(key=lambda b: (b.get("when") or ""), reverse=True)

        envs.append({
            "worktree": name,
            "slot": slot,
            "branch": branch,
            "path": path,
            "exists": name in worktrees,
            "running": name in running_by_name,
            "ports": ports,
            "services": services,
            "builds": builds[:8],
        })

    return {
        "free_mb": free_mb,
        "min_free_mb": MIN_FREE_MB,
        "swap_pct": round(swap_pct, 1),
        "max_swap_pct": MAX_SWAP_PCT,
        "build_lock_held": build_lock_held(),
        "env_count": len(running_by_name),
        "envs": envs,
        "generated_iso": _now_iso(),
    }


# ---------------------------------------------------------------------------
# Build + serve primitives
# ---------------------------------------------------------------------------

# Markers ng/esbuild prints when the bundle has been written successfully.
# We treat the build as DONE on either of these even if the `ng` process never
# exits (see _wait_for_build below for why it doesn't).
_BUILD_DONE_MARKERS = (
    "Application bundle generation complete",
    "Output location:",
)
# Hard ceiling for a single build. A real build of one MFE on the 8 GB box is
# well under this; if we never see a done-marker by here it's a genuine failure.
_BUILD_TIMEOUT_S = 600
# Once a done-marker appears, give the process this long to exit on its own
# before we reap its process group (the esbuild --service child keeps it alive).
_POST_DONE_GRACE_S = 5


def _dist_for_project(root: Path, project: str) -> Path:
    """dist/<dist-name>/browser for a project. Shell's dist name is 'frontend'."""
    dist_name = SHELL_DIST_NAME if project == "frontend" else project
    return served_dist_root(root, dist_name)


def _kill_process_group(pgid: int) -> None:
    """SIGTERM then SIGKILL the whole process group (ng + npm + esbuild service).

    Best-effort: a stray descendant may be unsignalable by our uid (e.g. a
    process owned by root). We swallow PermissionError because the global
    pkill-esbuild sweep in ng_build's finally clause is the real safety net, and
    by the time we call this the build's output has already been verified.
    """
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pgid, sig)
        except ProcessLookupError:
            return
        except PermissionError:
            info(f"killpg({pgid}) not permitted for a group member; "
                 f"relying on esbuild sweep")
            return
        time.sleep(0.5)


def _wait_for_build(proc: subprocess.Popen, logpath: Path, project: str) -> None:
    """Wait for a one-shot `ng build` to finish.

    ROOT-CAUSE NOTE (why this is not a simple .wait()):
    Angular 21.2.x's application builder leaves a persistent `esbuild --service`
    child running after the bundle is written, so the `ng build` process never
    exits — `subprocess.run(...).wait()` would block forever (observed 8m+ at
    ~0% CPU; confirmed even for a standalone `ng build`, so it is NOT a Python
    pipe-buffer deadlock). We therefore tail the per-app log for a done-marker
    and, once seen (and the dist output exists), reap the whole process group to
    sweep the orphan esbuild service, then move on. A genuine build failure is
    detected by the process exiting non-zero with no done-marker, or by the
    timeout elapsing with no done-marker.
    """
    dist = _dist_for_project(proc_root(proc), project)
    deadline = time.monotonic() + _BUILD_TIMEOUT_S
    pgid = os.getpgid(proc.pid)
    done = False
    while time.monotonic() < deadline:
        rc = proc.poll()
        # Read the log for a completion marker.
        try:
            text = logpath.read_text(errors="replace")
        except OSError:
            text = ""
        if any(m in text for m in _BUILD_DONE_MARKERS):
            done = True
            break
        if rc is not None:
            # Process exited before any done-marker. Could be a clean fast exit
            # whose marker we just missed, or a real failure.
            if any(m in text for m in _BUILD_DONE_MARKERS):
                done = True
            elif rc != 0 or not dist.exists():
                _kill_process_group(pgid)
                _tail_log(logpath)
                die(f"ng build {project} failed (exit {rc}); see {logpath}")
            else:
                done = True  # exited 0 and dist exists
            break
        time.sleep(1.0)

    if not done:
        _kill_process_group(pgid)
        _tail_log(logpath)
        die(f"ng build {project} timed out after {_BUILD_TIMEOUT_S}s "
            f"with no completion marker; see {logpath}")

    # Done-marker seen. Give it a brief grace to self-exit, then reap the group.
    grace = time.monotonic() + _POST_DONE_GRACE_S
    while time.monotonic() < grace and proc.poll() is None:
        time.sleep(0.3)
    _kill_process_group(pgid)

    if not dist.exists():
        _tail_log(logpath)
        die(f"ng build {project} reported done but dist {dist} is missing; "
            f"see {logpath}")
    info(f"ng build {project} OK -> {dist} (log {logpath})")


# proc_root: stash the build root on the Popen object so _wait_for_build can find
# the dist without re-threading it through every call.
def proc_root(proc: subprocess.Popen) -> Path:
    return getattr(proc, "_mesell_root")


def _tail_log(logpath: Path, n: int = 25) -> None:
    try:
        lines = logpath.read_text(errors="replace").splitlines()[-n:]
    except OSError:
        return
    sys.stderr.write(f"--- last {len(lines)} lines of {logpath} ---\n")
    for ln in lines:
        sys.stderr.write(ln + "\n")


def _now_iso() -> str:
    """UTC timestamp, second-resolution, ISO-8601 with trailing Z."""
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_build(project: str, start_iso: str, end_iso: str,
                 status: str, duration_s: float,
                 worktree: str | None = None, slot: int | None = None) -> None:
    """Append one build outcome to .nexus/build-history.jsonl (append-only).

    Each row carries `worktree` + `slot` so the dashboard can join a build onto
    ITS OWN env card by `(slot, project)` rather than by project alone — three
    slots building the same `mfe-catalog` now produce distinguishable rows.
    Old rows that predate this change lack both fields; the reader treats them
    as slot 0 / "unknown" worktree (see `load_build_history`).

    Best-effort: a recorder failure must never break a build. The file is a
    JSON-Lines stream (one object per line) so it is cheap to append and tail.
    """
    try:
        NEXUS_DIR.mkdir(parents=True, exist_ok=True)
        row = {
            "project": project,
            "worktree": worktree,
            "slot": slot,
            "start_iso": start_iso,
            "end_iso": end_iso,
            "status": status,
            "duration_s": round(duration_s, 1),
        }
        with open(BUILD_HISTORY, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError as exc:
        info(f"build-history record skipped ({project}): {exc}")


def ng_build(root: Path, project: str, *, stub: bool,
             slot: int | None = None, worktree: str | None = None) -> None:
    """Build one Angular project as a one-shot, under the global lock.

    Each build's stdout+stderr go to a per-ENV log file keyed by `slot`
    (`.nexus/build-slot<N>-<project>.log`, via `build_log_path`) — never an
    undrained PIPE and never a project-only path shared across worktrees. The
    build runs in its OWN process group, and we reap that group once the bundle
    is written — because `ng build` does not exit on its own on this Angular
    version (it leaks a persistent esbuild --service child). See _wait_for_build
    for the full root-cause note. `slot`/`worktree` are also stamped onto the
    build-history row so the dashboard can attribute the build to its env.
    """
    if stub:
        info(f"[stub] would run: ng build {project}  (cwd={root}/frontend)")
        return
    kill_esbuild()  # clear any stray service from a prior build BEFORE starting
    logpath = build_log_path(slot, project)
    NEXUS_DIR.mkdir(parents=True, exist_ok=True)
    info(f"ng build {project} ... (log {logpath})")
    # Build-history bookkeeping (additive — does not change build behaviour).
    start_iso = _now_iso()
    start_mono = time.monotonic()
    build_ok = False
    with open(logpath, "w") as logfh:
        proc = subprocess.Popen(
            ["npx", "ng", "build", project, "--configuration=development"],
            cwd=str(root / "frontend"),
            stdout=logfh,
            stderr=subprocess.STDOUT,
            start_new_session=True,  # own process group -> reliable group kill
        )
    proc._mesell_root = root  # type: ignore[attr-defined]
    try:
        _wait_for_build(proc, logpath, project)  # die()s on failure/timeout
        build_ok = True
    finally:
        kill_esbuild()  # belt-and-suspenders sweep after each build
        # _wait_for_build calls die() (SystemExit) on a failed/timed-out build,
        # so this finally records "ok" on success and "failed" on any exit.
        record_build(project, start_iso, _now_iso(),
                     "ok" if build_ok else "failed",
                     time.monotonic() - start_mono,
                     worktree=worktree, slot=slot)


def served_dist_root(root: Path, project_dist_name: str) -> Path:
    """The static directory serve.js serves: dist/<project>/browser."""
    return root / "frontend" / "dist" / project_dist_name / "browser"


def write_env_manifest(dist_root: Path, manifest: dict) -> None:
    """Write the per-env runtime federation manifest to the served dist root.

    This file is generated, never committed. It points touched MFEs at this
    env's local ports and everything else at the baseline ports.
    """
    dist_root.mkdir(parents=True, exist_ok=True)
    target = dist_root / "federation.manifest.json"
    target.write_text(json.dumps(manifest, indent=2) + "\n")
    info(f"wrote per-env manifest -> {target}")


def serve_static(root: Path, dist_root: Path, port: int, *, stub: bool,
                 backend_port: int | None = None) -> int | None:
    serve_js = root / SERVE_JS_REL
    if not serve_js.exists():
        die(f"serve.js not found at {serve_js}")
    # Only the SHELL passes backend_port: it hosts the federated app, which makes
    # relative /api/v1/* calls, so serve.js reverse-proxies those to the backend.
    # MFE remotes serve only static remoteEntry chunks (no API calls) -> no proxy.
    backend = f"http://127.0.0.1:{backend_port}" if backend_port else None
    if stub:
        proxy_note = f" (proxy -> {backend})" if backend else ""
        info(f"[stub] would serve {dist_root} on :{port}{proxy_note}")
        return None
    log = NEXUS_DIR / f"serve-{port}.log"
    fh = open(log, "w")
    cmd = ["node", str(serve_js), str(dist_root), str(port)]
    if backend:
        cmd.append(backend)
    proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
    proxy_note = f" (proxy -> {backend})" if backend else ""
    info(f"serving {dist_root} on :{port} (pid {proc.pid}, log {log}){proxy_note}")
    return proc.pid


def serve_backend(root: Path, port: int, *, stub: bool) -> int | None:
    if stub:
        info(f"[stub] would run uvicorn on :{port} (cwd={root}/backend)")
        return None
    venv_uvicorn = root / "backend" / ".venv" / "bin" / "uvicorn"
    uvicorn_cmd = str(venv_uvicorn) if venv_uvicorn.exists() else "uvicorn"
    log = NEXUS_DIR / f"backend-{port}.log"
    fh = open(log, "w")
    proc = subprocess.Popen(
        [uvicorn_cmd, "app.main:app", "--host", "127.0.0.1",
         "--port", str(port), "--reload"],
        cwd=str(root / "backend"),
        stdout=fh, stderr=subprocess.STDOUT,
    )
    info(f"backend uvicorn on :{port} (pid {proc.pid}, log {log})")
    return proc.pid


# ---------------------------------------------------------------------------
# Touched-MFE inference
# ---------------------------------------------------------------------------

def infer_touched_mfes(root: Path, branch: str | None, all_mfes: list[str]) -> tuple[list[str], bool]:
    """Return (touched_mfes, shell_touched) by diffing develop...<branch>.

    Scoped to frontend/apps/. If branch is unknown/baseline, returns ([], False).
    """
    if not branch or branch in ("(detached)", "develop"):
        return [], False
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "diff", "--name-only",
             f"origin/develop...{branch}", "--", "frontend/apps"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return [], False

    touched = set()
    shell_touched = False
    for line in out.splitlines():
        parts = line.split("/")
        if len(parts) >= 3 and parts[0] == "frontend" and parts[1] == "apps":
            app = parts[2]
            if app == SHELL_APP_DIR:
                shell_touched = True
            elif app in all_mfes:
                touched.add(app)
    return sorted(touched), shell_touched


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_ports(args) -> None:
    wt = resolve_worktree(args.worktree)
    root = Path(wt["path"])
    mfes = discover_mfes(root)
    slot = assign_slot(args.worktree)
    block = ports_for_slot(slot, mfes)
    print(f"worktree : {args.worktree}")
    print(f"branch   : {wt['branch']}")
    print(f"slot     : {block['slot']}")
    print(f"backend  : http://127.0.0.1:{block['backend']}")
    print(f"shell    : http://127.0.0.1:{block['shell']}")
    for name, p in block["mfes"].items():
        print(f"  {name:<16}: http://127.0.0.1:{p}")


def cmd_status(args) -> None:
    # Shares ONE code path with the dashboard via collect_dashboard_state().
    # probe=False keeps `status` instant (no HTTP health probes / blocking).
    model = collect_dashboard_state(probe=False)
    lock = "HELD (build in progress)" if model["build_lock_held"] else "free"
    print(f"RAM free: {model['free_mb']} MB    swap used: {model['swap_pct']:.1f}%"
          f"    build lock: {lock}    "
          f"(guard: free>={MIN_FREE_MB}MB, swap<={MAX_SWAP_PCT:.0f}%)")
    print()
    running = [e for e in model["envs"] if e["services"]]
    if not running:
        print("No running envs tracked.")
    else:
        print(f"{'worktree':<24}{'slot':<6}{'role':<14}{'port':<8}{'pid':<8}{'alive'}")
        print("-" * 70)
        for env in running:
            slot = env.get("slot", "?")
            for svc in env["services"]:
                pid = svc.get("pid")
                port = svc.get("port") or ""
                alive = "yes" if svc.get("alive") else "DEAD"
                print(f"{env['worktree']:<24}{str(slot):<6}{svc['role']:<14}"
                      f"{str(port):<8}{str(pid):<8}{alive}")
    print()
    print("Slot reservations:")
    for env in sorted((e for e in model["envs"] if e["slot"] is not None),
                      key=lambda e: e["slot"]):
        exists = "exists" if env["exists"] else "MISSING (gc to prune)"
        print(f"  slot {env['slot']}: {env['worktree']}  [{exists}]")


def cmd_up(args) -> None:
    base = baseline_name()
    wt = resolve_worktree(args.worktree)
    root = Path(wt["path"])
    branch = wt["branch"]
    all_mfes = discover_mfes(root)
    slot = assign_slot(args.worktree)
    block = ports_for_slot(slot, all_mfes)
    stub = args.stub

    # 1. BUDGET CHECK FIRST — refuse loudly, suggest a `down`.
    ok, summary = budget_ok()
    if not ok and not stub:
        state = load_state()
        idle = [n for n in state if n != args.worktree]
        hint = (f" Suggest: `meesell_env.py down {idle[0]}`" if idle else
                " Suggest closing idle apps or rebooting.")
        die(f"RAM budget refused up: {summary}.{hint}")
    info(f"budget ok: {summary}")

    # 2. Decide touched MFEs + shell-touched.
    if args.mfe is not None:
        touched = [m.strip() for m in args.mfe.split(",") if m.strip()]
        bad = [m for m in touched if m not in all_mfes]
        if bad:
            die(f"unknown MFE(s): {', '.join(bad)}. Known: {', '.join(all_mfes)}")
        # --mfe is explicit on MFEs; infer shell-touched from git separately.
        _, shell_touched = infer_touched_mfes(root, branch, all_mfes)
    else:
        touched, shell_touched = infer_touched_mfes(root, branch, all_mfes)

    info(f"touched MFEs: {touched or '(none — pure baseline shell)'}; "
         f"shell touched: {shell_touched}")

    # 3. Build per-env runtime manifest: touched -> local ports, rest -> baseline ports.
    baseline_slot = 0
    baseline_block = ports_for_slot(baseline_slot, all_mfes)
    manifest = {}
    for name in all_mfes:
        if name in touched:
            p = block["mfes"][name]
        else:
            p = baseline_block["mfes"][name]
        manifest[name] = f"http://localhost:{p}/remoteEntry.json"

    # 4. Build (serialized) — only shell-if-touched + touched MFEs.
    procs: dict[str, dict] = {}
    with BuildLock():
        if shell_touched:
            ng_build(root, "frontend", stub=stub, slot=slot, worktree=args.worktree)
        for name in touched:
            ng_build(root, name, stub=stub, slot=slot, worktree=args.worktree)

    # 5. Determine which shell dist to serve.
    #    - shell touched -> this worktree's freshly built shell (its own dist).
    #    - else -> a per-slot COPY of the baseline shell dist, so each env owns
    #      its own federation.manifest.json and concurrent envs never clobber a
    #      shared manifest. The copy is cheap (~16 MB) and lives under .nexus/.
    if shell_touched:
        shell_dist = served_dist_root(root, SHELL_DIST_NAME)
    else:
        baseline_shell = served_dist_root(MASTER_ROOT, SHELL_DIST_NAME)
        if not baseline_shell.exists() and not stub:
            die(f"baseline shell dist missing at {baseline_shell}. "
                f"Run `meesell_env.py baseline up` first.")
        shell_dist = NEXUS_DIR / f"shell-dist-slot-{slot}" / "browser"
        if not stub:
            if shell_dist.exists():
                shutil.rmtree(shell_dist.parent)
            shutil.copytree(baseline_shell, shell_dist)
            info(f"copied baseline shell dist -> {shell_dist} (per-env manifest isolation)")

    # 6. Write the per-env manifest into the served shell dist root.
    if not stub:
        write_env_manifest(shell_dist, manifest)
    else:
        info(f"[stub] manifest -> {shell_dist}/federation.manifest.json:")
        for k, v in manifest.items():
            info(f"[stub]   {k} -> {v}")

    # 7. Serve shell — with a backend proxy target so the federated app's relative
    #    /api/v1/* calls reach the backend. Target = this env's backend if touched,
    #    else the baseline backend (slot 0). Computed here so the shell can proxy.
    backend_touched = is_backend_touched(root, branch)
    shell_backend_port = (block["backend"] if backend_touched
                          else baseline_block["backend"])
    pid = serve_static(root, shell_dist, block["shell"], stub=stub,
                       backend_port=shell_backend_port)
    if pid:
        procs["shell"] = {"pid": pid, "port": block["shell"]}

    # 8. Serve touched MFEs from this env; untouched are served by baseline (slot 0).
    for name in touched:
        mfe_dist = served_dist_root(root, name)
        pid = serve_static(root, mfe_dist, block["mfes"][name], stub=stub)
        if pid:
            procs[name] = {"pid": pid, "port": block["mfes"][name]}

    # 9. Backend: only if touched; else point at baseline backend.
    if backend_touched:
        pid = serve_backend(root, block["backend"], stub=stub)
        if pid:
            procs["backend"] = {"pid": pid, "port": block["backend"]}
    else:
        info(f"backend not touched -> reuse baseline backend on "
             f":{baseline_block['backend']} (not started here)")

    # 10. Persist state.
    if not stub:
        state = load_state()
        state[args.worktree] = {
            "slot": slot,
            "path": str(root),
            "branch": branch,
            "procs": procs,
            "started": int(time.time()),
            "shell_dist": str(shell_dist),
        }
        save_state(state)

    info(f"env '{args.worktree}' up on slot {slot}. "
         f"Open shell: http://localhost:{block['shell']}")
    if not backend_touched:
        info(f"  (API expected at baseline :{baseline_block['backend']})")


def is_backend_touched(root: Path, branch: str | None) -> bool:
    if not branch or branch in ("(detached)", "develop"):
        return False
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), "diff", "--name-only",
             f"origin/develop...{branch}", "--", "backend"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return False
    return bool(out.strip())


def _stop_procs(env: dict) -> int:
    stopped = 0
    for role, meta in env.get("procs", {}).items():
        pid = meta.get("pid")
        if pid and pid_alive(pid):
            try:
                os.kill(pid, signal.SIGTERM)
                stopped += 1
                info(f"stopped {role} (pid {pid})")
            except ProcessLookupError:
                pass
    return stopped


def cmd_down(args) -> None:
    state = load_state()
    if args.worktree not in state:
        die(f"no running env tracked for '{args.worktree}'")
    env = state[args.worktree]
    stopped = _stop_procs(env)
    # Remove the per-slot baseline-shell copy if this env used one.
    slot = env.get("slot")
    if slot is not None:
        copy_dir = NEXUS_DIR / f"shell-dist-slot-{slot}"
        if copy_dir.exists():
            shutil.rmtree(copy_dir, ignore_errors=True)
    del state[args.worktree]
    save_state(state)
    info(f"env '{args.worktree}' down ({stopped} processes). Slot reservation kept.")


def cmd_baseline(args) -> None:
    if args.action not in ("up", "refresh"):
        die("baseline action must be 'up' or 'refresh'")
    stub = args.stub
    root = MASTER_ROOT
    all_mfes = discover_mfes(root)
    assign_slot(baseline_name())  # pin slot 0
    block = ports_for_slot(0, all_mfes)

    ok, summary = budget_ok()
    if not ok and not stub:
        die(f"RAM budget refused baseline build: {summary}")
    info(f"budget ok: {summary}")

    # Build shell + ALL MFEs, serialized. Baseline is always slot 0.
    base_wt = baseline_name()
    with BuildLock():
        ng_build(root, "frontend", stub=stub, slot=0, worktree=base_wt)
        for name in all_mfes:
            ng_build(root, name, stub=stub, slot=0, worktree=base_wt)

    # Baseline manifest: all remotes at baseline ports.
    shell_dist = served_dist_root(root, SHELL_DIST_NAME)
    manifest = {
        name: f"http://localhost:{block['mfes'][name]}/remoteEntry.json"
        for name in all_mfes
    }
    if not stub:
        write_env_manifest(shell_dist, manifest)

    procs: dict[str, dict] = {}
    # Shell proxies the baseline app's relative /api/v1/* calls to the slot-0 backend.
    pid = serve_static(root, shell_dist, block["shell"], stub=stub,
                       backend_port=block["backend"])
    if pid:
        procs["shell"] = {"pid": pid, "port": block["shell"]}
    for name in all_mfes:
        pid = serve_static(root, served_dist_root(root, name),
                           block["mfes"][name], stub=stub)
        if pid:
            procs[name] = {"pid": pid, "port": block["mfes"][name]}
    pid = serve_backend(root, block["backend"], stub=stub)
    if pid:
        procs["backend"] = {"pid": pid, "port": block["backend"]}

    if not stub:
        state = load_state()
        state[baseline_name()] = {
            "slot": 0, "path": str(root), "branch": "develop",
            "procs": procs, "started": int(time.time()),
            "shell_dist": str(shell_dist),
        }
        save_state(state)
    info(f"baseline {args.action} complete on slot 0. "
         f"Shell: http://localhost:{block['shell']}")


def cmd_gc(args) -> None:
    # 1. Stop dead/orphaned tracked processes.
    state = load_state()
    changed = False
    for wt_name in list(state):
        env = state[wt_name]
        live = {r: m for r, m in env.get("procs", {}).items()
                if m.get("pid") and pid_alive(m["pid"])}
        if not live:
            info(f"gc: env '{wt_name}' has no live processes — removing from state")
            del state[wt_name]
            changed = True
        elif len(live) != len(env.get("procs", {})):
            env["procs"] = live
            changed = True
    if changed:
        save_state(state)

    # 2. Prune slot reservations for worktrees that no longer exist.
    reg = load_ports()
    existing = set(git_worktrees())
    pruned = []
    for wt_name in list(reg):
        if wt_name == baseline_name():
            continue
        if wt_name not in existing:
            pruned.append((wt_name, reg.pop(wt_name)))
    if pruned:
        save_ports(reg)
        for n, s in pruned:
            info(f"gc: pruned slot {s} reservation for dead worktree '{n}'")
    if not pruned and not changed:
        info("gc: nothing to do.")


# ---------------------------------------------------------------------------
# Dashboard HTTP server (read-only). Stdlib ThreadingHTTPServer; serves the
# self-contained SPA + a JSON state API + a build-log tail. NEVER builds.
# ---------------------------------------------------------------------------

DASHBOARD_HTML = Path(__file__).resolve().parent / "env_dashboard" / "index.html"
_LOG_TAIL_BYTES = 64 * 1024   # tail at most this many bytes of a build log
_PROJECT_RE = re.compile(r"^[A-Za-z0-9_.-]+$")   # guard /api/log?project=


# ===========================================================================
# DEV LOG MONITOR (V1) — service-keyed runtime-log stream + error radar.
# Spec: docs/specs/DEV_LOG_MONITOR.md. Additive, read-only, stdlib-only,
# dev-only. NEVER builds, NEVER holds the build lock. Every line passes the
# redaction filter (§6) before it is parsed, returned, or counted.
# ===========================================================================

_SERVICE_RE = re.compile(r"^[A-Za-z0-9_.-]+$")  # guard /api/logs?service=
_LOGS_TAIL_BYTES = 96 * 1024     # runtime-log tail window (per request)
_LOGS_MAX_LINES = 400            # hard cap on lines returned per /api/logs call
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# Optional extra-log config (DF-3): a dev may opt-in extra service log paths,
# e.g. {"extra": {"postgres": "/opt/homebrew/var/log/postgresql@16.log"}}.
# Default-empty / absent => zero behaviour change.
LOGMONITOR_CONFIG = NEXUS_DIR / "logmonitor.json"


# ---------------------------------------------------------------------------
# §6 Secret redaction — ONE ordered list, applied at EVERY ingest path.
# Each entry is (compiled_regex, replacement). Adding a pattern is one line.
# This is a hard never-echo-creds rule; it runs BEFORE parse/display/count.
# ---------------------------------------------------------------------------

_REDACT_MASK = "***REDACTED***"

# Known secret env-var names whose echoed *value* must be masked.
_SECRET_ENV_NAMES = (
    "JWT_SECRET", "MSG91_AUTH_KEY", "MSG91_TEMPLATE_ID", "GEMINI_API_KEY",
    "GEMINI_API_KEY_CI", "RAZORPAY_KEY_SECRET", "RAZORPAY_KEY_ID",
    "RAZORPAY_WEBHOOK_SECRET", "REFRESH_TOKEN_PEPPER", "AUDIT_PII_SALT",
    "LANGFUSE_SECRET_KEY", "POSTGRES_PASSWORD", "VALKEY_PASSWORD",
    "DATABASE_URL", "VALKEY_URL", "CELERY_BROKER_URL", "CELERY_RESULT_BACKEND",
)
_SECRET_ENV_ALT = "|".join(re.escape(n) for n in _SECRET_ENV_NAMES)

_REDACTIONS: list[tuple[re.Pattern, str]] = [
    # Authorization / Bearer tokens (header or inline).
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-+/=]+"), "Bearer " + _REDACT_MASK),
    (re.compile(r"(?i)\bAuthorization\s*[:=]\s*\S+"), "Authorization: " + _REDACT_MASK),
    # JWTs — the xxxxx.yyyyy.zzzzz three-segment base64url shape.
    (re.compile(r"\beyJ[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+\.[A-Za-z0-9_\-]+"), _REDACT_MASK),
    (re.compile(r"\b[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), _REDACT_MASK),
    # Cookie / set-cookie values.
    (re.compile(r"(?i)\b(set-)?cookie\s*[:=]\s*\S+"), "cookie: " + _REDACT_MASK),
    # OTP codes — explicit otp/code fields (incl dev bypass 000000).
    (re.compile(r'(?i)\b(otp|code)\b["\']?\s*[:=]\s*["\']?(\d{4,8})'), r"\1=" + _REDACT_MASK),
    # Standalone 4-8 digit code near an otp/verify context.
    (re.compile(r"(?i)(otp|verify|2fa)[^\d]{0,16}\b\d{4,8}\b"), lambda m: m.group(0).replace(
        re.search(r"\d{4,8}", m.group(0)).group(0), _REDACT_MASK)),
    # Secret env-var name echoed with its value.
    (re.compile(r"(?i)\b(" + _SECRET_ENV_ALT + r")\s*[:=]\s*\S+"), r"\1=" + _REDACT_MASK),
    # Email — keep the domain, mask the local part (account-link debuggable).
    (re.compile(r"\b([A-Za-z0-9])[A-Za-z0-9._%+\-]*(@[A-Za-z0-9.\-]+\.[A-Za-z]{2,})"),
     r"\1***\2"),
    # Phone — +91 + 10 digits => mask the middle.
    (re.compile(r"(\+\d{1,3})\d{6,9}(\d{2,4})\b"), r"\1******\2"),
]


def redact(text: str) -> str:
    """Apply the ordered §6 redaction list. Hard never-echo-creds boundary.

    Run on every line before it is parsed, returned, displayed, or counted.
    Best-effort: a redactor failure must never leak the raw line, so any
    exception falls back to a fully-masked line.
    """
    try:
        for pat, repl in _REDACTIONS:
            text = pat.sub(repl, text)
        return text
    except Exception:  # noqa: BLE001 — fail closed: never return a raw line
        return _REDACT_MASK


# ---------------------------------------------------------------------------
# §3.1 Service-keyed log registry (in-memory name->path resolver).
# DF-1 decision: pure resolver (no symlink farm) so up/down/baseline/gc
# lifecycle behaviour is untouched. Build logs stay separate (already exposed
# via /api/log). Out-of-band procs (celery/postgres/valkey) are best-effort
# via the optional logmonitor.json extra-path config (DF-3, default-empty).
# ---------------------------------------------------------------------------

def _load_logmonitor_extra() -> dict[str, str]:
    cfg = _read_json(LOGMONITOR_CONFIG, {}) if LOGMONITOR_CONFIG.exists() else {}
    extra = cfg.get("extra", {}) if isinstance(cfg, dict) else {}
    return {str(k): str(v) for k, v in extra.items()} if isinstance(extra, dict) else {}


def service_log_index(state: dict | None = None) -> dict[str, Path]:
    """Map each live service key -> its on-disk runtime log file.

    service keys: `backend`, `shell`, `mfe-<name>` (derived from each env's
    port block) + any opt-in extra paths from logmonitor.json. Build logs are
    intentionally excluded (they have their own /api/log endpoint).
    """
    if state is None:
        state = collect_dashboard_state(probe=False)
    index: dict[str, Path] = {}
    for env in state.get("envs", []):
        ports = env.get("ports") or {}
        bport = ports.get("backend")
        if bport:
            index.setdefault("backend", NEXUS_DIR / f"backend-{bport}.log")
        sport = ports.get("shell")
        if sport:
            index.setdefault("shell", NEXUS_DIR / f"serve-{sport}.log")
        for mfe_name, mport in (ports.get("mfes") or {}).items():
            if mport:
                index.setdefault(mfe_name, NEXUS_DIR / f"serve-{mport}.log")
    # Best-effort celery: tool doesn't spawn it, but tail it if it logs here.
    for path in sorted(NEXUS_DIR.glob("celery-*.log")):
        index.setdefault("celery", path)
    # Opt-in extra paths (postgres/valkey/...): absolute or .nexus-relative.
    for key, raw in _load_logmonitor_extra().items():
        p = Path(raw)
        index.setdefault(key, p if p.is_absolute() else (NEXUS_DIR / raw))
    return index


# ---------------------------------------------------------------------------
# §3.2 Line parsing — normalize a raw log line into {ts, service, level, msg}.
# Level is parsed from uvicorn / Python-logging tokens; serve.js lines default
# INFO unless an error signature upgrades them.
# ---------------------------------------------------------------------------

_LEVEL_RE = re.compile(r"\b(CRITICAL|FATAL|ERROR|WARNING|WARN|INFO|DEBUG|TRACE)\b")
_HTTP_5XX_RE = re.compile(r"\b5\d\d\b")
_HTTP_4XX_RE = re.compile(r"\b4\d\d\b")


def parse_log_line(line: str, service: str) -> dict:
    """Redact FIRST, then classify into {service, level, msg}. ts kept implicit
    (the raw line carries its own timestamp text; we don't re-stamp)."""
    safe = redact(line.rstrip("\n"))
    m = _LEVEL_RE.search(safe)
    if m:
        tok = m.group(1).upper()
        level = "WARN" if tok in ("WARNING", "WARN") else (
            "ERROR" if tok in ("ERROR", "CRITICAL", "FATAL") else "INFO")
    else:
        level = "INFO"
    up = safe.lower()
    if level == "INFO":
        if ("traceback (most recent call last)" in up
                or "internal server error" in up or _HTTP_5XX_RE.search(safe)):
            level = "ERROR"
        elif "refused to load" in up or "deprecat" in up:
            level = "WARN"
    return {"service": service, "level": level, "msg": safe}


def tail_service_log(path: Path, *, max_bytes: int, max_lines: int) -> tuple[list[str], int, bool]:
    """Return (lines, size, truncated). Read at most max_bytes from the tail."""
    if not path.exists():
        return [], 0, False
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - max_bytes))
        raw = fh.read()
    text = _ANSI_RE.sub("", raw.decode("utf-8", errors="replace"))
    lines = [ln for ln in text.split("\n") if ln.strip()]
    truncated = size > max_bytes
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
        truncated = True
    return lines, size, truncated


# ---------------------------------------------------------------------------
# §3.3 Error radar — data-driven detectors over a rolling window.
# Each detector: {name, pattern, window_s, threshold, severity}. A line that
# matches a detector bumps its rolling-window deque; a detector is "firing"
# when the window count >= threshold. Adding a signature is a one-line edit.
# ---------------------------------------------------------------------------

_RADAR_DETECTORS = [
    {"name": "auth-401-storm",
     "pattern": re.compile(r"401.*\b/(api/v1/)?auth/(me|refresh)\b"),
     "window_s": 60, "threshold": 3, "severity": "error"},
    {"name": "python-traceback",
     "pattern": re.compile(r"Traceback \(most recent call last\)"),
     "window_s": 120, "threshold": 1, "severity": "error"},
    {"name": "http-500",
     "pattern": re.compile(r"(\b500\b.*\b(GET|POST|PUT|PATCH|DELETE)\b|Internal Server Error)"),
     "window_s": 60, "threshold": 1, "severity": "error"},
    {"name": "csp-violation",
     "pattern": re.compile(r"(?i)(Content-Security-Policy|Refused to load)"),
     "window_s": 120, "threshold": 1, "severity": "warn"},
    {"name": "login-redirect",
     "pattern": re.compile(r"(?i)(redirect.*/login|authGuard.*/login|->\s*/login)"),
     "window_s": 60, "threshold": 3, "severity": "warn"},
    {"name": "federation-singleton",
     "pattern": re.compile(r"(?i)(Native Federation|singleton|shared).*(mismatch|version|warn)"),
     "window_s": 300, "threshold": 1, "severity": "warn"},
    {"name": "route-404",
     "pattern": re.compile(r"\b404\b.*\s/api/"),
     "window_s": 60, "threshold": 1, "severity": "warn"},
]


class ErrorRadar:
    """Server-side detector bank with rolling-window counters.

    Stateful + in-memory only: per-detector deques of (monotonic_ts) plus the
    last redacted sample line + service. Bounded by window pruning, so RAM stays
    flat. Thread-safe (the ThreadingHTTPServer may classify concurrently)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._hits: dict[str, list[float]] = {d["name"]: [] for d in _RADAR_DETECTORS}
        self._sample: dict[str, tuple[str, str]] = {}  # name -> (sample, service)

    def classify(self, parsed: dict) -> None:
        """Feed one ALREADY-REDACTED parsed line through every detector."""
        msg = parsed.get("msg", "")
        service = parsed.get("service", "?")
        now = time.monotonic()
        with self._lock:
            for d in _RADAR_DETECTORS:
                if d["pattern"].search(msg):
                    self._hits[d["name"]].append(now)
                    self._sample[d["name"]] = (msg[:240], service)

    def snapshot(self) -> dict:
        now = time.monotonic()
        counters = []
        with self._lock:
            for d in _RADAR_DETECTORS:
                name = d["name"]
                win = d["window_s"]
                hits = [t for t in self._hits[name] if now - t <= win]
                self._hits[name] = hits  # prune in place
                count = len(hits)
                sample, service = self._sample.get(name, ("", ""))
                counters.append({
                    "name": name, "window_s": win, "count": count,
                    "threshold": d["threshold"], "severity": d["severity"],
                    "firing": count >= d["threshold"],
                    "sample": sample, "service": service,
                })
        return {"generated_iso": _now_iso(), "counters": counters}

    def ingest_recent(self, max_per_service: int = 200) -> None:
        """Best-effort: feed the tail of every service log through the radar so
        counters reflect what's on disk right now. Called on each /api/radar so
        the radar needs no background thread (read-only, stdlib ethos)."""
        try:
            index = service_log_index()
        except Exception:  # noqa: BLE001
            return
        for service, path in index.items():
            lines, _size, _trunc = tail_service_log(
                path, max_bytes=_LOGS_TAIL_BYTES, max_lines=max_per_service)
            for ln in lines:
                self.classify(parse_log_line(ln, service))


_RADAR = ErrorRadar()


class _DashboardHandler(BaseHTTPRequestHandler):
    """Routes: / (SPA), /api/state (JSON), /api/log?project=<name> (build-log
    tail), /api/logs?service=<name> (runtime-log poll-tail, redacted),
    /api/radar (error-radar counters, redacted)."""

    server_version = "meesell-env-dashboard"

    def log_message(self, fmt, *args):  # noqa: N802 — quiet the default access log
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _send_json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj).encode("utf-8"),
                   "application/json; charset=utf-8")

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        route = parsed.path
        if route == "/" or route == "/index.html":
            self._serve_index()
        elif route == "/api/state":
            # Read-only model with cached HTTP health probes.
            self._send_json(collect_dashboard_state(probe=True))
        elif route == "/api/log":
            self._serve_log(parse_qs(parsed.query))
        elif route == "/api/logs":
            self._serve_logs(parse_qs(parsed.query))
        elif route == "/api/radar":
            self._serve_radar()
        else:
            self._send_json({"error": "not found", "path": route}, code=404)

    do_HEAD = do_GET

    def _serve_index(self) -> None:
        try:
            body = DASHBOARD_HTML.read_bytes()
        except OSError:
            self._send_json(
                {"error": f"dashboard html missing at {DASHBOARD_HTML}"}, code=500)
            return
        self._send(200, body, "text/html; charset=utf-8")

    def _serve_log(self, qs: dict) -> None:
        proj = (qs.get("project") or [""])[0]
        if not proj or not _PROJECT_RE.match(proj):
            self._send_json({"error": "missing or invalid project"}, code=400)
            return
        # `slot` selects the per-env log (build-slot<N>-<project>.log). It is
        # validated with the SAME path-component allowlist as `project` so a
        # crafted value can never escape .nexus/. Omitted/blank -> slot 0.
        slot_raw = (qs.get("slot") or [""])[0]
        if slot_raw and not _PROJECT_RE.match(slot_raw):
            self._send_json({"error": "invalid slot"}, code=400)
            return
        try:
            slot = int(slot_raw) if slot_raw else 0
        except ValueError:
            self._send_json({"error": "invalid slot"}, code=400)
            return
        logpath = build_log_path(slot, proj)
        if not logpath.exists():
            # Backward compatibility: fall back to the legacy project-only log
            # (`build-<project>.log`) so old logs still tail after the upgrade.
            legacy = NEXUS_DIR / f"build-{proj}.log"
            if legacy.exists():
                logpath = legacy
            else:
                self._send_json(
                    {"project": proj, "slot": slot, "log": "", "exists": False,
                     "note": "no build log yet (project not built in this env)"})
                return
        try:
            with open(logpath, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                size = fh.tell()
                fh.seek(max(0, size - _LOG_TAIL_BYTES))
                raw = fh.read()
        except OSError as exc:
            self._send_json({"project": proj, "slot": slot, "error": str(exc)},
                            code=500)
            return
        text = raw.decode("utf-8", errors="replace")
        # Strip ANSI colour codes so the in-browser <pre> reads cleanly.
        text = re.sub(r"\x1b\[[0-9;]*m", "", text)
        self._send_json({"project": proj, "slot": slot, "exists": True,
                         "truncated": size > _LOG_TAIL_BYTES, "log": text})

    # ----- DEV LOG MONITOR (V1) endpoints --------------------------------

    def _serve_logs(self, qs: dict) -> None:
        """Poll-tail of one or all services' RUNTIME logs (not build logs).

        Mirrors the /api/log guards: service-name validation, ANSI strip,
        byte-bounded read. Every line is redacted (§6) before it is returned.
        `service` omitted/`all` => merged across every live service.
        `n` => max lines (capped at _LOGS_MAX_LINES).
        """
        index = service_log_index()
        req_svc = (qs.get("service") or [""])[0]
        try:
            n = int((qs.get("n") or [str(_LOGS_MAX_LINES)])[0])
        except ValueError:
            n = _LOGS_MAX_LINES
        n = max(1, min(n, _LOGS_MAX_LINES))

        if req_svc and req_svc not in ("", "all"):
            if not _SERVICE_RE.match(req_svc):
                self._send_json({"error": "invalid service"}, code=400)
                return
            if req_svc not in index:
                self._send_json({"service": req_svc, "lines": [], "exists": False,
                                 "services": sorted(index),
                                 "note": "no runtime log for this service"})
                return
            targets = {req_svc: index[req_svc]}
        else:
            targets = index

        out = []
        for service in sorted(targets):
            lines, _size, _trunc = tail_service_log(
                targets[service], max_bytes=_LOGS_TAIL_BYTES, max_lines=n)
            for ln in lines:
                out.append(parse_log_line(ln, service))  # redacts inside
        # Newest-last; for merged view cap the total to n*services already done.
        if req_svc in ("", "all") and len(out) > _LOGS_MAX_LINES:
            out = out[-_LOGS_MAX_LINES:]
        self._send_json({
            "service": req_svc or "all",
            "services": sorted(index),
            "count": len(out),
            "lines": out,
            "generated_iso": _now_iso(),
        })

    def _serve_radar(self) -> None:
        """Current error-radar counters + firing alerts. Ingests the tail of
        every service log on each call (no background thread; read-only)."""
        _RADAR.ingest_recent()
        self._send_json(_RADAR.snapshot())


def cmd_dashboard(args) -> None:
    if not DASHBOARD_HTML.exists():
        die(f"dashboard html not found at {DASHBOARD_HTML}")
    port = args.port
    httpd = ThreadingHTTPServer(("127.0.0.1", port), _DashboardHandler)
    info(f"env dashboard (read-only) on http://127.0.0.1:{port}")
    info("  GET /              the dashboard SPA")
    info("  GET /api/state     full JSON model")
    info("  GET /api/log?project=<name>&slot=<N>  tail of .nexus/build-slot<N>-<name>.log")
    info("  GET /api/logs?service=<name>  poll-tail of a service's RUNTIME log (redacted)")
    info("  GET /api/radar                error-radar detector counters (redacted)")
    info("Ctrl-C to stop. This server NEVER builds and NEVER holds the build lock.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        info("dashboard stopped")
    finally:
        httpd.server_close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="meesell_env.py",
        description="RAM-budgeted, port-isolated dev-environment manager for the 8GB box.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Port scheme (slot N, stride 10):\n"
            "  backend = 8000+N*10   shell = 4200+N*10   mfe[i] = 4201+N*10+i\n"
            "Baseline (master tree) is slot 0. The shell loads its federation\n"
            "manifest at RUNTIME, so untouched MFEs are reused from the baseline\n"
            "and only touched MFEs (+ shell if touched) are rebuilt per worktree.\n"
        ),
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    up = sub.add_parser("up", help="bring an env up (budget-checked, serialized build)")
    up.add_argument("worktree", help="worktree directory basename (see `git worktree list`)")
    up.add_argument("--mfe", default=None,
                    help="comma list of MFEs to rebuild/serve locally; "
                         "omit to infer from git diff develop...<branch>")
    up.add_argument("--stub", action="store_true",
                    help="skip real ng build / serve (smoke-test orchestration only)")
    up.set_defaults(func=cmd_up)

    down = sub.add_parser("down", help="stop an env's processes, keep its slot")
    down.add_argument("worktree")
    down.set_defaults(func=cmd_down)

    bl = sub.add_parser("baseline", help="build/serve develop's shell + ALL MFEs (slot 0)")
    bl.add_argument("action", choices=["up", "refresh"])
    bl.add_argument("--stub", action="store_true",
                    help="skip real ng build / serve")
    bl.set_defaults(func=cmd_baseline)

    st = sub.add_parser("status", help="running envs + live RAM/swap")
    st.set_defaults(func=cmd_status)

    gc = sub.add_parser("gc", help="stop orphaned procs; prune dead slot reservations")
    gc.set_defaults(func=cmd_gc)

    pr = sub.add_parser("ports", help="print a worktree's assigned port block")
    pr.add_argument("worktree")
    pr.set_defaults(func=cmd_ports)

    dash = sub.add_parser(
        "dashboard",
        help="serve the read-only env-monitoring dashboard (never builds)")
    dash.add_argument("--port", type=int, default=DASHBOARD_PORT,
                      help=f"port to serve on (default {DASHBOARD_PORT}, "
                           f"outside all slot ranges)")
    dash.set_defaults(func=cmd_dashboard)

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
