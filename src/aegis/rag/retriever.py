"""
RAG Retriever

Retrieve relevant documents with:
- Query understanding
- Multi-query expansion
- Reranking
- Citation tracking
"""

from typing import Any, Dict, List, Optional
from datetime import datetime
import asyncio

import structlog
from pydantic import BaseModel, Field

from aegis.rag.vectorstore import VectorStore, Document, SearchResult
from aegis.rag.embeddings import EmbeddingModel

logger = structlog.get_logger(__name__)


# =============================================================================
# Models
# =============================================================================

class Citation(BaseModel):
    """A citation for retrieved content."""
    document_id: str
    document_title: Optional[str]
    source: Optional[str]
    chunk_index: Optional[int]
    
    # Relevance
    score: float
    rank: int
    
    # Content
    excerpt: str  # Relevant excerpt from the document
    
    def to_reference(self) -> str:
        """Format as reference string."""
        if self.document_title:
            return f"[{self.rank}] {self.document_title}"
        return f"[{self.rank}] {self.source or self.document_id}"


class RAGResponse(BaseModel):
    """Response from RAG retrieval."""
    query: str
    
    # Retrieved context
    context: str  # Combined context for LLM
    
    # Individual results
    results: List[SearchResult] = Field(default_factory=list)
    
    # Citations
    citations: List[Citation] = Field(default_factory=list)
    
    # Metadata
    total_results: int = 0
    search_type: str = "hybrid"
    retrieval_time_ms: int = 0
    
    def get_context_with_citations(self) -> str:
        """Get context with inline citations."""
        lines = []
        for citation in self.citations:
            lines.append(f"{citation.to_reference()}:")
            lines.append(citation.excerpt)
            lines.append("")
        return "\n".join(lines)


# =============================================================================
# RAG Retriever
# =============================================================================

