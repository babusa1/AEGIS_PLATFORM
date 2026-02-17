# VeritOS Documentation Index

**Last Updated**: February 6, 2026  
**Purpose**: Central navigation for all VeritOS documentation

---

## 📚 DOCUMENTATION STRUCTURE

### Tier 1: Core Documents (Start Here) ⭐

1. **[00_PLATFORM_OVERVIEW_VISION.md](./00_PLATFORM_OVERVIEW_VISION.md)** ⭐
   - Platform vision and executive summary
   - Architecture overview (4-layer stack)
   - 5 Pillars breakdown
   - Key differentiators
   - Business impact

2. **[01_HIGH_LEVEL_DESIGN.md](./01_HIGH_LEVEL_DESIGN.md)** 📐
   - System Context (C4 Level 1)
   - Container Diagram (C4 Level 2)
   - 5 Pillars Architecture
   - Data Flow Diagrams
   - Integration Architecture
   - Deployment Architecture

3. **[02_LOW_LEVEL_DESIGN.md](./02_LOW_LEVEL_DESIGN.md)** 📐
   - Module Structure
   - API Specifications
   - Data Models (FHIR, Graph Schema)
   - Agent Architecture (Librarian, Guardian, Scribe, Scout)
   - Workflow Engine Design
   - RAG Pipeline Design

4. **[03_FUNCTIONAL_SPECIFICATION.md](./03_FUNCTIONAL_SPECIFICATION.md)** 📋
   - Feature List (by Pillar)
   - Use Cases
   - User Stories
   - API Endpoints
   - Bridge Apps (Oncolife, CKM)
   - Cowork Workflow

5. **[04_NON_FUNCTIONAL_SPECIFICATION.md](./04_NON_FUNCTIONAL_SPECIFICATION.md)** 📋
   - Performance Requirements
   - Security Requirements (HIPAA, PHI)
   - Scalability Requirements
   - Reliability Requirements
   - Compliance Requirements

6. **[05_PLAN_OF_ACTION.md](./05_PLAN_OF_ACTION.md)** 📝 ⭐
   - **Single source of truth** for current status
   - Completed features (all 17 tasks)
   - Known issues & bugs
   - Technical debt
   - Next steps (prioritized)

---

### Tier 2: Reference Documents

7. **[ARCHITECTURE_REVIEW.md](./ARCHITECTURE_REVIEW.md)** 🔄
   - Specification vs Implementation comparison
   - **100% completion status**
   - Feature mapping

8. **[AEGIS_VS_N8N_KOGO.md](./AEGIS_VS_N8N_KOGO.md)** 📊
   - Competitive analysis
   - Feature comparison matrix
   - Detailed comparison

9. **[AGENT_BUILDING_MECHANISM.md](./AGENT_BUILDING_MECHANISM.md)** 📚
   - How to build agents
   - VeritOS vs LangGraph/LangChain/n8n comparison
   - Visual builder guide

10. **[MASTER_PLAN.md](./MASTER_PLAN.md)** 📚
    - Development status by pillar
    - Roadmap and TODOs
    - Architecture details

11. **[ROADMAP.md](./ROADMAP.md)** 📚
    - Product roadmap
    - Feature timeline
    - Strategic direction

---

### Tier 3: Architecture Decision Records (ADRs)

12. **[adr/001-graph-database-selection.md](./adr/001-graph-database-selection.md)**
13. **[adr/002-ontology-standards.md](./adr/002-ontology-standards.md)**
14. **[adr/003-multi-tenancy-strategy.md](./adr/003-multi-tenancy-strategy.md)**
15. **[adr/004-authentication-approach.md](./adr/004-authentication-approach.md)**
16. **[adr/005-llm-provider-strategy.md](./adr/005-llm-provider-strategy.md)**
17. **[adr/006-event-driven-architecture.md](./adr/006-event-driven-architecture.md)**
18. **[adr/007-api-versioning-strategy.md](./adr/007-api-versioning-strategy.md)**

---

## 🎯 QUICK START GUIDE

### For Executives/Investors
→ Start with **[00_PLATFORM_OVERVIEW_VISION.md](./00_PLATFORM_OVERVIEW_VISION.md)**

### For Architects
→ Start with **[01_HIGH_LEVEL_DESIGN.md](./01_HIGH_LEVEL_DESIGN.md)** → **[02_LOW_LEVEL_DESIGN.md](./02_LOW_LEVEL_DESIGN.md)**

### For Developers
→ Start with **[05_PLAN_OF_ACTION.md](./05_PLAN_OF_ACTION.md)** → **[AGENT_BUILDING_MECHANISM.md](./AGENT_BUILDING_MECHANISM.md)** → **[02_LOW_LEVEL_DESIGN.md](./02_LOW_LEVEL_DESIGN.md)**

### For Product Managers
→ Start with **[00_PLATFORM_OVERVIEW_VISION.md](./00_PLATFORM_OVERVIEW_VISION.md)** → **[03_FUNCTIONAL_SPECIFICATION.md](./03_FUNCTIONAL_SPECIFICATION.md)** → **[ROADMAP.md](./ROADMAP.md)**

### For QA/Testers
→ Start with **[03_FUNCTIONAL_SPECIFICATION.md](./03_FUNCTIONAL_SPECIFICATION.md)** → **[04_NON_FUNCTIONAL_SPECIFICATION.md](./04_NON_FUNCTIONAL_SPECIFICATION.md)**

---

## 📋 DOCUMENTATION PRINCIPLES

1. **Single Source of Truth**: `05_PLAN_OF_ACTION.md` is the canonical status document
2. **Structured Hierarchy**: Tier 1 (Core) → Tier 2 (Reference) → Tier 3 (ADRs)
3. **No Duplication**: Each concept documented once, referenced elsewhere
4. **Living Documents**: Updated as platform evolves
5. **Clear Navigation**: This index provides clear paths to information

---

## 🔄 DOCUMENTATION MAINTENANCE

**When to Update**:
- New feature completed → Update `05_PLAN_OF_ACTION.md`
- Architecture change → Update `01_HIGH_LEVEL_DESIGN.md` + create ADR if major
- New document created → Add to this index
- Document deprecated → Mark as deprecated, don't delete

**Document Owners**:
- Platform Overview: Product Team
- Architecture: Engineering Team
- Plan of Action: Engineering Lead
- ADRs: Architecture Team

---

## 📊 DOCUMENT STATUS

| Document | Status | Last Updated | Owner |
|----------|--------|--------------|-------|
| 00_PLATFORM_OVERVIEW_VISION.md | ✅ Current | Feb 6, 2026 | Product |
| 01_HIGH_LEVEL_DESIGN.md | ✅ Current | Feb 6, 2026 | Architecture |
| 02_LOW_LEVEL_DESIGN.md | ✅ Current | Feb 6, 2026 | Engineering |
| 03_FUNCTIONAL_SPECIFICATION.md | ✅ Current | Feb 6, 2026 | Product |
| 04_NON_FUNCTIONAL_SPECIFICATION.md | ✅ Current | Feb 6, 2026 | Engineering |
| 05_PLAN_OF_ACTION.md | ✅ Current | Feb 6, 2026 | Engineering Lead |
| ARCHITECTURE_REVIEW.md | ✅ Current | Feb 6, 2026 | Architecture |
| AEGIS_VS_N8N_KOGO.md | ✅ Current | Feb 6, 2026 | Product |
| AGENT_BUILDING_MECHANISM.md | ✅ Current | Feb 6, 2026 | Engineering |

---

**Last Updated**: February 6, 2026
