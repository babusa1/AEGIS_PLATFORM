"""
Action Agent

Agent for executing healthcare operational workflows, particularly
denial appeal generation using Writer + Critic pattern.
"""

from typing import Literal

import structlog
from langgraph.graph import StateGraph, END

from aegis.agents.base import BaseAgent, AgentState
from aegis.agents.tools import AgentTools
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class ActionAgent(BaseAgent):
    """
    Action Agent - Denial Appeal Workflow
    
    This agent handles operational actions that require:
    - Data gathering from knowledge graph
    - Document generation (appeals, letters)
    - Human-in-the-loop approval
    - Action execution
    
    Uses a Writer + Critic pattern for appeal generation:
    1. Writer generates initial appeal letter
    2. Critic reviews for completeness, accuracy, persuasiveness
    3. Writer revises based on feedback
    4. Final review before human approval
    """
    
    def __init__(
        self,
        tenant_id: str,
        llm_client: LLMClient | None = None,
    ):
        self.tenant_id = tenant_id
        self.agent_tools = AgentTools(tenant_id)
        
        # Get relevant tools
        all_tools = self.agent_tools.get_all_tools()
        tools = {
            "get_claim": all_tools["get_claim"],
            "get_claim_for_appeal": all_tools["get_claim_for_appeal"],
            "get_denied_claims": all_tools["get_denied_claims"],
            "calculate_appeal_priority": all_tools["calculate_appeal_priority"],
        }
        
        super().__init__(
            name="action_agent",
            llm_client=llm_client,
            max_iterations=8,  # More iterations for writer/critic
            tools=tools,
        )
    
    def _get_system_prompt(self) -> str:
        return """You are the AEGIS Action Agent, specialized in healthcare 
revenue cycle operations and denial management.

Your primary function is to generate effective denial appeal letters that:
1. Are professionally written and persuasive
2. Reference specific clinical documentation
3. Cite relevant payer policies and regulations
4. Include strong medical necessity justification
5. Follow payer-specific appeal requirements

When generating appeals:
- Address the specific denial reason code
- Reference dates, diagnosis codes, and procedure codes
- Include supporting clinical evidence
- Cite applicable guidelines (LCD, NCD, clinical criteria)
- Maintain a professional but assertive tone
- Request specific action (reconsideration, peer review, etc.)

Always ensure the appeal is:
- Factually accurate (based on available data)
- Compliant with appeal deadlines
- Clear about the requested remedy
"""
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow for action execution."""
        
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("gather_evidence", self._gather_evidence)
        workflow.add_node("analyze_denial", self._analyze_denial)
        workflow.add_node("write_appeal", self._write_appeal)
        workflow.add_node("critique_appeal", self._critique_appeal)
        workflow.add_node("revise_appeal", self._revise_appeal)
        workflow.add_node("finalize", self._finalize_appeal)
        
        # Define edges
        workflow.set_entry_point("gather_evidence")
        workflow.add_edge("gather_evidence", "analyze_denial")
        workflow.add_edge("analyze_denial", "write_appeal")
        workflow.add_edge("write_appeal", "critique_appeal")
        
        # Conditional edge: revise or finalize
        workflow.add_conditional_edges(
            "critique_appeal",
            self._should_revise,
            {
                "revise": "revise_appeal",
                "finalize": "finalize",
            }
        )
        workflow.add_edge("revise_appeal", "critique_appeal")
        workflow.add_edge("finalize", END)
        
        return workflow
    
    def _should_revise(self, state: AgentState) -> Literal["revise", "finalize"]:
        """Determine if appeal needs revision."""
        iteration = state.get("iteration", 0)
        reasoning = state.get("reasoning", [])
        
        # Check if critic requested revisions
        last_reasoning = reasoning[-1] if reasoning else ""
        
        # Max 2 revision cycles
        if iteration >= 4:
            return "finalize"
        
        # Check for revision indicators
        if "NEEDS_REVISION" in last_reasoning or "revise" in last_reasoning.lower():
            return "revise"
        
        return "finalize"
    
    async def _gather_evidence(self, state: AgentState) -> dict:
        """Node: Gather all evidence needed for appeal."""
        query = state["current_input"]
        
        # Extract claim ID
        claim_id = None
        if "claim_id:" in query.lower():
            claim_id = query.lower().split("claim_id:")[1].split()[0].strip()
        elif "claim" in query.lower():
            # Try to extract claim ID
            words = query.split()
            for i, word in enumerate(words):
                if "claim" in word.lower() and i + 1 < len(words):
                    claim_id = words[i + 1].strip(".,!?")
                    break
        
        if not claim_id:
            # Use LLM to extract
            extract_prompt = f"""Extract the claim ID from this request:
"{query}"

