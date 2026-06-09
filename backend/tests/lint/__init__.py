"""§19 CI linter contracts — 10 total per ``BACKEND_ARCHITECTURE.md`` §19.C.

Files in this package:

* ``import_rules.toml``                            — import-linter contracts 1-7 (§16.E)
* ``check_scope_to_user.py``                       — Contract 8 AST scanner (§15.B)
* ``check_no_meesho_symbols_outside_export.py``    — Contract 9 AST scanner (§14.J + §15.F)
* ``check_message_id_regex.py``                    — Contract 10 regex scanner (§5A.H)
* ``test_import_contracts.py``                     — pytest wrapper for Contracts 1-7
* ``test_scope_to_user_enforcement.py``            — pytest wrapper for Contract 8
* ``test_no_meesho_symbols_outside_export.py``     — pytest wrapper for Contract 9
* ``test_message_id_regex.py``                     — pytest wrapper for Contract 10

Each ``check_*.py`` is runnable via ``python -m tests.lint.check_*`` and exits
non-zero on violation. The corresponding ``test_*.py`` wrapper invokes the
scanner in-process (via importable :func:`scan` / :func:`main` functions) and
includes counter-example assertions per §19's construction protocol.
"""
