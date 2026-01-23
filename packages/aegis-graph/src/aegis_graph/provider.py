"""
Graph Provider Factory

Creates the appropriate graph provider based on configuration.
This is the main entry point for the application.
"""

from enum import Enum
from typing import Any

import structlog

from aegis_graph.providers.base import BaseGraphProvider
from aegis_graph.providers.janusgraph import JanusGraphProvider
from aegis_graph.providers.neptune import NeptuneProvider

logger = structlog.get_logger(__name__)


class GraphProviderType(str, Enum):
    """Supported graph database providers."""
    JANUSGRAPH = "janusgraph"
    NEPTUNE = "neptune"
    NEO4J = "neo4j"  # Future support


class GraphProvider:
    """
    Graph Provider Factory.
    
    Creates and manages graph database connections based on configuration.
    
    Usage:
        # From config
        provider = GraphProvider.from_config(settings)
        
        # Or explicit
        provider = GraphProvider.create(
            provider_type="janusgraph",
            connection_url="ws://localhost:8182/gremlin"
        )
        
        async with provider as graph:
            await graph.create_vertex("Patient", {...})
    """
    
    _providers: dict[str, type[BaseGraphProvider]] = {
        GraphProviderType.JANUSGRAPH: JanusGraphProvider,
        GraphProviderType.NEPTUNE: NeptuneProvider,
    }
    
    @classmethod
    def create(
        cls,
        provider_type: str | GraphProviderType,
        connection_url: str,
        **kwargs
    ) -> BaseGraphProvider:
        """
        Create a graph provider instance.
        
        Args:
            provider_type: Type of provider ('janusgraph', 'neptune', 'neo4j')
            connection_url: Database connection URL
            **kwargs: Provider-specific options
            
        Returns:
            Configured graph provider instance
            
        Raises:
            ValueError: If provider type is not supported
        """
        if isinstance(provider_type, str):
            provider_type = GraphProviderType(provider_type.lower())
        
        provider_class = cls._providers.get(provider_type)
        
        if provider_class is None:
            supported = [p.value for p in GraphProviderType]
            raise ValueError(
                f"Unsupported provider: {provider_type}. "
                f"Supported: {supported}"
            )
        
        logger.info(
            "Creating graph provider",
            provider=provider_type.value,
            url=connection_url[:50] + "..."
        )
        
        return provider_class(connection_url, **kwargs)
    
    @classmethod
    def from_config(cls, config: Any) -> BaseGraphProvider:
        """
        Create provider from application config.
        
        Args:
            config: Configuration object with graph_db settings
            
        Returns:
            Configured graph provider
        """
        # Support both dict and object config
        if hasattr(config, "graph_db"):
            graph_config = config.graph_db
        elif isinstance(config, dict):
            graph_config = config.get("graph_db", config)
        else:
            graph_config = config
        
        # Extract settings
        if hasattr(graph_config, "provider"):
            provider_type = graph_config.provider
            connection_url = graph_config.connection_url
            extra_kwargs = {}
            if hasattr(graph_config, "region"):
                extra_kwargs["region"] = graph_config.region
        else:
            provider_type = graph_config.get("provider", "janusgraph")
            connection_url = graph_config.get("connection_url")
            extra_kwargs = {
                k: v for k, v in graph_config.items() 
                if k not in ("provider", "connection_url")
            }
        
        return cls.create(provider_type, connection_url, **extra_kwargs)
    
    @classmethod
    def register_provider(
        cls,
        provider_type: GraphProviderType,
        provider_class: type[BaseGraphProvider]
    ) -> None:
        """
        Register a custom graph provider.
        
        Args:
            provider_type: Provider type enum
            provider_class: Provider implementation class
        """
        cls._providers[provider_type] = provider_class
        logger.info("Registered graph provider", provider=provider_type.value)


# ==================== SINGLETON MANAGEMENT ====================

_graph_provider: BaseGraphProvider | None = None


async def get_graph_provider(config: Any = None) -> BaseGraphProvider:
    """
    Get the singleton graph provider instance.
    
    Args:
        config: Optional config (only used on first call)
        
    Returns:
        Connected graph provider
    """
    global _graph_provider
    
    if _graph_provider is None:
        if config is None:
            # Try to import settings
            try:
                from aegis.config import get_settings
                config = get_settings()
            except ImportError:
                raise ValueError("No config provided and aegis.config not available")
        
        _graph_provider = GraphProvider.from_config(config)
        await _graph_provider.connect()
    
    return _graph_provider


async def close_graph_provider() -> None:
    """Close the singleton graph provider."""
    global _graph_provider
    
    if _graph_provider is not None:
        await _graph_provider.disconnect()
        _graph_provider = None
