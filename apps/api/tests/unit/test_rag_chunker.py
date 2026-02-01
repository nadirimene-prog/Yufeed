from src.ai.rag_chunker import chunk_document, split_text
from src.models.models import LegalDocument


def test_chunk_document_article_aware():
    doc = LegalDocument(celex="TEST:1", title="Test")
    doc.article_breakdown = {
        "articles": [
            {"title": "Article 1", "article": "1", "text": "First text."},
            {"title": "Article 2", "article": "2", "text": "Second text."},
        ]
    }

    chunks = list(chunk_document(doc, max_chars=100, overlap=0))
    assert len(chunks) == 2
    assert {c["article_ref"] for c in chunks} == {"1", "2"}


def test_chunk_overlap_consistency():
    chunks = split_text("abcdefghij", max_chars=6, overlap=2)
    assert len(chunks) == 2
    assert chunks[0][-2:] == chunks[1][:2]