Return just the claim ID, nothing else. If none found, return "NONE".
"""
            claim_id = await self.llm.generate(prompt=extract_prompt)
            claim_id = claim_id.strip()
            
            if claim_id == "NONE":
                return {
                    "tool_results": [{"error": "No claim ID found in request"}],
                    "reasoning": ["Failed to extract claim ID from request"],
                    "iteration": state.get("iteration", 0) + 1,
                }
        
        # Get claim data for appeal
        appeal_data = await self.agent_tools.get_claim_for_appeal(claim_id)
        
        if "error" in appeal_data:
            return {
                "tool_results": [{"type": "evidence", "data": appeal_data}],
                "reasoning": [f"Failed to gather evidence: {appeal_data.get('error')}"],
                "iteration": state.get("iteration", 0) + 1,
            }
        
        return {
            "tool_results": [{"type": "evidence", "data": appeal_data}],
            "reasoning": [f"Gathered evidence for claim {claim_id}: {len(appeal_data.get('diagnoses', []))} diagnoses, {len(appeal_data.get('procedures', []))} procedures"],
            "iteration": state.get("iteration", 0) + 1,
        }
    
    async def _analyze_denial(self, state: AgentState) -> dict:
        """Node: Analyze the denial and determine appeal strategy."""
        tool_results = state.get("tool_results", [])
        
        # Get evidence
        evidence = None
        for result in tool_results:
            if isinstance(result, dict) and result.get("type") == "evidence":
                evidence = result.get("data")
                break
        
        if not evidence or "error" in evidence:
            return {
                "tool_results": [{"type": "strategy", "data": {"error": "No evidence available"}}],
                "reasoning": ["Cannot analyze denial without evidence"],
            }
        
        # Extract denial info
        denials = evidence.get("denials", [])
        if not denials:
            return {
                "tool_results": [{"type": "strategy", "data": {"error": "No denial found for this claim"}}],
                "reasoning": ["Claim does not have an active denial"],
            }
        
        denial = denials[0]  # Primary denial
        reason_code = denial.get("reason_code", ["Unknown"])[0] if isinstance(denial.get("reason_code"), list) else denial.get("reason_code", "Unknown")
        category = denial.get("category", ["other"])[0] if isinstance(denial.get("category"), list) else denial.get("category", "other")
        
        # Determine appeal strategy based on denial type
        strategy_prompt = f"""Analyze this denial and recommend an appeal strategy:

Denial Reason Code: {reason_code}
Category: {category}
Denial Details: {denial}

Patient Diagnoses: {evidence.get('diagnoses', [])}
Procedures: {evidence.get('procedures', [])}

Recommend:
1. Primary argument for appeal
2. Key evidence to cite
3. Relevant guidelines or policies to reference
4. Specific language to use/avoid
"""
        
        strategy = await self.llm.generate(
            prompt=strategy_prompt,
            system_prompt=self._get_system_prompt(),
        )
        
        return {
            "tool_results": [
                {"type": "strategy", "data": {"strategy": strategy, "denial": denial}},
            ],
            "reasoning": [f"Analyzed denial ({reason_code}): {category}"],
        }
    
    async def _write_appeal(self, state: AgentState) -> dict:
        """Node: Write initial appeal letter (Writer role)."""
        tool_results = state.get("tool_results", [])
        
        # Gather all context
        evidence = None
        strategy = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") == "evidence":
                    evidence = result.get("data")
                elif result.get("type") == "strategy":
                    strategy = result.get("data")
        
        if not evidence or not strategy:
            return {
                "tool_results": [{"type": "draft_appeal", "data": {"error": "Missing context"}}],
                "reasoning": ["Cannot write appeal without evidence and strategy"],
            }
        
        # Write appeal letter
        write_prompt = f"""Write a professional denial appeal letter using this information:

CLAIM INFORMATION:
{evidence.get('claim', {})}

DENIAL DETAILS:
{strategy.get('denial', {})}

APPEAL STRATEGY:
{strategy.get('strategy', '')}

CLINICAL EVIDENCE:
- Patient: {evidence.get('patient', {})}
- Encounter: {evidence.get('encounter', {})}
- Diagnoses: {evidence.get('diagnoses', [])}
- Procedures: {evidence.get('procedures', [])}

Write a complete appeal letter that:
1. Opens with claim identification and appeal request
2. States the specific denial reason being appealed
3. Presents clinical justification with specific evidence
4. References applicable guidelines
5. Requests specific action (reconsideration, peer review)
6. Closes professionally

Use a formal business letter format.
"""
        
        appeal_letter = await self.llm.generate(
            prompt=write_prompt,
            system_prompt=self._get_system_prompt(),
        )
        
        return {
            "tool_results": [{"type": "draft_appeal", "data": {"letter": appeal_letter, "version": 1}}],
            "reasoning": ["Writer: Generated initial appeal draft"],
        }
    
    async def _critique_appeal(self, state: AgentState) -> dict:
        """Node: Critique the appeal letter (Critic role)."""
        tool_results = state.get("tool_results", [])
        
        # Get latest appeal draft
        draft = None
        evidence = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") in ["draft_appeal", "revised_appeal"]:
                    draft = result.get("data")
                elif result.get("type") == "evidence":
                    evidence = result.get("data")
        
        if not draft:
            return {
                "reasoning": ["Critic: No appeal draft to review. NEEDS_REVISION"],
            }
        
        appeal_letter = draft.get("letter", "")
        version = draft.get("version", 1)
        
        # Critique the appeal
        critique_prompt = f"""You are reviewing a denial appeal letter. Evaluate it critically:

