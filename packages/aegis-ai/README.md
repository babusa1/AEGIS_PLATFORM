# AEGIS AI

AI/ML infrastructure for healthcare agents.

## Features

- **LLM Gateway**: Multi-provider support (Bedrock, OpenAI, Azure)
- **Agent Framework**: ReAct-style agents with tool use
- **Tool Registry**: Healthcare-specific tools for graph queries
- **Human-in-the-Loop**: Approval workflows for sensitive actions

## Installation

```bash
pip install aegis-ai

# With AWS Bedrock
pip install aegis-ai[bedrock]

# With OpenAI
pip install aegis-ai[openai]

# All providers
pip install aegis-ai[all]
```

## Quick Start

### LLM Gateway

```python
from aegis_ai import LLMGateway

# Create gateway with automatic failover
gateway = LLMGateway(
    primary_provider="bedrock",
    fallback_providers=["openai"]
)
await gateway.initialize()

# Simple chat
response = await gateway.chat(
    prompt="Summarize this patient's condition",
    system="You are a helpful healthcare assistant."
)

# With tools
response = await gateway.complete(
    messages=[Message.user("Get patient P123's lab results")],
    tools=tool_registry.get_schemas(["get_lab_results"])
)
```

### Agents

```python
from aegis_ai.agents import get_agent

# Get pre-configured agent
agent = get_agent("patient_360")

# Run agent
state = await agent.run(
    user_input="Give me a summary of patient P123",
    context={"patient_id": "P123", "tenant_id": "hospital-a"}
)

# Get response
print(agent.get_response(state))
```

### Available Agents

| Agent | Description |
|-------|-------------|
| `patient_360` | Unified patient view synthesis |
| `care_gap` | Care gap identification |
| `denial_writer` | Denial appeal drafting |
| `denial_auditor` | Appeal quality review |

### Tool Registry

```python
from aegis_ai import get_tool_registry, tool

registry = get_tool_registry()

# Register custom tool
@tool(name="my_tool", category="custom", phi_access=True)
async def my_tool(patient_id: str) -> dict:
    """My custom tool."""
    return {"data": "..."}

# Get tool schemas for LLM
schemas = registry.get_schemas(["get_patient_summary", "my_tool"])
```

### Human-in-the-Loop

```python
from aegis_ai.hitl import get_approval_workflow

workflow = get_approval_workflow()

# Request approval
request = await workflow.request_approval(
    action_type="draft_appeal",
    action_details={"denial_id": "D123"},
    risk_level="high"
)

# Wait for approval (async)
approved = await workflow.wait_for_approval(request, timeout_seconds=300)

# Or resolve manually
await workflow.resolve(
    request_id=request.id,
    approved=True,
    approver_id="user-456",
    notes="Looks good"
)
```

## Cost Tracking

```python
# Get usage stats
stats = gateway.get_usage_stats()
print(f"Total cost: ${stats['total_cost_usd']}")
print(f"Total tokens: {stats['total_tokens']}")
```

## License

MIT
