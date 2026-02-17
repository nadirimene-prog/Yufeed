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
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


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

    def _extract_cellar_xhtml(self, celex: str, language: str) -> Optional[Dict]:
        """Extract from CELLAR XHTML endpoint."""
        url = f"https://publications.europa.eu/resource/celex/{celex}?language={language}"

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        title = None
        title_elem = soup.find("p", class_="oj-doc-ti") or soup.find("title")
        if title_elem:
            title = title_elem.get_text(strip=True)

        articles = {}
        article_divs = soup.find_all("div", class_=re.compile("art.*", re.I))

        for art_div in article_divs:
            num_elem = art_div.find("p", class_=re.compile("art-ti.*", re.I))
            if num_elem:
                art_num = num_elem.get_text(strip=True)
                art_text = art_div.get_text(separator="\n", strip=True)
                articles[art_num] = art_text

        full_text_parts = []
        if title:
            full_text_parts.append(f"TITLE: {title}\n\n")
        for num, text in sorted(articles.items()):
            full_text_parts.append(f"ARTICLE {num}\n{text}\n\n")

        full_text = "".join(full_text_parts)

        return {
            "title": title,
            "articles": articles,
            "full_text": full_text,
            "word_count": len(full_text.split()),
        }

    def _extract_eurlex_html(self, celex: str, language: str) -> Optional[Dict]:
        """Extract from EUR-Lex HTML document page."""
        url = f"https://eur-lex.europa.eu/legal-content/{language}/TXT/HTML/?uri=CELEX:{celex}"

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

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
        url = f"https://eur-lex.europa.eu/legal-content/{language}/SUM/?uri=CELEX:{celex}"

        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()

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
            return {
                "title": result.title,
                "articles": result.articles,
                "full_text": result.full_text,
                "word_count": result.word_count,
            }
        return None
