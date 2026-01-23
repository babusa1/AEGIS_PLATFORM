# ADR-001: Graph Database Selection

## Status
Accepted

## Context
AEGIS requires a knowledge graph database to store healthcare entities (patients, encounters, claims, etc.) and their relationships. We need to choose between:
- Neo4j (Enterprise Edition)
- AWS Neptune
- JanusGraph (open-source)

## Decision
**Use JanusGraph with an abstraction layer** that allows swapping to Neptune or Neo4j in the future.

### Rationale
1. **Cloud-agnostic**: JanusGraph runs on any cloud or on-premise
2. **Open-source**: No vendor lock-in, no licensing costs for development
3. **Gremlin compatibility**: Same query language as AWS Neptune
4. **Scalability**: Supports Cassandra/HBase backends for massive scale
5. **Production path**: Easy migration to Neptune when needed (same Gremlin queries)

### Abstraction Layer
```python
class GraphProvider(ABC):
    @abstractmethod
    async def query(self, gremlin: str) -> list[dict]: ...
    @abstractmethod
    async def add_vertex(self, label: str, props: dict) -> str: ...

# Implementations
class JanusGraphProvider(GraphProvider): ...  # Current
class NeptuneProvider(GraphProvider): ...     # Future
class Neo4jProvider(GraphProvider): ...       # Future
```

## Consequences
- Local development uses JanusGraph via Docker
- Production can use JanusGraph, Neptune, or Neo4j
- Must maintain Gremlin-compatible queries (avoid Neptune/Neo4j specific features initially)
- Abstraction layer adds minimal overhead but maximum flexibility

## References
- [JanusGraph Documentation](https://janusgraph.org/)
- [AWS Neptune](https://aws.amazon.com/neptune/)
- [Gremlin Query Language](https://tinkerpop.apache.org/gremlin.html)
