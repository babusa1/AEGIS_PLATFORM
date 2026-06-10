# Testing & CI/CD Guide

**Version 2.1 | Updated January 2026**

**Developer:** NAVEEN BABU S A

This guide covers the test infrastructure and CI/CD workflows for OncoLife Monolith.

---

## 📁 Files Created

```
OncoLife_Monolith/
├── .github/
│   └── workflows/
│       ├── ci.yml                    # CI workflow (lint, test, build)
│       └── deploy.yml                # CD workflow (deploy to AWS)
├── apps/
│   ├── patient-platform/
│   │   └── patient-api/
│   │       ├── pytest.ini            # Pytest configuration
│   │       ├── alembic.ini           # Alembic configuration
│   │       ├── alembic/
│   │       │   ├── env.py            # Migration environment
│   │       │   ├── script.py.mako    # Migration template
│   │       │   └── versions/
│   │       │       └── 20260106_0001_initial_schema.py
│   │       └── tests/
│   │           ├── __init__.py
│   │           ├── conftest.py       # Shared fixtures
│   │           ├── test_health.py
│   │           ├── test_chat.py
│   │           ├── test_diary.py
│   │           └── test_questions.py
│   └── doctor-platform/
│       └── doctor-api/
│           ├── pytest.ini
│           ├── alembic.ini
│           ├── alembic/
│           │   ├── env.py
│           │   ├── script.py.mako
│           │   └── versions/
│           │       └── 20260106_0001_initial_schema.py
│           └── tests/
│               ├── __init__.py
│               ├── conftest.py
│               ├── test_health.py
│               ├── test_dashboard.py
│               ├── test_patients.py
│               └── test_staff.py
```

---

## 🧪 Running Tests

### Patient API

```bash
cd apps/patient-platform/patient-api

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run only unit tests (fast)
pytest -m unit

# Run specific test file
pytest tests/test_questions.py

# Run with verbose output
pytest -v --tb=long
```

### Doctor API

```bash
cd apps/doctor-platform/doctor-api

# Install test dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific marker
pytest -m "not slow"
```

### Test Markers

| Marker | Description |
|--------|-------------|
| `@pytest.mark.unit` | Fast unit tests, no external dependencies |
| `@pytest.mark.integration` | Tests requiring database |
| `@pytest.mark.slow` | Slow tests (skip with `-m "not slow"`) |
| `@pytest.mark.auth` | Authentication tests |

---

## 🗄️ Database Migrations (Alembic)

### Patient API

```bash
cd apps/patient-platform/patient-api

# Check current migration version
alembic current

# View migration history
alembic history

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific version
alembic downgrade 0001

# Generate new migration (after model changes)
alembic revision --autogenerate -m "add_new_column"

# Generate SQL script without applying
alembic upgrade head --sql > migration.sql
```

### Doctor API

```bash
cd apps/doctor-platform/doctor-api

# Same commands as above
alembic upgrade head
alembic downgrade -1
alembic revision --autogenerate -m "description"
```

### Environment Variables for Migrations

Set these before running migrations:

```bash
# Patient API
export PATIENT_DB_HOST=localhost
export PATIENT_DB_PORT=5432
export PATIENT_DB_USER=oncolife_admin
export PATIENT_DB_PASSWORD=your_password
export PATIENT_DB_NAME=oncolife_patient

# Doctor API
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
export POSTGRES_USER=oncolife_admin
export POSTGRES_PASSWORD=your_password
export POSTGRES_DOCTOR_DB=oncolife_doctor
```

Or use a `DATABASE_URL`:

```bash
export DATABASE_URL=postgresql://user:pass@host:5432/database
```

---

## 🔄 CI/CD Workflows

### CI Workflow (`.github/workflows/ci.yml`)

**Triggers:** Pull requests and pushes to `main`/`develop`

**Jobs:**
1. **Lint** - Runs ruff, black, ESLint
2. **Test Patient API** - Runs pytest with coverage
3. **Test Doctor API** - Runs pytest with coverage
4. **Build** - Builds all Docker images (validates Dockerfiles)

