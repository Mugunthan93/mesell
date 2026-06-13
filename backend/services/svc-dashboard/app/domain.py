"""``dashboard`` internal domain types per §13.F.

**Post-§13.A.1 amendment (2026-06-07):** dashboard has NO unique domain
types in V1. The original §13.F locked a :class:`Pagination` frozen
dataclass with 4 fields (``page``, ``limit``, ``status_filter``, ``search``);
the amendment narrows it to 2 fields (``page``, ``limit``) — which exactly
matches :class:`app.modules.catalog.domain.Pagination`. To avoid duplicating
the same 2-field dataclass on both sides of the cross-module call,
dashboard now imports catalog's ``Pagination`` directly (as permitted by
§16 Rule 4 — ``domain.py`` is the cross-module exchange currency, and
:class:`catalog.domain.Pagination` is a public domain type referenced in
the signature of :func:`catalog.service.list_products`).

In the extracted svc-dashboard tree the vendored ``Pagination`` /
``PaginatedProductsInternal`` / ``Product`` dataclasses live on the catalog
HTTP shim (``app.core.extracted_clients.catalog_client``), and
``ProfileCompleteness`` on the customer shim — so this file stays empty-but-
legal, kept for §3.C canonical-subtree completeness.

File kept for §3.C canonical-subtree completeness (alongside the structural
``repository.py`` absence locked at §13.D — exactly 5 files in dashboard's
subtree: ``__init__.py``, ``router.py``, ``service.py``, ``schemas.py``,
``domain.py``, ``exceptions.py``). The §19 CI linter must allowlist
dashboard's no-repository.py exception; it does NOT need to allowlist
this file (an empty ``domain.py`` is unusual but legal).

Cross-module imports flow through the service layer:

* ``catalog.domain.PaginatedProductsInternal`` — return type of
  :func:`catalog.service.list_products`; consumed by dashboard's
  ``_compose_response``.
* ``catalog.domain.Pagination`` — parameter type of
  :func:`catalog.service.list_products`; built by dashboard's router
  from :class:`schemas.DashboardQuery`.
* ``customer.domain.ProfileCompleteness`` — return type of
  :func:`customer.service.get_onboarding_completeness`; consumed by
  dashboard's ``_compose_response``.

V1.5 forward reference: if the §13.A.1 amendment is lifted and the original
4-field ``Pagination`` returns, that shape would re-land in this file (with
the ``status_filter`` + ``search`` predicates plumbed through to a §10
catalog-amendment) rather than reusing catalog's narrower V1 shape.
"""

from __future__ import annotations

__all__: list[str] = []
