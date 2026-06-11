"""Image-module pytest fixtures.

Per BACKEND_ARCHITECTURE.md §11.K:

* ``user`` / ``other_user`` — for cross-tenant assertions.
* ``beauty_category`` + ``beauty_template`` + ``beauty_profile`` —
  re-uses the §10 catalog fixture conventions so the product fixture
  can be constructed through the service layer or directly via ORM.
* ``product`` / ``other_product`` — pre-seeded ``products`` rows owned
  by ``user`` / ``other_user`` respectively.
* ``minimal_jpeg_bytes`` / ``small_png_bytes`` — deterministic image
  bytes for the route layer (Pillow-generated 1500x1500 RGB white
  JPEG for the happy path; tiny PNG for the wrong-format test).
* ``stub_gcs_upload`` — patches :func:`adapters.gcs.upload_bytes` with
  a deterministic stub + call recorder.
* ``stub_gcs_download`` — patches :func:`adapters.gcs.download_bytes`.
* ``stub_gcs_signed_url`` — patches :func:`adapters.gcs.generate_signed_url`.
* ``stub_celery_delay`` — patches
  :func:`image.tasks.image_precheck_task.delay` so unit tests can
  verify the enqueue contract without a live Celery worker.
* ``stub_call_gemini_watermark`` — replaces
  :func:`ai_ops.client.call_gemini` with a deterministic watermark
  response.
* ``stub_call_gemini_budget_exceeded`` — re-export from catalog
  conftest pattern; raises ``BudgetExceededError``.
"""

from __future__ import annotations

import io
from typing import Any
from uuid import UUID, uuid4

import pytest
import pytest_asyncio

from app.shared.models.catalog import Catalog as CatalogORM
from app.shared.models.category import Category as CategoryORM
from app.shared.models.product import Product as ProductORM
from app.shared.models.seller_profile import SellerProfile as SellerProfileORM
from app.shared.models.template import Template as TemplateORM
from app.shared.models.user import User


# ─────────────────────────────────────────────────────────────────────────────
# DB alias
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def db(db_session):
    yield db_session


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_user(db, phone: str) -> User:
    user = User(phone=phone, plan="free")
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture(loop_scope="function")
async def user(db) -> User:
    return await _seed_user(db, phone="+915550011001")


@pytest_asyncio.fixture(loop_scope="function")
async def other_user(db) -> User:
    return await _seed_user(db, phone="+915550011002")


