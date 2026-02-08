"""
AI-powered document analysis for compliance intelligence.
Uses LLM to classify documents, assess risk, and extract obligations.
"""

import json
import logging
import re
import time
import threading
import httpx
from datetime import datetime
from typing import Dict, List, Optional, Any

import anthropic  # Using Claude for legal text analysis

from src.utils.time import utc_now
from src.models.models import ComplianceDomain, RiskLevel
from src.config import settings

# Initialize Anthropic client
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None
ANTHROPIC_DISABLED_REASON: Optional[str] = None
OPENAI_DISABLED_REASON: Optional[str] = None
logger = logging.getLogger(__name__)

_analysis_ctx = threading.local()


def _reset_llm_usage() -> None:
    """Reset per-thread LLM usage markers for the current analysis run."""
    _analysis_ctx.llm_providers = set()


def _mark_llm_usage(provider: str) -> None:
    """Mark that a real LLM response was successfully returned in this thread."""
    providers = getattr(_analysis_ctx, "llm_providers", None)
    if providers is None:
        providers = set()
        _analysis_ctx.llm_providers = providers
    providers.add(provider)


def _llm_providers_used() -> List[str]:
    providers = getattr(_analysis_ctx, "llm_providers", None)
    if not providers:
        return []
    return sorted(providers)


def _llm_was_used() -> bool:
    return bool(getattr(_analysis_ctx, "llm_providers", None))


def _anthropic_enabled() -> bool:
    return client is not None and ANTHROPIC_DISABLED_REASON is None


def _disable_anthropic(reason: str):
    global ANTHROPIC_DISABLED_REASON
    if ANTHROPIC_DISABLED_REASON is None:
        ANTHROPIC_DISABLED_REASON = reason
        logger.warning("Anthropic disabled: %s", reason)


def _openai_enabled() -> bool:
    return bool(settings.OPENAI_API_KEY) and OPENAI_DISABLED_REASON is None


def _disable_openai(reason: str):
    global OPENAI_DISABLED_REASON
    if OPENAI_DISABLED_REASON is None:
        OPENAI_DISABLED_REASON = reason
        logger.warning("OpenAI disabled: %s", reason)


def _is_anthropic_credit_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "credit balance is too low" in msg or ("insufficient" in msg and "credit" in msg)


def _is_anthropic_model_not_found(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "not_found_error" in msg and "model" in msg


def _is_openai_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return (
        "insufficient_quota" in msg
        or "exceeded your current quota" in msg
        or ("quota" in msg and "exceeded" in msg)
    )


def _openai_chat(prompt: str, max_tokens: int, temperature: float = 0.3) -> str:
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise RuntimeError("missing OPENAI_API_KEY")
    base_url = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    model = settings.OPENAI_MODEL or "gpt-4.1"
    retries = max(0, int(getattr(settings, "OPENAI_RETRIES", 2)))
    backoff = max(0.1, float(getattr(settings, "OPENAI_BACKOFF_SECONDS", 2.0)))
    delay = max(0.0, float(getattr(settings, "OPENAI_DELAY_SECONDS", 0.0)))
    timeout_s = max(1.0, float(getattr(settings, "OPENAI_TIMEOUT_SECONDS", 60.0)))
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    last_exc: Optional[Exception] = None
    for attempt in range(retries + 1):
        if delay:
            time.sleep(delay)
        try:
            response = httpx.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout_s,
            )
            if response.status_code == 429 and attempt < retries:
                retry_after = response.headers.get("Retry-After")
                try:
                    sleep_s = float(retry_after) if retry_after else backoff * (2**attempt)
                except ValueError:
                    sleep_s = backoff * (2**attempt)
                time.sleep(sleep_s)
                continue
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            _mark_llm_usage("openai")
            return content
        except Exception as exc:
            last_exc = exc
            if attempt < retries:
                time.sleep(backoff * (2**attempt))
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("OpenAI request failed")


def _classify_heuristic(title: str) -> str:
    title_lower = (title or "").lower()
    if any(kw in title_lower for kw in ["money laundering", "aml", "terrorist financing"]):
        return ComplianceDomain.AML.value
    if any(kw in title_lower for kw in ["crypto", "digital asset", "virtual currency"]):
        return ComplianceDomain.CRYPTO.value
    if any(kw in title_lower for kw in ["payment", "psd", "electronic money"]):
        return ComplianceDomain.PAYMENTS.value
    if any(kw in title_lower for kw in ["sanction", "restrictive measure"]):
        return ComplianceDomain.SANCTIONS.value
    if any(
        kw in title_lower for kw in ["know your customer", "kyc", "customer due diligence", "cdd"]
    ):
        return ComplianceDomain.KYC.value
    if any(kw in title_lower for kw in ["gdpr", "data protection", "privacy"]):
        return ComplianceDomain.GDPR.value
    return ComplianceDomain.OTHER.value


