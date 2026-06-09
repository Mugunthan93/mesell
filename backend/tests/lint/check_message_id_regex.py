"""§19.C Contract 10 — ``validation_message_id`` registry regex check.

Per BACKEND_ARCHITECTURE.md §19.C + §5A.H (LOCKED 2026-06-06):

    Every key in ``app.i18n.messages_en.VALIDATION_MESSAGES`` MUST match
    the locked 3-segment snake_case regex::

        ^[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*\\.[a-z][a-z0-9_]*$

    i.e. three snake_case segments separated by dots, hyphens forbidden,
    uppercase forbidden, exactly 3 dots-segments.

This scanner is the §19.C Contract 10 sentinel — it loads the runtime
``VALIDATION_MESSAGES`` registry and asserts the regex holds for every key.
A failure indicates the registry has drifted from the §5A.H convention and
will surface as a missing-key resolver fallback at runtime (per §5A.I).

A belt-and-braces pytest module at ``tests/test_messages_en_id_regex.py``
covers the same surface with parametrised assertions and additional shape
checks (no hyphens, no uppercase, exactly 3 segments). This module is the
CLI-invocable entry point that the §19 contract test exercises in-process.

Runnable via::

    python -m tests.lint.check_message_id_regex
    python tests/lint/check_message_id_regex.py
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ── §5A.H locked regex. The bracketed character classes are kept verbatim
#    so a future grep for this string in BACKEND_ARCHITECTURE.md surfaces
#    the linkage between doc and code.
MESSAGE_ID_REGEX_SOURCE: str = r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$"
MESSAGE_ID_REGEX: re.Pattern[str] = re.compile(MESSAGE_ID_REGEX_SOURCE)


@dataclass(frozen=True)
class Violation:
    """One ``VALIDATION_MESSAGES`` key that does not match the §5A.H regex."""

    key: str
    reason: str

    def render(self) -> str:
        return f"  • {self.key!r} — {self.reason}"


def _classify(key: str) -> str | None:
    """Return None if the key matches the §5A.H regex, else a reason string.

    The reason text is human-readable and chosen for PR-review legibility.
    """
    if MESSAGE_ID_REGEX.match(key):
        return None
    segments = key.split(".")
    if len(segments) != 3:
        return f"has {len(segments)} segments — §5A.H locks exactly 3."
    if "-" in key:
        return "contains a hyphen — §5A.H forbids hyphens in any segment."
    if any(c.isupper() for c in key):
        return "contains uppercase — §5A.H locks snake_case (lowercase only)."
    return "does not match the §5A.H regex shape."


def _load_registry(repo_root: Path | None = None) -> dict[str, str]:
    """Import ``app.i18n.messages_en.VALIDATION_MESSAGES`` from the project.

    Handles invocation either inside the backend/ directory (where ``app/``
    is on ``sys.path``) or from above it.
    """
    if repo_root is None:
        here = Path(__file__).resolve()
        for parent in here.parents:
            if (parent / "app" / "i18n" / "messages_en.py").is_file():
                repo_root = parent
                break
    if repo_root is None:  # pragma: no cover — defensive
        raise RuntimeError(
            "Could not locate app/i18n/messages_en.py from script path or cwd."
        )

    repo_root = repo_root.resolve()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Import fresh so the registry is consistent with the on-disk source.
    from importlib import import_module, reload
    module = import_module("app.i18n.messages_en")
    module = reload(module)
    registry: dict[str, str] = getattr(module, "VALIDATION_MESSAGES")
    return registry


def scan(repo_root: Path | None = None) -> list[Violation]:
    """Walk the loaded registry, return list of regex-violating keys.

    Empty list = PASS. Non-empty list = FAIL.
    """
    registry = _load_registry(repo_root)
    out: list[Violation] = []
    for key in sorted(registry):
        reason = _classify(key)
        if reason is not None:
            out.append(Violation(key=key, reason=reason))
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--root",
        type=Path,
        default=None,
        help="Path to backend/ root (default: auto-detect).",
    )
    args = parser.parse_args(argv)

    violations = scan(args.root)
    if not violations:
        # Re-load to report the count.
        n_keys = len(_load_registry(args.root))
        print(
            f"§19.C Contract 10 PASS — all {n_keys} VALIDATION_MESSAGES "
            f"keys match the §5A.H regex `{MESSAGE_ID_REGEX_SOURCE}`."
        )
        return 0

    print(
        f"§19.C Contract 10 FAIL — {len(violations)} VALIDATION_MESSAGES "
        "key(s) violate the §5A.H 3-segment snake_case regex:",
        file=sys.stderr,
    )
    for v in violations:
        print(v.render(), file=sys.stderr)
    print(
        "\nRemediation: rename the key to match the regex "
        f"`{MESSAGE_ID_REGEX_SOURCE}` — exactly 3 dot-separated snake_case "
        "segments, no hyphens, no uppercase.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
