import pytest
import asyncio
from datetime import datetime, timezone

from src.ai.rag_service import RAGService, MAX_QUERY_LENGTH
from src.models.models import LegalDocument


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_service_fallback_answer(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    doc = LegalDocument(
        celex="32024R1111",
        title="AML Regulation",
        jurisdiction="EU",
        source_system="eur-lex",
        publication_date=datetime.now(timezone.utc),
    )
    db_session.add(doc)
    db_session.commit()

    service = RAGService(db_session)

    chunks = [
        {
            "celex": doc.celex,
            "title": doc.title,
            "chunk_text": "Summary text",
            "score": 5.0,
        }
    ]

    answer = service._fallback_answer("What is AML?", chunks)
    assert "Demo Mode" in answer["answer"] or "fallback" in answer["model"]


@pytest.mark.unit
def test_rag_service_sanitize_query():
    service = RAGService(None)

    with pytest.raises(ValueError):
        service._sanitize_query(123)

    with pytest.raises(ValueError):
        service._sanitize_query("   ")

    too_long = "x" * (MAX_QUERY_LENGTH + 1)
    with pytest.raises(ValueError):
        service._sanitize_query(too_long)

    assert service._sanitize_query(" ok ") == "ok"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_service_answer_query_with_stubbed_retrieval(db_session, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    service = RAGService(db_session)

    async def fake_retrieve_chunks(*args, **kwargs):
        return [
            {
                "celex": "32024R2222",
                "title": "Regulation",
                "chunk_text": "A short excerpt",
                "score": 3.0,
                "publication_date": datetime.now(timezone.utc),
            }
        ]

    monkeypatch.setattr(service, "_retrieve_chunks", fake_retrieve_chunks)

    result = await service.answer_query("What is regulation?", db=db_session)
    assert result["document_count"] == 1
    assert result["sources"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_rag_service_retrieve_chunks_fallback(monkeypatch, db_session):
    service = RAGService(db_session)

    # Stub search functions
    import src.search as search

    monkeypatch.setattr(search, "search_rag_chunks", lambda **kwargs: {"results": []})
    monkeypatch.setattr(
        search,
        "search_documents",
        lambda **kwargs: {
            "results": [
                {
                    "celex": "32024R3333",
                    "title": "Fallback Regulation",
                    "score": 2.0,
                }
            ]
        },
    )

    # Make to_thread run inline to simplify
    async def inline_to_thread(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", inline_to_thread)

    chunks = await service._retrieve_chunks("question", db_session, max_documents=2, filters=None)
    assert chunks
