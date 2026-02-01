from types import SimpleNamespace

from src.ai.rag_indexer import RAGIndexer
from src.config import settings
from src.models.models import LegalDocument
from src.models.rag_models import LegalChunk


class DummyEmbeddingProvider:
    available = False
    dimension = 8

    def embed_texts(self, texts):
        return None


class DummyOpenSearchClient:
    def __init__(self):
        self.indexed = []

    def index(self, index, id, body):
        self.indexed.append((index, id))


def test_index_idempotency(db_session, monkeypatch):
    # Avoid touching OpenSearch during unit tests
    dummy_client = DummyOpenSearchClient()
    monkeypatch.setattr("src.ai.rag_indexer.get_opensearch_client", lambda: dummy_client)
    monkeypatch.setattr("src.ai.rag_indexer.init_rag_index", lambda embedding_dim: None)

    settings.RAG_INDEX_ENABLED = True
    settings.RAG_CHUNK_SIZE = 50
    settings.RAG_CHUNK_OVERLAP = 0

    doc = LegalDocument(celex="TEST:INDEX", title="Index Doc", full_text="A" * 120)
    db_session.add(doc)
    db_session.commit()

    indexer = RAGIndexer(db_session, embedding_provider=DummyEmbeddingProvider())
    count_first = indexer.index_document(doc)
    count_second = indexer.index_document(doc)

    assert count_first == count_second
    assert db_session.query(LegalChunk).filter(LegalChunk.doc_id == doc.id).count() == count_first
