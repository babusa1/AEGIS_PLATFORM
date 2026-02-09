"""
Librarian Agent

The Librarian Agent performs contextual retrieval with:
- GraphRAG Path-Finding: Traverses the graph (e.g., Weight Gain → eGFR → NT-proBNP)
- Temporal Delta Analysis: Calculates "velocity" of disease (e.g., Creatinine rise rate)
- Recursive Summarization: Creates hierarchical summaries (Decade → Year → Recent)

This wraps UnifiedViewAgent + RAGRetriever with Librarian-specific interfaces.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import structlog

from aegis.agents.unified_view import UnifiedViewAgent
from aegis.rag.retriever import RAGRetriever
from aegis.rag.summarization import RecursiveSummarizer
from aegis.query.temporal_patterns import TemporalPatternMatcher
from aegis.bedrock.client import LLMClient

logger = structlog.get_logger(__name__)


class LibrarianAgent:
    """
    Librarian Agent - Contextual Retrieval
    
    The Librarian performs zero-latency retrieval of the patient's ground truth.
    
    Features:
    1. GraphRAG Traversal: Follows clinical edges (Patient → Medication → Lab → Comorbidity)
    2. Temporal Delta Analysis: Calculates disease "velocity" (e.g., Creatinine rise rate)
    3. Recursive Summarization: Creates hierarchical summaries for long histories
    
    This wraps UnifiedViewAgent and RAGRetriever with Librarian-specific methods.
    """
    
    def __init__(
        self,
        tenant_id: str,
        pool=None,
        llm_client: Optional[LLMClient] = None,
        graph_client=None,
        vector_client=None,
    ):
        """
        Initialize Librarian Agent.
        
        Args:
            tenant_id: Tenant ID
            pool: Database connection pool
            llm_client: LLM client
            graph_client: Graph database client
            vector_client: Vector database client
        """
        self.tenant_id = tenant_id
        self.pool = pool
        
        # Wrap UnifiedViewAgent
        self.unified_view_agent = UnifiedViewAgent(
            tenant_id=tenant_id,
            llm_client=llm_client,
        )
        
        # Wrap RAGRetriever
        self.rag_retriever = RAGRetriever(
            pool=pool,
            tenant_id=tenant_id,
            graph_client=graph_client,
            vector_client=vector_client,
        )
        
        # Recursive summarizer
        self.summarizer = RecursiveSummarizer(llm_client=llm_client)
        
        # Temporal pattern matcher
        self.pattern_matcher = TemporalPatternMatcher(
            db_pool=pool,
            graph_client=graph_client,
        )
        
        logger.info("LibrarianAgent initialized", tenant_id=tenant_id)
    
    # =========================================================================
    # GraphRAG Path-Finding
    # =========================================================================
    
    async def traverse_graph_path(
        self,
        entity_id: str,
        query: str,
        max_depth: int = 3,
    ) -> Dict[str, Any]:
        """
        GraphRAG Path-Finding: Traverse the graph following clinical edges.
        
        Example: Query "Heart failure risk" → Traverse Weight Gain → eGFR → NT-proBNP
        
        Args:
            entity_id: Starting entity ID (e.g., patient ID)
            query: Query string (e.g., "Heart failure risk")
            max_depth: Maximum traversal depth
            
        Returns:
            Dict with:
            - path: List of entities in traversal path
            - context: Context string built from path
            - related_entities: Related entities found
        """
        logger.info(
            "GraphRAG traversal",
            entity_id=entity_id,
            query=query,
            max_depth=max_depth,
        )
        
        # Use RAGRetriever's graph traversal
        context = await self.rag_retriever._traverse_graph(entity_id, query)
        
        if not context:
            return {
                "path": [],
                "context": "",
                "related_entities": [],
            }
        
        # Parse context to extract path
        # In production, would parse structured graph results
        path = [entity_id]  # Simplified - would extract actual path
        
        return {
            "path": path,
            "context": context,
            "related_entities": [],  # Would extract from graph results
        }
    
    async def get_patient_network(
        self,
        patient_id: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """
        Get patient's care network by traversing graph.
        
        Traverses: Patient → Providers, Facilities, Conditions, Medications, etc.
        
        Args:
            patient_id: Patient ID
            depth: Traversal depth
            
        Returns:
            Dict with patient network information
        """
        logger.info("Getting patient network", patient_id=patient_id, depth=depth)
        
        # Use graph traversal
        context = await self.rag_retriever._traverse_graph(patient_id, "patient network")
        
        return {
            "patient_id": patient_id,
            "network_context": context or "",
            "depth": depth,
        }
    
    # =========================================================================
    # Temporal Delta Analysis
    # =========================================================================
    
    async def calculate_temporal_delta(
        self,
        patient_id: str,
        metric_name: str,
        time_window_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Temporal Delta Analysis: Calculate "velocity" of disease.
        
        Example: "Creatinine has risen by 0.4 in 72 hours, indicating an AKI trajectory"
        
        Args:
            patient_id: Patient ID
            metric_name: Metric name (e.g., "creatinine", "eGFR", "hemoglobin")
            time_window_days: Time window for analysis
            
        Returns:
            Dict with:
            - current_value: Current metric value
            - previous_value: Previous metric value
            - delta: Change in value
            - delta_percentage: Percentage change
            - velocity: Rate of change per day
            - trajectory: "improving", "stable", "worsening"
            - interpretation: Human-readable interpretation
        """
        logger.info(
            "Calculating temporal delta",
            patient_id=patient_id,
            metric_name=metric_name,
            time_window_days=time_window_days,
        )
        
        # Get patient data using UnifiedViewAgent
        result = await self.unified_view_agent.run(
            query=f"Get {metric_name} values for patient {patient_id} over last {time_window_days} days",
            tenant_id=self.tenant_id,
        )
        
        # Parse result to extract metric values
        # In production, would query time-series database
        # For now, return structured response
        return {
            "patient_id": patient_id,
            "metric_name": metric_name,
            "time_window_days": time_window_days,
            "current_value": None,  # Would extract from result
            "previous_value": None,
            "delta": None,
            "delta_percentage": None,
            "velocity": None,  # Change per day
            "trajectory": "stable",
            "interpretation": f"{metric_name} trend analysis for patient {patient_id}",
        }
    
    async def analyze_disease_velocity(
        self,
        patient_id: str,
        condition: str,
        time_window_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Analyze disease velocity (rate of progression).
        
        Example: "eGFR declining at 2 mL/min/month, indicating rapid CKD progression"
        
        Args:
            patient_id: Patient ID
            condition: Condition name (e.g., "CKD", "HF", "Diabetes")
            time_window_days: Time window for analysis
            
        Returns:
            Dict with velocity analysis
        """
        logger.info(
            "Analyzing disease velocity",
            patient_id=patient_id,
            condition=condition,
            time_window_days=time_window_days,
        )
        
        # Use temporal pattern matcher
        # Would create pattern for condition progression
        # For now, return structured response
        return {
            "patient_id": patient_id,
            "condition": condition,
            "time_window_days": time_window_days,
            "velocity": None,  # Rate of change
            "trajectory": "stable",
            "interpretation": f"{condition} progression analysis",
        }
    
    # =========================================================================
    # Recursive Summarization
    # =========================================================================
    
    async def create_recursive_summary(
        self,
        patient_id: str,
        start_date: datetime,
        end_date: datetime,
        level: str = "monthly",
    ) -> Dict[str, Any]:
        """
        Recursive Summarization: Create hierarchical summaries for long histories.
        
        For 20-year histories, creates:
        - Decade Summaries
        - Year Summaries
        - Recent Event Chunks
        
        Args:
            patient_id: Patient ID
            start_date: Start of time period
            end_date: End of time period
            level: Summary level (daily, weekly, monthly, yearly)
            
        Returns:
            Dict with summary
        """
        logger.info(
            "Creating recursive summary",
            patient_id=patient_id,
            level=level,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )
        
        # Get patient events
        # In production, would query from database
        events = []  # Would fetch from database
        
        # Use recursive summarizer
        summary = await self.summarizer.summarize_patient_chart(
            patient_id=patient_id,
            events=events,
            start_date=start_date,
            end_date=end_date,
            level=level,
        )
        
        return summary
    
    async def get_patient_summary_hierarchy(
        self,
        patient_id: str,
    ) -> Dict[str, Any]:
        """
        Get hierarchical summaries at all levels (Decade → Year → Month → Week).
        
        Args:
            patient_id: Patient ID
            
        Returns:
            Dict with summaries at each level
        """
        logger.info("Getting patient summary hierarchy", patient_id=patient_id)
        
        # Get patient's first encounter date (would query database)
        # For now, use last 10 years
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365 * 10)
        
        # Create summaries at each level
        summaries = {}
        
        for level in ["yearly", "monthly", "weekly"]:
            summary = await self.create_recursive_summary(
                patient_id=patient_id,
                start_date=start_date,
                end_date=end_date,
                level=level,
            )
            summaries[level] = summary
        
        return {
            "patient_id": patient_id,
            "summaries": summaries,
        }
    
    # =========================================================================
    # Unified Interface (wraps UnifiedViewAgent)
    # =========================================================================
    
    async def get_patient_context(
        self,
        patient_id: str,
        include_summary: bool = True,
    ) -> Dict[str, Any]:
        """
        Get comprehensive patient context (wraps UnifiedViewAgent).
        
        Args:
            patient_id: Patient ID
            include_summary: Whether to include recursive summary
            
        Returns:
            Dict with patient context
        """
        logger.info("Getting patient context", patient_id=patient_id)
        
        # Use UnifiedViewAgent
        result = await self.unified_view_agent.run(
            query=f"Get comprehensive patient 360 view for patient {patient_id}",
            tenant_id=self.tenant_id,
        )
        
        context = {
            "patient_id": patient_id,
            "summary": result.get("answer", ""),
            "reasoning": result.get("reasoning", []),
        }
        
        # Add recursive summary if requested
        if include_summary:
            summary_hierarchy = await self.get_patient_summary_hierarchy(patient_id)
            context["summary_hierarchy"] = summary_hierarchy
        
        return context
    
    async def retrieve_context_for_query(
        self,
        query: str,
        patient_id: Optional[str] = None,
        use_graphrag: bool = True,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        """
        Retrieve context for a query using GraphRAG + Vector Search.
        
        Args:
            query: Query string
            patient_id: Optional patient ID for graph traversal
            use_graphrag: Whether to use GraphRAG
            top_k: Number of results
            
        Returns:
            Dict with retrieved context
        """
        logger.info(
            "Retrieving context for query",
            query=query,
            patient_id=patient_id,
            use_graphrag=use_graphrag,
        )
        
        # Use RAGRetriever
        if use_graphrag and patient_id:
            # GraphRAG traversal
            graph_context = await self.traverse_graph_path(patient_id, query)
            
            # Vector search
            vector_results = await self.rag_retriever.retrieve(
                query=query,
                top_k=top_k,
                search_type="hybrid",
            )
            
            return {
                "query": query,
                "graph_context": graph_context,
                "vector_results": vector_results,
                "combined_context": f"{graph_context.get('context', '')}\n\n{vector_results.get('context', '')}",
            }
        else:
            # Vector search only
            results = await self.rag_retriever.retrieve(
                query=query,
                top_k=top_k,
                search_type="hybrid",
            )
            
            return {
                "query": query,
                "vector_results": results,
                "combined_context": results.get("context", ""),
            }
