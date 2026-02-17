#!/usr/bin/env python3
"""
AI Analysis Confidence Scoring
- Prevents low-quality obligations from being created
- Uses content quality metrics
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@dataclass
class AnalysisConfidence:
    score: float  # 0.0 - 1.0
    quality_tier: str  # high, medium, low
    factors: Dict[str, float]
    recommendation: str


class ConfidenceScorer:
    """
    Scores document analysis quality to determine if obligations
    should be auto-created or sent for manual review.
    """

    # Thresholds
    HIGH_CONFIDENCE = 0.75
    MEDIUM_CONFIDENCE = 0.50

    def __init__(self):
        self.factors = {
            "has_full_text": 0.30,
            "has_article_breakdown": 0.20,
            "used_llm_analysis": 0.25,
            "content_word_count": 0.15,
            "has_key_sections": 0.10,
        }

    def calculate_confidence(
        self,
        full_text: Optional[str],
        articles: Optional[Dict],
        analysis_method: str,  # "llm", "heuristic", "manual"
        document_title: str,
        document_type: str,
    ) -> AnalysisConfidence:
        """
        Calculate confidence score for document analysis.
        """
        factors = {}

        # Factor 1: Has full text
        text_length = len(full_text) if full_text else 0
        word_count = len(full_text.split()) if full_text else 0
        factors["has_full_text"] = min(text_length / 5000, 1.0) * self.factors["has_full_text"]

        # Factor 2: Has article breakdown
        article_count = len(articles) if articles else 0
        factors["has_article_breakdown"] = (
            1.0 if article_count > 5 else article_count / 5.0
        ) * self.factors["has_article_breakdown"]

        # Factor 3: Analysis method
        if analysis_method == "llm":
            factors["used_llm_analysis"] = self.factors["used_llm_analysis"]
        elif analysis_method == "heuristic":
            factors["used_llm_analysis"] = self.factors["used_llm_analysis"] * 0.5
        else:
            factors["used_llm_analysis"] = 0.0

        # Factor 4: Content word count
        if word_count > 5000:
            factors["content_word_count"] = self.factors["content_word_count"]
        elif word_count > 1000:
            factors["content_word_count"] = self.factors["content_word_count"] * 0.7
        else:
            factors["content_word_count"] = self.factors["content_word_count"] * 0.3

        # Factor 5: Has key sections (definitions, obligations, etc.)
        if full_text:
            key_terms = ["obligation", "require", "shall", "must", "article"]
            key_term_count = sum(1 for term in key_terms if term.lower() in full_text.lower())
            factors["has_key_sections"] = (
                min(key_term_count / len(key_terms), 1.0) * self.factors["has_key_sections"]
            )
        else:
            factors["has_key_sections"] = 0.0

        # Calculate total score
        total_score = sum(factors.values())

        # Determine quality tier
        if total_score >= self.HIGH_CONFIDENCE:
            quality_tier = "high"
            recommendation = "Auto-create obligations"
        elif total_score >= self.MEDIUM_CONFIDENCE:
            quality_tier = "medium"
            recommendation = "Create obligations with review flag"
        else:
            quality_tier = "low"
            recommendation = "Queue for manual review - insufficient content quality"

        return AnalysisConfidence(
            score=round(total_score, 3),
            quality_tier=quality_tier,
            factors=factors,
            recommendation=recommendation,
        )

    def should_auto_create_obligations(self, confidence: AnalysisConfidence) -> bool:
        """Determine if obligations should be auto-created."""
        return confidence.quality_tier in ["high", "medium"]

    def get_review_priority(self, confidence: AnalysisConfidence) -> int:
        """Get review priority (1 = highest)."""
        if confidence.quality_tier == "low":
            return 1
        elif confidence.quality_tier == "medium":
            return 2
        return 3


def test_confidence_scoring():
    """Test confidence scoring with various scenarios."""

    scorer = ConfidenceScorer()

    test_cases = [
        # (description, full_text, articles, method, expected_tier)
        ("Full MiCA with articles", "a" * 50000, {"art1": "text", "art2": "text"}, "llm", "high"),
        ("Medium content, no articles", "a" * 5000, None, "llm", "medium"),
        ("Title only", None, None, "heuristic", "low"),
        ("Short text, heuristic", "a" * 500, None, "heuristic", "low"),
        ("Full text, no articles", "a" * 10000, None, "llm", "medium"),
    ]

    print("\n" + "=" * 70)
    print("CONFIDENCE SCORING - TEST RESULTS")
    print("=" * 70)

    passed = 0

    for description, text, articles, method, expected_tier in test_cases:
        conf = scorer.calculate_confidence(
            full_text=text,
            articles=articles,
            analysis_method=method,
            document_title="Test Document",
            document_type="Regulation",
        )

        correct = conf.quality_tier == expected_tier
        status = "✅ PASS" if correct else "❌ FAIL"

        print(f"\n{status} {description}")
        print(f"   Score: {conf.score:.3f} ({conf.quality_tier})")
        print(f"   Expected: {expected_tier}")
        print(f"   Factors: {conf.factors}")
        print(f"   Recommendation: {conf.recommendation}")

        if correct:
            passed += 1

    total = len(test_cases)
    print("\n" + "=" * 70)
    print(f"SUMMARY: {passed}/{total} tests passed ({100*passed//total}%)")
    print("=" * 70)

    return passed == total


def main():
    success = test_confidence_scoring()

    print("\n📊 CONFIDENCE THRESHOLDS")
    print("=" * 70)
    print(
        f"""
HIGH CONFIDENCE (≥0.75): Auto-create obligations
MEDIUM CONFIDENCE (0.50-0.74): Create with review flag
LOW CONFIDENCE (<0.50): Queue for manual review

Factors:
  - Has full text: up to 0.30
  - Has article breakdown: up to 0.20
  - Used LLM analysis: up to 0.25
  - Content word count: up to 0.15
  - Has key sections: up to 0.10
"""
    )

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