def _risk_heuristic(title: str) -> str:
    title_lower = (title or "").lower()
    if any(
        kw in title_lower for kw in ["aml", "money laundering", "sanction", "terrorist financing"]
    ):
        return RiskLevel.HIGH.value
    if any(kw in title_lower for kw in ["payment", "crypto", "kyc", "cdd"]):
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value


def classify_document(title: str, celex: str) -> Optional[str]:
    """
    Classify document into compliance domain based on title and CELEX.
    Returns: ComplianceDomain value or None
    """
    if _anthropic_enabled():
        try:
            prompt = f"""Classify this EU legal document into ONE compliance domain category.

Document: {celex}
Title: {title}

Categories:
- aml: Anti-Money Laundering
- cft: Counter-Terrorist Financing
- sanctions: Economic Sanctions
- kyc: Know Your Customer
- cdd: Customer Due Diligence
- payments: Payment Services
- crypto: Crypto Assets / Digital Assets
- gdpr: Data Protection / Privacy
- other: Other compliance areas

Respond with ONLY the category code (e.g., "aml", "crypto", "payments")."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",  # Fast and cost-effective
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            _mark_llm_usage("anthropic")

            result = message.content[0].text.strip().lower()
            # Validate result
            valid_domains = [d.value for d in ComplianceDomain]
            return result if result in valid_domains else ComplianceDomain.OTHER.value

        except Exception as e:
            if _is_anthropic_credit_error(e):
                _disable_anthropic("insufficient_credits")
            logger.warning("AI classification error: %s", e)

    if _openai_enabled():
        try:
            prompt = f"""Classify this EU legal document into ONE compliance domain category.

Document: {celex}
Title: {title}

Categories:
- aml: Anti-Money Laundering
- cft: Counter-Terrorist Financing
- sanctions: Economic Sanctions
- kyc: Know Your Customer
- cdd: Customer Due Diligence
- payments: Payment Services
- crypto: Crypto Assets / Digital Assets
- gdpr: Data Protection / Privacy
- other: Other compliance areas

Respond with ONLY the category code (e.g., "aml", "crypto", "payments")."""

            result = _openai_chat(prompt, max_tokens=50, temperature=0.0).strip().lower()
            valid_domains = [d.value for d in ComplianceDomain]
            return result if result in valid_domains else ComplianceDomain.OTHER.value
        except Exception as e:
            if _is_openai_quota_error(e):
                _disable_openai("insufficient_credits")
            logger.warning("OpenAI classification error: %s", e)

    return _classify_heuristic(title)


def assess_risk_level(title: str, celex: str, compliance_domain: Optional[str] = None) -> str:
    """
    Assess the risk level/impact of a regulation for banks.
    Returns: RiskLevel value
    """
    if _anthropic_enabled():
        try:
            prompt = f"""Assess the compliance risk level of this EU regulation for a bank's operations.

Document: {celex}
Title: {title}
Compliance Domain: {compliance_domain or "unknown"}

Consider:
- Direct impact on banking operations
- Penalties for non-compliance
- Implementation complexity
- Regulatory scrutiny level

Risk Levels:
- high: Critical compliance requirement, severe penalties, high regulatory scrutiny
- medium: Important but manageable, moderate impact
- low: Minor impact, informational, or not directly applicable to banks

