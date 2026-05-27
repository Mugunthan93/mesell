# CLAUDE.md — MeeSell Project Context

## What is MeeSell?

MeeSell is an AI-powered SaaS platform for Meesho marketplace suppliers. It helps sellers create product catalogs, validate listing quality, and optimize pricing — all from one platform at ₹499–1,999/month.

## Architecture

Single-node K3s cluster on GCP (asia-south1). All services run as Kubernetes pods.

```
Client (React PWA) → FastAPI API (2 replicas) → PostgreSQL + Valkey
                                              → Celery Workers (2 replicas)
                                              → GCS (file storage)
                                              → Gemini 2.5 Flash (AI)
```

## Tech Stack

- **Backend:** Python 3.12, FastAPI, SQLAlchemy (async), Celery
- **Frontend:** React 18, Vite, Tailwind CSS, Zustand
- **Database:** PostgreSQL 16 (K3s pod)
- **Cache/Queue:** Valkey 8 (Redis-compatible, K3s pod)
- **AI Text:** Google Gemini 2.5 Flash API
- **AI Image:** rembg (self-hosted, CPU mode)
- **Storage:** Google Cloud Storage (GCS)
- **Auth:** Phone OTP (MSG91) + JWT (PyJWT)
- **Payments:** Razorpay Subscriptions
- **Infra:** K3s on GCP e2-standard-2, Traefik ingress, cert-manager

## Project Structure

```
meesell/
├── CLAUDE.md                    ← You are here
├── TICKETS.md                   ← Sprint tasks (read this for next task)
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, middleware, health check
│   │   ├── config.py            # Pydantic Settings (env vars)
│   │   ├── database.py          # SQLAlchemy async engine + session
│   │   ├── models/              # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── catalog.py
│   │   │   ├── sku.py
│   │   │   ├── image.py
│   │   │   └── export.py
│   │   ├── schemas/             # Pydantic request/response schemas
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── catalog.py
│   │   │   ├── sku.py
│   │   │   ├── quality.py
│   │   │   └── pricing.py
│   │   ├── routers/             # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── auth.py
│   │   │   ├── catalogs.py
│   │   │   ├── skus.py
│   │   │   ├── images.py
│   │   │   ├── quality.py
│   │   │   ├── pricing.py
│   │   │   └── exports.py
│   │   ├── services/            # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── ai_engine.py     # Gemini API calls + prompt management
│   │   │   ├── image_processor.py # rembg + PIL pipeline
│   │   │   ├── quality_engine.py  # QualityGate rules engine
│   │   │   ├── pricing_engine.py  # P&L calculator
│   │   │   ├── export_service.py  # CSV/ZIP generation
│   │   │   ├── otp_service.py     # MSG91 integration
│   │   │   └── storage.py         # GCS upload/download
│   │   ├── workers/             # Celery tasks
│   │   │   ├── __init__.py
│   │   │   ├── celery_app.py
│   │   │   ├── image_tasks.py
│   │   │   └── generation_tasks.py
│   │   ├── middleware/
│   │   │   ├── __init__.py
│   │   │   ├── auth.py          # JWT validation
│   │   │   ├── rate_limit.py    # Valkey sliding window
│   │   │   └── plan_guard.py    # Plan limit enforcement
│   │   └── data/                # Static data files
│   │       ├── meesho_categories.json
│   │       ├── meesho_shipping_slabs.json
│   │       ├── banned_words.json
│   │       └── category_attributes.json
│   ├── alembic/                 # DB migrations
│   │   ├── alembic.ini
│   │   └── versions/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_catalog.py
│   │   ├── test_quality.py
│   │   └── test_pricing.py
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/
│   │   │   └── client.js        # Axios instance with JWT interceptor
│   │   ├── stores/
│   │   │   ├── authStore.js     # Zustand auth state
│   │   │   └── catalogStore.js  # Zustand catalog state
│   │   ├── pages/
│   │   │   ├── Onboarding.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── CatalogCreate.jsx
│   │   │   ├── CatalogPreview.jsx
│   │   │   ├── QualityCheck.jsx
│   │   │   ├── PriceCalculator.jsx
│   │   │   └── ExportPage.jsx
│   │   ├── components/
│   │   │   ├── ImageUploader.jsx
│   │   │   ├── QualityScorecard.jsx
│   │   │   ├── PnLBreakdown.jsx
│   │   │   ├── CatalogCard.jsx
│   │   │   └── Navbar.jsx
│   │   └── utils/
│   │       └── formatters.js
│   ├── public/
│   │   └── manifest.json
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   └── package.json
├── k8s/
│   ├── namespace.yaml
│   ├── secrets.yaml.example
│   ├── config.yaml
│   ├── postgres.yaml
│   ├── valkey.yaml
│   ├── api.yaml
│   ├── worker.yaml
│   ├── frontend.yaml
│   ├── ingress.yaml
│   └── backup-cronjob.yaml
├── scripts/
│   └── setup-vm.sh
├── docker-compose.dev.yml       # Local dev (no K3s needed)
├── Makefile
└── .gitignore
```