APPEAL LETTER:
{appeal_letter}

AVAILABLE EVIDENCE:
{evidence}

Evaluate the appeal on these criteria (score 1-10):
1. **Completeness**: Does it address all denial reasons?
2. **Evidence Citation**: Does it reference specific clinical data?
3. **Guideline References**: Does it cite relevant policies/guidelines?
4. **Persuasiveness**: Is the argument compelling?
5. **Professionalism**: Is the tone appropriate?
6. **Accuracy**: Are all facts correct based on evidence?

For each criterion scoring below 8, provide specific improvement suggestions.

If the appeal scores 8+ on all criteria, respond with "APPROVED".
Otherwise, list specific revisions needed and respond with "NEEDS_REVISION".
"""
        
        critique = await self.llm.generate(
            prompt=critique_prompt,
            system_prompt="You are a healthcare compliance expert reviewing appeal letters for quality.",
        )
        
        approved = "APPROVED" in critique and "NEEDS_REVISION" not in critique
        
        return {
            "tool_results": [{"type": "critique", "data": {"feedback": critique, "approved": approved, "version": version}}],
            "reasoning": [f"Critic (v{version}): {'APPROVED' if approved else 'NEEDS_REVISION'}\n{critique[:200]}..."],
        }
    
    async def _revise_appeal(self, state: AgentState) -> dict:
        """Node: Revise appeal based on critique."""
        tool_results = state.get("tool_results", [])
        
        # Get draft and critique
        draft = None
        critique = None
        evidence = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") in ["draft_appeal", "revised_appeal"]:
                    draft = result.get("data")
                elif result.get("type") == "critique":
                    critique = result.get("data")
                elif result.get("type") == "evidence":
                    evidence = result.get("data")
        
        if not draft or not critique:
            return {
                "reasoning": ["Cannot revise without draft and critique"],
            }
        
        # Revise based on feedback
        revise_prompt = f"""Revise this appeal letter based on the critique feedback:

CURRENT APPEAL:
{draft.get('letter', '')}

CRITIQUE FEEDBACK:
{critique.get('feedback', '')}

EVIDENCE FOR REFERENCE:
{evidence}

Revise the appeal to address all feedback points while maintaining:
- Professional tone
- Accurate facts
- Clear argument structure

Output only the revised letter.
"""
        
        revised_letter = await self.llm.generate(
            prompt=revise_prompt,
            system_prompt=self._get_system_prompt(),
        )
        
        new_version = draft.get("version", 1) + 1
        
        return {
            "tool_results": [{"type": "revised_appeal", "data": {"letter": revised_letter, "version": new_version}}],
            "reasoning": [f"Writer: Revised appeal to version {new_version}"],
            "iteration": state.get("iteration", 0) + 1,
        }
    
    async def _finalize_appeal(self, state: AgentState) -> dict:
        """Node: Finalize the appeal for human review."""
        tool_results = state.get("tool_results", [])
        
        # Get final appeal
        final_appeal = None
        evidence = None
        
        for result in tool_results:
            if isinstance(result, dict):
                if result.get("type") in ["draft_appeal", "revised_appeal"]:
                    final_appeal = result.get("data")
                elif result.get("type") == "evidence":
                    evidence = result.get("data")
        
        if not final_appeal:
            return {
                "final_answer": "Failed to generate appeal letter.",
                "confidence": 0.1,
            }
        
        letter = final_appeal.get("letter", "")
        version = final_appeal.get("version", 1)
        
        # Build final output
        claim_number = "Unknown"
        denial_reason = "Unknown"
        
        if evidence:
            claim = evidence.get("claim", {})
            claim_number = claim.get("claim_number", ["Unknown"])[0] if isinstance(claim.get("claim_number"), list) else claim.get("claim_number", "Unknown")
            
            denials = evidence.get("denials", [])
            if denials:
                denial_reason = denials[0].get("reason_code", ["Unknown"])[0] if isinstance(denials[0].get("reason_code"), list) else denials[0].get("reason_code", "Unknown")
        
        final_output = f"""## Denial Appeal Letter

**Claim Number:** {claim_number}
**Denial Reason:** {denial_reason}
**Appeal Version:** {version}
**Status:** Ready for Human Review

---

{letter}

---

**Next Steps:**
1. Review the appeal letter for accuracy
2. Attach supporting clinical documentation
3. Submit to payer before appeal deadline
4. Track appeal status in the system
"""
        
        return {
            "final_answer": final_output,
            "confidence": 0.85 if version > 1 else 0.75,
        }
    
    async def generate_appeal(
        self,
        claim_id: str,
        additional_context: str | None = None,
    ) -> dict:
        """
        Convenience method to generate a denial appeal.
        
        Args:
            claim_id: The claim ID to appeal
            additional_context: Optional additional notes
            
        Returns:
            Dict with appeal letter and metadata
        """
        query = f"Generate a denial appeal for claim_id: {claim_id}"
        if additional_context:
            query += f"\nAdditional context: {additional_context}"
        
        result = await self.run(
            query=query,
            tenant_id=self.tenant_id,
        )
        
        return result
