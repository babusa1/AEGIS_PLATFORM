from aegis.vector.indexer import VectorIndexer


def test_vector_indexer_index_and_search():
    idx = VectorIndexer()
    docs = [{"id": "d1", "text": "hello"}, {"id": "d2", "text": "world"}]
    ids = idx.index_documents(docs)
    assert ids == ["d1", "d2"]

    results = idx.search([0.1, 0.2], k=1)
    assert isinstance(results, list)
    assert results[0]["id"] == "d1"
