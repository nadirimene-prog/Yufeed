# YuFeed - Makefile
# Common development tasks and shortcuts

.PHONY: help install dev build test lint format type-check security-scan verify clean docker-up docker-down

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
BLUE := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)YuFeed - Available Commands:$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'

# =============================================================================
# Setup & Installation
# =============================================================================

install: ## Install all dependencies
	@echo "$(BLUE)Installing Python dependencies...$(NC)"
	cd apps/api && pip install -r requirements.txt
	@echo "$(BLUE)Installing Node dependencies...$(NC)"
	cd apps/web && npm install
	@echo "$(GREEN)Installation complete!$(NC)"

dev-setup: ## Setup development environment
	@echo "$(BLUE)Setting up development environment...$(NC)"
	cp .env.example .env
	@echo "$(YELLOW)Please edit .env with your configuration$(NC)"
	@make install
	@echo "$(GREEN)Setup complete! Run 'make docker-up' to start services.$(NC)"

# =============================================================================
# Development Server
# =============================================================================

dev-api: ## Start API development server
	cd apps/api && source .venv/bin/activate && uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

dev-web: ## Start web development server
	cd apps/web && npm run dev

dev: ## Start all development servers (requires docker-compose up first)
	@echo "$(YELLOW)Make sure infrastructure is running: make docker-up$(NC)"
	@make -j2 dev-api dev-web

# =============================================================================
# Docker Operations
# =============================================================================

docker-up: ## Start all Docker services
	@echo "$(BLUE)Starting Docker services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started!$(NC)"
	@echo "  API: http://localhost:8000"
	@echo "  Web: http://localhost:3000"
	@echo "  Grafana: http://localhost:3001"

docker-down: ## Stop all Docker services
	@echo "$(BLUE)Stopping Docker services...$(NC)"
	docker-compose down

docker-logs: ## View Docker logs
	docker-compose logs -f

docker-clean: ## Remove all Docker containers and volumes
	@echo "$(RED)Warning: This will remove all data!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	docker-compose down -v
	docker system prune -f

# =============================================================================
# Database Operations
# =============================================================================

db-migrate: ## Run database migrations
	cd apps/api && alembic upgrade head

db-rollback: ## Rollback last database migration
	cd apps/api && alembic downgrade -1

db-reset: ## Reset database (dangerous!)
	@echo "$(RED)Warning: This will delete all data!$(NC)"
	@read -p "Are you sure? [y/N] " confirm && [ $$confirm = y ] || exit 1
	cd apps/api && alembic downgrade base && alembic upgrade head

db-seed: ## Seed database with initial data
	cd apps/api && python scripts/seed_data.py

db-shell: ## Open database shell
	psql $(DATABASE_URL)

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	cd apps/api && pytest -xvs

test-unit: ## Run unit tests only
	cd apps/api && pytest tests/unit -xvs

test-integration: ## Run integration tests
	cd apps/api && pytest tests/integration -xvs --integration

test-coverage: ## Run tests with coverage report
	cd apps/api && pytest --cov=src --cov-report=term-missing --cov-report=html

test-watch: ## Run tests in watch mode
	cd apps/api && ptw

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run all linters
	@echo "$(BLUE)Running Python linters...$(NC)"
	cd apps/api && flake8 src/ tests/
	@echo "$(BLUE)Running frontend linters...$(NC)"
	cd apps/web && npm run lint

format: ## Format all code
	@echo "$(BLUE)Formatting Python code...$(NC)"
	cd apps/api && black src/ tests/
	cd apps/api && isort src/ tests/
	@echo "$(BLUE)Formatting frontend code...$(NC)"
	cd apps/web && npm run format

format-check: ## Check code formatting without making changes
	cd apps/api && black --check src/ tests/
	cd apps/api && isort --check-only src/ tests/

type-check: ## Run type checking
	@echo "$(BLUE)Running Python type checker...$(NC)"
	cd apps/api && mypy src/ --ignore-missing-imports
	@echo "$(BLUE)Running TypeScript type checker...$(NC)"
	cd apps/web && npm run type-check

security-scan: ## Run security scans
	@echo "$(BLUE)Running security scans...$(NC)"
	cd apps/api && bandit -r src/
	cd apps/api && safety check
	@echo "$(BLUE)Running secrets detection...$(NC)"
	trufflehog git file://.

pre-commit: ## Run pre-commit hooks on all files
	pre-commit run --all-files

# =============================================================================
# Verification
# =============================================================================

verify: ## Run all verification checks (lint, test, type-check, security)
	@echo "$(BLUE)Running full verification suite...$(NC)"
	@make format-check
	@make lint
	@make type-check
	@make test
	@make security-scan
	@echo "$(GREEN)All checks passed!$(NC)"

# =============================================================================
# Build & Deploy
# =============================================================================

build: ## Build production Docker images
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml build

build-api: ## Build API Docker image
	docker build -t yufeed-api:latest -f apps/api/Dockerfile apps/api

build-web: ## Build web Docker image
	docker build -t yufeed-web:latest -f apps/web/Dockerfile apps/web

push: ## Push Docker images to registry
	docker push yufeed-api:latest
	docker push yufeed-web:latest

# =============================================================================
# Documentation
# =============================================================================

docs-serve: ## Serve documentation locally
	cd docs && mkdocs serve

docs-build: ## Build documentation
	cd docs && mkdocs build

# =============================================================================
# Utilities
# =============================================================================

clean: ## Clean build artifacts and cache files
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".coverage" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	rm -f apps/api/.coverage apps/api/coverage.xml
	@echo "$(GREEN)Cleanup complete!$(NC)"

api-shell: ## Open API shell (Python)
	cd apps/api && source .venv/bin/activate && python

api-logs: ## View API logs
	docker-compose logs -f api

generate-client: ## Generate API client from OpenAPI spec
	cd apps/web && npm run generate-api-client

# =============================================================================
# CI/CD Helpers
# =============================================================================

ci-test: ## Run tests in CI mode
	cd apps/api && pytest -xvs --cov=src --cov-report=xml --cov-report=term

ci-lint: ## Run linters in CI mode
	cd apps/api && flake8 src/ tests/ --format=json --output-file=lint-report.json

ci-security: ## Run security scans in CI mode
	cd apps/api && bandit -r src/ -f json -o security-report.json
