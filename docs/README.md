# AEGIS Documentation

## Overview

AEGIS (Agentic Engine for Graph-Integrated Systems) is the healthcare data platform that unifies clinical, financial, and operational data into a single knowledge graph, powered by AI agents.

## 📚 Documentation Structure

### 🎯 Master Documents (Read First)
- **[`MASTER_PLAN.md`](./MASTER_PLAN.md)** ← **START HERE** - Single source of truth, current status, next steps
- [`PLATFORM_OVERVIEW.md`](./PLATFORM_OVERVIEW.md) - One-page platform architecture overview
- [`LOCAL_TESTING.md`](./LOCAL_TESTING.md) - Step-by-step local testing guide

### 📊 Status & Planning
- [`COVERAGE_ANALYSIS.md`](./COVERAGE_ANALYSIS.md) - Detailed blueprint coverage analysis
- [`PLATFORM_ANGLE_REVIEW.md`](./PLATFORM_ANGLE_REVIEW.md) - Platform-first review (Data Moat → Agents)
- [`STATUS_REVIEW.md`](./STATUS_REVIEW.md) - Phase-by-phase implementation status
- [`ACTION_PLAN.md`](./ACTION_PLAN.md) - Week-by-week action plan
- [`QUICK_STATUS.md`](./QUICK_STATUS.md) - Quick reference checklist

### 🏗️ Architecture & Vision
- [`PLATFORM_VISION.md`](./PLATFORM_VISION.md) - Product vision and roadmap
- [`ORCHESTRATION_ENGINE_SPEC.md`](./ORCHESTRATION_ENGINE_SPEC.md) - Technical specification
- [`ROADMAP.md`](./ROADMAP.md) - Long-term roadmap
- [`AEGIS_VS_N8N_KOGO.md`](./AEGIS_VS_N8N_KOGO.md) - Competitor comparison

## Documentation Structure

```
docs/
├── README.md                    # This file
├── architecture/
│   └── README.md               # System architecture overview
├── adr/                        # Architecture Decision Records
│   ├── 001-graph-database-selection.md
│   ├── 002-ontology-standards.md
│   ├── 003-multi-tenancy-strategy.md
│   ├── 004-authentication-approach.md
│   ├── 005-llm-provider-strategy.md
│   ├── 006-event-driven-architecture.md
│   └── 007-api-versioning-strategy.md
├── ontology/                   # Data model documentation
│   └── README.md
└── api/                        # API documentation
    └── openapi-spec.yaml
```

## Quick Links

- [Architecture Overview](architecture/README.md)
- [API Documentation](http://localhost:8001/docs) (when running)
- [ADRs](adr/)

## Getting Started

### Prerequisites
- Python 3.11+
- Docker and Docker Compose
- 8GB RAM minimum

### Quick Start

```bash
# Install dependencies
make install

# Start demo (for investors/demos)
make demo

# Start development environment
make dev

# Run tests
make test
```

### Demo Credentials
- Email: `admin@aegis.health`
- Password: `admin123`

## Architecture Decisions

All major architecture decisions are documented as ADRs (Architecture Decision Records) in the [adr/](adr/) folder:

| ADR | Title | Status |
|-----|-------|--------|
| 001 | Graph Database Selection | Accepted |
| 002 | Ontology Standards | Accepted |
| 003 | Multi-Tenancy Strategy | Accepted |
| 004 | Authentication Approach | Accepted |
| 005 | LLM Provider Strategy | Accepted |
| 006 | Event-Driven Architecture | Accepted |
| 007 | API Versioning Strategy | Accepted |

## Contributing

1. Read the relevant ADRs before making changes
2. Follow the code style (run `make lint` before committing)
3. Add tests for new functionality
4. Update documentation as needed
