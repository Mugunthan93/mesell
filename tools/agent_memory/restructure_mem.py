#!/usr/bin/env python3
"""
Restructure a fat agent MEMORY.md into: identity (inline) + index (pointers) + per-entry detail files.
ZERO content loss by construction: every section body is written VERBATIM to a detail file.
Built-in verification: every non-blank original line must appear (>= original count) in the new fileset.

Usage: restructure_mem.py <MEMORY.md path> [--apply]
Without --apply: DRY RUN (writes nothing, prints plan + verification against an in-memory build).
"""
import sys, os, re, hashlib
from collections import Counter

KEEP_INLINE = re.compile(r'^##\s+(Agent Identity|Initial State|Identity)\b', re.I)
INDEX_HDR   = re.compile(r'^##\s+.*\bindex\b', re.I) or re.compile(r'^##\s+MEMORY\.md\s*$', re.I)
INDEX_HDR2  = re.compile(r'^##\s+(MEMORY\.md|Memory)\s*(\(Index\))?\s*$', re.I)
REUSE_MARK  = re.compile(r'LOAD-BEARING|ground-truth|GOTCHA|gotcha|\bpattern\b|\brecipe\b|LOCKED|P0|CRITICAL|carry.forward|reuse', re.I)

def slugify(h, n):
    s = re.sub(r'^#+\s*', '', h).strip().lower()
    s = re.sub(r'\{#.*?\}', '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s).strip('-')
    s = re.sub(r'-+', '-', s)[:60].strip('-')
    return f"mem_{n:02d}_{s or 'entry'}"

def split_blocks(lines, level):
    """Split into (header_line, [body_lines_incl_header]) at the given header level (## or ###)."""
    pat = re.compile(rf'^#{{{level}}}\s+')
    blocks, cur = [], None
    pre = []  # lines before first header
    for ln in lines:
        if pat.match(ln):
            if cur is not None:
                blocks.append(cur)
            cur = [ln]
        else:
            (cur if cur is not None else pre).append(ln)
    if cur is not None:
        blocks.append(cur)
    return pre, blocks

def main():
    path = sys.argv[1]
    apply = '--apply' in sys.argv
    agent_dir = os.path.dirname(path)
    agent = os.path.basename(agent_dir)
    raw = open(path, encoding='utf-8').read()
    lines = raw.split('\n')

    pre, blocks = split_blocks(lines, 2)  # split at '## '

    inline_blocks = []   # kept in new MEMORY.md verbatim
    index_entries = []   # (display, slug, reuse, body_lines)
    dropped_index_lines = []  # navigational TOC lines we intentionally don't carry

    # Preserve the ENTIRE preamble (title + any prose/blockquote memos before first '## ') inline.
    preamble = pre if pre else [f"# Memory — {agent}"]

    def is_toc_line(s):
        t = s.strip()
        return (t == '' or t.startswith('- [') or t.startswith('|')
                or t.startswith('* [') or re.match(r'^-\s*\[', t) is not None)

    n = 0
    for blk in blocks:
        hdr = blk[0]
        body = '\n'.join(blk).rstrip('\n')
        if KEEP_INLINE.match(hdr):
            inline_blocks.append(blk)
            continue
        # Is this an INDEX container? Match ONLY true index titles, not headers
        # that merely contain the substring "index" (e.g. "...G10-index...COMPLETE").
        htext = re.sub(r'^#+\s*', '', hdr).strip()
        is_index = re.match(r'^(memory(\.md)?(\s*\(?\s*index\s*\)?)?|index)\s*$', htext, re.I) is not None
        if is_index:
            # Does it contain ### sub-entries that are REAL content (not just links)?
            sub_pre, subs = split_blocks(blk, 3)  # split body at '### '
            if subs:
                # compact-entry container: each ### -> detail file (verbatim, heading kept)
                # sub_pre[0] is the '## Index' header; remaining sub_pre lines dropped only if TOC
                if sub_pre:
                    dropped_index_lines.append(sub_pre[0])  # the '## Index' header
                tail = sub_pre[1:]
                if all(is_toc_line(s) for s in tail):
                    for sl in tail:
                        if sl.strip():
                            dropped_index_lines.append(sl)
                else:
                    n += 1
                    notes = '\n'.join(sub_pre).rstrip('\n')
                    index_entries.append(("Index notes (preamble prose)",
                                          slugify("index-notes", n), False, sub_pre))
                for sb in subs:
                    n += 1
                    shdr = sb[0]
                    sbody = '\n'.join(sb).rstrip('\n')
                    reuse = len(REUSE_MARK.findall(sbody)) >= 2
                    index_entries.append((re.sub(r'^#+\s*','',shdr).strip(), slugify(shdr, n), reuse, sb))
            else:
                # No ### subs. Drop ONLY if every body line is a TOC link/table/blank.
                body_lines = blk[1:]
                if all(is_toc_line(s) for s in body_lines):
                    dropped_index_lines.append(hdr)           # record dropped header
                    for sl in body_lines:
                        if sl.strip():
                            dropped_index_lines.append(sl)
                else:
                    # Index header hides real prose -> preserve as a detail file (no loss).
                    n += 1
                    reuse = len(REUSE_MARK.findall(body)) >= 2
                    index_entries.append((re.sub(r'^#+\s*','',hdr).strip(),
                                          slugify(hdr, n), reuse, blk))
            continue
        # regular section -> detail file
        n += 1
        reuse = len(REUSE_MARK.findall(body)) >= 2
        index_entries.append((re.sub(r'^#+\s*','',hdr).strip(), slugify(hdr, n), reuse, blk))

    # Build new MEMORY.md
    out = ['\n'.join(preamble).rstrip('\n'), '']
    for blk in inline_blocks:
        out.append('\n'.join(blk).rstrip('\n'))
        out.append('')
    out.append('## Index')
    out.append('> Bodies live in `mem/`. ⭐ = contains reusable pattern / gotcha / ground-truth.')
    out.append('')
    for disp, slug, reuse, _ in index_entries:
        star = '⭐ ' if reuse else ''
        out.append(f"- {star}[{disp}](mem/{slug}.md)")
    new_memory = '\n'.join(out).rstrip('\n') + '\n'

    # Detail files map
    detail_files = {f"mem/{slug}.md": '\n'.join(blk).rstrip('\n') + '\n'
                    for _, slug, _, blk in index_entries}

    # ---- VERIFICATION (content preservation) ----
    def content_counter(text):
        return Counter(l.rstrip() for l in text.split('\n') if l.strip())
    orig_c = content_counter(raw)
    new_c = Counter()
    new_c.update(content_counter(new_memory))
    for t in detail_files.values():
        new_c.update(content_counter(t))
    dropped_set = Counter(l.rstrip() for l in dropped_index_lines if l.strip())

    missing = {}
    for line, cnt in orig_c.items():
        have = new_c.get(line, 0)
        if have < cnt:
            deficit = cnt - have
            # acceptable only if covered by intentionally-dropped TOC lines
            allowed = dropped_set.get(line, 0)
            if have + allowed < cnt:
                missing[line] = (cnt, have, allowed)

    # ---- REPORT ----
    print(f"=== {agent} ===")
    print(f"original lines: {len(lines)}  | inline blocks kept: {len(inline_blocks)} | detail files: {len(detail_files)} | reusable-flagged: {sum(1 for e in index_entries if e[2])}")
    print(f"new MEMORY.md lines: {new_memory.count(chr(10))}")
    print(f"intentionally-dropped TOC/index lines: {len(dropped_index_lines)}")
    if missing:
        print(f"!!! VERIFICATION FAILED — {len(missing)} content lines unaccounted for:")
        for l,(c,h,a) in list(missing.items())[:40]:
            print(f"    orig×{c} new×{h} toc×{a} | {l[:120]}")
    else:
        print("VERIFICATION PASSED — every original content line is preserved (in MEMORY.md, a detail file, or an intentionally-dropped TOC line).")

    if apply and not missing:
        os.makedirs(os.path.join(agent_dir, 'mem'), exist_ok=True)
        for rel, txt in detail_files.items():
            open(os.path.join(agent_dir, rel), 'w', encoding='utf-8').write(txt)
        open(path, 'w', encoding='utf-8').write(new_memory)
        print(f">>> APPLIED: wrote {len(detail_files)} detail files + new MEMORY.md")
    elif apply and missing:
        print(">>> NOT APPLIED (verification failed)")

if __name__ == '__main__':
    main()
