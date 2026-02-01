import pytest
from datetime import datetime, timezone

from src import search


class DummyIndices:
    def __init__(self):
        self.created = []
        self._exists = set()
        self._mapping = {}

    def exists(self, index):
        return index in self._exists

    def create(self, index, body):
        self._exists.add(index)
        self.created.append(index)

    def get_mapping(self, index):
        return self._mapping


class DummyClient:
    def __init__(self):
        self.indices = DummyIndices()
        self.search_calls = []
        self.index_calls = []

    def search(self, index, body):
        self.search_calls.append((index, body))
        return {
            "hits": {
                "hits": [
                    {"_id": "1", "_score": 1.0, "_source": {"celex": "A"}},
                    {"_id": "2", "_score": 0.5, "_source": {"celex": "B"}},
                ],
                "total": {"value": 2},
            }
        }

    def index(self, index, id, body):
        self.index_calls.append((index, id, body))


@pytest.mark.unit
def test_rrf_and_merge():
    scores = search._rrf_scores([{"_id": "a"}, {"_id": "b"}])
    assert "a" in scores and "b" in scores

    merged = search._merge_hybrid_results(
        [{"_id": "a"}, {"_id": "b"}], [{"_id": "b"}, {"_id": "c"}], alpha=0.7, size=3
    )
    assert any(hit["_id"] == "a" for hit in merged)


@pytest.mark.unit
def test_search_documents_and_index(monkeypatch):
    client = DummyClient()
    monkeypatch.setattr(search, "get_opensearch_client", lambda: client)

    search.init_indices()
    assert "legal_documents" in client.indices.created

    results = search.search_documents(q="aml", compliance_domain="aml", size=1)
    assert results["total"] == 2

    class DummyDoc:
        celex = "CELEX1"
        eli = None
        cellar_id = None
        title = "Title"
        publication_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        entry_into_force_date = None
        status = "active"
        type = "regulation"
        compliance_domain = "aml"
        risk_level = "high"
        implementation_deadline = None
        jurisdictional_scope = "EU"
        ai_summary = "summary"
        full_text = "text"
        word_count = 10

    assert search.index_document(DummyDoc()) is True


@pytest.mark.unit
def test_search_rag_chunks(monkeypatch):
    client = DummyClient()
    monkeypatch.setattr(search, "get_opensearch_client", lambda: client)

    results = search.search_rag_chunks("query", size=2, alpha=1.0)
    assert results["total"] == 2


@pytest.mark.unit
def test_init_rag_index_dimension_warning(monkeypatch):
    client = DummyClient()
    client.indices._exists.add("rag_index")
    client.indices._mapping = {
        "rag_index": {"mappings": {"properties": {"embedding": {"dimension": 10}}}}
    }

    monkeypatch.setattr(search, "get_opensearch_client", lambda: client)
    monkeypatch.setattr(search.settings, "RAG_INDEX_NAME", "rag_index")

    search.init_rag_index(embedding_dim=5)


@pytest.mark.unit
def test_get_opensearch_client_security_branch(monkeypatch):
    class DummyOpenSearch:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    # Ensure fresh client
    search._opensearch_client = None

    monkeypatch.setenv("OPENSEARCH_SECURITY_ENABLED", "true")
    monkeypatch.setenv("OPENSEARCH_USER", "admin")
    monkeypatch.setenv("OPENSEARCH_PASSWORD", "secret")

    monkeypatch.setattr(search, "OpenSearch", lambda **kwargs: DummyOpenSearch(**kwargs))
    monkeypatch.setattr(search.settings, "OPENSEARCH_URL", "http://localhost:9200")

    client = search.get_opensearch_client()
    assert hasattr(client, "kwargs")
    assert client.kwargs.get("use_ssl") is True


@pytest.mark.unit
def test_get_opensearch_client_security_missing_password(monkeypatch):
    search._opensearch_client = None
    monkeypatch.setenv("OPENSEARCH_SECURITY_ENABLED", "true")
    monkeypatch.delenv("OPENSEARCH_PASSWORD", raising=False)
    monkeypatch.setattr(search.settings, "OPENSEARCH_URL", "http://localhost:9200")

    with pytest.raises(ValueError):
        search.get_opensearch_client()


@pytest.mark.unit
def test_search_documents_match_all_and_date_filters(monkeypatch):
    client = DummyClient()
    monkeypatch.setattr(search, "get_opensearch_client", lambda: client)

    results = search.search_documents(q=None, date_from=datetime(2024, 1, 1), date_to=datetime(2024, 1, 2))
    assert results["total"] == 2
    assert client.search_calls


@pytest.mark.unit
def test_search_rag_chunks_vector_path(monkeypatch):
    client = DummyClient()
    monkeypatch.setattr(search, "get_opensearch_client", lambda: client)

    class DummyProvider:
        available = True

        def embed_query(self, q):
            return [0.1, 0.2]

    monkeypatch.setattr(search, "get_embedding_provider", lambda: DummyProvider())

    # Fake different responses for bm25 vs vector search
    def fake_search(index, body):
        if "knn" in str(body):
            return {
                "hits": {
                    "hits": [
                        {"_id": "v1", "_score": 2.0, "_source": {"celex": "V"}},
                    ]
                }
            }
        return {
            "hits": {
                "hits": [
                    {"_id": "b1", "_score": 1.0, "_source": {"celex": "B"}},
                ]
            }
        }

    client.search = fake_search

    results = search.search_rag_chunks("query", size=1, alpha=0.5)
    assert results["total"] == 1


@pytest.mark.unit
def test_search_rag_chunks_vector_failure(monkeypatch):
    client = DummyClient()
    monkeypatch.setattr(search, "get_opensearch_client", lambda: client)

    class DummyProvider:
        available = True

        def embed_query(self, q):
            return [0.1, 0.2]

    monkeypatch.setattr(search, "get_embedding_provider", lambda: DummyProvider())

    def fake_search(index, body):
        if "knn" in str(body):
            raise RuntimeError("vector fail")
        return {
            "hits": {
                "hits": [
                    {"_id": "b1", "_score": 1.0, "_source": {"celex": "B"}},
                ]
            }
        }

    client.search = fake_search

    results = search.search_rag_chunks("query", size=1, alpha=0.5)
    assert results["total"] == 1
