"""QA Wave 3 — W3-BE-6: Export ZIP member structure (Wave-1 P1.11 carry-forward).

REWRITE of the Wave-1 self-skipping test. The previous version called
``svc._build_xlsx_bytes(...)`` which does not exist on the ``export.service``
module (the actual XLSX writer is ``_write_xlsx(row: XlsxRowSpec) -> bytes``
and the image-zip packager is ``_package_images_zip(image_refs, user_id, db)``).

This rewrite targets the CORRECT helper signatures:
  - ``_write_xlsx(XlsxRowSpec)`` — builds XLSX bytes (unit-testable, no DB).
  - ``_package_images_zip(image_refs, user_id, db)`` — builds an image ZIP;
    GCSAdapter mocked so downloads return in-memory bytes.

Two test cases:
  1. XLSX member is a valid ZIP internally (openpyxl-readable) and carries
     at least one worksheet.
  2. Image ZIP produced by ``_package_images_zip`` with mocked GCS contains
     the expected member names (one per image_ref, keyed by basename).

GCSAdapter is mocked at the adapter boundary (``app.adapters.gcs.download_bytes``)
via the shared ``mock_gcs_adapter`` conftest fixture — never calls real GCS.

Marker: integration (uses the real ``app.modules.export.service`` + ``domain``
module; no DB connection needed for the XLSX builder path; no real external calls).
"""

from __future__ import annotations

import io
import uuid
import zipfile

import pytest

pytestmark = pytest.mark.integration


