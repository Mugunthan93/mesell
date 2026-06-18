"""gen_openapi.py — dump the FastAPI app's OpenAPI spec to JSON.

Usage (from backend/ directory):
    python scripts/gen_openapi.py [--out path/to/openapi.json]

The script imports app.main, which triggers Pydantic Settings validation.
Because Settings has 18 Required fields (per §5.D), the script sets dummy
non-empty env vars for every Required field before the import so the
fail-fast validator passes without real credentials.

Zero cloud spend: no network calls are made.  The OpenAPI spec is generated
entirely in-process from the FastAPI route/schema declarations.

If the app import fails (e.g. missing venv dep), the script falls back to
fetching the spec from a running server at http://localhost:8000/openapi.json
(per the task brief's fallback instruction).  Set MEESELL_OPENAPI_URL to
override the fallback URL.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# ── Required env vars (§5.D) — dev-sentinel values so Settings validator passes ──
_REQUIRED_SENTINEL: dict[str, str] = {
    "DATABASE_URL": "postgresql+asyncpg://meesell:dev@localhost:5432/meesell",
    "VALKEY_URL": "redis://localhost:6379/0",
    "JWT_SECRET": "dev-jwt-secret-sentinel-64chars-placeholder-00000",
    "REFRESH_TOKEN_PEPPER": "dev-refresh-pepper-sentinel",
    "MSG91_AUTH_KEY": "dev-msg91-auth-key-sentinel",
    "MSG91_TEMPLATE_ID": "dev-msg91-template-id-sentinel",
    "RAZORPAY_KEY_ID": "rzp_test_sentinel_key_id",
    "RAZORPAY_KEY_SECRET": "dev-razorpay-secret-sentinel",
    "RAZORPAY_WEBHOOK_SECRET": "dev-webhook-secret-sentinel",
    "GEMINI_API_KEY": "dev-gemini-api-key-sentinel",
    "GCS_BUCKET": "dev-gcs-bucket-sentinel",
    "GCS_PROJECT_ID": "dev-gcs-project-id-sentinel",
    "LANGFUSE_PUBLIC_KEY": "dev-langfuse-public-key-sentinel",
    "LANGFUSE_SECRET_KEY": "dev-langfuse-secret-key-sentinel",
    "AUDIT_PII_SALT": "dev-audit-pii-salt-sentinel",
    "CORS_ALLOWED_ORIGINS": "http://localhost:4200",
    "APP_ENV": "development",
}


def _inject_sentinel_env() -> None:
    """Set sentinel env vars for any Required field not already set."""
    for key, val in _REQUIRED_SENTINEL.items():
        os.environ.setdefault(key, val)


def _dump_from_app() -> dict:
    """Import app.main and call app.openapi() to get the spec."""
    _inject_sentinel_env()
    # Must add backend/ to sys.path so `import app.main` resolves.
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from app.main import app  # noqa: PLC0415
    return app.openapi()


def _dump_from_server(url: str) -> dict:
    """Fetch the OpenAPI JSON from a running server."""
    import urllib.request  # stdlib — no extra dep

    print(f"[gen_openapi] Fetching live spec from {url}", file=sys.stderr)
    with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310
        return json.loads(resp.read())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dump MeeSell OpenAPI spec to JSON")
    parser.add_argument(
        "--out",
        default="backend/postman/openapi.json",
        help="Output path (default: backend/postman/openapi.json)",
    )
    args = parser.parse_args(argv)

    try:
        spec = _dump_from_app()
        source = "app.main"
    except Exception as exc:  # noqa: BLE001
        fallback_url = os.environ.get(
            "MEESELL_OPENAPI_URL", "http://localhost:8000/openapi.json"
        )
        print(
            f"[gen_openapi] App import failed: {exc}. "
            f"Falling back to live server at {fallback_url}",
            file=sys.stderr,
        )
        try:
            spec = _dump_from_server(fallback_url)
            source = f"live server ({fallback_url})"
        except Exception as fetch_exc:  # noqa: BLE001
            print(
                f"[gen_openapi] Fallback also failed: {fetch_exc}",
                file=sys.stderr,
            )
            return 1

    # Resolve the output path relative to the script's parent directory
    # (backend/) so it works regardless of cwd.
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = args.out
    if not os.path.isabs(out_path):
        out_path = os.path.join(backend_dir, "..", out_path)
    out_path = os.path.normpath(out_path)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    path_count = len(spec.get("paths", {}))
    op_count = sum(
        len([m for m in path_item if m in ("get", "post", "patch", "put", "delete")])
        for path_item in spec.get("paths", {}).values()
    )
    print(
        f"[gen_openapi] Wrote {out_path} "
        f"(source={source}, paths={path_count}, operations={op_count})",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
