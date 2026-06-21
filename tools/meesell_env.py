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
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

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
# Build + serve primitives
# ---------------------------------------------------------------------------

def ng_build(root: Path, project: str, *, stub: bool) -> None:
    """Run `ng build <project>` under the global lock. Stub mode skips the real build."""
    if stub:
        info(f"[stub] would run: ng build {project}  (cwd={root}/frontend)")
        return
    kill_esbuild()
    info(f"ng build {project} ...")
    proc = subprocess.run(
        ["npx", "ng", "build", project, "--configuration=development"],
        cwd=str(root / "frontend"),
    )
    kill_esbuild()
    if proc.returncode != 0:
        die(f"ng build {project} failed (exit {proc.returncode})")


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


def serve_static(root: Path, dist_root: Path, port: int, *, stub: bool) -> int | None:
    serve_js = root / SERVE_JS_REL
    if not serve_js.exists():
        die(f"serve.js not found at {serve_js}")
    if stub:
        info(f"[stub] would serve {dist_root} on :{port}")
        return None
    log = NEXUS_DIR / f"serve-{port}.log"
    fh = open(log, "w")
    proc = subprocess.Popen(
        ["node", str(serve_js), str(dist_root), str(port)],
        stdout=fh, stderr=subprocess.STDOUT,
    )
    info(f"serving {dist_root} on :{port} (pid {proc.pid}, log {log})")
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
    free_mb, swap_pct = ram_stats()
    state = load_state()
    reg = load_ports()
    print(f"RAM free: {free_mb} MB    swap used: {swap_pct:.1f}%    "
          f"(guard: free>={MIN_FREE_MB}MB, swap<={MAX_SWAP_PCT:.0f}%)")
    print()
    if not state:
        print("No running envs tracked.")
    else:
        print(f"{'worktree':<24}{'slot':<6}{'role':<14}{'port':<8}{'pid':<8}{'alive'}")
        print("-" * 70)
        for wt_name, env in sorted(state.items()):
            slot = env.get("slot", "?")
            for role, meta in env.get("procs", {}).items():
                pid = meta.get("pid")
                port = meta.get("port", "")
                alive = "yes" if (pid and pid_alive(pid)) else "DEAD"
                print(f"{wt_name:<24}{str(slot):<6}{role:<14}{str(port):<8}"
                      f"{str(pid):<8}{alive}")
    print()
    print("Slot reservations:")
    for wt_name, slot in sorted(reg.items(), key=lambda kv: kv[1]):
        exists = "exists" if wt_name in git_worktrees() else "MISSING (gc to prune)"
        print(f"  slot {slot}: {wt_name}  [{exists}]")


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
            ng_build(root, "frontend", stub=stub)
        for name in touched:
            ng_build(root, name, stub=stub)

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

    # 7. Serve shell.
    pid = serve_static(root, shell_dist, block["shell"], stub=stub)
    if pid:
        procs["shell"] = {"pid": pid, "port": block["shell"]}

    # 8. Serve touched MFEs from this env; untouched are served by baseline (slot 0).
    for name in touched:
        mfe_dist = served_dist_root(root, name)
        pid = serve_static(root, mfe_dist, block["mfes"][name], stub=stub)
        if pid:
            procs[name] = {"pid": pid, "port": block["mfes"][name]}

    # 9. Backend: only if touched; else point at baseline backend.
    backend_touched = is_backend_touched(root, branch)
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

    # Build shell + ALL MFEs, serialized.
    with BuildLock():
        ng_build(root, "frontend", stub=stub)
        for name in all_mfes:
            ng_build(root, name, stub=stub)

    # Baseline manifest: all remotes at baseline ports.
    shell_dist = served_dist_root(root, SHELL_DIST_NAME)
    manifest = {
        name: f"http://localhost:{block['mfes'][name]}/remoteEntry.json"
        for name in all_mfes
    }
    if not stub:
        write_env_manifest(shell_dist, manifest)

    procs: dict[str, dict] = {}
    pid = serve_static(root, shell_dist, block["shell"], stub=stub)
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

    return p


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
