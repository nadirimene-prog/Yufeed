"""
Content Extractor V2 - Multi-strategy extraction with CELEX normalization
Integrated into the main codebase.
"""

import re
import time
import logging
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
from urllib.parse import quote
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

RDF_ABOUT_ATTR = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}about"
RDF_RESOURCE_ATTR = "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource"

LANGUAGE_CODE_MAP = {
    "BG": "BUL",
    "CS": "CES",
    "DA": "DAN",
    "DE": "DEU",
    "EL": "ELL",
    "EN": "ENG",
    "ES": "SPA",
    "ET": "EST",
    "FI": "FIN",
    "FR": "FRA",
    "GA": "GLE",
    "HR": "HRV",
    "HU": "HUN",
    "IT": "ITA",
    "LT": "LIT",
    "LV": "LAV",
    "MT": "MLT",
    "NL": "NLD",
    "PL": "POL",
    "PT": "POR",
    "RO": "RON",
    "SK": "SLK",
    "SL": "SLV",
    "SV": "SWE",
}


@dataclass
class ExtractionResult:
    celex: str
    strategy: str
    word_count: int
    title: Optional[str]
    articles: Dict[str, str]
    full_text: str
    attempted_celexes: List[str]
    errors: List[str]
    extracted_at: str


# Document type patterns for CELEX correction
DOC_TYPE_KEYWORDS = {
    "DIRECTIVE": ["DIRECTIVE", "PSD", "EMD", "AMLD", "MLD", "CRD", "CRR", "NIS"],
    "REGULATION": ["REGULATION", "AMLR", "GDPR", "MICA", "SFDR", "CSRD", "ESEF", "DORA"],
    "DECISION": ["DECISION", "CFR", "EDPB", "EBA", "ESMA"],
}


class CELEXUtils:
    """Utilities for CELEX validation and normalization."""

    @staticmethod
    def normalize(celex: str, title: str = "") -> Tuple[str, List[str]]:
        """Normalize CELEX and suggest variants."""
        variants = [celex]
        original = celex

        celex = re.sub(r"[.\s]", "", celex.upper())

        if not re.match(r"^[123]", celex):
            return original, variants

        # Detect document type from title
        title_upper = title.upper()
        detected_type = None

        for doc_type, keywords in DOC_TYPE_KEYWORDS.items():
            for kw in keywords:
                if kw in title_upper:
                    detected_type = doc_type
                    break
            if detected_type:
                break

        # Suggest corrections
        if detected_type == "DIRECTIVE":
            if len(celex) > 5 and celex[4] not in ["L", "D"]:
                corrected = celex[:4] + "L" + celex[5:]
                variants.append(corrected)
        elif detected_type == "REGULATION":
            if len(celex) > 5 and celex[4] != "R":
                corrected = celex[:4] + "R" + celex[5:]
                variants.append(corrected)

        return celex, list(dict.fromkeys(variants))


