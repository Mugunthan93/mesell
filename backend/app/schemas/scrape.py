"""Meesho research scraper request/response schemas."""

from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

_ALLOWED_HOSTS = {"meesho.com", "www.meesho.com"}


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="A meesho.com search or category URL")
    max_items: int = Field(default=100, ge=1, le=500)
    endpoint_hint: str | None = Field(
        default=None,
        description="Optional substring identifying the catalog XHR; refine via discover().",
    )

    @field_validator("url")
    @classmethod
    def _must_be_meesho(cls, v: str) -> str:
        host = (urlparse(v).hostname or "").lower()
        if host not in _ALLOWED_HOSTS:
            raise ValueError("url must be a meesho.com link")
        return v


class ScrapeProduct(BaseModel):
    id: str | None = None
    name: str | None = None
    price: float | None = None
    mrp: float | None = None
    rating: float | None = None
    rating_count: int | str | None = None
    shop: str | None = None
    image: str | None = None
    url: str | None = None


class ScrapeJobResponse(BaseModel):
    job_id: str
    status: str
    url: str
