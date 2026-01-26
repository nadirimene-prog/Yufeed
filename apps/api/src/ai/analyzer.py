"""
AI-powered document analysis for compliance intelligence.
Uses LLM to classify documents, assess risk, and extract obligations.
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import anthropic  # Using Claude for legal text analysis
from src.models.models import ComplianceDomain, RiskLevel

# Initialize Anthropic client
API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
client = anthropic.Anthropic(api_key=API_KEY) if API_KEY else None

def classify_document(title: str, celex: str) -> Optional[str]:
    """
    Classify document into compliance domain based on title and CELEX.
    Returns: ComplianceDomain value or None
    """
    if not client:
        # Fallback: simple keyword matching
        title_lower = title.lower()
        if any(kw in title_lower for kw in ["money laundering", "aml", "terrorist financing"]):
            return ComplianceDomain.AML.value
        elif any(kw in title_lower for kw in ["crypto", "digital asset", "virtual currency"]):
            return ComplianceDomain.CRYPTO.value
        elif any(kw in title_lower for kw in ["payment", "psd", "electronic money"]):
            return ComplianceDomain.PAYMENTS.value
        elif any(kw in title_lower for kw in ["sanction", "restrictive measure"]):
            return ComplianceDomain.SANCTIONS.value
        elif any(kw in title_lower for kw in ["know your customer", "kyc", "customer due diligence", "cdd"]):
            return ComplianceDomain.KYC.value
        elif any(kw in title_lower for kw in ["gdpr", "data protection", "privacy"]):
            return ComplianceDomain.GDPR.value
        return ComplianceDomain.OTHER.value
    
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = message.content[0].text.strip().lower()
        # Validate result
        valid_domains = [d.value for d in ComplianceDomain]
        return result if result in valid_domains else ComplianceDomain.OTHER.value
        
    except Exception as e:
        print(f"AI classification error: {e}")
        return None


def assess_risk_level(title: str, celex: str, compliance_domain: Optional[str] = None) -> str:
    """
    Assess the risk level/impact of a regulation for banks.
    Returns: RiskLevel value
    """
    if not client:
        # Fallback: simple heuristics
        title_lower = title.lower()
        # High risk keywords
        if any(kw in title_lower for kw in ["aml", "money laundering", "sanction", "terrorist financing"]):
            return RiskLevel.HIGH.value
        # Medium risk
        if any(kw in title_lower for kw in ["payment", "crypto", "kyc", "cdd"]):
            return RiskLevel.MEDIUM.value
        return RiskLevel.LOW.value
    
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = message.content[0].text.strip().lower()
        valid_levels = [r.value for r in RiskLevel]
        return result if result in valid_levels else RiskLevel.UNKNOWN.value
        
    except Exception as e:
        print(f"AI risk assessment error: {e}")
        return RiskLevel.UNKNOWN.value


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
    if not client:
        return []
    
    try:
        excerpts = _select_article_excerpts(article_breakdown)
        context = ""
        if excerpts:
            context = "Relevant excerpts:\\n" + "\\n\\n".join(excerpts)
        elif full_text:
            context = "Excerpt:\\n" + _truncate_text(full_text, 8000)

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

        message = client.messages.create(
            model="claude-3-sonnet-20240229",  # Better for complex extraction
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_text = message.content[0].text.strip()
        # Try to parse JSON
        try:
            obligations = json.loads(result_text)
            return obligations if isinstance(obligations, list) else []
        except json.JSONDecodeError:
            return []
        
    except Exception as e:
        print(f"AI obligation extraction error: {e}")
        return []


def extract_deadline(title: str, publication_date: Optional[datetime] = None) -> Optional[datetime]:
    """
    Extract implementation deadline from document title or calculate based on publication date.
    Returns: datetime or None
    """
    if not client:
        # Simple heuristic: directives typically have 2-year transposition period
        if publication_date and "directive" in title.lower():
            from dateutil.relativedelta import relativedelta
            return publication_date + relativedelta(years=2)
        return None
    
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        result = message.content[0].text.strip().lower()
        if result == "none":
            return None
        
        # Try to parse date
        try:
            return datetime.strptime(result, "%Y-%m-%d")
        except ValueError:
            return None
        
    except Exception as e:
        print(f"AI deadline extraction error: {e}")
        return None


def generate_summary(title: str, celex: str) -> str:
    """
    Generate executive summary for AMLRO.
    Returns: Plain text summary
    """
    if not client:
        return f"Document {celex}: {title}"
    
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
            messages=[{"role": "user", "content": prompt}]
        )
        
        return message.content[0].text.strip()
        
    except Exception as e:
        print(f"AI summary generation error: {e}")
        return ""


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
    
    # Run all analyses
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
    
    return {
        "compliance_domain": compliance_domain,
        "risk_level": risk_level,
        "obligations_json": obligations,
        "implementation_deadline": deadline,
        "ai_summary": summary,
        "analyzed_at": datetime.utcnow()
    }
