#!/usr/bin/env python3
"""
Obligation Deduplication Service
- Prevents duplicate obligations from being created
- Uses semantic similarity detection
"""

import sys
import re
import hashlib
from typing import List, Tuple, Optional
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class DuplicateMatch:
    existing_id: int
    similarity: float
    match_type: str  # exact, semantic, fuzzy
    existing_text: str
    new_text: str


class ObligationDeduplicator:
    """
    Detects and prevents duplicate obligations using multiple methods.
    """

    # Similarity thresholds
    EXACT_THRESHOLD = 1.0
    SEMANTIC_THRESHOLD = 0.85
    FUZZY_THRESHOLD = 0.70

    def __init__(self):
        # Simple word-based hashing for exact matches
        self.exact_hashes = set()
        # Would use embeddings in production
        self.text_signatures = {}

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        # Lowercase, remove extra whitespace, normalize numbers
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\d+", "#", text)  # Normalize numbers
        text = text.strip()
        return text

    def compute_exact_hash(self, text: str) -> str:
        """Compute hash for exact matching."""
        normalized = self.normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def compute_signature(self, text: str) -> set:
        """Compute word signature for fuzzy matching."""
        normalized = self.normalize_text(text)
        words = set(normalized.split())
        # Remove common stop words
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "of"}
        return words - stop_words

    def jaccard_similarity(self, set1: set, set2: set) -> float:
        """Compute Jaccard similarity between two sets."""
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def check_duplicate(
        self, new_text: str, existing_obligations: List[Tuple[int, str]]
    ) -> Optional[DuplicateMatch]:
        """
        Check if new obligation is a duplicate of existing ones.

        Returns DuplicateMatch if duplicate found, None otherwise.
        """
        new_text_normalized = self.normalize_text(new_text)
        new_hash = self.compute_exact_hash(new_text)
        new_signature = self.compute_signature(new_text)

        # Check exact match
        for existing_id, existing_text in existing_obligations:
            existing_hash = self.compute_exact_hash(existing_text)

            if new_hash == existing_hash:
                return DuplicateMatch(
                    existing_id=existing_id,
                    similarity=1.0,
                    match_type="exact",
                    existing_text=existing_text[:200],
                    new_text=new_text[:200],
                )

            # Check semantic similarity (using simple set overlap for now)
            existing_signature = self.compute_signature(existing_text)
            similarity = self.jaccard_similarity(new_signature, existing_signature)

            if similarity >= self.SEMANTIC_THRESHOLD:
                return DuplicateMatch(
                    existing_id=existing_id,
                    similarity=similarity,
                    match_type="semantic",
                    existing_text=existing_text[:200],
                    new_text=new_text[:200],
                )

            # Check fuzzy similarity
            if similarity >= self.FUZZY_THRESHOLD:
                return DuplicateMatch(
                    existing_id=existing_id,
                    similarity=similarity,
                    match_type="fuzzy",
                    existing_text=existing_text[:200],
                    new_text=new_text[:200],
                )

        return None

    def find_duplicates_batch(self, obligations: List[str]) -> List[Tuple[int, int, float]]:
        """
        Find duplicates within a batch of new obligations.

        Returns list of (index1, index2, similarity) tuples.
        """
        duplicates = []

        for i in range(len(obligations)):
            for j in range(i + 1, len(obligations)):
                sig1 = self.compute_signature(obligations[i])
                sig2 = self.compute_signature(obligations[j])
                similarity = self.jaccard_similarity(sig1, sig2)

                if similarity >= self.FUZZY_THRESHOLD:
                    duplicates.append((i, j, similarity))

        return duplicates


def test_deduplication():
    """Test deduplication with sample obligations."""

    # Sample obligations (some duplicates)
    obligations = [
        (
            1,
            "Crypto-asset service providers must maintain own funds equal to at least 2% of the funds they hold for clients.",
        ),
        (
            2,
            "CASPs must hold own funds of at least 2% of the funds held on behalf of clients.",
        ),  # Semantic dup
        (3, "Issuers of asset-referenced tokens must publish a white paper."),
        (4, "ART issuers must publish a white paper for each token."),  # Semantic dup
        (5, "Market abuse regulations apply to all crypto-asset transactions."),
        (
            6,
            "Crypto-asset service providers must maintain own funds equal to at least 2% of the funds they hold for clients.",
        ),  # Exact dup
    ]

    dedup = ObligationDeduplicator()

    print("\n" + "=" * 70)
    print("OBLIGATION DEDUPLICATION - TEST RESULTS")
    print("=" * 70)

    # Test new obligation against existing
    new_obligation = "Crypto asset service providers must hold own funds equal to at least 2 percent of client funds."

    match = dedup.check_duplicate(new_obligation, obligations)

    if match:
        print(f"\n🔍 Duplicate found for new obligation:")
        print(f"   New: {new_obligation[:100]}...")
        print(f"   Match: ID {match.existing_id} ({match.match_type}, {match.similarity:.2%})")
        print(f"   Existing: {match.existing_text[:100]}...")
    else:
        print("\n✅ No duplicate found")

    # Test batch deduplication
    new_batch = [
        "Issuers must maintain a reserve of assets.",
        "Token issuers must maintain asset reserves.",
        "Completely unique requirement about something else.",
        "Issuers must maintain a reserve of assets.",  # Exact dup within batch
    ]

    dups = dedup.find_duplicates_batch(new_batch)

    print(f"\n📦 Batch duplicates found: {len(dups)}")
    for i, j, sim in dups:
        print(f"   Items {i} and {j}: {sim:.2%} similarity")
        print(f"     A: {new_batch[i][:80]}...")
        print(f"     B: {new_batch[j][:80]}...")

    print("\n" + "=" * 70)
    print("DEDUPLICATION WORKING: ✅" if match else "DEDUPLICATION NOT WORKING: ❌")
    print("=" * 70)

    return match is not None


def main():
    success = test_deduplication()

    print("\n📊 DEDUPLICATION THRESHOLDS")
    print("=" * 70)
    print(
        """
Matching Levels:
  EXACT (100%):    Hash match after normalization
  SEMANTIC (85%+): High word overlap, same meaning
  FUZZY (70%+):    Similar wording, possible duplicate
  UNIQUE (<70%):   Considered unique

Benefits:
  ✓ Prevents duplicate work in compliance review
  ✓ Reduces database bloat
  ✓ Improves obligation search quality
  ✓ Reduces confusion from duplicate requirements

Production Implementation:
  - Use sentence-transformers for embeddings
  - Use FAISS or pgvector for similarity search
  - Add pre-computed embeddings to obligations table
"""
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
