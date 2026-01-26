import feedparser
import logging
import re
from datetime import date
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode
from xml.etree import ElementTree

import httpx
from bs4 import BeautifulSoup

from src.config import settings

logger = logging.getLogger(__name__)

class RSSFetcher:
    # Official Journal feeds (generic placeholders, often use search RSS)
    # For MVP we can use the direct feed URLs if they are stable
    OJ_L_FEED = "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=en"
    OJ_C_FEED = "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=C&lang=en"
    CELLAR_INGESTION_URL = "https://publications.europa.eu/webapi/notification/ingestion"
    
    def fetch_feed(self, url: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Fetch and parse a single RSS feed.
        Returns a list of dictionaries with normalized keys.
        """
        logger.info(f"Fetching RSS feed: {url}")
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": settings.RSS_USER_AGENT},
                timeout=15.0,
            )
            response.raise_for_status()
            content = response.text

            feed = feedparser.parse(content)
            if feed.bozo:
                logger.warning(f"Feed parse warning for {url}: {feed.bozo_exception}")
            
            entries = []
            for entry in feed.entries:
                entries.append(self._normalize_entry(entry, language=language))
            if entries:
                return entries

            # Fallback for malformed feeds (EUR-Lex often returns invalid XML)
            fallback_entries = self._parse_rss_fallback(content, language=language)
            if fallback_entries:
                logger.info(f"Fallback parser recovered {len(fallback_entries)} entries for {url}")
            return fallback_entries
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
            return []

    def get_latest_oj_entries(
        self,
        language: str = "en",
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get combined entries from OJ L and C series feeds.
        """
        # Prefer CELLAR ingestion feed (more stable than legacy EUR-Lex RSS).
        return self.fetch_cellar_ingestion(
            language=language,
            start_date=start_date,
            end_date=end_date,
            only_oj=True,
            allow_fallback=True,
        )

    def fetch_cellar_ingestion(
        self,
        language: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        only_oj: bool = True,
        allow_fallback: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Fetch EU publications ingestion feed from CELLAR and filter to OJ L/C items.
        """
        params = {}
        if start_date:
            params["startDate"] = start_date.isoformat()
        if end_date:
            params["endDate"] = end_date.isoformat()
        params["wemiClasses"] = "work"

        url = f"{self.CELLAR_INGESTION_URL}?{urlencode(params)}" if params else self.CELLAR_INGESTION_URL
        logger.info(f"Fetching CELLAR ingestion feed: {url}")
        try:
            response = httpx.get(
                url,
                headers={"User-Agent": settings.RSS_USER_AGENT, "Accept": "application/rss+xml"},
                timeout=30.0,
            )
            response.raise_for_status()
            content = response.text
            entries = self._parse_cellar_ingestion_feed(content, language=language)
            if only_oj:
                oj_entries = [entry for entry in entries if entry.get("is_oj")]
                if oj_entries:
                    return oj_entries
                if allow_fallback and entries:
                    logger.warning(
                        "No OJ-tagged entries detected in CELLAR feed; "
                        "falling back to all EU entries to avoid missing updates."
                    )
                    return entries
                return oj_entries
            return entries
        except Exception as e:
            logger.error(f"Error fetching CELLAR ingestion feed {url}: {e}")
            return []

    def _oj_feed(self, url: str, language: str) -> str:
        if "lang=" in url:
            return re.sub(r"lang=[a-z]+", f"lang={language}", url, flags=re.IGNORECASE)
        return url
        
    def _normalize_entry(self, entry: Any, language: str = "en") -> Dict[str, Any]:
        """
        Extract relevant fields and attempt to find identifiers.
        """
        link = getattr(entry, "link", "")
        title = getattr(entry, "title", "No Title")
        description = getattr(entry, "description", "")
        published = getattr(entry, "published", None)
        
        # extraction logic
        celex = self._extract_celex(link) or self._extract_celex(description)
        eli = self._extract_eli(link) or self._extract_eli(description)
        
        return {
            "title": title,
            "link": link,
            "description": description,
            "published": published,
            "celex": celex,
            "eli": eli,
            "language": language,
            "source_system": "eur-lex",
            "jurisdiction": "EU",
            "source_reference": link,
            "raw_entry": entry
        }

    def _parse_rss_fallback(self, content: str, language: str = "en") -> List[Dict[str, Any]]:
        """
        Fallback parser for malformed RSS/Atom feeds.
        Uses BeautifulSoup (html.parser) to extract item/entry fields.
        """
        if not content:
            return []

        soup = BeautifulSoup(content, "html.parser")
        items = soup.find_all(["item", "entry"])
        entries: List[Dict[str, Any]] = []

        for item in items:
            title_tag = item.find("title")
            link_tag = item.find("link")
            desc_tag = item.find("description") or item.find("summary") or item.find("content")
            pub_tag = item.find("pubdate") or item.find("published") or item.find("updated")

            link = ""
            if link_tag:
                link = link_tag.get("href") or (link_tag.text or "").strip()

            title = (title_tag.text or "").strip() if title_tag else "No Title"
            description = (desc_tag.text or "").strip() if desc_tag else ""
            published = (pub_tag.text or "").strip() if pub_tag else None

            celex = self._extract_celex(link) or self._extract_celex(description)
            eli = self._extract_eli(link) or self._extract_eli(description)

            entries.append(
                {
                    "title": title,
                    "link": link,
                    "description": description,
                    "published": published,
                    "celex": celex,
                    "eli": eli,
                    "language": language,
                    "source_system": "eur-lex",
                    "jurisdiction": "EU",
                    "source_reference": link,
                    "raw_entry": item,
                }
            )

        return entries

    def _parse_cellar_ingestion_feed(self, content: str, language: str) -> List[Dict[str, Any]]:
        """
        Parse CELLAR ingestion RSS and filter to Official Journal L/C entries.
        """
        if not content:
            return []

        try:
            root = ElementTree.fromstring(content)
            return self._parse_cellar_from_xml(root, language=language)
        except Exception as exc:
            logger.warning(f"XML parsing failed for CELLAR feed: {exc}; falling back to HTML parser")
            soup = BeautifulSoup(content, "html.parser")
            return self._parse_cellar_from_soup(soup, language=language)

    def _parse_cellar_from_xml(self, root: ElementTree.Element, language: str) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []

        for elem in root.iter():
            tag = elem.tag.split("}")[-1].lower()
            if tag not in ("item", "entry"):
                continue

            raw_xml = ElementTree.tostring(elem, encoding="unicode")
            celex = self._extract_celex(raw_xml)
            if not celex:
                continue
            eli = self._extract_eli(raw_xml)

            oj_ref = self._extract_oj_reference(raw_xml)
            oj_series = self._extract_oj_series(oj_ref)
            is_oj = bool(oj_ref or oj_series)

            title = self._find_xml_text(elem, ["title"]) or (
                f"Official Journal {oj_ref}" if oj_ref else f"EU publication {celex}"
            )
            published = self._find_xml_text(elem, ["pubdate", "published", "updated", "date"])

            link = self._find_xml_link(elem) or f"https://eur-lex.europa.eu/legal-content/{language.upper()}/TXT/?uri=CELEX:{celex}"

            entries.append(
                {
                    "title": title,
                    "link": link,
                    "description": f"OJ reference: {oj_ref}" if oj_ref else "EU publication",
                    "published": published,
                    "celex": celex,
                    "eli": eli,
                    "language": language,
                    "source_system": "eur-lex",
                    "jurisdiction": "EU",
                    "source_reference": oj_ref or link or celex,
                    "oj_ref": oj_ref,
                    "oj_series": oj_series,
                    "is_oj": is_oj,
                    "raw_entry": raw_xml,
                }
            )

        return entries

    def _parse_cellar_from_soup(self, soup: BeautifulSoup, language: str) -> List[Dict[str, Any]]:
        entries: List[Dict[str, Any]] = []
        items = soup.find_all(["item", "entry"])

        for item in items:
            raw = str(item)
            celex = self._extract_celex(raw)
            if not celex:
                continue
            eli = self._extract_eli(raw)
            oj_ref = self._extract_oj_reference(raw)
            oj_series = self._extract_oj_series(oj_ref)
            is_oj = bool(oj_ref or oj_series)

            title_tag = item.find("title")
            pub_tag = item.find("pubdate") or item.find("published") or item.find("updated")

            link_tag = item.find("link")
            link = ""
            if link_tag:
                link = link_tag.get("href") or (link_tag.text or "").strip()

            title = (title_tag.text or "").strip() if title_tag else (
                f"Official Journal {oj_ref}" if oj_ref else f"EU publication {celex}"
            )
            published = (pub_tag.text or "").strip() if pub_tag else None

            if not link:
                link = f"https://eur-lex.europa.eu/legal-content/{language.upper()}/TXT/?uri=CELEX:{celex}"

            entries.append(
                {
                    "title": title,
                    "link": link,
                    "description": f"OJ reference: {oj_ref}" if oj_ref else "EU publication",
                    "published": published,
                    "celex": celex,
                    "eli": eli,
                    "language": language,
                    "source_system": "eur-lex",
                    "jurisdiction": "EU",
                    "source_reference": oj_ref or link or celex,
                    "oj_ref": oj_ref,
                    "oj_series": oj_series,
                    "is_oj": is_oj,
                    "raw_entry": raw,
                }
            )

        return entries

    def _find_xml_text(self, elem: ElementTree.Element, names: List[str]) -> Optional[str]:
        for child in elem.iter():
            tag = child.tag.split("}")[-1].lower()
            if tag in names and child.text:
                return child.text.strip()
        return None

    def _find_xml_link(self, elem: ElementTree.Element) -> Optional[str]:
        for child in elem.iter():
            tag = child.tag.split("}")[-1].lower()
            if tag != "link":
                continue
            href = child.attrib.get("href")
            if href:
                return href
            if child.text:
                return child.text.strip()
        return None

    def _extract_oj_reference(self, text: str) -> Optional[str]:
        if not text:
            return None
        patterns = [
            r"oj:(JOL|JOC)_[0-9_]+",
            r"JOL_[0-9_]+",
            r"JOC_[0-9_]+",
            r"OJ\\s*[LC]",
            r"Official Journal",
            r"Journal officiel",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _extract_oj_series(self, oj_ref: Optional[str]) -> Optional[str]:
        if not oj_ref:
            return None
        ref_upper = oj_ref.upper()
        if "JOL" in ref_upper or re.search(r"OJ\\s*L", ref_upper):
            return "L"
        if "JOC" in ref_upper or re.search(r"OJ\\s*C", ref_upper):
            return "C"
        return None

    def _extract_eli(self, text: Optional[str]) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"https?://data\.europa\.eu/eli/[^\s\"<]+", text)
        if match:
            return match.group(0)
        match = re.search(r"eli[:=]\s*(https?://[^\s\"<]+)", text, flags=re.IGNORECASE)
        if match:
            return match.group(1)
        return None
    
    def _extract_celex(self, text: str) -> str:
        """
        Attempt to extract CELEX number from URL or text.
        Common pattern: CELEX:32023R1234
        Or in URL: ...uri=CELEX:32023R1234...
        """
        if not text:
            return None
        patterns = [
            r"CELEX[:=]([0-9A-Z]+)",
            r"celex[:=]([0-9A-Z]+)",
            r"/celex/([0-9A-Z]+)",
            r"celex/([0-9A-Z]+)",
            r"uri=CELEX:([0-9A-Z]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
