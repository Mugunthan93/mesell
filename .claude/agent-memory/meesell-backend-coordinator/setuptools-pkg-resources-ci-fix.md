# CI fix: razorpay SDK needs setuptools/pkg_resources (2026-06-20)

**Context:** PR #323 (feature/razorpay → develop). CI "Gate 1: unit" failed with
16 `ModuleNotFoundError: No module named 'pkg_resources'` collection errors across
nearly every test module.

**Root cause (verified, not assumed):**
- `razorpay==1.4.2` → `razorpay/client.py:4` does `import pkg_resources` at module load.
- `pkg_resources` ships in **setuptools**. Python 3.12 + `actions/setup-python` no
  longer bundle setuptools into the env. New pip (26.x) also does NOT seed setuptools
  into venvs by default.
- razorpay 1.4.2 METADATA declares only `Requires-Dist: requests` — it does NOT
  declare setuptools, despite importing pkg_resources. Latent SDK bug.
- Import chain causing the CASCADE: `tests/conftest.py` (collected for whole tree) →
  `app.main` → `app.modules.iam` router → iam `service.py`/`tasks.py` import
  `app.adapters.razorpay` → `import razorpay`. So one missing dep fails ALL test
  collection at once.

**Fix:** add `setuptools>=70,<81` to `backend/requirements.txt` (the ONLY req file;
CI Gate 1 runs `pip install -r requirements.txt` in `backend/`, ci.yml L142-143).
- Upper bound `<81` is LOAD-BEARING: setuptools 81 REMOVES pkg_resources entirely.
  An unbounded pin would reintroduce the exact failure (today is past the 2025-11-30
  removal date the deprecation warning cites). Range-pin style matches existing
  `pydantic-settings>=2.5,<3`, `fakeredis>=2.21,<3`.

**Proof (throwaway py3.11 venv mirroring CI, master venv untouched):**
- BEFORE (setuptools removed): `pytest --collect-only -m unit` → 17 errors (my
  worktree HEAD has 1 extra test module vs the 16 CI saw; identical signature).
- AFTER (`pip install 'setuptools>=70,<81'`): 0 collection errors, 900 tests collected.
- `python -c "import pkg_resources; import razorpay; print('ok')"` → ok.

**Commit:** 4091d24 on feature/razorpay (NOT pushed — Director handles git).

**LESSON / pattern:** when adding a 3rd-party Python SDK to requirements, check
whether it `import pkg_resources` (or anything from setuptools) at import time.
Modern Python (3.12+) and modern pip do NOT guarantee setuptools is present.
If so, add an explicit `setuptools` pin (bounded `<81`). This is a merge-gate
check item for any future adapter that wraps an older SDK.