class RAGRetriever:
    """
    RAG retriever with advanced retrieval strategies including GraphRAG.
    
    Features:
    - Multi-query expansion (generate related queries)
    - Hybrid search (vector + keyword)
    - GraphRAG (graph traversal + vector search)
    - Reranking (cross-encoder or LLM-based)
    - Parent document retrieval
    - Citation tracking
    """
    
    def __init__(
        self,
        vector_store: VectorStore,
        embedding_model: EmbeddingModel,
        llm_client=None,  # For query expansion and reranking
        graph_client=None,  # For GraphRAG - graph traversal
    ):
        self.vector_store = vector_store
        self.embedding_model = embedding_model
        self.llm_client = llm_client
        self.graph_client = graph_client
    
    async def retrieve(
        self,
        query: str,
        top_k: int = 5,
        search_type: str = "hybrid",  # vector, keyword, hybrid, graphrag
        filters: Dict[str, Any] = None,
        expand_queries: bool = False,
        rerank: bool = True,
        include_parent: bool = False,
        use_graphrag: bool = False,  # Enable GraphRAG (graph traversal + RAG)
        graph_entity_id: Optional[str] = None,  # Starting entity ID for graph traversal
        temporal_priority: bool = False,  # Enable temporal RAG (time-based prioritization)
        time_window_days: Optional[int] = None,  # Prioritize documents within N days
    ) -> RAGResponse:
        """
        Retrieve relevant documents for a query.
        
        Args:
            query: User query
            top_k: Number of results to return
            search_type: Type of search (vector, keyword, hybrid)
            filters: Metadata filters
            expand_queries: Whether to generate additional queries
            rerank: Whether to rerank results
            include_parent: Whether to include parent documents
        """
        start_time = datetime.utcnow()
        
        # GraphRAG: If enabled, traverse graph first to get related entities
        graph_context = None
        if use_graphrag and self.graph_client and graph_entity_id:
            graph_context = await self._traverse_graph(graph_entity_id, query)
            # Enhance query with graph context
            if graph_context:
                query = f"{query}\n\nRelated context from knowledge graph:\n{graph_context}"
        
        # Expand queries if enabled
        queries = [query]
        if expand_queries and self.llm_client:
            queries.extend(await self._expand_query(query))
        
        # Get embeddings for all queries
        embeddings = await self.embedding_model.embed_batch(queries)
        
        # Search with all queries
        all_results = []
        for q, emb in zip(queries, embeddings):
            if search_type == "vector":
                results = await self.vector_store.search(emb, top_k * 2, filters)
            elif search_type == "keyword":
                results = await self.vector_store.keyword_search(q, top_k * 2, filters)
            elif search_type == "graphrag":
                # GraphRAG: Combine graph traversal results with vector search
                graph_results = await self._graphrag_search(q, emb, graph_entity_id, top_k * 2, filters)
                all_results.extend(graph_results)
                continue  # Skip regular search for graphrag mode
            else:  # hybrid
                results = await self.vector_store.hybrid_search(q, emb, top_k * 2, 0.7, filters)
            
            all_results.extend(results)
        
        # Deduplicate by document ID
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result.document.id not in seen_ids:
                seen_ids.add(result.document.id)
                unique_results.append(result)
        
        # Temporal RAG: Apply time-based prioritization
        if temporal_priority:
            unique_results = self._apply_temporal_priority(unique_results, time_window_days)
        
        # Rerank if enabled
        if rerank and len(unique_results) > top_k:
            unique_results = await self._rerank(query, unique_results, top_k * 2)
        
        # Take top_k
        final_results = unique_results[:top_k]
        
        # Include parent documents if hierarchical
        if include_parent:
            final_results = await self._include_parents(final_results)
        
        # Build citations
        citations = self._build_citations(final_results)
        
        # Build combined context
        context = self._build_context(final_results)
        
        # Calculate retrieval time
        retrieval_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return RAGResponse(
            query=query,
            context=context,
            results=final_results,
            citations=citations,
            total_results=len(final_results),
            search_type=search_type,
            retrieval_time_ms=retrieval_time_ms,
        )
    
    async def _expand_query(self, query: str) -> List[str]:
        """Generate additional queries using LLM."""
        if not self.llm_client:
            return []
        
        try:
            prompt = f"""Generate 2-3 alternative ways to search for information about this query. 
Only return the alternative queries, one per line.

Original query: {query}

Alternative queries:"""
            
            from aegis.llm.providers import Message, Role
            response = await self.llm_client.generate(prompt, max_tokens=200)
            
            # Parse response into queries
            lines = response.content.strip().split("\n")
            expanded = [line.strip().lstrip("- ").lstrip("1234567890.") for line in lines if line.strip()]
            
            logger.info(f"Expanded query into {len(expanded)} alternatives")
            return expanded[:3]
            
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return []
    
    async def _rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Rerank results using cross-encoder or LLM.
        
        Falls back to score-based ranking if LLM not available.
        """
        if not self.llm_client or len(results) <= top_k:
            # Simple score-based ranking
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
        
        try:
            # Use LLM to score relevance
            scored_results = []
            
            for result in results[:top_k * 2]:
                # Score each result
                prompt = f"""Rate the relevance of this document excerpt to the query on a scale of 0-10.
Only respond with a number.

Query: {query}

Document: {result.document.content[:500]}

