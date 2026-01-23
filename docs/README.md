# AEGIS Documentation

## Overview

AEGIS (Agentic Engine for Graph-Integrated Systems) is the healthcare data platform that unifies clinical, financial, and operational data into a single knowledge graph, powered by AI agents.

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
