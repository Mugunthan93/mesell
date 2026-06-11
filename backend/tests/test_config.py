"""Settings + helper-property tests for app.config."""

import importlib
import os

import pytest

pytestmark = pytest.mark.unit


def _reload_config(env: dict[str, str]):
    """Reload app.shared.config with a controlled environment."""
    original = {k: os.environ.get(k) for k in env}
    try:
        for k, v in env.items():
            os.environ[k] = v
        import app.shared.config

        importlib.reload(app.shared.config)
        return app.shared.config.settings
    finally:
        for k, v in original.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_settings_defaults_to_development_dev_flag_true():
    s = _reload_config({"APP_ENV": "development"})
    assert s.is_dev is True
    assert s.APP_ENV == "development"


def test_settings_production_dev_flag_false():
    s = _reload_config({"APP_ENV": "production"})
    assert s.is_dev is False


def test_cors_origin_list_splits_and_trims():
    s = _reload_config(
        {
            "APP_ENV": "development",
            "CORS_ALLOWED_ORIGINS": (
                "https://meesell.in, https://www.meesell.in ,https://api.meesell.in"
            ),
        }
    )
    assert s.CORS_ALLOWED_ORIGINS == [
        "https://meesell.in",
        "https://www.meesell.in",
        "https://api.meesell.in",
    ]


def test_jwt_secret_picks_up_env_override():
    s = _reload_config({"APP_ENV": "development", "JWT_SECRET": "override-from-env"})
    assert s.JWT_SECRET == "override-from-env"


def test_database_url_default_uses_async_driver():
    s = _reload_config({"APP_ENV": "development"})
    assert s.DATABASE_URL.startswith("postgresql+asyncpg://")