Relevance score (0-10):"""
                
                from aegis.llm.providers import Message, Role
                response = await self.llm_client.generate(prompt, max_tokens=10)
                
                try:
                    score = float(response.content.strip())
                    result.score = score
                except ValueError:
                    pass
                
                scored_results.append(result)
            
            scored_results.sort(key=lambda x: x.score, reverse=True)
            return scored_results[:top_k]
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:top_k]
    
    async def _include_parents(self, results: List[SearchResult]) -> List[SearchResult]:
        """Include parent documents for hierarchical chunks."""
        enhanced_results = []
        seen_parents = set()
        
        for result in results:
            enhanced_results.append(result)
            
            # If this chunk has a parent, fetch it
            if result.document.parent_id and result.document.parent_id not in seen_parents:
                parent = await self.vector_store.get(result.document.parent_id)
                if parent:
                    seen_parents.add(parent.id)
                    enhanced_results.append(SearchResult(
                        document=parent,
                        score=result.score * 0.8,  # Slightly lower score for parent
                        search_type="parent",
                    ))
        
        return enhanced_results
    
    def _build_citations(self, results: List[SearchResult]) -> List[Citation]:
        """Build citations from search results."""
        citations = []
        
        for rank, result in enumerate(results, 1):
            doc = result.document
            
            # Get excerpt (first 300 chars or highlight)
            excerpt = result.highlights[0] if result.highlights else doc.content[:300]
            if len(doc.content) > 300 and not result.highlights:
                excerpt += "..."
            
            citations.append(Citation(
                document_id=doc.id,
                document_title=doc.title,
                source=doc.source,
                chunk_index=doc.chunk_index,
                score=result.score,
                rank=rank,
                excerpt=excerpt,
            ))
        
        return citations
    
    async def _traverse_graph(self, entity_id: str, query: str) -> Optional[str]:
        """
        Traverse knowledge graph to get related entities for GraphRAG.
        
        Example: Query patient → traverse graph → get conditions, medications, encounters, providers
        
        Returns:
            Context string with related entities from graph
        """
        if not self.graph_client:
            return None
        
        try:
            # Traverse graph: get entity and related entities
            # Example Gremlin query: g.V(entity_id).out().valueMap(true)
            gremlin_query = f"""
            g.V('{entity_id}')
                .union(
                    identity(),
                    out().limit(10),
                    in().limit(10)
                )
                .valueMap(true)
                .limit(20)
            """
            
            # Execute graph query
            if hasattr(self.graph_client, 'query'):
                graph_results = await self.graph_client.query(gremlin_query)
            elif isinstance(self.graph_client, dict) and 'g' in self.graph_client:
                # Gremlin traversal object
                g = self.graph_client['g']
                graph_results = []
                # Execute traversal
                vertices = g.V(entity_id).union(
                    lambda: g.V(entity_id),
                    lambda: g.V(entity_id).out().limit(10),
                    lambda: g.V(entity_id).in_().limit(10)
                ).valueMap(True).limit(20).toList()
                
                for v in vertices:
                    graph_results.append(dict(v))
            else:
                return None
            
            # Build context from graph results
            context_parts = []
            for i, vertex in enumerate(graph_results[:10], 1):
                label = vertex.get('label', ['Unknown'])[0] if isinstance(vertex.get('label'), list) else vertex.get('label', 'Unknown')
                props = {k: v[0] if isinstance(v, list) and len(v) > 0 else v for k, v in vertex.items() if k != 'label'}
                
                context_parts.append(f"[Graph Entity {i}] {label}")
                for key, value in props.items():
                    if key not in ['id', 'tenant_id']:
                        context_parts.append(f"  {key}: {value}")
                context_parts.append("")
            
            return "\n".join(context_parts) if context_parts else None
            
        except Exception as e:
            logger.error("Graph traversal failed", error=str(e), entity_id=entity_id)
            return None
    
    async def _graphrag_search(
        self,
        query: str,
        query_embedding: List[float],
        entity_id: Optional[str],
        top_k: int,
        filters: Optional[Dict[str, Any]],
    ) -> List[SearchResult]:
        """
        GraphRAG search: Combine graph traversal with vector search.
        
        1. Traverse graph from entity_id to get related entities
        2. Search vector store for documents related to those entities
        3. Combine and rank results
        """
        all_results = []
        
        # Step 1: Get graph context
        if entity_id:
            graph_context = await self._traverse_graph(entity_id, query)
            if graph_context:
                # Extract entity IDs/types from graph context
                # Use them to enhance vector search filters
                if filters is None:
                    filters = {}
                # Add graph-derived filters (e.g., patient_id from graph)
                filters['graph_enhanced'] = True
        
        # Step 2: Vector search with enhanced query
        vector_results = await self.vector_store.search(query_embedding, top_k * 2, filters)
        all_results.extend(vector_results)
        
        # Step 3: If graph context exists, also search for documents mentioning graph entities
        if entity_id and self.graph_client:
            # Search for documents that might reference this entity
            entity_filters = filters.copy() if filters else {}
            entity_filters['entity_id'] = entity_id
            entity_results = await self.vector_store.search(query_embedding, top_k, entity_filters)
            all_results.extend(entity_results)
        
        # Deduplicate
        seen_ids = set()
        unique_results = []
        for result in all_results:
            if result.document.id not in seen_ids:
                seen_ids.add(result.document.id)
                unique_results.append(result)
        
        # Sort by score
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results[:top_k]
    
    def _apply_temporal_priority(
        self,
        results: List[SearchResult],
        time_window_days: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Apply temporal prioritization to search results.
        
        Prioritizes:
        1. Most recent documents (within time window if specified)
        2. Recent documents get score boost
        3. Older documents are deprioritized
        
        Args:
            results: Search results to prioritize
            time_window_days: If specified, prioritize documents within this window (default: 90 days)
            
        Returns:
            Re-ranked results with temporal boost applied
        """
        from datetime import timedelta
        
        if not results:
            return results
        
        now = datetime.utcnow()
        time_window = timedelta(days=time_window_days or 90)
        
        prioritized_results = []
        
        for result in results:
            doc = result.document
            doc_time = doc.created_at or doc.updated_at or now
            
            # Calculate age
            age = now - doc_time if isinstance(doc_time, datetime) else timedelta(days=365)
            
            # Boost score for recent documents
            temporal_boost = 0.0
            if age <= time_window:
                # Within time window: boost based on recency
                days_ago = age.total_seconds() / 86400
                # Linear boost: newer = higher boost (max 0.3 boost)
                temporal_boost = max(0.0, 0.3 * (1 - days_ago / time_window_days))
            else:
                # Outside time window: slight penalty
                temporal_boost = -0.1
            
            # Apply boost to score
            boosted_score = result.score + temporal_boost
            result.score = max(0.0, boosted_score)  # Ensure non-negative
            
            prioritized_results.append(result)
        
        # Re-sort by boosted score
        prioritized_results.sort(key=lambda x: x.score, reverse=True)
        
        logger.debug(
            "Applied temporal priority",
            results_count=len(prioritized_results),
            time_window_days=time_window_days or 90,
        )
        
        return prioritized_results
    
    def _build_context(self, results: List[SearchResult]) -> str:
        """Build combined context from search results."""
        context_parts = []
        
        for i, result in enumerate(results, 1):
            doc = result.document
            header = f"[Document {i}]"
            if doc.title:
                header += f" {doc.title}"
            
            context_parts.append(header)
            context_parts.append(doc.content)
            context_parts.append("")
        
        return "\n".join(context_parts)


