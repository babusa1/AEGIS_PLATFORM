# AEGIS Documentation Structure

**Purpose**: Prevent document sprawl through structured organization  
**Last Updated**: February 6, 2026

---

## 📁 DOCUMENTATION HIERARCHY

### Tier 1: Core Documents (Must Read) ⭐

These are the **essential documents** everyone should read:

1. **00_PLATFORM_OVERVIEW_VISION.md** ⭐
   - Platform vision, architecture overview, business impact
   - **Audience**: Everyone (executives, developers, architects)

2. **01_HIGH_LEVEL_DESIGN.md** 📐
   - System architecture, components, interactions
   - **Audience**: Architects, technical leads

3. **02_LOW_LEVEL_DESIGN.md** 📐
   - Detailed module design, APIs, data models
   - **Audience**: Developers, architects

4. **03_FUNCTIONAL_SPECIFICATION.md** 📋
   - Complete feature specifications, use cases
   - **Audience**: Product managers, developers, QA

5. **04_NON_FUNCTIONAL_SPECIFICATION.md** 📋
   - Performance, security, scalability requirements
   - **Audience**: Architects, DevOps, security team

6. **05_PLAN_OF_ACTION.md** 📝 ⭐
   - Single source of truth for status and next steps
   - **Audience**: Everyone (developers, product, executives)

---

### Tier 2: Reference Documents

7. **ARCHITECTURE_REVIEW.md** 🔄 - Spec vs Implementation comparison
8. **AEGIS_VS_N8N_KOGO.md** 📊 - Competitive analysis
9. **AGENT_BUILDING_MECHANISM.md** 📚 - Developer guide
10. **MASTER_PLAN.md** 📚 - Development status
11. **ROADMAP.md** 📚 - Product roadmap

---

### Tier 3: Architecture Decision Records (ADRs)

12-18. **adr/** - Architecture Decision Records (7 ADRs)

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
- ❌ Create documents for temporary status (use 05_PLAN_OF_ACTION.md instead)
- ❌ Create documents without clear purpose

---

## 📝 DOCUMENT TEMPLATES

### For New Features

```markdown
# Feature Name

**Status**: In Progress / Complete  
**Last Updated**: [Date]  
**Related**: [Link to 05_PLAN_OF_ACTION.md section]

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
**Architecture**: `01_HIGH_LEVEL_DESIGN.md`, `02_LOW_LEVEL_DESIGN.md`  
**Features**: `03_FUNCTIONAL_SPECIFICATION.md`  
**Quality**: `04_NON_FUNCTIONAL_SPECIFICATION.md`  
**Status**: `05_PLAN_OF_ACTION.md`  
**Agents**: `AGENT_BUILDING_MECHANISM.md`  
**ADRs**: `adr/` directory

### By Audience

**Executives**: `00_PLATFORM_OVERVIEW_VISION.md`  
**Architects**: `01_HIGH_LEVEL_DESIGN.md`, `02_LOW_LEVEL_DESIGN.md`  
**Developers**: `05_PLAN_OF_ACTION.md`, `AGENT_BUILDING_MECHANISM.md`, `02_LOW_LEVEL_DESIGN.md`  
**Product**: `00_PLATFORM_OVERVIEW_VISION.md`, `03_FUNCTIONAL_SPECIFICATION.md`, `ROADMAP.md`  
**QA**: `03_FUNCTIONAL_SPECIFICATION.md`, `04_NON_FUNCTIONAL_SPECIFICATION.md`

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

---

**Maintained By**: AEGIS Documentation Team  
**Last Updated**: February 6, 2026
