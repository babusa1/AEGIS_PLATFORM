# AEGIS Platform Architecture

## Overview

AEGIS (Agentic Engine for Graph-Integrated Systems) is a multi-tenant healthcare data platform that provides:

1. **Unified Knowledge Graph** - All healthcare data in one connected graph
2. **AI Agents** - Intelligent automation for RCM, care gaps, and more
3. **Multi-Tenant SaaS** - Secure, isolated data for each customer

## System Context (C4 Level 1)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AEGIS Platform                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐              │
│   │   Hospital  │     │   Payer     │     │  Analytics  │              │
│   │   Users     │     │   Portals   │     │   Team      │              │
│   └──────┬──────┘     └──────┬──────┘     └──────┬──────┘              │
│          │                   │                   │                      │
│          ▼                   ▼                   ▼                      │
│   ┌─────────────────────────────────────────────────────┐              │
│   │                    AEGIS API                         │              │
│   │  • Patient 360  • RCM  • Care Gaps  • Agents        │              │
│   └─────────────────────────┬───────────────────────────┘              │
│                             │                                           │
│   ┌─────────────────────────▼───────────────────────────┐              │
│   │               Knowledge Graph (Spine)                │              │
│   │  Patients • Encounters • Claims • Denials • Gaps    │              │
│   └─────────────────────────────────────────────────────┘              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┐
        ▼                           ▼                           ▼
┌───────────────┐         ┌───────────────┐         ┌───────────────┐
│     EHR       │         │    Payer      │         │    Claims     │
│ (Epic/Cerner) │         │   Systems     │         │  Clearinghouse│
└───────────────┘         └───────────────┘         └───────────────┘
```

## Container Diagram (C4 Level 2)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           AEGIS Platform                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      API Gateway Layer                           │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐            │   │
│  │  │  Auth   │  │ Patient │  │   RCM   │  │ Quality │            │   │
│  │  │ Service │  │   API   │  │   API   │  │   API   │            │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘            │   │
│  └─────────────────────────────┬───────────────────────────────────┘   │
│                                │                                        │
│  ┌─────────────────────────────▼───────────────────────────────────┐   │
│  │                     Platform Services                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │  Tenant  │  │  Agent   │  │ Ingestion│  │ Webhook  │        │   │
│  │  │ Service  │  │ Workers  │  │ Workers  │  │ Receiver │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│  └─────────────────────────────┬───────────────────────────────────┘   │
│                                │                                        │
│  ┌─────────────────────────────▼───────────────────────────────────┐   │
│  │                       Data Layer                                 │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │   │
│  │  │  Graph   │  │  Vector  │  │ Postgres │  │  Redis   │        │   │
│  │  │   DB     │  │   DB     │  │   DB     │  │  Cache   │        │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Knowledge Graph (The Spine)
- **Technology**: JanusGraph (abstracted for Neptune/Neo4j)
- **Purpose**: Store all healthcare entities and relationships
- **Key Entities**: Patient, Encounter, Claim, Denial, CareGap

### 2. Agent Framework
- **Technology**: LangGraph + AWS Bedrock
- **Purpose**: AI-powered automation
- **Key Agents**: Unified View, Denial Appeal, Care Gap Closure

### 3. Multi-Tenancy
- **Strategy**: Schema-per-tenant (PostgreSQL) + Namespace-per-tenant (Graph)
- **Isolation**: Complete data isolation between tenants

### 4. Authentication
- **Technology**: OIDC (Cognito/Auth0) + PBAC
- **Features**: SSO, MFA, Purpose-Based Access Control

## Use Cases

### Patient 360
- Unified view of patient across all data sources
- Timeline visualization
- Cross-system data aggregation

### RCM / Denial Management
- Automated denial detection
- AI-generated appeals (Writer + Auditor pattern)
- Payer portal integration

### Care Gaps
- Quality measure calculation (HEDIS, CMS)
- Gap identification and prioritization
- Intervention tracking

## Documentation Index

- [ADR-001: Graph Database Selection](../adr/001-graph-database-selection.md)
- [ADR-002: Ontology Standards](../adr/002-ontology-standards.md)
- [ADR-003: Multi-Tenancy Strategy](../adr/003-multi-tenancy-strategy.md)
- [ADR-004: Authentication Approach](../adr/004-authentication-approach.md)
- [ADR-005: LLM Provider Strategy](../adr/005-llm-provider-strategy.md)
- [ADR-006: Event-Driven Architecture](../adr/006-event-driven-architecture.md)
- [ADR-007: API Versioning Strategy](../adr/007-api-versioning-strategy.md)
