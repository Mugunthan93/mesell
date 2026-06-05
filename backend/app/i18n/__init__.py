"""i18n — Versioned rule modules for the MeeSell seed pipeline.

This package contains canonical, code-locked implementations of rules that
drive the shape of ``templates.schema_jsonb``.  Any edit to a rule module
MUST:
  1. Bump the module's ``*_VERSION`` constant.
  2. Trigger a re-run of ``scripts/seed_all.py`` against the relevant environment.
  3. Ensure the regression tests in ``backend/tests/test_step_assignment.py``
     and ``backend/tests/test_primitive_classifier.py`` still pass.

Modules:
  - ``step_assignment``:  ``STEP_ASSIGNMENT``, ``STEP_ORDER``, ``assign_step``
  - ``primitive_classifier``:  ``classify_primitive`` + its constants
"""
