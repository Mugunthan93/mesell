#!/usr/bin/env python3
"""Independent post-write verification: every non-blank content line in the git HEAD
original must appear (>= original multiplicity) across the new MEMORY.md + mem/*.md.
Intentionally-dropped lines allowed = TOC links / table rows / index headers only."""
import sys, os, subprocess, re, glob
from collections import Counter

def counter(text):
    return Counter(l.rstrip() for l in text.split('\n') if l.strip())

def is_allowed_drop(s):
    t = s.strip()
    htext = re.sub(r'^#+\s*', '', t).strip()
    return (t.startswith('- [') or t.startswith('* [') or t.startswith('|')
            or re.match(r'^(memory(\.md)?(\s*\(?\s*index\s*\)?)?|index)\s*$', htext, re.I) is not None)

def _resolve_repo():
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env and os.path.isdir(env):
        return env
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True).stdout.strip()
        if top and os.path.isdir(top):
            return top
    except Exception:
        pass
    return "/Users/mugunthansrinivasan/Project/mesell"

repo = _resolve_repo()
agents = sys.argv[1:]
all_ok = True
for agent in agents:
    rel = f".claude/agent-memory/{agent}/MEMORY.md"
    orig = subprocess.run(["git","-C",repo,"show",f"HEAD:{rel}"],
                          capture_output=True, text=True).stdout
    adir = os.path.join(repo, ".claude/agent-memory", agent)
    new = open(os.path.join(adir,"MEMORY.md"), encoding='utf-8').read()
    newc = counter(new)
    for mf in glob.glob(os.path.join(adir,"mem","*.md")):
        newc.update(counter(open(mf, encoding='utf-8').read()))
    oc = counter(orig)
    bad = []
    for line, cnt in oc.items():
        if newc.get(line,0) < cnt and not is_allowed_drop(line):
            bad.append((line, cnt, newc.get(line,0)))
    status = "PASS" if not bad else "FAIL"
    all_ok &= not bad
    print(f"[{status}] {agent}: orig_content_lines={sum(oc.values())} new_unique={len(newc)} unaccounted={len(bad)}")
    for l,c,h in bad[:20]:
        print(f"      orig×{c} new×{h} | {l[:110]}")
print("\nALL PASS" if all_ok else "\nSOME FAILED")
