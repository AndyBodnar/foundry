# =============================================================================
# Foundry MLOps Platform - Makefile
# =============================================================================
# Common commands for development, testing, and deployment.
# =============================================================================

.PHONY: help install dev dev-up dev-down dev-logs dev-reset test lint format \
        build push deploy migrate seed clean docs security

# Default target
.DEFAULT_GOAL := help

# =============================================================================
# Variables
# =============================================================================

PYTHON := python3
PIP := pip3
DOCKER_COMPOSE := docker-compose
DOCKER := docker
KUBECTL := kubectl
TERRAFORM := terraform
ALEMBIC := alembic

# Docker image settings
REGISTRY := ghcr.io/foundry
VERSION := $(shell git describe --tags --always --dirty 2>/dev/null || echo "dev")
COMMIT := $(shell git rev-parse --short HEAD 2>/dev/null || echo "unknown")

# Kubernetes namespace
K8S_NAMESPACE := foundry

# =============================================================================
# Help
# =============================================================================

help: ## Show this help message
	@echo "Foundry MLOps Platform - Available Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "\033[36m"} /^[a-zA-Z_-]+:.*?##/ { printf "  %-20s \033[0m%s\n", $$1, $$2 }' $(MAKEFILE_LIST)

# =============================================================================
# Installation & Setup
# =============================================================================

install: ## Install all dependencies
	@echo "Installing backend dependencies..."
	cd backend && $(PIP) install -e ".[dev]"
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installing CLI dependencies..."
	cd cli && $(PIP) install -e ".[dev]"

setup: ## First-time setup (creates .env, installs deps)
	@if [ ! -f .env ]; then cp .env.example .env; fi
	$(MAKE) install

# =============================================================================
# Development Environment
# =============================================================================

dev: dev-up ## Start development environment (alias for dev-up)

dev-up: ## Start all development services
	@echo "Starting development environment..."
	docker compose up --build -d
	@echo ""
	@echo "Foundry is running!"
	@echo "  Dashboard: http://localhost:3000"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo "  Grafana:   http://localhost:3001"

dev-down: ## Stop all development services
	@echo "Stopping development environment..."
	$(DOCKER_COMPOSE) down

dev-logs: ## View logs from all services
	$(DOCKER_COMPOSE) logs -f

dev-reset: ## Reset development environment (removes all data)
	@echo "Resetting development environment..."
	docker compose down -v
	docker compose up --build -d

dev-status: ## Check status of development services
	$(DOCKER_COMPOSE) ps

# =============================================================================
# Database
# =============================================================================

migrate: ## Run database migrations
	@echo "Running database migrations..."
	cd backend && $(ALEMBIC) upgrade head

migrate-down: ## Rollback last migration
	@echo "Rolling back last migration..."
	cd backend && $(ALEMBIC) downgrade -1

migrate-create: ## Create a new migration (usage: make migrate-create MSG="description")
	@if [ -z "$(MSG)" ]; then echo "Usage: make migrate-create MSG=\"description\""; exit 1; fi
	cd backend && $(ALEMBIC) revision --autogenerate -m "$(MSG)"

seed: ## Seed database with sample data
	@echo "Seeding database..."
	$(PYTHON) scripts/seed-data.py

db-shell: ## Open PostgreSQL shell
	$(DOCKER) exec -it foundry-postgres psql -U foundry -d foundry

redis-cli: ## Open Redis CLI
	$(DOCKER) exec -it foundry-redis redis-cli -a foundry_redis_password

# =============================================================================
# Testing
# =============================================================================

test: ## Run all tests
	@echo "Running backend tests..."
	cd backend && pytest tests/ -v --cov=src --cov-report=term-missing
	@echo "Running frontend tests..."
	cd frontend && npm test

test-unit: ## Run unit tests only
	cd backend && pytest tests/unit -v

test-integration: ## Run integration tests
	cd backend && pytest tests/integration -v

test-e2e: ## Run end-to-end tests
	cd backend && pytest tests/e2e -v

test-load: ## Run load tests
	cd backend && locust -f tests/load/locustfile.py --headless -u 100 -r 10 -t 5m

test-coverage: ## Generate test coverage report
	cd backend && pytest tests/ --cov=src --cov-report=html
	@echo "Coverage report generated in backend/htmlcov/index.html"

# =============================================================================
# Code Quality
# =============================================================================

lint: ## Run linters
	@echo "Linting backend..."
	cd backend && ruff check src tests
	cd backend && mypy src
	@echo "Linting frontend..."
	cd frontend && npm run lint

format: ## Format code
	@echo "Formatting backend..."
	cd backend && ruff format src tests
	cd backend && ruff check --fix src tests
	@echo "Formatting frontend..."
	cd frontend && npm run format

check: lint test ## Run all checks (lint + test)

# =============================================================================
# Security
# =============================================================================

security: ## Run security scans
	@echo "Running backend security scan..."
	cd backend && bandit -r src
	cd backend && safety check
	@echo "Running frontend security scan..."
	cd frontend && npm audit
	@echo "Running container security scan..."
	$(DOCKER) scan $(REGISTRY)/api:$(VERSION) || true

# =============================================================================
# Building
# =============================================================================

build: build-backend build-frontend build-worker ## Build all Docker images

build-backend: ## Build backend API image
	@echo "Building API image..."
	$(DOCKER) build -t $(REGISTRY)/api:$(VERSION) \
		--build-arg VERSION=$(VERSION) \
		--build-arg COMMIT=$(COMMIT) \
		-f backend/Dockerfile backend

build-frontend: ## Build frontend image
	@echo "Building frontend image..."
	$(DOCKER) build -t $(REGISTRY)/frontend:$(VERSION) \
		--build-arg VERSION=$(VERSION) \
		-f frontend/Dockerfile frontend

build-worker: ## Build worker image
	@echo "Building worker image..."
	$(DOCKER) build -t $(REGISTRY)/worker:$(VERSION) \
		--build-arg VERSION=$(VERSION) \
		--build-arg COMMIT=$(COMMIT) \
		-f backend/Dockerfile.worker backend

# =============================================================================
# Docker Registry
# =============================================================================

push: ## Push Docker images to registry
	@echo "Pushing images..."
	$(DOCKER) push $(REGISTRY)/api:$(VERSION)
	$(DOCKER) push $(REGISTRY)/frontend:$(VERSION)
	$(DOCKER) push $(REGISTRY)/worker:$(VERSION)

pull: ## Pull Docker images from registry
	$(DOCKER) pull $(REGISTRY)/api:$(VERSION)
	$(DOCKER) pull $(REGISTRY)/frontend:$(VERSION)
	$(DOCKER) pull $(REGISTRY)/worker:$(VERSION)

# =============================================================================
# Kubernetes Deployment
# =============================================================================

deploy-dev: ## Deploy to development cluster
	@echo "Deploying to development..."
	$(KUBECTL) apply -k infrastructure/kubernetes/overlays/dev

deploy-staging: ## Deploy to staging cluster
	@echo "Deploying to staging..."
	$(KUBECTL) apply -k infrastructure/kubernetes/overlays/staging

deploy-prod: ## Deploy to production cluster
	@echo "Deploying to production..."
	$(KUBECTL) apply -k infrastructure/kubernetes/overlays/production

rollback: ## Rollback to previous deployment
	@echo "Rolling back deployment..."
	$(KUBECTL) rollout undo deployment/foundry-api -n $(K8S_NAMESPACE)
	$(KUBECTL) rollout undo deployment/foundry-worker -n $(K8S_NAMESPACE)

k8s-status: ## Check Kubernetes deployment status
	$(KUBECTL) get pods -n $(K8S_NAMESPACE)
	$(KUBECTL) get svc -n $(K8S_NAMESPACE)

k8s-logs: ## View Kubernetes logs
	$(KUBECTL) logs -f -l app.kubernetes.io/part-of=foundry-mlops -n $(K8S_NAMESPACE)

# =============================================================================
# Terraform
# =============================================================================

tf-init: ## Initialize Terraform
	cd infrastructure/terraform/environments/$(ENV) && $(TERRAFORM) init

tf-plan: ## Plan Terraform changes
	cd infrastructure/terraform/environments/$(ENV) && $(TERRAFORM) plan -out=tfplan

tf-apply: ## Apply Terraform changes
	cd infrastructure/terraform/environments/$(ENV) && $(TERRAFORM) apply tfplan

tf-destroy: ## Destroy Terraform resources (use with caution!)
	@echo "WARNING: This will destroy all infrastructure!"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	cd infrastructure/terraform/environments/$(ENV) && $(TERRAFORM) destroy

# =============================================================================
# Documentation
# =============================================================================

docs: ## Generate documentation
	@echo "Generating API documentation..."
	cd backend && $(PYTHON) -c "from foundry.main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/api/openapi.json
	@echo "Documentation generated in docs/"

docs-serve: ## Serve documentation locally
	cd docs && mkdocs serve

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean build artifacts
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov 2>/dev/null || true
	rm -rf frontend/.next 2>/dev/null || true

clean-docker: ## Remove Docker containers and volumes
	$(DOCKER_COMPOSE) down -v --rmi local
	$(DOCKER) system prune -f

clean-all: clean clean-docker ## Clean everything

# =============================================================================
# Monitoring
# =============================================================================

grafana: ## Open Grafana dashboard
	@echo "Opening Grafana at http://localhost:3001"
	@open http://localhost:3001 2>/dev/null || xdg-open http://localhost:3001 2>/dev/null || echo "Open http://localhost:3001 in your browser"

prometheus: ## Open Prometheus dashboard
	@echo "Opening Prometheus at http://localhost:9090"
	@open http://localhost:9090 2>/dev/null || xdg-open http://localhost:9090 2>/dev/null || echo "Open http://localhost:9090 in your browser"

jaeger: ## Open Jaeger UI
	@echo "Opening Jaeger at http://localhost:16686"
	@open http://localhost:16686 2>/dev/null || xdg-open http://localhost:16686 2>/dev/null || echo "Open http://localhost:16686 in your browser"

# =============================================================================
# Quick Access
# =============================================================================

api-logs: ## View API logs
	$(DOCKER) logs -f foundry-api

worker-logs: ## View worker logs
	$(DOCKER) logs -f foundry-worker

kafka-ui: ## Open Kafka UI
	@open http://localhost:8090 2>/dev/null || xdg-open http://localhost:8090 2>/dev/null || echo "Open http://localhost:8090 in your browser"

minio-ui: ## Open MinIO Console
	@open http://localhost:9001 2>/dev/null || xdg-open http://localhost:9001 2>/dev/null || echo "Open http://localhost:9001 in your browser"
