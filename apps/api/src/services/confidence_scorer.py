"""
AI Analysis Confidence Scoring
Prevents low-quality obligations from being created.
"""

from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class AnalysisConfidence:
    score: float  # 0.0 - 1.0
    quality_tier: str  # high, medium, low
    factors: Dict[str, float]
    recommendation: str


class ConfidenceScorer:
    """Scores document analysis quality."""

    HIGH_CONFIDENCE = 0.70
    MEDIUM_CONFIDENCE = 0.45

    def __init__(self):
        self.factors = {
            "has_full_text": 0.30,
            "has_article_breakdown": 0.20,
            "used_llm_analysis": 0.25,
            "content_word_count": 0.15,
            "has_key_sections": 0.10,
        }

    def calculate_confidence(
        self, full_text: Optional[str], articles: Optional[Dict], analysis_method: str = "llm"
    ) -> AnalysisConfidence:
        """Calculate confidence score for document analysis."""
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
        else:
            factors["used_llm_analysis"] = self.factors["used_llm_analysis"] * 0.5

        # Factor 4: Content word count
        if word_count > 5000:
            factors["content_word_count"] = self.factors["content_word_count"]
        elif word_count > 1000:
            factors["content_word_count"] = self.factors["content_word_count"] * 0.7
        else:
            factors["content_word_count"] = self.factors["content_word_count"] * 0.3

        # Factor 5: Has key sections
        if full_text:
            key_terms = ["obligation", "require", "shall", "must", "article"]
            key_term_count = sum(1 for term in key_terms if term.lower() in full_text.lower())
            factors["has_key_sections"] = (
                min(key_term_count / len(key_terms), 1.0) * self.factors["has_key_sections"]
            )
        else:
            factors["has_key_sections"] = 0.0

        total_score = sum(factors.values())

        if total_score >= self.HIGH_CONFIDENCE:
            quality_tier = "high"
            recommendation = "Auto-create obligations"
        elif total_score >= self.MEDIUM_CONFIDENCE:
            quality_tier = "medium"
            recommendation = "Create obligations with review flag"
        else:
            quality_tier = "low"
            recommendation = "Queue for manual review - insufficient content"

        return AnalysisConfidence(
            score=round(total_score, 3),
            quality_tier=quality_tier,
            factors=factors,
            recommendation=recommendation,
        )

    def should_auto_create_obligations(self, confidence: AnalysisConfidence) -> bool:
        return confidence.quality_tier in ["high", "medium"]
