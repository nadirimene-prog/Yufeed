import sys
import types

import pytest

import src.ai.embeddings as embeddings_module
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


@pytest.mark.unit
def test_embedding_provider_reuses_loaded_model(monkeypatch):
    class FakeEncoded:
        def __init__(self, data):
            self._data = data

        def tolist(self):
            return self._data

    class FakeSentenceTransformer:
        init_calls = 0

        def __init__(self, model_name, **kwargs):
            self.model_name = model_name
            self.kwargs = kwargs
            FakeSentenceTransformer.init_calls += 1

        def get_sentence_embedding_dimension(self):
            return 3

        def encode(self, texts, **kwargs):
            return FakeEncoded([[0.1, 0.2, 0.3] for _ in texts])

    monkeypatch.setenv("RAG_EMBEDDING_PROVIDER", "sentence_transformers")
    monkeypatch.setenv("RAG_EMBEDDING_MODEL", "test/fake-model")
    monkeypatch.setenv("RAG_ALLOW_EMBEDDING_DOWNLOAD", "1")
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer),
    )
    embeddings_module._MODEL_CACHE.clear()

    provider_one = EmbeddingProvider()
    provider_two = EmbeddingProvider()

    assert provider_one.available is True
    assert provider_two.available is True
    assert FakeSentenceTransformer.init_calls == 1
    assert provider_two.embed_query("hello") == [0.1, 0.2, 0.3]
