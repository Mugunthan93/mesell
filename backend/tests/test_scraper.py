"""Meesho scraper unit tests — pure helpers + schema validation (no browser)."""

import pytest
from pydantic import ValidationError

from app.schemas.scrape import ScrapeRequest
from app.services.meesho_scraper import _extract_records, _first, _normalise


def test_extract_records_finds_list_of_dicts_nested():
    payload = {"data": {"catalogs": [{"id": 1}, {"id": 2}]}}
    assert _extract_records(payload) == [{"id": 1}, {"id": 2}]


def test_extract_records_ignores_scalar_lists():
    assert _extract_records({"sizes": ["S", "M"], "items": [{"x": 1}]}) == [{"x": 1}]


def test_extract_records_empty_when_no_dicts():
    assert _extract_records({"meta": 1, "tags": ["a"]}) == []


def test_first_prefers_earlier_non_empty_key():
    rec = {"selling_price": None, "min_product_price": 299, "price": 350}
    assert _first(rec, ("price", "selling_price", "min_product_price")) == 350
    assert _first({"a": "", "b": "x"}, ("a", "b")) == "x"


def test_normalise_maps_known_fields_and_keeps_raw():
    rec = {"product_id": "p1", "name": "Kurti", "min_product_price": 299,
           "supplier_name": "ShopX", "extra": "keep-me"}
    out = _normalise(rec)
    assert out["id"] == "p1"
    assert out["name"] == "Kurti"
    assert out["price"] == 299
    assert out["shop"] == "ShopX"
    assert out["_raw"]["extra"] == "keep-me"


def test_scrape_request_accepts_meesho_url():
    req = ScrapeRequest(url="https://www.meesho.com/kurtis/pl/abc", max_items=50)
    assert req.max_items == 50


def test_scrape_request_rejects_non_meesho_url():
    with pytest.raises(ValidationError):
        ScrapeRequest(url="https://example.com/products")


def test_scrape_request_caps_max_items():
    with pytest.raises(ValidationError):
        ScrapeRequest(url="https://meesho.com/x", max_items=10_000)
