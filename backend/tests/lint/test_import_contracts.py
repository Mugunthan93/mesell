"""§19.G — pytest wrapper for import-linter Contracts 1-7 (§16.E).

Invokes ``lint-imports`` against the locked ``tests/lint/import_rules.toml``
in a subprocess so the import-linter exit code IS the contract verdict (per
the §19.G fixture sketch).

The TOML file is the source of truth for Contracts 1-7. This module only
wires the CLI invocation + asserts non-zero exit fails the test.

Executable resolution order:
1. ``lint-imports`` on ``$PATH`` (set when the venv is activated)
2. ``<sys.prefix>/bin/lint-imports`` (venv bin dir even when not activated)
3. ``<sys.prefix>/Scripts/lint-imports`` (Windows convention)

The fallback path lets the test pass in CI runners that invoke pytest with
``.venv/bin/python -m pytest`` without first activating the venv.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

# ── Locked path to import-linter's TOML config file (relative to backend/).
_LINT_CONFIG_RELATIVE = Path("tests") / "lint" / "import_rules.toml"


def _backend_root() -> Path:
    """Locate backend/ from this module's path."""
    return Path(__file__).resolve().parents[2]


def _lint_imports_executable() -> str | None:
    """Resolve the ``lint-imports`` CLI per import-linter packaging.

    Searches in three places in order:
      1. ``$PATH`` via :func:`shutil.which` (works when venv activated).
      2. ``<sys.prefix>/bin/`` (the venv bin dir, even when not activated).
      3. ``<sys.prefix>/Scripts/`` (Windows variant).

    Returns ``None`` only when import-linter is not installed in the active
    interpreter; the test then errors loudly with a fixable diagnostic.
    """
    cli = shutil.which("lint-imports")
    if cli:
        return cli
    prefix = Path(sys.prefix)
    for candidate in (prefix / "bin" / "lint-imports",
                      prefix / "Scripts" / "lint-imports.exe",
                      prefix / "Scripts" / "lint-imports"):
        if candidate.is_file():
            return str(candidate)
    return None


@pytest.mark.smoke
def test_import_linter_config_exists() -> None:
    """The locked TOML config MUST exist (§16.E + §19.G + §3.J test layout)."""
    config = _backend_root() / _LINT_CONFIG_RELATIVE
    assert config.is_file(), (
        f"§16.E import-linter config missing at {config!s}. The 7 contracts "
        "cannot be enforced without this file."
    )


@pytest.mark.smoke
def test_import_linter_contracts_pass() -> None:
    """All 7 import-linter contracts (§16.E) MUST pass against current code.

    Per the §19.G fixture sketch::

        result = subprocess.run(
            ["lint-imports", "--config", "tests/lint/import_rules.toml"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

    Falls back to ``python -m importlinter`` invocation when the
    ``lint-imports`` console script is not on PATH (handles missing
    venv-activation in CI runners).
    """
    backend = _backend_root()
    config = backend / _LINT_CONFIG_RELATIVE
    cli = _lint_imports_executable()
    if cli is None:
        pytest.fail(
            "`lint-imports` not installed. Add `import-linter>=2.0,<3` to "
            "backend/requirements.txt and `pip install -r backend/requirements.txt`."
        )
    cmd = [cli, "--config", str(config)]

    result = subprocess.run(
        cmd,
        cwd=str(backend),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "§16.E import-linter contracts FAILED.\n"
        f"command   : {' '.join(cmd)}\n"
        f"cwd       : {backend}\n"
        f"exit code : {result.returncode}\n"
        "--- stdout ---\n"
        f"{result.stdout}\n"
        "--- stderr ---\n"
        f"{result.stderr}"
    )
