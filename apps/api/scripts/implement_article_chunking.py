#!/usr/bin/env python3
"""
Article-Level RAG Chunking
- Replaces document-level chunking with article-level
- Stores article metadata for better search
"""

import sys
import re
import json
import hashlib
from typing import List, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class ArticleChunk:
    chunk_id: str
    celex: str
    article_number: str
    article_title: str
    content: str
    word_count: int
    content_hash: str
    parent_doc_id: Optional[int] = None


class ArticleChunker:
    """Create RAG chunks at article level instead of document level."""

    MAX_CHUNK_SIZE = 4000  # Words per chunk (articles longer than this get split)
    OVERLAP = 200  # Words overlap between chunks

    def __init__(self):
        self.article_pattern = re.compile(
            r"(Article\s+(\d+[\w\.]*)[.:]?\s*([^\n]*))", re.IGNORECASE
        )

    def chunk_by_articles(
        self, celex: str, full_text: str, article_breakdown: Optional[Dict] = None
    ) -> List[ArticleChunk]:
        """
        Create article-level chunks from document text.
        """
        chunks = []

        if article_breakdown:
            # Use provided article breakdown
            for article_num, article_text in article_breakdown.items():
                chunk = self._create_article_chunk(celex, article_num, article_text)
                chunks.append(chunk)
        else:
            # Parse from full text
            chunks = self._parse_articles_from_text(celex, full_text)

        # Split oversized articles
        final_chunks = []
        for chunk in chunks:
            if chunk.word_count > self.MAX_CHUNK_SIZE:
                sub_chunks = self._split_large_article(chunk)
                final_chunks.extend(sub_chunks)
            else:
                final_chunks.append(chunk)

        return final_chunks

    def _create_article_chunk(
        self, celex: str, article_num: str, article_text: str
    ) -> ArticleChunk:
        """Create a single article chunk."""
        # Extract article title if present
        lines = article_text.split("\n")
        article_title = ""

        if len(lines) > 1:
            # First non-empty line might be the title
            for line in lines[1:]:
                if line.strip():
                    article_title = line.strip()[:200]
                    break

        content_hash = hashlib.sha256(article_text.encode()).hexdigest()[:16]

        return ArticleChunk(
            chunk_id=f"{celex}_art_{article_num}",
            celex=celex,
            article_number=article_num,
            article_title=article_title,
            content=article_text,
            word_count=len(article_text.split()),
            content_hash=content_hash,
        )

    def _parse_articles_from_text(self, celex: str, full_text: str) -> List[ArticleChunk]:
        """Parse articles from unstructured text."""
        chunks = []

        # Find all article markers
        matches = list(self.article_pattern.finditer(full_text))

        if not matches:
            # No article markers found - treat entire text as one chunk
            chunk = self._create_article_chunk(celex, "FULL", full_text)
            chunks.append(chunk)
            return chunks

        # Create chunks for each article
        for i, match in enumerate(matches):
            article_num = match.group(2)
            article_title = match.group(3).strip() if match.group(3) else ""

            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)

            article_text = full_text[start:end].strip()

            chunk = ArticleChunk(
                chunk_id=f"{celex}_art_{article_num}",
                celex=celex,
                article_number=article_num,
                article_title=article_title,
                content=article_text,
                word_count=len(article_text.split()),
                content_hash=hashlib.sha256(article_text.encode()).hexdigest()[:16],
            )
            chunks.append(chunk)

        return chunks

    def _split_large_article(self, chunk: ArticleChunk) -> List[ArticleChunk]:
        """Split an oversized article into multiple chunks."""
        chunks = []
        words = chunk.content.split()

        part_num = 1
        start = 0

        while start < len(words):
            end = min(start + self.MAX_CHUNK_SIZE, len(words))

            # Find sentence boundary if possible
            if end < len(words):
                # Try to end at a sentence
                text_so_far = " ".join(words[start:end])
                last_period = text_so_far.rfind(". ")
                if last_period > len(text_so_far) * 0.8:  # Within last 20%
                    end = start + len(text_so_far[:last_period].split()) + 1

            chunk_text = " ".join(words[start:end])

            sub_chunk = ArticleChunk(
                chunk_id=f"{chunk.celex}_art_{chunk.article_number}_p{part_num}",
                celex=chunk.celex,
                article_number=f"{chunk.article_number}.{part_num}",
                article_title=f"{chunk.article_title} (Part {part_num})",
                content=chunk_text,
                word_count=len(chunk_text.split()),
                content_hash=hashlib.sha256(chunk_text.encode()).hexdigest()[:16],
            )
            chunks.append(sub_chunk)

            start = end - self.OVERLAP
            part_num += 1

        return chunks


def test_article_chunking():
    """Test article chunking with sample data."""

    # Sample document with articles
    sample_text = """
Article 1
Subject matter and scope
1. This Regulation lays down rules on:
(a) the authorisation and supervision of crypto-asset service providers, issuers of asset-referenced tokens and issuers of e-money tokens;
(b) the issuance, offer to the public and admission to trading of crypto-assets;
(c) the provision of services related to crypto-assets.

Article 2
Definitions
For the purposes of this Regulation, the following definitions apply:
(1) 'crypto-asset' means a digital representation of value or rights which may be transferred and stored electronically, using distributed ledger technology or similar technology;
(2) 'distributed ledger technology' or 'DLT' means a technology enabling the operation and use of distributed ledgers;

Article 3
Authorisation
1. No person shall provide crypto-asset services unless that person is authorised in accordance with this Article.
2. An application for authorisation shall be submitted to the competent authority of the Member State where the applicant is established.
"""

    chunker = ArticleChunker()
    chunks = chunker.chunk_by_articles("32023R1114", sample_text)

    print("\n" + "=" * 70)
    print("ARTICLE CHUNKING - TEST RESULTS")
    print("=" * 70)

    print(f"\nCreated {len(chunks)} chunks from sample text")
    print(f"Total words in original: {len(sample_text.split())}")

    for chunk in chunks:
        print(f"\n📄 {chunk.chunk_id}")
        print(f"   Article: {chunk.article_number} - {chunk.article_title[:50]}...")
        print(f"   Words: {chunk.word_count}")
        print(f"   Hash: {chunk.content_hash}")

    # Test with large article
    large_text = "Article 1\nDefinitions\n" + "word " * 5000
    large_chunks = chunker.chunk_by_articles("TEST123", large_text)

    print(f"\n\nLarge article test:")
    print(f"   Original words: 5000+ -> Chunks: {len(large_chunks)}")
    for lc in large_chunks:
        print(f"   - {lc.chunk_id}: {lc.word_count} words")

    # Verify all chunks are under limit
    all_valid = all(c.word_count <= chunker.MAX_CHUNK_SIZE for c in chunks + large_chunks)

    print("\n" + "=" * 70)
    print(f"All chunks under size limit: {'✅ YES' if all_valid else '❌ NO'}")
    print("=" * 70)

    return True


def main():
    success = test_article_chunking()

    print("\n📊 ARTICLE CHUNKING BENEFITS")
    print("=" * 70)
    print(
        """
Advantages over document-level chunking:
  ✓ Better search precision - find specific articles
  ✓ Maintains document structure
  ✓ Easier to reference exact locations
  ✓ Supports article-level obligation mapping
  ✓ Smaller, more focused chunks for RAG
  ✓ Handles large articles by splitting intelligently

Chunk Structure:
  - chunk_id: {celex}_art_{number}[_p{part}]
  - article_number: Article identifier
  - article_title: Section heading
  - content: Full article text
  - content_hash: For change detection
"""
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
