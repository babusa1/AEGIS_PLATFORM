import pytest

from aegis.agents.workflows import HealthcareWorkflow
import aegis.bedrock.client as llm_client_mod


@pytest.mark.asyncio
async def test_healthcare_workflow_patient_intent():
    # Reset LLM singleton to ensure MockLLMClient is used
    llm_client_mod._llm_client = None

    wf = HealthcareWorkflow(pool=None)
    result = await wf.run("Show me patient-123 summary")

    assert result.get("success") is True
    assert result.get("result") is not None
    trace = result.get("trace")
    assert isinstance(trace, list)
    nodes = [s.get("node") for s in trace]
    assert "supervisor" in nodes
    assert "patient_agent" in nodes
    assert "synthesizer" in nodes


@pytest.mark.asyncio
async def test_healthcare_workflow_denial_intent():
    llm_client_mod._llm_client = None

    wf = HealthcareWorkflow(pool=None)
    result = await wf.run("Provide an appeal recommendation for denials")

    assert result.get("success") is True
    trace = result.get("trace")
    nodes = [s.get("node") for s in trace]
    assert "supervisor" in nodes
    assert "denial_agent" in nodes
    assert "synthesizer" in nodes
