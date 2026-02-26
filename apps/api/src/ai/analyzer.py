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
    _analysis_ctx.obligation_extraction_report = None


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


def _set_obligation_extraction_report(report: Optional[Dict[str, Any]]) -> None:
    _analysis_ctx.obligation_extraction_report = report


def _obligation_extraction_report() -> Optional[Dict[str, Any]]:
    return getattr(_analysis_ctx, "obligation_extraction_report", None)


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


def _anthropic_client_for_obligation_extraction(timeout_s: Optional[float] = None):
    """Disable SDK retries for extraction calls so timeout budgets remain predictable."""
    if client is None:
        return None
    with_options = getattr(client, "with_options", None)
    if not callable(with_options):
        return client
    try:
        kwargs: Dict[str, Any] = {"max_retries": 0}
        if timeout_s is not None:
            kwargs["timeout"] = timeout_s
        return with_options(**kwargs)
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.debug("Anthropic extraction client override failed: %s", exc)
        return client


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


def _format_article_header(article: Dict[str, Any]) -> str:
    number = article.get("number") or article.get("article") or ""
    title = article.get("title") or ""
    header = f"Article {number}".strip()
    if title:
        header = f"{header}: {title}" if header else str(title)
    return header or "Article"


def _article_number_str(article: Dict[str, Any]) -> Optional[str]:
    raw = article.get("number") or article.get("article")
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    # Prefer the bare number token (e.g., "16", "24a") for coverage matching.
    m = re.search(r"(\d+[A-Za-z]?)", text)
    return m.group(1) if m else text


