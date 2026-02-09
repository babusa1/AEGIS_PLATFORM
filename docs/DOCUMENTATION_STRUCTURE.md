# AEGIS Documentation Structure

**Purpose**: Prevent document sprawl through structured organization  
**Last Updated**: February 6, 2026

---

## 📁 DOCUMENTATION HIERARCHY

### Tier 1: Core Documents (Must Read)

These are the **essential documents** everyone should read:

1. **00_PLATFORM_OVERVIEW_VISION.md** ⭐
   - Platform vision, architecture overview, business impact
   - **Audience**: Everyone (executives, developers, architects)

2. **05_MASTER_PLAN.md** ⭐
   - Single source of truth for development status
   - **Audience**: Developers, product managers

---

### Tier 2: Implementation Guides

3. **ARCHITECTURE_REVIEW.md**
   - Specification vs implementation comparison
   - **Audience**: Architects, technical leads

4. **AGENT_BUILDING_MECHANISM.md**
   - How to build agents
   - **Audience**: Developers building agents

5. **COWORK_IMPLEMENTATION_PLAN.md**
   - Detailed implementation plan
   - **Audience**: Developers implementing features

---

### Tier 3: Feature-Specific

6. **ONCOLIFE_INTEGRATION.md** - Oncolife bridge app
7. **PHASE1_PHASE2_COMPLETION.md** - Feature completion summaries
8. **ORCHESTRATION_ENGINE_SPEC.md** - Technical specifications

---

### Tier 4: Reference Documents

9. **ADRs** (`adr/`) - Architecture Decision Records
10. **Status Documents** - QUICK_STATUS, STATUS_REVIEW, etc.
11. **Competitive Analysis** - AEGIS_VS_N8N_KOGO.md

---

## 🚫 DOCUMENTATION RULES

### DO:
- ✅ Create new documents only when necessary
- ✅ Reference existing documents instead of duplicating
- ✅ Update `README.md` index when adding documents
- ✅ Use clear, descriptive filenames with prefixes (00_, 01_, etc.)
- ✅ Keep documents focused (one document = one topic)

### DON'T:
- ❌ Create duplicate documents
- ❌ Create documents without updating index
- ❌ Create documents for temporary status (use MASTER_PLAN.md instead)
- ❌ Create documents without clear purpose

---

## 📝 DOCUMENT TEMPLATES

### For New Features

```markdown
# Feature Name

**Status**: In Progress / Complete  
**Last Updated**: [Date]  
**Related**: [Link to MASTER_PLAN.md section]

## Overview
[Brief description]

## Implementation
[Details]

## API
[If applicable]

## Examples
[If applicable]
```

### For ADRs

```markdown
# ADR-XXX: [Decision Title]

## Status
Accepted / Proposed / Rejected

## Context
[Why this decision is needed]

## Decision
[What we decided]

## Consequences
[Positive and negative impacts]
```

---

## 🔍 FINDING DOCUMENTS

### By Topic

**Platform Vision**: `00_PLATFORM_OVERVIEW_VISION.md`  
**Architecture**: `ARCHITECTURE_REVIEW.md`, `MASTER_PLAN.md`  
**Agents**: `AGENT_BUILDING_MECHANISM.md`  
**Status**: `MASTER_PLAN.md`, `COMPLETION_STATUS.md`  
**Implementation**: `COWORK_IMPLEMENTATION_PLAN.md`  
**ADRs**: `adr/` directory

### By Audience

**Executives**: `00_PLATFORM_OVERVIEW_VISION.md`  
**Developers**: `MASTER_PLAN.md`, `AGENT_BUILDING_MECHANISM.md`  
**Architects**: `ARCHITECTURE_REVIEW.md`, `adr/`  
**Product**: `00_PLATFORM_OVERVIEW_VISION.md`, `ROADMAP.md`

---

## 📊 DOCUMENT STATUS

| Document | Status | Last Updated | Owner |
|----------|--------|--------------|-------|
| 00_PLATFORM_OVERVIEW_VISION.md | ✅ Current | Feb 6, 2026 | Product |
| MASTER_PLAN.md | ✅ Current | Feb 6, 2026 | Engineering |
| ARCHITECTURE_REVIEW.md | ✅ Current | Feb 6, 2026 | Architecture |
| AGENT_BUILDING_MECHANISM.md | ✅ Current | Feb 6, 2026 | Engineering |
| COWORK_IMPLEMENTATION_PLAN.md | ✅ Current | Feb 6, 2026 | Engineering |

---

**Maintained By**: AEGIS Documentation Team  
**Last Updated**: February 6, 2026
