#!/usr/bin/env python3
"""Phase 0: mine local Claude Code transcripts for the RTK savings ceiling.

Read-only over ~/.claude/projects/*/*.jsonl (last 30 days by mtime).
Attributes tool_result sizes to the tool that produced them, computes the
Bash-share of tool-result tokens (the only surface RTK can compress), and
writes phase0-ceiling-report.md next to this script's parent directory.

Token estimate: chars / 3.3 (calibrated heuristic, ±10%; same basis as the
EXPERIMENT_PLAN so all numbers stay comparable).
"""
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

CHARS_PER_TOKEN = 3.3
DAYS = 30
PROJECTS_DIR = Path.home() / ".claude" / "projects"
OUT = Path(__file__).resolve().parent.parent / "phase0-ceiling-report.md"

# Commands RTK ships filters for (README-verified list, first-word or in-chain)
RTK_SUPPORTED = {
    "git", "grep", "rg", "find", "ls", "cat", "head", "tail", "pytest",
    "cargo", "go", "npm", "pnpm", "yarn", "tsc", "eslint", "docker",
    "kubectl", "prisma", "pip", "pip3", "ruff", "mypy", "make", "ng",
    "jest", "vitest", "tox", "gradle", "mvn", "curl", "wc", "du", "df",
}


def est_tokens(n_chars: int) -> int:
    return max(0, round(n_chars / CHARS_PER_TOKEN))


def result_chars(content) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        total = 0
        for block in content:
            if isinstance(block, dict):
                total += len(block.get("text", "") or "")
        return total
    return 0


def first_word_chain(cmd: str):
    """Yield candidate command words across &&/;/| chains."""
    for seg in cmd.replace("&&", ";").replace("||", ";").replace("|", ";").split(";"):
        parts = seg.strip().split()
        for p in parts[:3]:  # cmd, or env-var/cd prefix then cmd
            w = os.path.basename(p)
            if w and "=" not in w and w not in ("cd", "sudo", "env", "caffeinate", "-i"):
                yield w
                break


def classify_bash(cmd: str) -> str:
    words = list(first_word_chain(cmd or ""))
    for w in words:
        if w in RTK_SUPPORTED:
            return w
    return words[0] if words else "(empty)"


def main():
    cutoff = time.time() - DAYS * 86400
    files = [p for p in PROJECTS_DIR.glob("*/*.jsonl") if p.stat().st_mtime >= cutoff]

    per_project = defaultdict(lambda: defaultdict(int))  # project -> tool -> tokens
    bash_cmds = defaultdict(int)          # command word -> result tokens
    usage_totals = defaultdict(int)       # usage field -> tokens
    n_lines = n_results = 0

    for f in files:
        project = f.parent.name
        id2name, id2cmd = {}, {}
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    n_lines += 1
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    msg = rec.get("message") or {}
                    content = msg.get("content")
                    if isinstance(content, list):
                        for block in content:
                            if not isinstance(block, dict):
                                continue
                            bt = block.get("type")
                            if bt == "tool_use":
                                tid = block.get("id", "")
                                name = block.get("name", "?")
                                id2name[tid] = name
                                if name == "Bash":
                                    id2cmd[tid] = (block.get("input") or {}).get("command", "")
                            elif bt == "tool_result":
                                tid = block.get("tool_use_id", "")
                                name = id2name.get(tid, "(unmapped)")
                                tok = est_tokens(result_chars(block.get("content")))
                                per_project[project][name] += tok
                                n_results += 1
                                if name == "Bash":
                                    bash_cmds[classify_bash(id2cmd.get(tid, ""))] += tok
                    u = msg.get("usage") or {}
                    for k in ("input_tokens", "output_tokens",
                              "cache_read_input_tokens", "cache_creation_input_tokens"):
                        usage_totals[k] += u.get(k) or 0
        except OSError:
            continue

    # Aggregate
    overall = defaultdict(int)
    for tools in per_project.values():
        for t, v in tools.items():
            overall[t] += v
    total = sum(overall.values()) or 1
    bash = overall.get("Bash", 0)
    bash_share = bash / total
    supported = sum(v for k, v in bash_cmds.items() if k in RTK_SUPPORTED)
    supported_share_of_bash = supported / bash if bash else 0
    # Ceiling: RTK compresses 60-90% of SUPPORTED bash-result tokens
    lo = bash_share * supported_share_of_bash * 0.60
    hi = bash_share * supported_share_of_bash * 0.90

    lines = []
    lines.append("# Phase 0 — Ceiling Report (RTK token-adoption experiment)")
    lines.append(f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M')}  |  Window: last {DAYS} days  |  Files: {len(files)}  |  tool_results: {n_results:,}")
    lines.append(f"\n## Overall tool-result token attribution (est., chars/3.3)\n")
    lines.append("| Tool | Tokens | Share |")
    lines.append("|------|-------:|------:|")
    for t, v in sorted(overall.items(), key=lambda x: -x[1])[:12]:
        lines.append(f"| {t} | {v:,} | {v/total:.1%} |")
    lines.append(f"| **TOTAL** | **{total:,}** | 100% |")
    lines.append(f"\n## Headline numbers\n")
    lines.append(f"- **Bash-share of tool-result tokens: {bash_share:.1%}**")
    lines.append(f"- RTK-supported commands within Bash results: {supported_share_of_bash:.1%}")
    lines.append(f"- **Theoretical RTK ceiling on tool-result tokens: {lo:.1%} – {hi:.1%}**")
    lines.append(f"\n## Session usage context (real API usage fields, same window)\n")
    for k, v in usage_totals.items():
        lines.append(f"- {k}: {v:,}")
    lines.append(f"\n## Top bash command types by result tokens\n")
    lines.append("| Command | Result tokens | RTK-supported |")
    lines.append("|---------|--------------:|:-------------:|")
    for k, v in sorted(bash_cmds.items(), key=lambda x: -x[1])[:15]:
        lines.append(f"| {k} | {v:,} | {'YES' if k in RTK_SUPPORTED else 'no'} |")
    lines.append(f"\n## Per-project Bash-share (top 8 by volume)\n")
    lines.append("| Project | Total result tokens | Bash-share |")
    lines.append("|---------|--------------------:|-----------:|")
    proj_rows = sorted(per_project.items(), key=lambda x: -sum(x[1].values()))[:8]
    for p, tools in proj_rows:
        pt = sum(tools.values()) or 1
        lines.append(f"| {p} | {pt:,} | {tools.get('Bash', 0)/pt:.1%} |")
    lines.append("\n## Gate G0 evaluation\n")
    verdict = "PROCEED (>=20%)" if bash_share >= 0.20 else ("MARGINAL (10-20%) — founder decides" if bash_share >= 0.10 else "STOP (<10%) — pivot per plan §4")
    lines.append(f"- Bash-share {bash_share:.1%} → **{verdict}**")

    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"report -> {OUT}")
    print(f"files={len(files)} results={n_results:,} total_result_tokens={total:,}")
    print(f"BASH_SHARE={bash_share:.1%} SUPPORTED_OF_BASH={supported_share_of_bash:.1%} CEILING={lo:.1%}-{hi:.1%}")
    print(f"G0={verdict}")


if __name__ == "__main__":
    sys.exit(main())