# =============================================================================
# Multi-Index Retriever
# =============================================================================

class MultiIndexRetriever:
    """
    Retrieve from multiple indexes (e.g., policies, guidelines, patient records).
    
    Useful when you have different document collections.
    """
    
    def __init__(self, retrievers: Dict[str, RAGRetriever]):
        self.retrievers = retrievers
    
    async def retrieve(
        self,
        query: str,
        indexes: List[str] = None,
        top_k_per_index: int = 3,
        **kwargs,
    ) -> RAGResponse:
        """Retrieve from multiple indexes."""
        indexes = indexes or list(self.retrievers.keys())
        
        all_results = []
        all_citations = []
        
        tasks = []
        for index_name in indexes:
            if index_name in self.retrievers:
                retriever = self.retrievers[index_name]
                tasks.append(retriever.retrieve(query, top_k=top_k_per_index, **kwargs))
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        for response in responses:
            if isinstance(response, Exception):
                logger.error(f"Retriever failed: {response}")
                continue
            
            all_results.extend(response.results)
            all_citations.extend(response.citations)
        
        # Sort all results by score
        all_results.sort(key=lambda x: x.score, reverse=True)
        
        # Renumber citations
        for i, citation in enumerate(all_citations, 1):
            citation.rank = i
        
        # Build combined context
        context_parts = []
        for result in all_results:
            context_parts.append(result.document.content)
        
        return RAGResponse(
            query=query,
            context="\n\n".join(context_parts),
            results=all_results,
            citations=all_citations,
            total_results=len(all_results),
            search_type="multi_index",
        )
