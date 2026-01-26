from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set
import re
import httpx
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from src.ingestion.cellar import CellarClient
from src.utils.celex_utils import normalize_celex


class EurLexSearchFetcher:
    def __init__(self):
        self.cellar = CellarClient()
        self.http = httpx.Client(timeout=30.0, follow_redirects=True)
        self.search_base_url = "https://eur-lex.europa.eu/search.html"

    def search_terms(
        self,
        terms: Iterable[str],
        language: str,
        limit: int,
        offset: int,
        require_language: bool = True,
    ) -> List[Dict[str, Any]]:
        terms_list = [term for term in terms if term and term.strip()]
        results = self.cellar.search_by_title_terms(
            terms=terms_list,
            language=language,
            limit=limit,
            offset=offset,
            require_language=require_language,
        )
        if results:
            return results

        celexes = self._search_html_celex(terms_list, language=language, page=self._page_from_offset(limit, offset))
        if not celexes:
            return []

        metadata_map = self.cellar.query_bulk_celex(sorted(celexes), use_cache=True)
        return [meta for meta in metadata_map.values() if meta]

    def _page_from_offset(self, limit: int, offset: int) -> int:
        if limit <= 0:
            return 1
        return int(offset / limit) + 1

    def _search_html_celex(self, terms: List[str], language: str, page: int = 1) -> Set[str]:
        celexes: Set[str] = set()
        if not terms:
            return celexes

        language = (language or "en").lower()
        for term in terms:
            params = {
                "scope": "EURLEX",
                "text": term,
                "lang": language,
                "type": "quick",
                "page": str(page),
            }
            url = f"{self.search_base_url}?{urlencode(params)}"
            try:
                response = self.http.get(url, headers={"User-Agent": "Yufeed/1.0"})
                response.raise_for_status()
                celexes.update(self._extract_celexes(response.text))
            except Exception:
                continue
        return celexes

    @staticmethod
    def _extract_celexes(html: str) -> Set[str]:
        celexes: Set[str] = set()
        if not html:
            return celexes

        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)
        for link in links:
            href = link.get("href") or ""
            for match in re.findall(r"CELEX[:=]([0-9A-Z]{6,})", href.upper()):
                normalized = normalize_celex(match, log=False)
                if normalized:
                    celexes.add(normalized)
            for match in re.findall(r"uri=CELEX%3A([0-9A-Z]{6,})", href.upper()):
                normalized = normalize_celex(match, log=False)
                if normalized:
                    celexes.add(normalized)
        return celexes

    @staticmethod
    def to_entry(metadata: Dict[str, Any], language: str) -> Dict[str, Any]:
        celex = metadata.get("celex")
        title = metadata.get("title") or metadata.get("celex") or "Untitled document"
        publication_date = metadata.get("date_document")
        if hasattr(publication_date, "isoformat"):
            publication_date = publication_date.isoformat()

        language = (language or "en").lower()
        language_upper = language.upper()
        source_url = f"https://eur-lex.europa.eu/legal-content/{language_upper}/ALL/?uri=CELEX:{celex}"

        return {
            "title": title,
            "link": source_url,
            "description": "",
            "published": publication_date,
            "celex": celex,
            "eli": metadata.get("eli"),
            "language": language,
            "source_system": "eur-lex",
            "jurisdiction": "EU",
            "source_reference": source_url,
            "metadata_only": True,
            "raw_entry": metadata,
        }
