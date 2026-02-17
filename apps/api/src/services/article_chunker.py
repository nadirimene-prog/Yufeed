"""
Article-Level RAG Chunker
Creates chunks at article level for better search precision.
"""

import re
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class ArticleChunk:
    chunk_id: str
    celex: str
    article_number: str
    article_title: str
    content: str
    word_count: int
    content_hash: str
    doc_id: Optional[int] = None


class ArticleChunker:
    """Create RAG chunks at article level."""

    MAX_CHUNK_SIZE = 4000
    OVERLAP = 200

    def __init__(self):
        self.article_pattern = re.compile(
            r"(Article\s+(\d+[\w\.]*)[.:]?\s*([^\n]*))", re.IGNORECASE
        )

    def chunk_document(
        self, doc_id: int, celex: str, full_text: str, article_breakdown: Optional[Dict] = None
    ) -> List[ArticleChunk]:
        """Create article-level chunks from document."""
        chunks = []

        if article_breakdown and isinstance(article_breakdown, dict):
            articles = article_breakdown.get("articles", article_breakdown)
            if isinstance(articles, dict):
                for article_num, article_text in articles.items():
                    chunk = self._create_chunk(doc_id, celex, article_num, article_text)
                    chunks.append(chunk)
            elif isinstance(articles, list):
                for i, article_text in enumerate(articles):
                    chunk = self._create_chunk(doc_id, celex, str(i + 1), article_text)
                    chunks.append(chunk)
        else:
            chunks = self._parse_from_text(doc_id, celex, full_text)

        # Split oversized articles
        final_chunks = []
        for chunk in chunks:
            if chunk.word_count > self.MAX_CHUNK_SIZE:
                final_chunks.extend(self._split_large_article(chunk))
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _create_chunk(
        self, doc_id: int, celex: str, article_num: str, article_text: str
    ) -> ArticleChunk:
        """Create a single article chunk."""
        lines = article_text.split("\n")
        article_title = ""

        for line in lines[1:3]:
            if line.strip():
                article_title = line.strip()[:200]
                break

        content_hash = hashlib.sha256(article_text.encode()).hexdigest()[:16]

        return ArticleChunk(
            chunk_id=f"{celex}_art_{article_num}",
            celex=celex,
            article_number=str(article_num),
            article_title=article_title,
            content=article_text,
            word_count=len(article_text.split()),
            content_hash=content_hash,
            doc_id=doc_id,
        )

    def _parse_from_text(self, doc_id: int, celex: str, full_text: str) -> List[ArticleChunk]:
        """Parse articles from unstructured text."""
        chunks = []
        matches = list(self.article_pattern.finditer(full_text))

        if not matches:
            # No article markers - treat as one chunk
            return [self._create_chunk(doc_id, celex, "FULL", full_text)]

        for i, match in enumerate(matches):
            article_num = match.group(2)
            article_title = (match.group(3) or "").strip()

            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

            article_text = full_text[start:end].strip()
            content_hash = hashlib.sha256(article_text.encode()).hexdigest()[:16]

            chunks.append(
                ArticleChunk(
                    chunk_id=f"{celex}_art_{article_num}",
                    celex=celex,
                    article_number=article_num,
                    article_title=article_title,
                    content=article_text,
                    word_count=len(article_text.split()),
                    content_hash=content_hash,
                    doc_id=doc_id,
                )
            )

        return chunks

    def _split_large_article(self, chunk: ArticleChunk) -> List[ArticleChunk]:
        """Split an oversized article into parts."""
        chunks = []
        words = chunk.content.split()

        part_num = 1
        start = 0

        while start < len(words):
            end = min(start + self.MAX_CHUNK_SIZE, len(words))

            # Find sentence boundary
            if end < len(words):
                text_so_far = " ".join(words[start:end])
                last_period = text_so_far.rfind(". ")
                if last_period > len(text_so_far) * 0.8:
                    end = start + len(text_so_far[:last_period].split()) + 1

            chunk_text = " ".join(words[start:end])
            content_hash = hashlib.sha256(chunk_text.encode()).hexdigest()[:16]

            chunks.append(
                ArticleChunk(
                    chunk_id=f"{chunk.celex}_art_{chunk.article_number}_p{part_num}",
                    celex=chunk.celex,
                    article_number=f"{chunk.article_number}.{part_num}",
                    article_title=(
                        f"{chunk.article_title} (Part {part_num})"
                        if chunk.article_title
                        else f"Part {part_num}"
                    ),
                    content=chunk_text,
                    word_count=len(chunk_text.split()),
                    content_hash=content_hash,
                    doc_id=chunk.doc_id,
                )
            )

            start = end - self.OVERLAP
            part_num += 1

        return chunks


# Global instance
chunker = ArticleChunker()