## Coding Conventions

### Python (Backend)

- **Python 3.12**, type hints on all function signatures
- **Async everything**: use `async def` for all route handlers and service methods
- **SQLAlchemy async**: use `AsyncSession`, never synchronous queries
- **Pydantic v2** for all request/response schemas
- **Error handling**: raise `HTTPException` with appropriate status codes, never return raw error strings
- **Naming**: snake_case for functions/variables, PascalCase for classes, UPPER_CASE for constants
- **Imports**: stdlib → third-party → local, separated by blank lines
- **No print()**: use `logging.getLogger(__name__)` everywhere
- **Docstrings**: required on all service functions, optional on simple route handlers
- **Tests**: pytest + httpx AsyncClient for API tests

```python
# Example pattern for a router
from fastapi import APIRouter, Depends, HTTPException, status
from app.schemas.catalog import CatalogCreate, CatalogResponse
from app.services.catalog_service import CatalogService
from app.middleware.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/catalogs", tags=["catalogs"])

@router.post("/", response_model=CatalogResponse, status_code=status.HTTP_201_CREATED)
async def create_catalog(
    data: CatalogCreate,
    user: User = Depends(get_current_user),
    service: CatalogService = Depends(),
) -> CatalogResponse:
    return await service.create(user_id=user.id, data=data)
```

```python
# Example pattern for a service
import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.catalog import Catalog
from app.schemas.catalog import CatalogCreate

logger = logging.getLogger(__name__)

class CatalogService:
    def __init__(self, db: AsyncSession = Depends(get_db)):
        self.db = db

    async def create(self, user_id: UUID, data: CatalogCreate) -> Catalog:
        """Create a new catalog for the user."""
        catalog = Catalog(user_id=user_id, name=data.name, status="draft")
        self.db.add(catalog)
        await self.db.commit()
        await self.db.refresh(catalog)
        logger.info(f"Catalog created: {catalog.id} for user {user_id}")
        return catalog
```

### React (Frontend)

- **React 18** with functional components and hooks only
- **Tailwind CSS** for all styling, no CSS modules, no styled-components
- **Zustand** for global state (auth, catalog), React state for local UI state
- **Axios** for API calls via centralized client with JWT interceptor
- **Naming**: PascalCase for components, camelCase for functions/variables, UPPER_CASE for constants
- **File structure**: one component per file, named same as component
- **No inline styles**: use Tailwind classes exclusively
- **Error boundaries**: wrap page-level components
- **Loading states**: show skeleton/spinner for all async operations

```jsx
// Example pattern for a page component
import { useState, useEffect } from "react";
import { useAuthStore } from "../stores/authStore";
import { api } from "../api/client";
import CatalogCard from "../components/CatalogCard";

export default function Dashboard() {
  const { user } = useAuthStore();
  const [catalogs, setCatalogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/catalogs").then(res => {
      setCatalogs(res.data.catalogs);
      setLoading(false);
    });
  }, []);

  if (loading) return <div className="animate-pulse">Loading...</div>;

  return (
    <div className="max-w-5xl mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">Dashboard</h1>
      {catalogs.map(c => <CatalogCard key={c.id} catalog={c} />)}
    </div>
  );
}
```

