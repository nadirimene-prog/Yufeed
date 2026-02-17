"""
Obligation Deduplication Service
Prevents duplicate obligations from being created.
"""

import re
import hashlib
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class DuplicateMatch:
    existing_id: int
    similarity: float
    match_type: str
    existing_text: str
    new_text: str


class ObligationDeduplicator:
    """Detects and prevents duplicate obligations."""

    EXACT_THRESHOLD = 1.0
    SEMANTIC_THRESHOLD = 0.85
    FUZZY_THRESHOLD = 0.70

    def normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        text = text.lower()
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\d+", "#", text)
        return text.strip()

    def compute_exact_hash(self, text: str) -> str:
        """Compute hash for exact matching."""
        normalized = self.normalize_text(text)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def compute_signature(self, text: str) -> set:
        """Compute word signature for fuzzy matching."""
        normalized = self.normalize_text(text)
        words = set(normalized.split())
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "of",
            "for",
            "with",
        }
        return words - stop_words

    def jaccard_similarity(self, set1: set, set2: set) -> float:
        """Compute Jaccard similarity."""
        if not set1 and not set2:
            return 1.0
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    def find_duplicate(
        self, new_text: str, existing_obligations: List[Tuple[int, str]]
    ) -> Optional[DuplicateMatch]:
        """Check if new obligation is a duplicate."""
        new_text_normalized = self.normalize_text(new_text)
        new_hash = self.compute_exact_hash(new_text)
        new_signature = self.compute_signature(new_text)

        for existing_id, existing_text in existing_obligations:
            existing_hash = self.compute_exact_hash(existing_text)

            # Exact match
            if new_hash == existing_hash:
                return DuplicateMatch(
                    existing_id=existing_id,
                    similarity=1.0,
                    match_type="exact",
                    existing_text=existing_text[:200],
                    new_text=new_text[:200],
                )

            # Semantic similarity
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

            # Fuzzy match
            if similarity >= self.FUZZY_THRESHOLD:
                return DuplicateMatch(
                    existing_id=existing_id,
                    similarity=similarity,
                    match_type="fuzzy",
                    existing_text=existing_text[:200],
                    new_text=new_text[:200],
                )

        return None

    def find_duplicates_in_batch(self, obligations: List[str]) -> List[Tuple[int, int, float]]:
        """Find duplicates within a batch of new obligations."""
        duplicates = []

        for i in range(len(obligations)):
            for j in range(i + 1, len(obligations)):
                sig1 = self.compute_signature(obligations[i])
                sig2 = self.compute_signature(obligations[j])
                similarity = self.jaccard_similarity(sig1, sig2)

                if similarity >= self.FUZZY_THRESHOLD:
                    duplicates.append((i, j, similarity))

        return duplicates


# Global instance
deduplicator = ObligationDeduplicator()
