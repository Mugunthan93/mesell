.PHONY: dev test lint migrate build deploy
dev:
	docker compose -f docker-compose.dev.yml up --build
dev-down:
	docker compose -f docker-compose.dev.yml down
test:
	cd backend && python -m pytest tests/ -v
lint:
	cd backend && python -m ruff check app/
migrate:
	cd backend && alembic upgrade head
migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"
build:
	docker build -t asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/api:latest ./backend
	docker build -t asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/frontend:latest ./frontend
deploy: build
	docker push asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/api:latest
	docker push asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/frontend:latest
	ssh meesell-vm "kubectl -n meesell set image deployment/api api=asia-south1-docker.pkg.dev/$(PROJECT_ID)/meesell/api:latest"
	ssh meesell-vm "kubectl -n meesell rollout status deployment/api --timeout=120s"
frontend-dev:
	cd frontend && npm run dev
