"""
Chunking utilities for legal documents.
"""
from typing import Dict, Iterable, List, Optional
import re

from src.models.models import LegalDocument
from src.config import settings


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def split_text(text: str, max_chars: int, overlap: int) -> List[str]:
    """Split text into overlapping character chunks."""
    cleaned = _normalize_whitespace(text)
    if not cleaned:
        return []

    chunks: List[str] = []
    start = 0
    length = len(cleaned)
    while start < length:
        end = min(length, start + max_chars)
        chunk = cleaned[start:end]
        if chunk:
            chunks.append(chunk)
        if end >= length:
            break
        start = max(0, end - overlap)
    return chunks


def _extract_articles(article_breakdown: object) -> List[Dict[str, str]]:
    """Extract article sections from structured breakdown."""
    if not article_breakdown:
        return []

    articles = []
    if isinstance(article_breakdown, dict):
        candidates = article_breakdown.get("articles") or article_breakdown.get("content") or []
    elif isinstance(article_breakdown, list):
        candidates = article_breakdown
    else:
        return []

    for entry in candidates:
        if not isinstance(entry, dict):
            continue
        text = (
            entry.get("text")
            or entry.get("content")
            or entry.get("body")
            or entry.get("paragraphs")
        )
        if isinstance(text, list):
            text = "\n".join([str(t) for t in text])
        if not text:
            continue
        articles.append(
            {
                "title": entry.get("title") or entry.get("heading"),
                "article_ref": entry.get("article") or entry.get("number"),
                "text": str(text),
            }
        )

    return articles


def chunk_document(
    document: LegalDocument,
    max_chars: Optional[int] = None,
    overlap: Optional[int] = None,
) -> Iterable[Dict[str, object]]:
    """Yield chunk dicts for a legal document."""
    max_chars = max_chars or settings.RAG_CHUNK_SIZE
    overlap = overlap or settings.RAG_CHUNK_OVERLAP

    sections: List[Dict[str, Optional[str]]] = []
    articles = _extract_articles(document.article_breakdown)
    if articles:
        for article in articles:
            sections.append(
                {
                    "section_title": article.get("title"),
                    "article_ref": article.get("article_ref"),
                    "text": article.get("text"),
                }
            )
    elif document.full_text:
        sections.append(
            {
                "section_title": None,
                "article_ref": None,
                "text": document.full_text,
            }
        )

    chunk_index = 0
    for section in sections:
        text = section.get("text") or ""
        for part in split_text(text, max_chars, overlap):
            yield {
                "chunk_index": chunk_index,
                "section_title": section.get("section_title"),
                "article_ref": section.get("article_ref"),
                "text": part,
            }
            chunk_index += 1