# ─────────────────────────────────────────────────────────────────────────────
# Seller profile (Beauty-eligible — re-uses §10 conventions)
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def beauty_profile(db, user: User) -> SellerProfileORM:
    profile = SellerProfileORM(
        user_id=user.id,
        manufacturer_name="Test Mfr",
        manufacturer_address="1 Test Rd",
        manufacturer_pincode="560001",
        packer_name="Test Packer",
        packer_address="1 Test Rd",
        packer_pincode="560001",
        country_of_origin="India",
        active_super_categories=["19"],
        compliance_extensions={
            "19": {
                "license_registration_number": "LIC-12345",
                "license_registration_type": "CDSCO",
                "license_expiry_date": "2030-12-31",
            }
        },
        onboarding_complete=True,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


# ─────────────────────────────────────────────────────────────────────────────
# Category + template
# ─────────────────────────────────────────────────────────────────────────────
@pytest_asyncio.fixture(loop_scope="function")
async def beauty_template(db) -> TemplateORM:
    template = TemplateORM(
        schema_hash="image-test-template-hash-abc123",
        schema_jsonb={
            "fields": [
                {
                    "canonical_name": "product_name",
                    "display_label": "Product Name",
                    "data_type": "text_short",
                    "max_length": 100,
                    "compulsory": True,
                },
            ],
            "compulsory": ["product_name"],
            "optional": [],
            "advanced": [],
            "primitives": ["text_short"],
        },
        compliance_shape="collapsed",
    )
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


@pytest_asyncio.fixture(loop_scope="function")
async def beauty_category(db, beauty_template: TemplateORM) -> CategoryORM:
    category = CategoryORM(
        meesho_leaf_id="img-tst-001",
        super_id="19",
        super_name="Beauty",
        path="Beauty > Skincare > Eye Serum",
        leaf_name="Eye Serum",
        template_id=beauty_template.id,
    )
    db.add(category)
    await db.flush()
    await db.refresh(category)
    return category


# ─────────────────────────────────────────────────────────────────────────────
# Products
# ─────────────────────────────────────────────────────────────────────────────
async def _seed_product(
    db, user_id: UUID, category_id: UUID, *, name: str = "Test Product"
) -> ProductORM:
    catalog = CatalogORM(user_id=user_id, name="Test Catalog", status="draft")
    db.add(catalog)
    await db.flush()
    await db.refresh(catalog)

    product = ProductORM(
        user_id=user_id,
        catalog_id=catalog.id,
        category_id=category_id,
        name=name,
        status="draft",
        fields_jsonb={},
        ai_suggestions_jsonb={},
    )
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


@pytest_asyncio.fixture(loop_scope="function")
async def product(db, user: User, beauty_category: CategoryORM) -> ProductORM:
    return await _seed_product(db, user.id, beauty_category.id)


@pytest_asyncio.fixture(loop_scope="function")
async def other_product(db, other_user: User, beauty_category: CategoryORM) -> ProductORM:
    return await _seed_product(
        db, other_user.id, beauty_category.id, name="Other User Product"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Image byte fixtures (deterministic Pillow-generated)
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def minimal_jpeg_bytes() -> bytes:
    """1500x1500 white-background RGB JPEG bytes.

    Generated in-memory via Pillow.  Constant across test invocations —
    Pillow's JPEG encoder is deterministic for a given input + quality.
    """
    from PIL import Image

    img = Image.new("RGB", (1500, 1500), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def small_jpeg_bytes() -> bytes:
    """200x200 RGB JPEG — fails the resolution check but is valid JPEG."""
    from PIL import Image

    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@pytest.fixture
def small_png_bytes() -> bytes:
    """Tiny PNG — used for the wrong-format test."""
    from PIL import Image

    img = Image.new("RGB", (10, 10), color=(255, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# GCS adapter stubs
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def stub_gcs_upload(monkeypatch):
    """Patch :func:`adapters.gcs.upload_bytes` with a deterministic stub.

    Captures every call as a dict in ``state['calls']`` so tests can
    assert path / content_type / data length.

    Returns a closure ``state`` for inspection in the test body.
    """
    from app.adapters import gcs as gcs_adapter

    state: dict[str, Any] = {"calls": []}

    async def _stub(path: str, data: bytes, content_type: str, *, bucket=None) -> str:
        state["calls"].append(
            {
                "path": path,
                "data_len": len(data),
                "content_type": content_type,
                "bucket": bucket,
            }
        )
        return f"gs://meesell-images/{path}"

    monkeypatch.setattr(gcs_adapter, "upload_bytes", _stub)
    return state


@pytest.fixture
def stub_gcs_download(monkeypatch, minimal_jpeg_bytes):
    """Patch :func:`adapters.gcs.download_bytes` to return the
    1500x1500 white JPEG by default.

    Configure a different payload via ``stub_gcs_download.set(b'...')``.
    """
    from app.adapters import gcs as gcs_adapter

    state: dict[str, Any] = {"payload": minimal_jpeg_bytes, "calls": []}

    async def _stub(path: str, *, bucket=None) -> bytes:
        state["calls"].append({"path": path, "bucket": bucket})
        return state["payload"]

    monkeypatch.setattr(gcs_adapter, "download_bytes", _stub)

    def configure(payload: bytes) -> None:
        state["payload"] = payload

    state["set"] = configure
    return state


@pytest.fixture
def stub_gcs_signed_url(monkeypatch):
    """Patch :func:`adapters.gcs.generate_signed_url` to return a
    deterministic URL.
    """
    from app.adapters import gcs as gcs_adapter

    state: dict[str, Any] = {"calls": []}

    async def _stub(path: str, *, bucket=None, ttl_seconds=3600, method="GET") -> str:
        state["calls"].append({"path": path, "ttl_seconds": ttl_seconds, "method": method})
        return f"https://storage.googleapis.com/test/{path}?signed=1&ttl={ttl_seconds}"

    monkeypatch.setattr(gcs_adapter, "generate_signed_url", _stub)
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Celery enqueue stub
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def stub_celery_delay(monkeypatch):
    """Patch :func:`image.tasks.image_precheck_task.delay` so unit tests
    can verify the enqueue contract without a live Celery broker.

    Captures every call as a dict in ``state['calls']``.  Returns an
    object with a deterministic ``.id`` attribute (mimics
    Celery's AsyncResult).
    """
    from app.modules.image import tasks as image_tasks

    state: dict[str, Any] = {"calls": []}

    class _FakeAsyncResult:
        def __init__(self, task_id: str):
            self.id = task_id

    def _stub_delay(*args, **kwargs):
        state["calls"].append({"args": tuple(args), "kwargs": dict(kwargs)})
        return _FakeAsyncResult(task_id=f"fake-task-{uuid4()}")

    # Patch the unbound `.delay` attribute on the celery shared_task object.
    monkeypatch.setattr(image_tasks.image_precheck_task, "delay", _stub_delay)
    return state


# ─────────────────────────────────────────────────────────────────────────────
# Gemini watermark stubs
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def stub_call_gemini_watermark(monkeypatch):
    """Replace :func:`ai_ops.client.call_gemini` with a deterministic
    watermark response.

    Default response: ``{"has_watermark": False, "confidence": 0.95}``
    (no watermark detected).  Configure via the returned callable.
    """
    from app.adapters.gemini import GeminiResponse
    from app.ai_ops import client as ai_ops_client
    from app.ai_ops.client import AIResponse

    state: dict[str, Any] = {
        "parsed": {"has_watermark": False, "confidence": 0.95},
        "calls": [],
    }

    async def _stub(ctx, prompt_id, prompt_vars=None, *, image_bytes=None,
                    allowed_enums=None, response_mime_type=None,
                    max_output_tokens=None):
        state["calls"].append(
            {
                "workload": ctx.workload,
                "prompt_id": prompt_id,
                "image_bytes_len": len(image_bytes) if image_bytes else 0,
            }
        )
        return AIResponse(
            parsed=dict(state["parsed"]),
            raw_response=GeminiResponse(
                text="", input_tokens=10, output_tokens=10,
                finish_reason="STOP", raw={"stub": True},
            ),
            cost_inr=0.0,
            layer2_retries=0,
            trace_id="stub-watermark-trace",
        )

    monkeypatch.setattr(ai_ops_client, "call_gemini", _stub)

    def configure(*, parsed: dict | None = None) -> dict[str, Any]:
        if parsed is not None:
            state["parsed"] = dict(parsed)
        return state

    return configure


@pytest.fixture
def stub_call_gemini_budget_exceeded(monkeypatch):
    """Replace :func:`ai_ops.client.call_gemini` with one that raises
    :class:`BudgetExceededError`.

    Per §11.K integration #2 contract — the watermark step gracefully
    falls back to ``"skipped_budget"`` AND overall status still
    resolves to ``"ready"`` if the 4 deterministic checks pass.
    """
    from app.ai_ops import client as ai_ops_client
    from app.ai_ops.budget_cap import BudgetExceededError

    async def _raise(*args, **kwargs):
        raise BudgetExceededError(
            detail="Daily AI budget exhausted (test stub)."
        )

    monkeypatch.setattr(ai_ops_client, "call_gemini", _raise)
