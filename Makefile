# AEGIS Platform - Makefile
# ===========================
# Common commands for development, testing, and deployment

.PHONY: help demo dev test lint format clean install docker-up docker-down

# Default target
help:
	@echo "AEGIS Platform - Available Commands"
	@echo "===================================="
	@echo ""
	@echo "Development:"
	@echo "  make install     - Install dependencies"
	@echo "  make demo        - Start demo (API + minimal services)"
	@echo "  make dev         - Start full development stack"
	@echo "  make test        - Run all tests"
	@echo "  make lint        - Run linters (ruff, mypy)"
	@echo "  make format      - Format code (ruff)"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-up   - Start all Docker services"
	@echo "  make docker-down - Stop all Docker services"
	@echo "  make docker-lite - Start minimal services (JanusGraph only)"
	@echo ""
	@echo "Database:"
	@echo "  make seed        - Seed database with demo data"
	@echo "  make reset-db    - Reset all databases"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs        - Generate API documentation"
	@echo ""

# ===========================
# Installation
# ===========================

install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt
	@echo "Done!"

install-dev: install
	@echo "Installing dev dependencies..."
	pip install pytest pytest-asyncio pytest-cov ruff mypy
	@echo "Done!"

# ===========================
# Demo Mode (for investors)
# ===========================

demo: docker-lite
	@echo "Starting AEGIS Demo..."
	@echo "======================"
	@echo ""
	@echo "API will be available at: http://localhost:8001"
	@echo "API Docs: http://localhost:8001/docs"
	@echo ""
	@echo "Demo Credentials:"
	@echo "  Email: admin@aegis.health"
	@echo "  Password: admin123"
	@echo ""
	set PYTHONPATH=src && python -m uvicorn aegis.api.main:app --reload --port 8001

demo-windows:
	@echo "Starting AEGIS Demo (Windows)..."
	powershell -Command "$$env:PYTHONPATH='src'; python -m uvicorn aegis.api.main:app --reload --port 8001"

# ===========================
# Development Mode
# ===========================

dev: docker-up
	@echo "Starting AEGIS Development Server..."
	set PYTHONPATH=src && python -m uvicorn aegis.api.main:app --reload --port 8001

dev-windows:
	@echo "Starting AEGIS Dev Server (Windows)..."
	powershell -Command "$$env:PYTHONPATH='src'; python -m uvicorn aegis.api.main:app --reload --port 8001"

# ===========================
# Testing
# ===========================

test:
	@echo "Running tests..."
	set PYTHONPATH=src && pytest tests/ -v --cov=src/aegis --cov-report=term-missing

test-unit:
	@echo "Running unit tests..."
	set PYTHONPATH=src && pytest tests/unit/ -v

test-integration:
	@echo "Running integration tests..."
	set PYTHONPATH=src && pytest tests/integration/ -v

test-e2e:
	@echo "Running end-to-end tests..."
	set PYTHONPATH=src && pytest tests/e2e/ -v

# ===========================
# Code Quality
# ===========================

lint:
	@echo "Running linters..."
	ruff check src/
	mypy src/aegis --ignore-missing-imports

format:
	@echo "Formatting code..."
	ruff format src/
	ruff check src/ --fix

# ===========================
# Docker
# ===========================

docker-up:
	@echo "Starting all Docker services..."
	docker-compose up -d
	@echo "Waiting for services to be ready..."
	timeout /t 10 /nobreak > nul 2>&1 || sleep 10
	@echo "Services started!"

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-lite:
	@echo "Starting minimal Docker services (JanusGraph only)..."
	docker-compose -f docker-compose.lite.yml up -d
	@echo "Waiting for JanusGraph..."
	timeout /t 15 /nobreak > nul 2>&1 || sleep 15
	@echo "JanusGraph ready!"

docker-logs:
	docker-compose logs -f

docker-clean:
	@echo "Removing all containers and volumes..."
	docker-compose down -v
	docker system prune -f

# ===========================
# Database
# ===========================

seed:
	@echo "Seeding database with demo data..."
	set PYTHONPATH=src && python -m aegis.ingestion.synthetic_data
	@echo "Done!"

reset-db:
	@echo "Resetting databases..."
	docker-compose down -v
	docker-compose up -d
	@echo "Databases reset!"

# ===========================
# Documentation
# ===========================

docs:
	@echo "API docs available at http://localhost:8001/docs when server is running"

docs-serve:
	@echo "Starting documentation server..."
	cd docs && mkdocs serve

# ===========================
# Cleanup
# ===========================

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done!"

# ===========================
# Production
# ===========================

build:
	@echo "Building Docker image..."
	docker build -t aegis-api:latest .

deploy-staging:
	@echo "Deploying to staging..."
	# Add deployment commands here

deploy-production:
	@echo "Deploying to production..."
	# Add deployment commands here
