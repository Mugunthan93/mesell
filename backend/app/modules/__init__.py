"""Domain modules root — per BACKEND_ARCHITECTURE.md §3.C.

Each subpackage is a §2.x domain module: ``iam``, ``customer``, ``category``,
``catalog``, ``image``, ``pricing``, ``dashboard``, ``export``.  Per §16 cross-
module communication is strictly via service-layer call sites; repository
imports across modules are forbidden.
"""