class ContentExtractorV2:
    """Enhanced content extractor with multiple fallback strategies."""

    STRATEGIES = ["cellar_xhtml", "eurlex_html", "eurlex_summary"]
    RETRY_DELAY = 2
    MAX_RETRIES = 2

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Yufeed Legal Content Extractor/2.0)"}
        )
        self.celex_utils = CELEXUtils()

    def extract(
        self, celex: str, title: str = "", language: str = "EN"
    ) -> Optional[ExtractionResult]:
        """Extract content with all strategies and CELEX variants."""
        language = (language or "EN").upper()
        normalized_celex, celex_variants = self.celex_utils.normalize(celex, title)
        logger.info(f"Extracting {celex} - trying variants: {celex_variants}")

        errors = []
        attempted_celexes = []

        for variant in celex_variants:
            attempted_celexes.append(variant)

            for strategy in self.STRATEGIES:
                logger.debug(f"Trying {strategy} with CELEX {variant}...")

                for attempt in range(self.MAX_RETRIES):
                    try:
                        if strategy == "cellar_xhtml":
                            result = self._extract_cellar_xhtml(variant, language)
                        elif strategy == "eurlex_html":
                            result = self._extract_eurlex_html(variant, language)
                        elif strategy == "eurlex_summary":
                            result = self._extract_eurlex_summary(variant, language)
                        else:
                            continue

                        if result and result["word_count"] > 100:
                            logger.info(f"Success with {strategy}: {result['word_count']} words")
                            return ExtractionResult(
                                celex=variant,
                                strategy=strategy,
                                word_count=result["word_count"],
                                title=result.get("title"),
                                articles=result.get("articles", {}),
                                full_text=result.get("full_text", ""),
                                attempted_celexes=attempted_celexes,
                                errors=errors,
                                extracted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                            )

                    except Exception as e:
                        error_msg = f"{strategy} failed: {str(e)[:80]}"
                        errors.append(error_msg)
                        if attempt < self.MAX_RETRIES - 1:
                            time.sleep(self.RETRY_DELAY * (attempt + 1))

        logger.error(f"All strategies failed for {celex}")
        return None

    def _looks_like_rdf(self, response: requests.Response) -> bool:
        ctype = (response.headers.get("content-type") or "").lower()
        if "rdf+xml" in ctype:
            return True
        text = (response.text or "").lstrip()
        return text.startswith("<rdf:RDF")

    def _parse_rdf(self, xml_text: str) -> ET.Element:
        try:
            return ET.fromstring(xml_text)
        except ET.ParseError as exc:
            raise Exception(f"Invalid RDF XML: {exc}") from exc

    def _fetch_rdf_root(self, url: str, timeout: int = 30) -> ET.Element:
        resp = self.session.get(url, timeout=timeout)
        resp.raise_for_status()
        if not self._looks_like_rdf(resp):
            raise Exception(f"Expected RDF response from {url}")
        return self._parse_rdf(resp.text)

    def _language_codes(self, language: str) -> List[str]:
        normalized = (language or "EN").upper()
        variants = [normalized]
        if len(normalized) == 2:
            variants.append(LANGUAGE_CODE_MAP.get(normalized, normalized))
        elif len(normalized) == 3:
            # Prefer canonical 3-letter code but also try the first 2 letters.
            variants.append(normalized[:2])
        return list(dict.fromkeys([v for v in variants if v]))

    def _resolve_publications_office_xhtml_item(self, celex: str, language: str) -> str:
        work_root = self._fetch_rdf_root(f"https://publications.europa.eu/resource/celex/{celex}")
        lang_suffixes = tuple(f".{code}" for code in self._language_codes(language))

        expression_uri: Optional[str] = None
        for desc in work_root:
            for child in desc:
                if not child.tag.endswith("work_has_expression"):
                    continue
                candidate = child.attrib.get(RDF_RESOURCE_ATTR, "")
                if candidate and candidate.endswith(lang_suffixes):
                    expression_uri = candidate
                    break
            if expression_uri:
                break

        if not expression_uri:
            raise Exception(f"No language expression found for CELEX {celex} ({language})")

        expression_root = self._fetch_rdf_root(expression_uri)
        xhtml_manifestation_uri: Optional[str] = None
        fallback_manifestation_uri: Optional[str] = None
        for desc in expression_root:
            for child in desc:
                if not child.tag.endswith("expression_manifested_by_manifestation"):
                    continue
                candidate = child.attrib.get(RDF_RESOURCE_ATTR, "")
                if not candidate:
                    continue
                if candidate.endswith(".xhtml"):
                    xhtml_manifestation_uri = candidate
                    break
                fallback_manifestation_uri = fallback_manifestation_uri or candidate
            if xhtml_manifestation_uri:
                break

        manifestation_uri = xhtml_manifestation_uri or fallback_manifestation_uri
        if not manifestation_uri:
            raise Exception(f"No manifestation found for CELEX {celex} ({expression_uri})")
        if not manifestation_uri.endswith(".xhtml"):
            raise Exception(
                f"No XHTML manifestation found for CELEX {celex}; got {manifestation_uri}"
            )

        manifestation_root = self._fetch_rdf_root(manifestation_uri)
        item_url: Optional[str] = None
        for desc in manifestation_root:
            about = desc.attrib.get(RDF_ABOUT_ATTR, "")
            if about.endswith("/DOC_1"):
                item_url = about
                break
        if not item_url:
            raise Exception(f"No DOC_1 item found for CELEX {celex} ({manifestation_uri})")
        return item_url

    def _extract_title_from_xhtml(self, soup: BeautifulSoup) -> Optional[str]:
        candidates: List[str] = []
        for elem in soup.select("p.oj-doc-ti"):
            text = elem.get_text(" ", strip=True)
            if text:
                candidates.append(text)
        if candidates:
            # Prefer the longest title-like line (usually the full act title in OJ XHTML).
            candidates = [c for c in candidates if len(c) >= 20]
            if candidates:
                return max(candidates, key=len)

        title_elem = soup.find("title")
        if title_elem:
            text = title_elem.get_text(" ", strip=True)
            if text:
                return text
        return None

    def _parse_articles_from_text(self, celex: str, full_text: str) -> Dict[str, str]:
        if not full_text:
            return {}

        operative_text = full_text
        start_match = re.search(
            r"HAVE\s+ADOPTED\s+THIS\s+(REGULATION|DIRECTIVE|DECISION)\s*:?\s*",
            full_text,
            flags=re.IGNORECASE,
        )
        if start_match:
            operative_text = full_text[start_match.start() :]

        try:
            from src.services.article_chunker import ArticleChunker

            chunks = ArticleChunker()._parse_from_text(
                doc_id=0, celex=celex, full_text=operative_text
            )
        except Exception:
            chunks = []

        articles: Dict[str, str] = {}
        for chunk in chunks:
            article_num = str(getattr(chunk, "article_number", "") or "")
            if not article_num or article_num == "FULL":
                continue
            content = str(getattr(chunk, "content", "") or "").strip()
            if not content:
                continue
            if article_num not in articles:
                articles[article_num] = content
        return articles

    def _parse_xhtml_document(self, celex: str, xhtml_text: str) -> Dict:
        soup = BeautifulSoup(xhtml_text, "html.parser")
        for elem in soup(["script", "style"]):
            elem.decompose()

        title = self._extract_title_from_xhtml(soup)
        full_text = soup.get_text(separator="\n", strip=True)
        full_text = (full_text or "").replace("\xa0", " ")
        full_text = re.sub(r"[ \t]+\n", "\n", full_text)
        full_text = re.sub(r"\n{3,}", "\n\n", full_text).strip()

        articles = self._parse_articles_from_text(celex, full_text)

        return {
            "title": title,
            "articles": articles,
            "full_text": full_text,
            "word_count": len(full_text.split()),
        }

    def _extract_cellar_xhtml(self, celex: str, language: str) -> Optional[Dict]:
        """Extract from CELLAR XHTML endpoint."""
        url = f"https://publications.europa.eu/resource/celex/{celex}?language={quote(language)}"

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

        if self._looks_like_rdf(resp):
            logger.info(
                "CELLAR CELEX endpoint returned RDF for %s; resolving XHTML manifestation via RDF graph",
                celex,
            )
            item_url = self._resolve_publications_office_xhtml_item(celex, language)
            item_resp = self.session.get(item_url, timeout=60)
            item_resp.raise_for_status()
            return self._parse_xhtml_document(celex, item_resp.text)

        return self._parse_xhtml_document(celex, resp.text)

    def _extract_eurlex_html(self, celex: str, language: str) -> Optional[Dict]:
        """Extract from EUR-Lex HTML document page."""
        url = f"https://eur-lex.europa.eu/legal-content/{language.upper()}/TXT/HTML/?uri=CELEX:{celex}"

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        if resp.status_code == 202:
            raise Exception("EUR-Lex HTML endpoint returned 202 placeholder")

        soup = BeautifulSoup(resp.text, "html.parser")

        for elem in soup(["script", "style", "nav", "header", "footer"]):
            elem.decompose()

        title = None
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

        main = soup.find("main") or soup.find("div", id="text") or soup.find("body")
        if not main:
            raise Exception("No content area found")

        full_text = main.get_text(separator="\n", strip=True)

        return {
            "title": title,
            "articles": {},
            "full_text": full_text,
            "word_count": len(full_text.split()),
        }

    def _extract_eurlex_summary(self, celex: str, language: str) -> Optional[Dict]:
        """Extract summary/metadata from EUR-Lex."""
        url = f"https://eur-lex.europa.eu/legal-content/{language.upper()}/SUM/?uri=CELEX:{celex}"

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        if resp.status_code == 202:
            raise Exception("EUR-Lex summary endpoint returned 202 placeholder")

        soup = BeautifulSoup(resp.text, "html.parser")
        full_text = soup.get_text(separator="\n", strip=True)

        return {
            "title": None,
            "articles": {},
            "full_text": full_text,
            "word_count": len(full_text.split()),
        }


# Legacy compatibility
class ContentExtractor(ContentExtractorV2):
    """Backwards-compatible wrapper."""

    def extract_content(self, celex: str, language: str = "EN") -> Optional[Dict]:
        result = self.extract(celex, language=language)
        if result:
            article_breakdown = [
                {"number": str(article_num), "content": article_text}
                for article_num, article_text in (result.articles or {}).items()
            ]
            return {
                "title": result.title,
                "articles": result.articles,
                "article_breakdown": article_breakdown,
                "full_text": result.full_text,
                "word_count": result.word_count,
                "extraction_method": result.strategy,
            }
        return None