### Valkey (Cache/Queue)

- **Connection URL**: `redis://valkey:6379/{db}` (Valkey uses Redis protocol)
- **DB 0**: Sessions, OTP, rate limits
- **DB 1**: Celery broker
- **DB 2**: Celery result backend
- **Key naming**: `{namespace}:{entity}:{id}` (e.g., `otp:+919876543210`, `ratelimit:user123:generate:60`)
- **TTL**: always set TTL on temporary keys, never store without expiry
- **Library**: `redis.asyncio` (works with Valkey unchanged)

### Database

- **UUIDs** for all primary keys (gen_random_uuid())
- **TIMESTAMPTZ** for all timestamps (timezone-aware)
- **JSONB** for flexible structured data (ai_attributes, quality_checks)
- **Indexes**: on all foreign keys + frequently queried columns
- **Migrations**: Alembic, one migration per ticket, descriptive message
- **No raw SQL in routes**: always go through SQLAlchemy ORM or service layer

### API Design

- **Prefix**: `/api/v1/` for all endpoints
- **Auth**: JWT Bearer token in Authorization header
- **Pagination**: `?page=1&limit=20` with response `{ data: [...], total: N, page: N }`
- **Errors**: `{ "detail": "Human-readable message" }` with appropriate HTTP status
- **File uploads**: multipart/form-data, max 10MB per image
- **Background jobs**: return `{ "job_id": "...", "status": "processing" }`, poll via GET

### Git

- **Branch naming**: `ticket/{ticket-number}-short-description` (e.g., `ticket/T01-project-setup`)
- **Commit messages**: `T01: Set up FastAPI project with config and health endpoint`
- **One ticket per PR**, squash merge to main
- **Never commit**: .env, secrets.yaml, __pycache__, node_modules, .venv

## Key Decisions (Do Not Change)

1. **Valkey, not Redis** — open-source Redis fork, same protocol, no license issues
2. **GCS, not S3** — we're on GCP, same cloud as Gemini API
3. **Gemini 2.5 Flash, not GPT-4** — 10x cheaper, sufficient quality for catalog text
4. **rembg on CPU, not GPU** — 3-5s/image is acceptable for MVP, no GPU cost
5. **Phone OTP login, not email** — Indian sellers prefer phone, no password friction
6. **K3s, not docker-compose in prod** — consistent with Shotfox infra, easy to scale
7. **Meesho CSV export, not API upload** — Meesho has no open API for small third parties
8. **FastAPI, not Django** — async-first, better for AI/ML pipeline integration
9. **Zustand, not Redux** — minimal boilerplate for small frontend
10. **Tailwind, not MUI** — lighter, more customizable, mobile-first

## Environment Variables

See `backend/.env.example` for full list. Key ones:
- `DATABASE_URL` — PostgreSQL async connection string
- `VALKEY_URL` — Valkey connection (redis:// protocol)
- `GEMINI_API_KEY` — Google Gemini API key
- `GCS_BUCKET` — GCS bucket name for images/exports
- `MSG91_AUTH_KEY` — SMS OTP provider
- `JWT_SECRET` — JWT signing secret
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — Payment gateway

## Commands

```bash
# Local development
make dev              # Start docker-compose.dev.yml (API + Valkey + PostgreSQL)
make migrate          # Run Alembic migrations
make test             # Run pytest
make lint             # Run ruff linter

# Frontend
cd frontend && npm run dev    # Vite dev server on :5173
cd frontend && npm run build  # Production build

# Production (on GCP VM)
make deploy           # Build, push, kubectl rolling update
```

## What to Read Before Starting

1. This file (CLAUDE.md) — you're here
2. `TICKETS.md` — find your assigned ticket, read it fully
3. The relevant service/router files referenced in the ticket
4. `backend/.env.example` for required environment variables
