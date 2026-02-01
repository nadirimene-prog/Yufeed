import pytest
from types import SimpleNamespace

from src.ai import rag_chunker


@pytest.mark.unit
def test_split_text_with_overlap():
    text = "A" * 50
    chunks = rag_chunker.split_text(text, max_chars=20, overlap=5)
    assert chunks
    assert chunks[0] == "A" * 20
    assert chunks[1].startswith("A" * 5)


@pytest.mark.unit
def test_extract_articles():
    breakdown = {
        "articles": [
            {"title": "Art 1", "article": "1", "text": "Some content"},
            {"heading": "Art 2", "number": "2", "content": ["Line 1", "Line 2"]},
        ]
    }
    articles = rag_chunker._extract_articles(breakdown)
    assert len(articles) == 2
    assert articles[0]["article_ref"] == "1"


@pytest.mark.unit
def test_chunk_document_from_articles(monkeypatch):
    monkeypatch.setattr(rag_chunker.settings, "RAG_CHUNK_SIZE", 10)
    monkeypatch.setattr(rag_chunker.settings, "RAG_CHUNK_OVERLAP", 2)

    doc = SimpleNamespace(
        article_breakdown={
            "articles": [
                {"title": "Art 1", "article": "1", "text": "ABCDEFGHIJKL"},
            ]
        },
        full_text=None,
    )

    chunks = list(rag_chunker.chunk_document(doc))
    assert chunks
    assert chunks[0]["article_ref"] == "1"


@pytest.mark.unit
def test_chunk_document_fallback_full_text(monkeypatch):
    monkeypatch.setattr(rag_chunker.settings, "RAG_CHUNK_SIZE", 8)
    monkeypatch.setattr(rag_chunker.settings, "RAG_CHUNK_OVERLAP", 1)

    doc = SimpleNamespace(
        article_breakdown=None,
        full_text="Hello world from RAG",
    )

    chunks = list(rag_chunker.chunk_document(doc))
    assert chunks
    assert all("text" in chunk for chunk in chunks)
