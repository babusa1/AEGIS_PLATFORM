# AEGIS Documentation Index

**Last Updated**: February 6, 2026  
**Purpose**: Central navigation for all AEGIS documentation

---

## 📚 DOCUMENTATION STRUCTURE

### Tier 1: Core Documents (Start Here)

1. **[00_PLATFORM_OVERVIEW_VISION.md](./00_PLATFORM_OVERVIEW_VISION.md)** ⭐
   - Platform vision and executive summary
   - Architecture overview
   - Key differentiators
   - Business impact

2. **[01_ARCHITECTURE.md](./MASTER_PLAN.md#architecture)** (See MASTER_PLAN.md)
   - Detailed technical architecture
   - 5 Pillars breakdown
   - Component descriptions

3. **[05_MASTER_PLAN.md](./MASTER_PLAN.md)** ⭐
   - **Single source of truth** for development
   - Current status and completion tracking
   - Roadmap and TODOs

---

### Tier 2: Implementation & Status

4. **[ARCHITECTURE_REVIEW.md](./ARCHITECTURE_REVIEW.md)**
   - Specification vs Implementation comparison
   - Completion analysis (~85%)
   - Gap identification

5. **[COMPLETION_STATUS.md](./COMPLETION_STATUS.md)**
   - Current implementation status
   - Completed vs remaining features

6. **[COWORK_IMPLEMENTATION_PLAN.md](./COWORK_IMPLEMENTATION_PLAN.md)**
   - Detailed implementation plan for Options 1 & 2
   - 17 tasks breakdown
   - Timeline estimates

---

### Tier 3: Feature Documentation

7. **[AGENT_BUILDING_MECHANISM.md](./AGENT_BUILDING_MECHANISM.md)**
   - How to build agents
   - AEGIS vs LangGraph/LangChain/n8n comparison
   - Visual builder guide

8. **[ONCOLIFE_INTEGRATION.md](./ONCOLIFE_INTEGRATION.md)**
   - Oncolife symptom checker integration
   - Phase 1 & 2 enhancements

9. **[PHASE1_PHASE2_COMPLETION.md](./PHASE1_PHASE2_COMPLETION.md)**
   - Oncolife and CKM bridge app completion summary

---

### Tier 4: Technical Specifications

10. **[ORCHESTRATION_ENGINE_SPEC.md](./ORCHESTRATION_ENGINE_SPEC.md)**
    - WorkflowEngine specification
    - LangGraph integration details

11. **[PLATFORM_ANGLE_REVIEW.md](./PLATFORM_ANGLE_REVIEW.md)**
    - Platform-first review
    - Data Moat analysis

12. **[AEGIS_VS_N8N_KOGO.md](./AEGIS_VS_N8N_KOGO.md)**
    - Competitive analysis

---

### Tier 5: Architecture Decision Records (ADRs)

13. **[adr/001-graph-database-selection.md](./adr/001-graph-database-selection.md)**
14. **[adr/002-ontology-standards.md](./adr/002-ontology-standards.md)**
15. **[adr/003-multi-tenancy-strategy.md](./adr/003-multi-tenancy-strategy.md)**
16. **[adr/004-authentication-approach.md](./adr/004-authentication-approach.md)**
17. **[adr/005-llm-provider-strategy.md](./adr/005-llm-provider-strategy.md)**
18. **[adr/006-event-driven-architecture.md](./adr/006-event-driven-architecture.md)**
19. **[adr/007-api-versioning-strategy.md](./adr/007-api-versioning-strategy.md)**

---

### Tier 6: Status & Progress (Reference)

20. **[QUICK_STATUS.md](./QUICK_STATUS.md)** - Quick status snapshot
21. **[STATUS_REVIEW.md](./STATUS_REVIEW.md)** - Detailed status review
22. **[COVERAGE_ANALYSIS.md](./COVERAGE_ANALYSIS.md)** - Code coverage analysis
23. **[IMPLEMENTATION_PROGRESS.md](./IMPLEMENTATION_PROGRESS.md)** - Implementation progress
24. **[ACTION_PLAN.md](./ACTION_PLAN.md)** - Action items
25. **[ROADMAP.md](./ROADMAP.md)** - Product roadmap

---

## 🎯 QUICK START GUIDE

### For Executives/Investors
→ Start with **[00_PLATFORM_OVERVIEW_VISION.md](./00_PLATFORM_OVERVIEW_VISION.md)**

### For Developers
→ Start with **[05_MASTER_PLAN.md](./MASTER_PLAN.md)** → **[AGENT_BUILDING_MECHANISM.md](./AGENT_BUILDING_MECHANISM.md)**

### For Architects
→ Start with **[ARCHITECTURE_REVIEW.md](./ARCHITECTURE_REVIEW.md)** → **[ORCHESTRATION_ENGINE_SPEC.md](./ORCHESTRATION_ENGINE_SPEC.md)**

### For Product Managers
→ Start with **[00_PLATFORM_OVERVIEW_VISION.md](./00_PLATFORM_OVERVIEW_VISION.md)** → **[ROADMAP.md](./ROADMAP.md)**

---

## 📋 DOCUMENTATION PRINCIPLES

1. **Single Source of Truth**: `MASTER_PLAN.md` is the canonical status document
2. **Structured Hierarchy**: Tier 1 (Core) → Tier 2 (Implementation) → Tier 3+ (Reference)
3. **No Duplication**: Each concept documented once, referenced elsewhere
4. **Living Documents**: Updated as platform evolves
5. **Clear Navigation**: This index provides clear paths to information

---

## 🔄 DOCUMENTATION MAINTENANCE

**When to Update**:
- New feature completed → Update `MASTER_PLAN.md`
- Architecture change → Update `ARCHITECTURE_REVIEW.md` + create ADR if major
- New document created → Add to this index
- Document deprecated → Mark as deprecated, don't delete

**Document Owners**:
- Platform Overview: Product Team
- Architecture: Engineering Team
- Master Plan: Engineering Lead
- ADRs: Architecture Team

---

**Last Updated**: February 6, 2026