Respond with ONLY the risk level (high, medium, or low)."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )
            _mark_llm_usage("anthropic")

            result = message.content[0].text.strip().lower()
            valid_levels = [r.value for r in RiskLevel]
            return result if result in valid_levels else RiskLevel.UNKNOWN.value

        except Exception as e:
            if _is_anthropic_credit_error(e):
                _disable_anthropic("insufficient_credits")
            logger.warning("AI risk assessment error: %s", e)

    if _openai_enabled():
        try:
            prompt = f"""Assess the compliance risk level of this EU regulation for a bank's operations.

Document: {celex}
Title: {title}
Compliance Domain: {compliance_domain or "unknown"}

Consider:
- Direct impact on banking operations
- Penalties for non-compliance
- Implementation complexity
- Regulatory scrutiny level

Risk Levels:
- high: Critical compliance requirement, severe penalties, high regulatory scrutiny
- medium: Important but manageable, moderate impact
- low: Minor impact, informational, or not directly applicable to banks

Respond with ONLY the risk level (high, medium, or low)."""

            result = _openai_chat(prompt, max_tokens=50, temperature=0.0).strip().lower()
            valid_levels = [r.value for r in RiskLevel]
            return result if result in valid_levels else RiskLevel.UNKNOWN.value
        except Exception as e:
            if _is_openai_quota_error(e):
                _disable_openai("insufficient_credits")
            logger.warning("OpenAI risk assessment error: %s", e)

    return _risk_heuristic(title)


def _truncate_text(text: str, max_chars: int) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "..."


def _select_article_excerpts(article_breakdown: Optional[List[Dict[str, Any]]]) -> List[str]:
    if not article_breakdown:
        return []

    scored: List[tuple[int, str]] = []
    for article in article_breakdown:
        if not isinstance(article, dict):
            continue
        number = article.get("number") or article.get("article") or ""
        title = article.get("title") or ""
        content = article.get("content") or article.get("text") or ""
        if not content:
            continue

        content_lower = content.lower()
        score = 0
        if "shall" in content_lower:
            score += 2
        if "must" in content_lower:
            score += 2
        if "required" in content_lower:
            score += 1
        if "obligation" in content_lower:
            score += 1

        excerpt = _truncate_text(content, 900)
        header = f"Article {number}".strip()
        if title:
            header = f"{header}: {title}" if header else title
        entry = f"{header}\n{excerpt}".strip()
        scored.append((score, entry))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in scored[:12]]


def _split_sentences(text: str) -> List[str]:
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _contains_obligation(text: str) -> bool:
    if not text:
        return False
    haystack = text.lower()
    keywords = [
        "shall",
        "must",
        "required to",
        "is required to",
        "shall not",
        "must not",
        "may not",
        "prohibited",
        "is prohibited",
    ]
    return any(kw in haystack for kw in keywords)


def _heuristic_obligations(
    article_breakdown: Optional[List[Dict[str, Any]]],
    full_text: Optional[str],
    max_items: int = 10,
) -> List[Dict[str, str]]:
    obligations: List[Dict[str, str]] = []

    if article_breakdown:
        for article in article_breakdown:
            if not isinstance(article, dict):
                continue
            content = article.get("content") or article.get("text") or ""
            if not content:
                continue
            article_ref = article.get("number") or article.get("article") or article.get("title")
            for sentence in _split_sentences(content):
                if _contains_obligation(sentence):
                    obligations.append(
                        {
                            "obligation": _truncate_text(sentence, 400),
                            "article": article_ref,
                            "source_excerpt": _truncate_text(sentence, 400),
                        }
                    )
                    if len(obligations) >= max_items:
                        return obligations

    if full_text:
        for sentence in _split_sentences(full_text):
            if _contains_obligation(sentence):
                obligations.append(
                    {
                        "obligation": _truncate_text(sentence, 400),
                        "article": None,
                        "source_excerpt": _truncate_text(sentence, 400),
                    }
                )
                if len(obligations) >= max_items:
                    break

    return obligations


def _select_full_text_obligation_snippets(full_text: Optional[str], max_items: int = 25) -> str:
    """
    Select short snippets from anywhere in the full text that look like obligations.

    This avoids the common failure mode where the first N characters contain only
    preamble/recitals, causing the LLM to (correctly) return [].
    """
    if not full_text:
        return ""

    snippets: List[str] = []
    for sentence in _split_sentences(full_text):
        if _contains_obligation(sentence):
            snippets.append(_truncate_text(sentence, 420))
            if len(snippets) >= max_items:
                break

    # If we couldn't find obligation-like sentences, fall back to an initial excerpt.
    if not snippets:
        return _truncate_text(full_text, 8000)

    joined = "\n".join(f"- {snippet}" for snippet in snippets)
    return _truncate_text(joined, 9000)


