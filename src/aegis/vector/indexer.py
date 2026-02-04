"""Vector Indexer skeleton

Simple interface for indexing documents into a vector store (e.g., OpenSearch,
FAISS). This is a skeleton with mock behavior useful for unit tests and
integration prototypes.
"""

from typing import List, Dict, Any


class VectorIndexer:
    def __init__(self, host: str | None = None):
        self.host = host or "http://localhost:9200"
        self.index = {}

    def index_documents(self, docs: List[Dict[str, Any]]) -> List[str]:
        """Index documents and return list of document IDs."""
        ids = []
        for d in docs:
            doc_id = d.get("id") or f"doc_{len(self.index) + 1}"
            self.index[doc_id] = d
            ids.append(doc_id)
        return ids

    def search(self, query_vector: List[float], k: int = 5) -> List[Dict[str, Any]]:
        """Mock search that returns first k docs."""
        results = list(self.index.values())[:k]
        return results
