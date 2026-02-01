import pytest

from src.ai.embeddings import EmbeddingProvider


@pytest.mark.unit
def test_embeddings_disabled(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "disabled")
    provider = EmbeddingProvider()
    assert provider.available is False
    assert provider.embed_texts(["hello"]) is None


@pytest.mark.unit
def test_embeddings_unknown_provider(monkeypatch):
    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "unknown")
    provider = EmbeddingProvider()
    assert provider.available is False
    assert provider.embed_query("query") is None
