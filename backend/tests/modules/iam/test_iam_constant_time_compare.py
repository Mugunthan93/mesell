"""Unit test §7.J #4 — constant-time comparison regression guard.

Per BACKEND_ARCHITECTURE.md §7.J unit 4:

    "Constant-time comparison regression — `secrets.compare_digest` used
    for OTP hash compare AND for refresh-token lookup (Valkey key is
    HMAC-based, but the Lua script's existence check is constant-time at
    the Redis level; this test guards against future refactors
    reintroducing `==`)."

Strategy
--------
Static-AST scan of the two source files that own token comparison —
``app/modules/iam/service.py`` and ``app/core/auth.py``.  Any ``==``
comparison whose left- or right-operand mentions ``otp_hash``,
``refresh_token``, or ``digest`` fails the test.  Future refactors that
drop ``secrets.compare_digest`` for ``==`` on a security boundary trip
this guard at CI time.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


# ── Files under guard (security boundary) ──────────────────────────────────
_BACKEND_ROOT = Path(__file__).resolve().parents[3] / "app"
_GUARDED_FILES = (
    _BACKEND_ROOT / "modules" / "iam" / "service.py",
    _BACKEND_ROOT / "core" / "auth.py",
)

# Identifiers whose ``==`` comparison would be a security regression.
_SENSITIVE_NAMES = frozenset(
    {
        "otp_hash",
        "presented_hash",
        "stored_hash",
        "refresh_token",
        "digest",
        "token",
    }
)


def _identifier(node: ast.AST) -> str | None:
    """Best-effort identifier extraction for AST operand inspection."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.Subscript):
        return _identifier(node.value)
    if isinstance(node, ast.Call):
        return _identifier(node.func)
    return None


def _eq_on_sensitive_operand(node: ast.Compare) -> bool:
    """Return True if this comparison uses ``==`` on a sensitive identifier."""
    if not any(isinstance(op, ast.Eq) for op in node.ops):
        return False
    all_operands = [node.left, *node.comparators]
    for operand in all_operands:
        ident = _identifier(operand)
        if ident and ident in _SENSITIVE_NAMES:
            return True
    return False


@pytest.mark.parametrize("path", _GUARDED_FILES, ids=lambda p: p.name)
def test_no_eq_on_sensitive_token_operands(path: Path) -> None:
    """Fail if any ``==`` comparison touches an OTP/token identifier."""
    assert path.is_file(), f"Guarded file missing: {path}"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    offending: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and _eq_on_sensitive_operand(node):
            offending.append(f"{path.name}:{node.lineno}")
    assert not offending, (
        "Sensitive ``==`` comparison detected — use secrets.compare_digest:\n  "
        + "\n  ".join(offending)
    )


def test_secrets_compare_digest_imported_or_referenced_in_iam_service() -> None:
    """Iam service must reference :func:`secrets.compare_digest` (positive guard)."""
    src = (_BACKEND_ROOT / "modules" / "iam" / "service.py").read_text(encoding="utf-8")
    assert "secrets.compare_digest" in src, (
        "iam.service.py no longer uses secrets.compare_digest — OTP compare "
        "regressed to ==; refactor must preserve constant-time semantics."
    )
