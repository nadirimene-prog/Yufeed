import pytest
from datetime import datetime, timezone

from src.ai.rag_indexer import RAGIndexer
from src.models.models import LegalDocument
from src.models.rag_models import LegalChunk


class DummyEmbeddingProvider:
    def __init__(self):
        self._available = False
        self._dim = 8

    @property
    def available(self):
        return False

    @property
    def dimension(self):
        return self._dim

    def embed_texts(self, texts):
        return None


class DummyOpenSearchClient:
    def __init__(self):
        self.index_calls = []

    def index(self, index, id, body):
        self.index_calls.append((index, id, body))


@pytest.mark.unit
def test_rag_indexer_index_document(monkeypatch, db_session):
    dummy_client = DummyOpenSearchClient()

    monkeypatch.setattr("src.ai.rag_indexer.get_opensearch_client", lambda: dummy_client)
    monkeypatch.setattr("src.ai.rag_indexer.init_rag_index", lambda embedding_dim: None)

    doc = LegalDocument(
        celex="32024R1234",
        title="RAG Doc",
        jurisdiction="EU",
        source_system="eur-lex",
        primary_language="en",
        publication_date=datetime.now(timezone.utc),
        full_text="Hello world, this is a long document for RAG chunking.",
    )
    db_session.add(doc)
    db_session.commit()

    indexer = RAGIndexer(db_session, embedding_provider=DummyEmbeddingProvider())
    count = indexer.index_document(doc)

    assert count > 0
    assert dummy_client.index_calls
    assert db_session.query(LegalChunk).filter(LegalChunk.doc_id == doc.id).count() == count


@pytest.mark.unit
def test_rag_indexer_index_all_documents(monkeypatch, db_session):
    dummy_client = DummyOpenSearchClient()

    monkeypatch.setattr("src.ai.rag_indexer.get_opensearch_client", lambda: dummy_client)
    monkeypatch.setattr("src.ai.rag_indexer.init_rag_index", lambda embedding_dim: None)

    doc = LegalDocument(
        celex="32024R5678",
        title="RAG Doc 2",
        jurisdiction="EU",
        source_system="eur-lex",
        primary_language="en",
        publication_date=datetime.now(timezone.utc),
        full_text="Another document for indexing.",
    )
    db_session.add(doc)
    db_session.commit()

    indexer = RAGIndexer(db_session, embedding_provider=DummyEmbeddingProvider())
    total = indexer.index_all_documents(limit=1)
    assert total >= 0