# ─────────────────────────────────────────────────────────────────────────────
# W3-BE-6a — _write_xlsx produces a valid XLSX ZIP with at least one sheet
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_write_xlsx_produces_valid_xlsx_with_expected_members():
    """_write_xlsx(XlsxRowSpec) → bytes that openpyxl can load (valid XLSX).

    Arrangement: build a minimal XlsxRowSpec with 2 columns.
    Act: call _write_xlsx synchronously.
    Assert: returned bytes load as a valid openpyxl Workbook + have ≥1 sheet
            + the sheet carries the expected headers in row 1.

    GCS is NOT involved — this helper is pure in-memory XLSX construction.
    """
    openpyxl = pytest.importorskip("openpyxl", reason="openpyxl required for XLSX assertion")

    from app.modules.export.domain import XlsxColumnSpec, XlsxRowSpec
    from app.modules.export.service import _write_xlsx

    row = XlsxRowSpec(
        main_sheet_label="Eye-Serum",
        columns=(
            XlsxColumnSpec(
                canonical_name="product_name",
                meesho_column_header="Product Name",
                meesho_column_index=0,
                value="Glow Eye Serum",
            ),
            XlsxColumnSpec(
                canonical_name="brand_name",
                meesho_column_header="Brand Name",
                meesho_column_index=1,
                value="BrightLab",
            ),
        ),
    )

    # Act.
    xlsx_bytes = _write_xlsx(row)

    # Assert — non-empty bytes.
    assert isinstance(xlsx_bytes, bytes) and len(xlsx_bytes) > 0, (
        "_write_xlsx must return non-empty bytes"
    )

    # Assert — XLSX is a valid ZIP (openpyxl can open it).
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    assert wb.sheetnames, "XLSX must contain at least one sheet"

    # Assert — the XLSX itself is a ZIP archive (all XLSX files are).
    assert zipfile.is_zipfile(io.BytesIO(xlsx_bytes)), (
        "XLSX bytes must be a valid ZIP archive (XLSX is a ZIP internally)"
    )

    # Assert — sheet header row carries the expected Meesho column names.
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    assert len(rows) >= 1, "Workbook sheet must have at least one row (headers)"
    header_row = rows[0]
    assert "Product Name" in header_row, (
        f"Header row must contain 'Product Name'; got: {header_row}"
    )
    assert "Brand Name" in header_row, (
        f"Header row must contain 'Brand Name'; got: {header_row}"
    )

    # Assert — data row carries the expected values.
    assert len(rows) >= 2, "Workbook sheet must have a data row after the header"
    data_row = rows[1]
    assert "Glow Eye Serum" in data_row, (
        f"Data row must carry 'Glow Eye Serum'; got: {data_row}"
    )
    assert "BrightLab" in data_row, (
        f"Data row must carry 'BrightLab'; got: {data_row}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# W3-BE-6b — _package_images_zip produces a ZIP with the expected member names
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_package_images_zip_member_names_match_gcs_basenames(
    mock_gcs_adapter,
):
    """_package_images_zip builds a ZIP whose member names equal GCS path basenames.

    Arrangement:
      - Seed the mock_gcs_adapter.storage with 2 JPEG stubs keyed by GCS path.
      - Build image_refs tuple with those paths.
    Act: call _package_images_zip.
    Assert:
      - Returns non-empty bytes.
      - ZIP is valid and contains exactly the 2 expected member names.
      - Member names are the basenames of the GCS paths (not the full paths).
      - GCSAdapter.download_bytes was called (not real GCS).
    """
    from app.modules.export.service import _package_images_zip

    user_id = uuid.uuid4()
    product_id = uuid.uuid4()

    # Stub image bytes (minimal valid bytes — the ZIP packager stores bytes as-is).
    img_bytes_1 = b"\xff\xd8\xff\xe0" + b"\x00" * 10 + b"\xff\xd9"
    img_bytes_2 = b"\xff\xd8\xff\xe0" + b"\x01" * 10 + b"\xff\xd9"

    path_1 = f"meesell-images/{user_id}/{product_id}/0.jpg"
    path_2 = f"meesell-images/{user_id}/{product_id}/1.jpg"

    # Seed mock GCS storage.
    mock_gcs_adapter.storage[path_1] = img_bytes_1
    mock_gcs_adapter.storage[path_2] = img_bytes_2

    image_refs = (path_1, path_2)

    # _package_images_zip takes db but uses it only for signature parity (ARG001).
    class _FakeDB:
        pass

    # Act.
    zip_bytes = await _package_images_zip(
        image_refs=image_refs,
        user_id=user_id,
        db=_FakeDB(),
    )

    # Assert — non-empty bytes.
    assert isinstance(zip_bytes, bytes) and len(zip_bytes) > 0, (
        "_package_images_zip must return non-empty bytes when image_refs is non-empty"
    )

    # Assert — valid ZIP.
    assert zipfile.is_zipfile(io.BytesIO(zip_bytes)), (
        "_package_images_zip must return a valid ZIP archive"
    )

    # Assert — member names are the GCS path basenames.
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        member_names = zf.namelist()

    assert "0.jpg" in member_names, (
        f"ZIP must contain member '0.jpg'; got members: {member_names}"
    )
    assert "1.jpg" in member_names, (
        f"ZIP must contain member '1.jpg'; got members: {member_names}"
    )
    assert len(member_names) == 2, (
        f"ZIP must have exactly 2 members (one per image_ref); got: {member_names}"
    )

    # Assert — GCS adapter was called (not real GCS).
    assert mock_gcs_adapter.download_bytes.await_count == 2, (
        f"GCSAdapter.download_bytes must be called exactly 2 times; "
        f"got {mock_gcs_adapter.download_bytes.await_count}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# W3-BE-6c — _package_images_zip returns empty bytes for empty image_refs
# ─────────────────────────────────────────────────────────────────────────────
@pytest.mark.asyncio
async def test_package_images_zip_empty_refs_returns_empty_bytes(
    mock_gcs_adapter,
):
    """_package_images_zip(image_refs=()) → b'' (no ZIP produced).

    This is the 'export-only xlsx, no images' path (format='xlsx_only').
    """
    from app.modules.export.service import _package_images_zip

    class _FakeDB:
        pass

    zip_bytes = await _package_images_zip(
        image_refs=(),
        user_id=uuid.uuid4(),
        db=_FakeDB(),
    )

    assert zip_bytes == b"", (
        "_package_images_zip must return b'' when image_refs is empty"
    )
    # GCS was never called.
    assert mock_gcs_adapter.download_bytes.await_count == 0
