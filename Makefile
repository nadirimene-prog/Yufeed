.PHONY: help setup setup-api setup-web lint lint-api lint-web test test-api test-web build-web build-images docker-up docker-down ci

API_DIR := apps/api
WEB_DIR := apps/web
PYTHON ?= python3

help:
	@echo "YuFeed developer commands"
	@echo ""
	@echo "  make setup        Install backend + frontend dependencies"
	@echo "  make lint         Run backend and frontend lint checks"
	@echo "  make test         Run backend and frontend tests"
	@echo "  make build-web    Build Next.js frontend bundle"
	@echo "  make build-images Build backend and frontend Docker images"
	@echo "  make docker-up    Start local stack with Docker Compose"
	@echo "  make docker-down  Stop local Docker Compose stack"
	@echo "  make ci           Run pre-commit checks on all files"

setup: setup-api setup-web

setup-api:
	cd $(API_DIR) && $(PYTHON) -m pip install --upgrade pip && $(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

setup-web:
	cd $(WEB_DIR) && npm ci

lint: lint-api lint-web

lint-api:
	cd $(API_DIR) && $(PYTHON) -m flake8 src tests --max-line-length=100 --extend-ignore=E203,E402,E501,E712,E741,F401,F841 && $(PYTHON) -m black --check src

lint-web:
	cd $(WEB_DIR) && npm run lint -- --max-warnings=0 && npm run type-check

test: test-api test-web

test-api:
	cd $(API_DIR) && pytest

test-web:
	cd $(WEB_DIR) && npm run test:coverage

build-web:
	cd $(WEB_DIR) && npm run build

build-images:
	docker compose build api web

docker-up:
	docker compose up --build

docker-down:
	docker compose down

ci:
	pre-commit run --all-files
