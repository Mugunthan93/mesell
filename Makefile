.PHONY: dev dev-local dev-down test lint migrate migrate-new build deploy frontend-dev

# Docker-based full stack (API + Postgres + Valkey in containers). Requires Docker Desktop.
dev:
	docker compose -f docker-compose.dev.yml up --build
dev-down:
	docker compose -f docker-compose.dev.yml down

# Native local stack — NO Docker. Backend equivalent of the frontend `pnpm run dev:static`.
# Starts brew Postgres+Valkey, applies migrations, runs uvicorn :8000 in the foreground (Ctrl-C to stop).
dev-local:
	-brew services start postgresql@16
	-brew services start valkey
	cd backend && .venv/bin/alembic upgrade head && .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

test:
	cd backend && TEST_DATABASE_URL=postgresql+asyncpg://meesell:password@localhost:5432/meesell_test .venv/bin/python -m pytest tests/ -v
lint:
	cd backend && python -m ruff check app/
migrate:
	cd backend && .venv/bin/alembic upgrade head
migrate-new:
	cd backend && .venv/bin/alembic revision --autogenerate -m "$(msg)"
build:
	docker build -t asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/api:latest ./backend
	docker build -t asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/frontend:latest ./frontend
deploy: build
	docker push asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/api:latest
	docker push asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/frontend:latest
	ssh meesell-vm "kubectl -n meesell set image deployment/api api=asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/api:latest"
	ssh meesell-vm "kubectl -n meesell rollout status deployment/api --timeout=120s"

# Native frontend (memory-safe static path; no Docker). Builds 7 apps then serves 4200-4206.
frontend-dev:
	cd frontend && pnpm run dev:static up