def _canonical_article_key(article_ref: Optional[str]) -> Optional[str]:
    if article_ref is None:
        return None
    text = str(article_ref).strip()
    if not text:
        return None
    m = re.search(r"(?:article|art\.?)\s*(\d+[A-Za-z]?)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).lower()
    m = re.search(r"^(\d+[A-Za-z]?)$", text)
    if m:
        return m.group(1).lower()
    return None


def _article_signal_score(text: str) -> int:
    if not text:
        return 0
    # Count obligation-like sentences as a lightweight proxy for likely extractable requirements.
    return sum(1 for sentence in _split_sentences(text) if _contains_obligation(sentence))


def _chunk_text(text: str, max_chars: int = 3200, overlap: int = 300) -> List[str]:
    if not text:
        return []
    cleaned = text.strip()
    if len(cleaned) <= max_chars:
        return [cleaned]

    chunks: List[str] = []
    start = 0
    max_chars = max(500, max_chars)
    overlap = max(0, min(overlap, max_chars // 3))

    while start < len(cleaned):
        end = min(len(cleaned), start + max_chars)
        if end < len(cleaned):
            window = cleaned[start:end]
            split_at = max(
                window.rfind("\n\n"),
                window.rfind(". "),
                window.rfind("; "),
                window.rfind(": "),
            )
            if split_at > int(max_chars * 0.6):
                end = start + split_at + 1

        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(cleaned):
            break

        next_start = end - overlap
        if next_start <= start:
            next_start = end
        start = next_start

    return chunks


def _build_article_obligation_batches(
    article_breakdown: Optional[List[Dict[str, Any]]],
    max_segments_per_batch: int = 4,
    max_batch_chars: int = 16000,
) -> List[Dict[str, Any]]:
    if not article_breakdown:
        return []

    segments: List[Dict[str, Any]] = []
    for article in article_breakdown:
        if not isinstance(article, dict):
            continue
        content = article.get("content") or article.get("text") or ""
        if not content:
            continue
        article_number = _article_number_str(article)
        header = _format_article_header(article)
        content_str = str(content)
        article_signal = _article_signal_score(content_str)
        for idx, chunk in enumerate(_chunk_text(content_str), start=1):
            chunk_header = header if idx == 1 else f"{header} (chunk {idx})"
            chunk_signal = _article_signal_score(chunk)
            segments.append(
                {
                    "article_number": article_number,
                    "article_key": _canonical_article_key(article_number),
                    "header": chunk_header,
                    "chunk_index": idx,
                    "content": chunk,
                    "segment_text": f"{chunk_header}\n{chunk}".strip(),
                    "signal_score": max(chunk_signal, article_signal if idx == 1 else 0),
                }
            )

    if not segments:
        return []

    # Prioritize higher-signal segments first so large acts produce obligations before budget exhaustion.
    segments.sort(
        key=lambda s: (
            -int(s.get("signal_score") or 0),
            str(s.get("article_key") or ""),
            int(s.get("chunk_index") or 0),
        )
    )

    batches: List[Dict[str, Any]] = []
    current_segments: List[Dict[str, Any]] = []
    current_chars = 0
    max_segments_per_batch = max(1, max_segments_per_batch)
    max_batch_chars = max(3000, max_batch_chars)

    def flush() -> None:
        nonlocal current_segments, current_chars
        if not current_segments:
            return
        body = "\n\n".join(str(seg.get("segment_text") or "") for seg in current_segments)
        article_numbers = [
            seg.get("article_number")
            for seg in current_segments
            if seg.get("article_number") is not None
        ]
        article_keys = [
            seg.get("article_key") for seg in current_segments if seg.get("article_key") is not None
        ]
        batch_signal = sum(int(seg.get("signal_score") or 0) for seg in current_segments)
        batches.append(
            {
                "context": f"Articles to analyze:\n{body}",
                "segments": [dict(seg) for seg in current_segments],
                "article_numbers": list(dict.fromkeys([str(n) for n in article_numbers])),
                "article_keys": list(dict.fromkeys([str(k) for k in article_keys])),
                "signal_score": batch_signal,
            }
        )
        current_segments = []
        current_chars = 0

    for segment in segments:
        segment_len = len(str(segment.get("segment_text") or ""))
        if current_segments and (
            len(current_segments) >= max_segments_per_batch
            or (current_chars + segment_len + 2) > max_batch_chars
        ):
            flush()
        current_segments.append(segment)
        current_chars += segment_len + 2
    flush()
    return batches


def _build_article_obligation_contexts(
    article_breakdown: Optional[List[Dict[str, Any]]],
    max_segments_per_batch: int = 4,
    max_batch_chars: int = 16000,
) -> List[str]:
    return [
        batch.get("context", "")
        for batch in _build_article_obligation_batches(
            article_breakdown,
            max_segments_per_batch=max_segments_per_batch,
            max_batch_chars=max_batch_chars,
        )
    ]


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


def _parse_obligation_result(result_text: str) -> List[Dict[str, Any]]:
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
            return [item for item in parsed if isinstance(item, dict)]
        if isinstance(parsed, dict):
            for key in ("obligations", "items", "data"):
                value = parsed.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]

    return []


def _dedupe_obligation_candidates(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        obligation = str(item.get("obligation") or item.get("text") or "").strip()
        article = str(item.get("article") or "").strip()
        excerpt = str(item.get("source_excerpt") or "").strip()
        key = (
            re.sub(r"\s+", " ", obligation).lower(),
            re.sub(r"\s+", " ", article).lower(),
            re.sub(r"\s+", " ", excerpt).lower(),
        )
        if not key[0]:
            continue
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    return deduped


def _obligation_article_keys(items: List[Dict[str, Any]]) -> set[str]:
    keys: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        for source in (item.get("article"), item.get("article_ref"), item.get("source_excerpt")):
            key = _canonical_article_key(source)
            if key:
                keys.add(key)
                break
    return keys


def _article_catalog(article_breakdown: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []
    if not article_breakdown:
        return catalog
    for article in article_breakdown:
        if not isinstance(article, dict):
            continue
        content = str(article.get("content") or article.get("text") or "").strip()
        if not content:
            continue
        number = _article_number_str(article)
        key = _canonical_article_key(number)
        catalog.append(
            {
                "number": number,
                "key": key,
                "title": (article.get("title") or None),
                "content": content,
                "signal_score": _article_signal_score(content),
            }
        )
    return catalog


def _article_coverage_report(
    article_breakdown: Optional[List[Dict[str, Any]]],
    obligations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    catalog = _article_catalog(article_breakdown)
    article_count = len(catalog)
    signal_articles = [a for a in catalog if int(a.get("signal_score") or 0) > 0]
    signal_article_keys = {str(a["key"]) for a in signal_articles if a.get("key")}
    referenced_article_keys = _obligation_article_keys(obligations)
    covered_signal_keys = signal_article_keys & referenced_article_keys
    uncovered_signal_articles = [
        {
            "article": f"Article {a['number']}" if a.get("number") else None,
            "signal_score": a["signal_score"],
        }
        for a in signal_articles
        if a.get("key") not in referenced_article_keys
    ]

    return {
        "article_count": article_count,
        "articles_with_obligation_signal": len(signal_articles),
        "referenced_article_count": len(referenced_article_keys),
        "covered_signal_article_count": len(covered_signal_keys),
        "uncovered_signal_article_count": len(uncovered_signal_articles),
        "uncovered_signal_articles_sample": uncovered_signal_articles[:20],
        "obligations_without_article_ref": sum(
            1
            for item in obligations
            if isinstance(item, dict) and not _canonical_article_key(item.get("article"))
        ),
    }


def _sweep_candidate_articles(
    article_breakdown: Optional[List[Dict[str, Any]]],
    obligations: List[Dict[str, Any]],
    max_articles: int = 24,
) -> List[Dict[str, Any]]:
    catalog = _article_catalog(article_breakdown)
    covered_keys = _obligation_article_keys(obligations)
    candidates = [
        a
        for a in catalog
        if a.get("key") and int(a.get("signal_score") or 0) > 0 and a.get("key") not in covered_keys
    ]
    candidates.sort(
        key=lambda a: (
            -int(a.get("signal_score") or 0),
            (
                int(re.match(r"^\d+", str(a.get("number") or "0")).group(0))
                if re.match(r"^\d+", str(a.get("number") or ""))
                else 999999
            ),
            str(a.get("number") or ""),
        )
    )
    return candidates[: max(0, max_articles)]


def _build_obligation_prompt(
    title: str,
    celex: str,
    context: str,
    exhaustive: bool = False,
    pass_mode: str = "primary",
) -> str:
    is_sweep = pass_mode == "sweep"
    if not exhaustive:
        extraction_instruction = "Extract the key compliance obligations from this EU regulation that banks or regulated entities must follow."
    elif is_sweep:
        extraction_instruction = (
            "Second-pass coverage sweep: the following article snippets likely contain obligations that were missed earlier. "
            "Extract every explicit duty/prohibition/mandatory control/reporting/notification/governance requirement from each snippet. "
            "Do not skip items because they seem repetitive. Prefer preserving article references exactly (e.g., 'Article 16'). "
            "Return [] only if an article snippet truly contains no obligation."
        )
    else:
        extraction_instruction = (
            "Extract all explicit compliance obligations, prohibitions, conditions, and mandatory requirements in the provided article text. "
            "Treat legal formulations such as 'shall', 'shall ensure', 'shall not', 'may only', 'is to', 'is required to', "
            "'must', and authorization/notification/reporting conditions as obligations when they impose a duty or restriction. "
            "The snippets may contain legal formatting noise (paragraph numbers, points (a), non-breaking spaces). "
            "Use the article headings provided in the snippets for article references. "
            "Do not impose an arbitrary cap. Return one item per distinct requirement. "
            "If the snippets only contain definitions/scope without duties, return []."
        )

    count_instruction = (
        "Extract all obligations present in the provided text. If none are present, return []."
        if exhaustive
        else "Extract 3-7 obligations if available. If no obligations are present, return []."
    )

    extra_rules = (
        "Rules:\n"
        "- Ignore recitals/preamble unless they appear inside a provided article snippet.\n"
        "- Include obligations on regulated entities and competent authorities if the article imposes a mandatory duty.\n"
        "- Prefer one JSON item per obligation sentence or tightly coupled requirement.\n"
        "- Put the article heading reference in `article` whenever possible (e.g., `Article 2`, `Article 81`)."
    )

    return f"""{extraction_instruction}

Document: {celex}
Title: {title}

Extraction pass: {pass_mode}

{context}

{extra_rules}

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

{count_instruction}
Respond with JSON only."""


def _extract_obligations_with_llm(
    prompt: str,
    max_tokens: int = 3000,
    timeout_s: Optional[float] = None,
) -> List[Dict[str, Any]]:
    anthropic_timeout = timeout_s
    if _anthropic_enabled():
        # Use the configured model when valid, but fall back to a known-good Sonnet model if misconfigured.
        model = (settings.ANTHROPIC_MODEL or "").strip() or "claude-sonnet-4-20250514"
        anthropic_client = _anthropic_client_for_obligation_extraction(anthropic_timeout)
        try:
            message = anthropic_client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                timeout=anthropic_timeout,
            )
            _mark_llm_usage("anthropic")
            result_text = message.content[0].text.strip()
            return _parse_obligation_result(result_text)
        except Exception as e:
            if _is_anthropic_credit_error(e):
                _disable_anthropic("insufficient_credits")
                logger.warning("AI obligation extraction error: %s", e)
            elif _is_anthropic_model_not_found(e) and model != "claude-sonnet-4-20250514":
                try:
                    message = anthropic_client.messages.create(
                        model="claude-sonnet-4-20250514",
                        max_tokens=max_tokens,
                        messages=[{"role": "user", "content": prompt}],
                        timeout=anthropic_timeout,
                    )
                    _mark_llm_usage("anthropic")
                    result_text = message.content[0].text.strip()
                    return _parse_obligation_result(result_text)
                except Exception as e2:
                    if _is_anthropic_credit_error(e2):
                        _disable_anthropic("insufficient_credits")
                    logger.warning("AI obligation extraction error: %s", e2)
            else:
                logger.warning("AI obligation extraction error: %s", e)

    if _openai_enabled():
        try:
            result_text = _openai_chat(prompt, max_tokens=max_tokens, temperature=0.2).strip()
            return _parse_obligation_result(result_text)
        except Exception as e:
            if _is_openai_quota_error(e):
                _disable_openai("insufficient_credits")
            logger.warning("OpenAI obligation extraction error: %s", e)

    return []


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
    report: Dict[str, Any] = {
        "celex": celex,
        "article_input_count": len(article_breakdown) if isinstance(article_breakdown, list) else 0,
    }
    if not (_anthropic_enabled() or _openai_enabled()):
        items = _heuristic_obligations(
            article_breakdown,
            full_text,
            max_items=250 if article_breakdown else 50,
        )
        report.update(
            {
                "path": "heuristic_only",
                "extracted_count": len(items),
                "coverage": _article_coverage_report(article_breakdown, items),
            }
        )
        _set_obligation_extraction_report(report)
        return items

    batch_timeout_s = max(
        10.0,
        float(getattr(settings, "OBLIGATION_EXTRACTION_BATCH_TIMEOUT_SECONDS", 90.0) or 90.0),
    )
    total_budget_s = max(
        30.0,
        float(getattr(settings, "OBLIGATION_EXTRACTION_MAX_SECONDS", 600.0) or 600.0),
    )
    sweep_enabled = bool(getattr(settings, "OBLIGATION_EXTRACTION_SWEEP_ENABLED", True))
    sweep_max_articles = max(
        0,
        int(getattr(settings, "OBLIGATION_EXTRACTION_SWEEP_MAX_ARTICLES", 24) or 24),
    )
    sweep_max_batches = max(
        0,
        int(getattr(settings, "OBLIGATION_EXTRACTION_SWEEP_MAX_BATCHES", 8) or 8),
    )
    started_at = time.monotonic()
    report.update(
        {
            "path": "llm",
            "batch_timeout_seconds": batch_timeout_s,
            "total_budget_seconds": total_budget_s,
            "sweep_enabled": sweep_enabled,
        }
    )

    # Prefer article-by-article batch extraction for broader coverage on large acts.
    article_batches = _build_article_obligation_batches(article_breakdown)
    report["article_batch_count"] = len(article_batches)
    if article_batches:
        aggregated: List[Dict[str, Any]] = []
        total_batches = len(article_batches)
        primary_batches_run = 0
        primary_batches_with_results = 0
        for idx, batch in enumerate(article_batches, start=1):
            elapsed = time.monotonic() - started_at
            if elapsed >= total_budget_s:
                logger.warning(
                    "Stopping obligation extraction early for %s after %.1fs (budget %.1fs) at batch %s/%s",
                    celex,
                    elapsed,
                    total_budget_s,
                    idx,
                    total_batches,
                )
                break
            context = str(batch.get("context") or "")
            logger.info(
                "Obligation extraction batch %s/%s for %s (elapsed=%.1fs timeout=%.1fs signal=%s articles=%s)",
                idx,
                total_batches,
                celex,
                elapsed,
                batch_timeout_s,
                int(batch.get("signal_score") or 0),
                batch.get("article_numbers") or [],
            )
            prompt = _build_obligation_prompt(
                title,
                celex,
                context,
                exhaustive=True,
                pass_mode="primary",
            )
            items = _extract_obligations_with_llm(
                prompt,
                max_tokens=3000,
                timeout_s=batch_timeout_s,
            )
            primary_batches_run += 1
            if items:
                primary_batches_with_results += 1
            logger.info(
                "Obligation extraction batch %s/%s for %s returned %s items",
                idx,
                total_batches,
                celex,
                len(items or []),
            )
            if items:
                aggregated.extend(items)

        deduped_primary = _dedupe_obligation_candidates(aggregated)
        report["primary_pass"] = {
            "batches_total": total_batches,
            "batches_run": primary_batches_run,
            "batches_with_results": primary_batches_with_results,
            "raw_items": len(aggregated),
            "deduped_items": len(deduped_primary),
            "coverage": _article_coverage_report(article_breakdown, deduped_primary),
        }

        deduped = deduped_primary
        sweep_stats: Dict[str, Any] = {
            "candidates": 0,
            "batches_total": 0,
            "batches_run": 0,
            "raw_items": 0,
            "deduped_items_added": 0,
        }
        if sweep_enabled and article_breakdown and sweep_max_articles > 0 and sweep_max_batches > 0:
            remaining_budget = total_budget_s - (time.monotonic() - started_at)
            if remaining_budget > 0:
                sweep_candidates = _sweep_candidate_articles(
                    article_breakdown,
                    deduped_primary,
                    max_articles=sweep_max_articles,
                )
                sweep_stats["candidates"] = len(sweep_candidates)
                if sweep_candidates:
                    logger.info(
                        "Obligation extraction sweep for %s candidates=%s remaining_budget=%.1fs",
                        celex,
                        len(sweep_candidates),
                        remaining_budget,
                    )
                    sweep_articles = [
                        {
                            "number": candidate.get("number"),
                            "title": candidate.get("title"),
                            "content": candidate.get("content"),
                        }
                        for candidate in sweep_candidates
                    ]
                    sweep_batches = _build_article_obligation_batches(
                        sweep_articles,
                        max_segments_per_batch=2,
                        max_batch_chars=10000,
                    )[:sweep_max_batches]
                    sweep_stats["batches_total"] = len(sweep_batches)
                    sweep_raw: List[Dict[str, Any]] = []
                    for idx, batch in enumerate(sweep_batches, start=1):
                        elapsed = time.monotonic() - started_at
                        if elapsed >= total_budget_s:
                            logger.warning(
                                "Stopping obligation sweep early for %s after %.1fs (budget %.1fs) at sweep batch %s/%s",
                                celex,
                                elapsed,
                                total_budget_s,
                                idx,
                                len(sweep_batches),
                            )
                            break
                        logger.info(
                            "Obligation extraction sweep batch %s/%s for %s (elapsed=%.1fs timeout=%.1fs articles=%s)",
                            idx,
                            len(sweep_batches),
                            celex,
                            elapsed,
                            batch_timeout_s,
                            batch.get("article_numbers") or [],
                        )
                        prompt = _build_obligation_prompt(
                            title,
                            celex,
                            str(batch.get("context") or ""),
                            exhaustive=True,
                            pass_mode="sweep",
                        )
                        items = _extract_obligations_with_llm(
                            prompt,
                            max_tokens=3000,
                            timeout_s=batch_timeout_s,
                        )
                        sweep_stats["batches_run"] += 1
                        logger.info(
                            "Obligation extraction sweep batch %s/%s for %s returned %s items",
                            idx,
                            len(sweep_batches),
                            celex,
                            len(items or []),
                        )
                        if items:
                            sweep_raw.extend(items)
                    sweep_stats["raw_items"] = len(sweep_raw)
                    if sweep_raw:
                        before_len = len(deduped)
                        deduped = _dedupe_obligation_candidates(deduped + sweep_raw)
                        sweep_stats["deduped_items_added"] = max(0, len(deduped) - before_len)

        report["second_pass_sweep"] = sweep_stats
        report["coverage_after_llm_article_passes"] = _article_coverage_report(
            article_breakdown, deduped
        )

        if deduped:
            logger.info(
                "Obligation extraction aggregated %s obligations from %s article batches for %s",
                len(deduped),
                len(article_batches),
                celex,
            )
            report["extracted_count"] = len(deduped)
            _set_obligation_extraction_report(report)
            return deduped

    if full_text:
        elapsed = time.monotonic() - started_at
        if elapsed >= total_budget_s:
            logger.warning(
                "Skipping full-text fallback obligation extraction for %s due to budget exhaustion (%.1fs/%.1fs)",
                celex,
                elapsed,
                total_budget_s,
            )
            items = _heuristic_obligations(
                article_breakdown,
                full_text,
                max_items=250 if article_breakdown else 50,
            )
            report["full_text_fallback"] = {
                "used": False,
                "reason": "budget_exhausted",
            }
            report["fallback_path"] = "heuristic_after_budget_exhaustion"
            report["extracted_count"] = len(items)
            report["coverage"] = _article_coverage_report(article_breakdown, items)
            _set_obligation_extraction_report(report)
            return items
        context = "Relevant excerpts:\n" + _select_full_text_obligation_snippets(
            full_text, max_items=80
        )
        prompt = _build_obligation_prompt(
            title,
            celex,
            context,
            exhaustive=bool(article_breakdown),
            pass_mode="full_text",
        )
        logger.info(
            "Obligation extraction full-text fallback for %s (elapsed=%.1fs timeout=%.1fs)",
            celex,
            elapsed,
            batch_timeout_s,
        )
        items = _extract_obligations_with_llm(prompt, max_tokens=3000, timeout_s=batch_timeout_s)
        deduped = _dedupe_obligation_candidates(items)
        if deduped:
            report["full_text_fallback"] = {
                "used": True,
                "raw_items": len(items),
                "deduped_items": len(deduped),
            }
            report["fallback_path"] = "llm_full_text"
            report["extracted_count"] = len(deduped)
            report["coverage"] = _article_coverage_report(article_breakdown, deduped)
            _set_obligation_extraction_report(report)
            return deduped

    items = _heuristic_obligations(
        article_breakdown,
        full_text,
        max_items=250 if article_breakdown else 50,
    )
    report["fallback_path"] = "heuristic_after_llm"
    report["extracted_count"] = len(items)
    report["coverage"] = _article_coverage_report(article_breakdown, items)
    _set_obligation_extraction_report(report)
    return items


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
        "obligation_extraction_report": _obligation_extraction_report(),
        "implementation_deadline": deadline,
        "ai_summary": summary,
        # Only set analyzed_at when an LLM actually responded. This keeps documents analyzable later.
        "analyzed_at": utc_now() if _llm_was_used() else None,
        "analysis_provider": analysis_provider,
        "llm_providers": providers,
    }
