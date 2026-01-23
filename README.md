# AEGIS: The Agentic Operating System for Healthcare

> **From Data Rich to Action Ready**

AEGIS is a healthcare data platform that transforms passive hospital data into autonomous action through AI agents and a unified knowledge graph.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        AEGIS Platform                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  API Layer   │  │   Agents     │  │  Execution   │          │
│  │  (GraphQL/   │  │  (LangGraph  │  │  (EHR/Payer  │          │
│  │   REST)      │  │   + Bedrock) │  │   Writeback) │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                 │                 │                   │
│         └─────────────────┼─────────────────┘                   │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────┐           │
│  │              Knowledge Graph (Neptune)           │           │
│  │         + Vector Store (OpenSearch)              │           │
│  └──────────────────────────────────────────────────┘           │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────┐           │
│  │           Data Ingestion (FHIR/HL7/EDI)          │           │
│  └──────────────────────────────────────────────────┘           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- AWS Account (for Bedrock - optional for local dev)

### 1. Clone and Setup

```bash
cd aegis
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start Local Infrastructure

```bash
docker-compose up -d
```

This starts:
- **JanusGraph** (port 8182) - Graph database (Neptune-compatible)
- **OpenSearch** (port 9200) - Vector database & search
- **Kafka** (port 9092) - Event streaming
- **Redis** (port 6379) - Caching

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Run the API Server

```bash
uvicorn src.aegis.api.main:app --reload --port 8000
```

### 5. Access the API

- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Project Structure

```
aegis/
├── src/aegis/
│   ├── api/              # FastAPI application
│   ├── agents/           # LangGraph agents
│   ├── ingestion/        # FHIR/HL7/EDI parsers
│   ├── graph/            # Graph database operations
│   ├── vector/           # Vector store operations
│   ├── platform/         # Multi-tenant, auth, audit
│   └── bedrock/          # LLM integration
├── ontology/             # OWL ontology definitions
├── synthetic_data/       # Data generators
├── tests/                # Test suite
└── docker-compose.yml    # Local dev environment
```

## Key Features

### 1. Knowledge Graph (The Spine)
- Unified ontology for clinical, financial, and operational data
- Relationships preserved (not just flat tables)
- Real-time updates via event streaming

### 2. AI Agents (The Brain)
- **Unified View Agent**: 360° patient view
- **Action Agent**: Denial appeals, discharge prep
- **Insight Agent**: Pattern detection, anomalies

### 3. Closed-Loop Execution (The Hands)
- Draft actions with AI
- Human approval workflow
- Execute to EHR/payer systems

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Code Quality

```bash
black src/ tests/
ruff check src/ tests/
mypy src/
```

### Local LLM Options

1. **Mock** (default): Simulated responses for fast development
2. **AWS Bedrock**: Cloud-based LLM (Claude)
3. **Ollama**: Local open-source models

Set `LLM_PROVIDER` in `.env` to switch.

## License

Proprietary - All Rights Reserved
