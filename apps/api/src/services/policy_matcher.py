"""Semantic policy matcher for obligation -> policy suggestions."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.ai.embeddings import EmbeddingProvider
from src.config import settings
from src.models.compliance_workflow import PolicyDocument, RegulatoryObligation

logger = logging.getLogger(__name__)


_POLICY_EMBED_CACHE: Dict[int, Dict[str, Any]] = {}


def _dot_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    return float(sum((a * b for a, b in zip(vec_a, vec_b))))


class PolicyMatcher:
    """Suggest the most relevant policy documents for an obligation."""

    def __init__(self, db: Session):
        self.db = db
        self.embedding_provider = EmbeddingProvider()

    def suggest_policies(self, obligation: RegulatoryObligation, limit: int = 3) -> List[dict]:
        text = " ".join(
            [
                obligation.obligation_text or "",
                obligation.article_ref or "",
                obligation.applicability or "",
                obligation.celex or "",
            ]
        ).strip()
        if not text:
            return []

        policies = self._candidate_policies()
        if not policies:
            return []

        semantic = self._semantic_suggestions(text, policies, limit=limit)
        if semantic:
            return semantic
        return self._keyword_suggestions(text, policies, limit=limit)

    def _candidate_policies(self) -> List[PolicyDocument]:
        return (
            self.db.query(PolicyDocument)
            .filter(PolicyDocument.status.in_(["active", "approved", "draft", "in_review"]))
            .order_by(PolicyDocument.updated_at.desc())
            .all()
        )

    def _policy_context(self, policy: PolicyDocument) -> str:
        metadata = policy.metadata_json if isinstance(policy.metadata_json, dict) else {}
        category = metadata.get("category") if isinstance(metadata, dict) else None
        return " ".join(
            [policy.policy_id or "", policy.name or "", str(category or ""), policy.content or ""]
        )

    def _semantic_suggestions(
        self,
        obligation_text: str,
        policies: List[PolicyDocument],
        *,
        limit: int,
    ) -> List[dict]:
        if not settings.FEATURE_SEMANTIC_POLICY_MATCHING:
            return []
        if not self.embedding_provider.available:
            return []

        query_vec = self._embed_text(obligation_text)
        if not query_vec:
            return []

        scored: List[dict] = []
        for policy in policies:
            policy_vec = self._cached_policy_embedding(policy)
            if not policy_vec:
                continue
            similarity = max(0.0, min(1.0, _dot_similarity(query_vec, policy_vec)))
            scored.append(
                {
                    "policy_document_id": policy.id,
                    "policy_id": policy.policy_id,
                    "name": policy.name,
                    "category": (
                        (policy.metadata_json or {}).get("category")
                        if isinstance(policy.metadata_json, dict)
                        else None
                    ),
                    "score": round(similarity, 4),
                    "confidence": round(similarity, 4),
                    "reasoning": "Embedding cosine similarity on obligation/policy context",
                    "match_method": "semantic",
                }
            )

        if not scored:
            return []

        scored.sort(key=lambda item: item["confidence"], reverse=True)
        top = scored[: max(limit, 3)]
        refined = self._llm_refine(obligation_text, top)
        if refined:
            refined.sort(key=lambda item: item["confidence"], reverse=True)
            return refined[:limit]
        return top[:limit]

    def _cached_policy_embedding(self, policy: PolicyDocument) -> Optional[List[float]]:
        updated_at = policy.updated_at.isoformat() if policy.updated_at else ""
        cached = _POLICY_EMBED_CACHE.get(policy.id)
        if cached and cached.get("updated_at") == updated_at:
            return cached.get("embedding")

        text = self._policy_context(policy)
        embedding = self._embed_text(text)
        if not embedding:
            return None
        _POLICY_EMBED_CACHE[policy.id] = {"updated_at": updated_at, "embedding": embedding}
        return embedding

    def _embed_text(self, text: str) -> Optional[List[float]]:
        """Compatibility seam used by tests to force keyword fallback."""
        return self.embedding_provider.embed_query(text)

    def invalidate_policy_cache(self, policy_id: int) -> None:
        _POLICY_EMBED_CACHE.pop(policy_id, None)

    def _llm_refine(self, obligation_text: str, suggestions: List[dict]) -> List[dict]:
        if not settings.POLICY_MATCH_ENABLE_LLM_REFINEMENT:
            return suggestions
        if not settings.ANTHROPIC_API_KEY:
            return suggestions

        try:
            from anthropic import Anthropic  # type: ignore

            client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        except Exception as exc:
            logger.debug("Policy matcher LLM client unavailable: %s", exc)
            return suggestions

        compact = [
            {
                "policy_document_id": s["policy_document_id"],
                "policy_id": s["policy_id"],
                "name": s["name"],
                "semantic_score": s["confidence"],
            }
            for s in suggestions[:3]
        ]
        prompt = (
            "Tu es un assistant compliance. Choisis la meilleure policy pour cette obligation, "
            'retourne JSON: {"items":[{"policy_document_id":int,"confidence":0..1,'
            '"reasoning":"..."}]}.\n'
            f"Obligation:\n{obligation_text}\n"
            f"Candidates:\n{json.dumps(compact, ensure_ascii=False)}"
        )
        try:
            msg = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=300,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text if msg.content else ""
            parsed = self._extract_json(text)
            items = parsed.get("items") if isinstance(parsed, dict) else None
            if not isinstance(items, list):
                return suggestions

            by_id = {int(s["policy_document_id"]): dict(s) for s in suggestions}
            refined: List[dict] = []
            for item in items:
                if not isinstance(item, dict):
                    continue
                policy_pk = item.get("policy_document_id")
                if not isinstance(policy_pk, int) or policy_pk not in by_id:
                    continue
                base = dict(by_id[policy_pk])
                confidence = item.get("confidence")
                if isinstance(confidence, (int, float)):
                    base["confidence"] = max(0.0, min(1.0, float(confidence)))
                    base["score"] = round(base["confidence"], 4)
                reasoning = item.get("reasoning")
                if isinstance(reasoning, str) and reasoning.strip():
                    base["reasoning"] = reasoning.strip()
                refined.append(base)
            return refined or suggestions
        except Exception as exc:
            logger.debug("Policy matcher LLM refinement failed: %s", exc)
            return suggestions

    def _extract_json(self, text: str) -> Dict[str, Any]:
        if not text:
            return {}
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
            text = re.sub(r"```$", "", text).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return {}
        try:
            return json.loads(text[start : end + 1])
        except Exception:
            return {}

    def _keyword_suggestions(
        self,
        obligation_text: str,
        policies: List[PolicyDocument],
        *,
        limit: int,
    ) -> List[dict]:
        haystack = obligation_text.lower()
        scored: List[dict] = []
        for policy in policies:
            context = self._policy_context(policy).lower()
            score = 0
            for keyword in ["aml", "cft", "kyc", "payment", "crypto", "risk", "dora"]:
                if keyword in haystack and keyword in context:
                    score += 1
            if score <= 0:
                continue
            confidence = min(1.0, 0.2 + (score * 0.15))
            scored.append(
                {
                    "policy_document_id": policy.id,
                    "policy_id": policy.policy_id,
                    "name": policy.name,
                    "category": (
                        (policy.metadata_json or {}).get("category")
                        if isinstance(policy.metadata_json, dict)
                        else None
                    ),
                    "score": score,
                    "confidence": round(confidence, 4),
                    "reasoning": "Keyword overlap fallback",
                    "match_method": "keyword",
                }
            )

        scored.sort(key=lambda item: item["confidence"], reverse=True)
        return scored[:limit]
