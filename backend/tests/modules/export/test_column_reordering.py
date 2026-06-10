"""§14.K unit test 10 — column reordering.

Schema fields[] order ``[b, a, c]`` → row.columns sorted to ``[b, a, c]``
by :attr:`XlsxColumnSpec.meesho_column_index`.
"""

from __future__ import annotations

from app.modules.export.domain import XlsxColumnSpec, XlsxRowSpec
from app.modules.export.service import _reorder_columns


def test_reorder_columns_sorts_by_meesho_index():
    """Out-of-order columns are sorted into ascending index order."""
    row = XlsxRowSpec(
        main_sheet_label="Sheet",
        columns=(
            XlsxColumnSpec(
                canonical_name="c", meesho_column_header="C", meesho_column_index=2, value="C-val"
            ),
            XlsxColumnSpec(
                canonical_name="a", meesho_column_header="A", meesho_column_index=0, value="A-val"
            ),
            XlsxColumnSpec(
                canonical_name="b", meesho_column_header="B", meesho_column_index=1, value="B-val"
            ),
        ),
    )
    sorted_row = _reorder_columns(row, schema={})
    indices = [c.meesho_column_index for c in sorted_row.columns]
    canonicals = [c.canonical_name for c in sorted_row.columns]
    assert indices == [0, 1, 2]
    assert canonicals == ["a", "b", "c"]


def test_reorder_columns_idempotent_on_sorted_input():
    """Already-sorted columns survive a second reorder pass unchanged."""
    row = XlsxRowSpec(
        main_sheet_label="Sheet",
        columns=(
            XlsxColumnSpec(
                canonical_name="a", meesho_column_header="A", meesho_column_index=0, value="A"
            ),
            XlsxColumnSpec(
                canonical_name="b", meesho_column_header="B", meesho_column_index=1, value="B"
            ),
            XlsxColumnSpec(
                canonical_name="c", meesho_column_header="C", meesho_column_index=2, value="C"
            ),
        ),
    )
    pass1 = _reorder_columns(row, schema={})
    pass2 = _reorder_columns(pass1, schema={})
    assert [c.canonical_name for c in pass2.columns] == ["a", "b", "c"]


def test_reorder_columns_schema_arg_is_unused():
    """The ``schema`` arg is kept for §14.C signature parity but the
    sort is driven purely by ``meesho_column_index``.  We pass an empty
    schema to prove it.
    """
    row = XlsxRowSpec(
        main_sheet_label="Sheet",
        columns=(
            XlsxColumnSpec(
                canonical_name="z", meesho_column_header="Z", meesho_column_index=5, value="z"
            ),
            XlsxColumnSpec(
                canonical_name="a", meesho_column_header="A", meesho_column_index=1, value="a"
            ),
        ),
    )
    result = _reorder_columns(row, schema={"fields": []})
    assert [c.canonical_name for c in result.columns] == ["a", "z"]