def extract_obligations(
    title: str,
    celex: str,
    full_text: Optional[str] = None,
    article_breakdown: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    """
    Extract specific obligations/requirements from the document.
    Returns: List of obligations with text and article reference
    """
    if not (_anthropic_enabled() or _openai_enabled()):
        return _heuristic_obligations(article_breakdown, full_text)

    excerpts = _select_article_excerpts(article_breakdown)
    context = ""
    if excerpts:
        context = "Relevant excerpts:\\n" + "\\n\\n".join(excerpts)
    elif full_text:
        context = "Relevant excerpts:\\n" + _select_full_text_obligation_snippets(full_text)

    prompt = f"""Extract the key compliance obligations from this EU regulation that banks or regulated entities must follow.

Document: {celex}
Title: {title}

{context}

For each obligation, provide:
1. obligation: the specific requirement (clear, actionable)
2. article: article or section reference (if available)
3. deadline: specific date or timeframe if stated
4. applicability: who/what this applies to (e.g., PSP, VASP, banks)
5. source_excerpt: a short supporting excerpt (max 200 chars)

Format as JSON array:
[
  {{"obligation": "Banks must...", "article": "Article 5", "deadline": "2026-01-01", "applicability": "banks", "source_excerpt": "…"}},
  ...
]

Extract 3-7 obligations if available. If no obligations are present, return [].
    Respond with JSON only."""

    def _parse_result(result_text: str) -> List[Dict[str, str]]:
        if not result_text:
            return []

        # Claude (and some OpenAI models) often wrap JSON in Markdown fences.
        cleaned = result_text.strip()
        if cleaned.startswith("```"):
            # Remove leading ```json (or ```), and trailing ```.
            cleaned = re.sub(r"^```[a-zA-Z0-9_-]*\\s*", "", cleaned)
            cleaned = re.sub(r"\\s*```\\s*$", "", cleaned)
            cleaned = cleaned.strip()

        candidates = [cleaned]
        # Fallback: extract the first JSON-looking array substring.
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1 and end > start:
            candidates.append(cleaned[start : end + 1])

        for candidate in candidates:
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            if isinstance(parsed, list):
                return parsed
            if isinstance(parsed, dict):
                for key in ("obligations", "items", "data"):
                    value = parsed.get(key)
                    if isinstance(value, list):
                        return value

        return []

    if _anthropic_enabled():
        # Use the configured model when valid, but fall back to a known-good Sonnet model if misconfigured.
        model = (settings.ANTHROPIC_MODEL or "").strip() or "claude-sonnet-4-20250514"
        try:
            message = client.messages.create(
                model=model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )
            _mark_llm_usage("anthropic")
            result_text = message.content[0].text.strip()
            return _parse_result(result_text)
        except Exception as e:
            if _is_anthropic_credit_error(e):
                _disable_anthropic("insufficient_credits")
                logger.warning("AI obligation extraction error: %s", e)
            elif _is_anthropic_model_not_found(e) and model != "claude-sonnet-4-20250514":
                try:
                    message = client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=1000,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    _mark_llm_usage("anthropic")
                    result_text = message.content[0].text.strip()
                    return _parse_result(result_text)
                except Exception as e2:
                    if _is_anthropic_credit_error(e2):
                        _disable_anthropic("insufficient_credits")
                    logger.warning("AI obligation extraction error: %s", e2)
            else:
                logger.warning("AI obligation extraction error: %s", e)

    if _openai_enabled():
        try:
            result_text = _openai_chat(prompt, max_tokens=1000, temperature=0.3).strip()
            return _parse_result(result_text)
        except Exception as e:
            if _is_openai_quota_error(e):
                _disable_openai("insufficient_credits")
            logger.warning("OpenAI obligation extraction error: %s", e)

    return _heuristic_obligations(article_breakdown, full_text)


def extract_deadline(title: str, publication_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Extract implementation deadline from document title or calculate based on publication date.
    Returns: datetime or None
    """
    if _anthropic_enabled():
        try:
            prompt = f"""Extract the implementation/transposition deadline from this EU legal document title.

Title: {title}
Publication Date: {publication_date.strftime('%Y-%m-%d') if publication_date else 'unknown'}

Common patterns:
- Directives: typically 18-24 months for transposition
- Regulations: often immediate or 6-12 months
- Look for phrases like "applicable from", "entry into force", "transposition deadline"

If you can determine a specific deadline date, respond with ONLY the date in YYYY-MM-DD format.
If you can only determine a relative timeframe (e.g., "18 months"), calculate from publication date.
If no deadline can be determined, respond with "none".
"""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            _mark_llm_usage("anthropic")

            result = message.content[0].text.strip().lower()
            if result == "none":
                return None

            # Try to parse date
            try:
                return datetime.strptime(result, "%Y-%m-%d")
            except ValueError:
                return None

        except Exception as e:
            if _is_anthropic_credit_error(e):
                _disable_anthropic("insufficient_credits")
            logger.warning("AI deadline extraction error: %s", e)

    if _openai_enabled():
        try:
            prompt = f"""Extract the implementation/transposition deadline from this EU legal document title.

Title: {title}
Publication Date: {publication_date.strftime('%Y-%m-%d') if publication_date else 'unknown'}

Common patterns:
- Directives: typically 18-24 months for transposition
- Regulations: often immediate or 6-12 months
- Look for phrases like "applicable from", "entry into force", "transposition deadline"

If you can determine a specific deadline date, respond with ONLY the date in YYYY-MM-DD format.
If you can only determine a relative timeframe (e.g., "18 months"), calculate from publication date.
If no deadline can be determined, respond with "none".
"""
            result = _openai_chat(prompt, max_tokens=100, temperature=0.0).strip().lower()
            if result == "none":
                return None
            try:
                return datetime.strptime(result, "%Y-%m-%d")
            except ValueError:
                return None
        except Exception as e:
            if _is_openai_quota_error(e):
                _disable_openai("insufficient_credits")
            logger.warning("OpenAI deadline extraction error: %s", e)

    # Simple heuristic: directives typically have 2-year transposition period
    if publication_date and "directive" in title.lower():
        from dateutil.relativedelta import relativedelta

        return publication_date + relativedelta(years=2)
    return None


def generate_summary(title: str, celex: str) -> str:
    """
    Generate executive summary for AMLRO.
    Returns: Plain text summary
    """
    if _anthropic_enabled():
        try:
            prompt = f"""Create a concise executive summary (2-3 sentences) of this EU regulation for an AML/Compliance Officer at a bank.

Document: {celex}
Title: {title}

Focus on:
- What this regulation does
- Key impact on banks
- Main compliance requirements

Keep it under 100 words."""

            message = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            _mark_llm_usage("anthropic")

            return message.content[0].text.strip()

        except Exception as e:
            if _is_anthropic_credit_error(e):
                _disable_anthropic("insufficient_credits")
            logger.warning("AI summary generation error: %s", e)

    if _openai_enabled():
        try:
            prompt = f"""Create a concise executive summary (2-3 sentences) of this EU regulation for an AML/Compliance Officer at a bank.

Document: {celex}
Title: {title}

Focus on:
- What this regulation does
- Key impact on banks
- Main compliance requirements

Keep it under 100 words."""
            return _openai_chat(prompt, max_tokens=200, temperature=0.3).strip()
        except Exception as e:
            if _is_openai_quota_error(e):
                _disable_openai("insufficient_credits")
            logger.warning("OpenAI summary generation error: %s", e)

    return f"Document {celex}: {title}"


def analyze_document(doc_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform complete AI analysis on a document.

    Args:
        doc_data: Dict with keys: celex, title, publication_date (optional)

    Returns:
        Dict with analysis results
    """
    celex = doc_data.get("celex", "")
    title = doc_data.get("title", "")
    pub_date = doc_data.get("publication_date")
    full_text = doc_data.get("full_text")
    article_breakdown = doc_data.get("article_breakdown")

    _reset_llm_usage()

    # Run all analyses (may fall back to heuristics if AI providers are unavailable).
    compliance_domain = classify_document(title, celex)
    risk_level = assess_risk_level(title, celex, compliance_domain)
    obligations = extract_obligations(
        title,
        celex,
        full_text=full_text,
        article_breakdown=article_breakdown if isinstance(article_breakdown, list) else None,
    )
    deadline = extract_deadline(title, pub_date)
    summary = generate_summary(title, celex)

    providers = _llm_providers_used()
    analysis_provider = (
        "anthropic"
        if "anthropic" in providers
        else "openai" if "openai" in providers else "heuristic"
    )

    return {
        "compliance_domain": compliance_domain,
        "risk_level": risk_level,
        "obligations_json": obligations,
        "implementation_deadline": deadline,
        "ai_summary": summary,
        # Only set analyzed_at when an LLM actually responded. This keeps documents analyzable later.
        "analyzed_at": utc_now() if _llm_was_used() else None,
        "analysis_provider": analysis_provider,
        "llm_providers": providers,
    }