### CD Workflow (`.github/workflows/deploy.yml`)

**Triggers:** Merge to `main` or manual dispatch

**Jobs:**
1. **Build & Push** - Builds images and pushes to ECR
2. **Migrate** - Runs database migrations
3. **Deploy** - Updates ECS services

### Required GitHub Secrets

| Secret | Description |
|--------|-------------|
| `AWS_ACCOUNT_ID` | AWS account ID for ECR |
| `AWS_ACCESS_KEY_ID` | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key |
| `PATIENT_DATABASE_URL` | Patient DB connection string |
| `DOCTOR_DATABASE_URL` | Doctor DB connection string |
| `PATIENT_API_URL` | Production patient API URL |
| `PATIENT_WS_URL` | Production WebSocket URL |
| `DOCTOR_API_URL` | Production doctor API URL |

### Setting Up Secrets

1. Go to GitHub Repository → Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret listed above

---

## 🚀 Manual Deployment

If you need to deploy manually (without CI/CD):

```powershell
# 1. Build images
docker build -t oncolife-patient-api apps/patient-platform/patient-api
docker build -t oncolife-doctor-api apps/doctor-platform/doctor-api
docker build -t oncolife-patient-web apps/patient-platform/patient-web
docker build -t oncolife-doctor-web apps/doctor-platform/doctor-web

# 2. Login to ECR
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com

# 3. Tag and push
docker tag oncolife-patient-api:latest $ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-patient-api:latest
docker push $ACCOUNT_ID.dkr.ecr.us-west-2.amazonaws.com/oncolife-patient-api:latest

# 4. Run migrations
cd apps/patient-platform/patient-api
alembic upgrade head

cd apps/doctor-platform/doctor-api
alembic upgrade head

# 5. Update ECS services
aws ecs update-service --cluster oncolife-production --service patient-api-service --force-new-deployment
aws ecs update-service --cluster oncolife-production --service doctor-api-service --force-new-deployment
```

---

## 📊 Test Coverage

View coverage reports after running tests:

```bash
# HTML report
open coverage_html/index.html

# Terminal report
pytest --cov=src --cov-report=term-missing
```

Target coverage: **60%** minimum (configurable in `pytest.ini`)

---

## 🔧 Configuration Files

### pytest.ini

Key settings:
- `testpaths = tests` - Test directory
- `asyncio_mode = auto` - Async test support
- `--cov-fail-under=60` - Minimum coverage threshold

### alembic.ini

Key settings:
- `script_location = alembic` - Migration scripts location
- `prepend_sys_path = src` - Add src to path for model imports

---

## 📝 Writing New Tests

### Example Test Structure

```python
"""
Feature Endpoint Tests
======================
"""

import pytest
from fastapi.testclient import TestClient


class TestFeatureEndpoints:
    """Tests for feature endpoints."""

    @pytest.mark.unit
    def test_list_items(self, client: TestClient):
        """Should return list of items."""
        response = client.get("/api/v1/feature")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    @pytest.mark.unit
    def test_create_item(self, client: TestClient):
        """Should create a new item."""
        response = client.post("/api/v1/feature", json={
            "name": "Test Item"
        })
        
        assert response.status_code == 201
```

### Using Fixtures

```python
def test_with_sample_data(self, client: TestClient, sample_question: dict):
    """Test using fixture data."""
    response = client.post("/api/v1/questions", json=sample_question)
    assert response.status_code == 201
```

---

## 🐛 Troubleshooting

### Tests fail with import errors

```bash
# Ensure PYTHONPATH includes src
export PYTHONPATH=src
pytest
```

### Alembic can't find models

```bash
# Ensure you're in the correct directory
cd apps/patient-platform/patient-api
alembic upgrade head
```

### CI workflow fails

1. Check the workflow logs in GitHub Actions
2. Ensure all secrets are configured
3. Verify Docker builds work locally

---

*Last Updated: January 2026*

