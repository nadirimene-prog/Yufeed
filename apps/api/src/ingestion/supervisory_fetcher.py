"""
Specialized fetchers for EU Supervisory Authorities.

Handles AMLA, ESMA, EBA, and national regulators with custom parsing.
"""

import logging
from typing import List, Dict, Any, Optional
import feedparser
import httpx
from bs4 import BeautifulSoup
from datetime import datetime

logger = logging.getLogger(__name__)


class AMLAFetcher:
    """Fetcher for AMLA (Anti-Money Laundering Authority) news."""

    BASE_URL = "https://www.amla.europa.eu"
    RSS_URL = "https://www.amla.europa.eu/news_en/rss"

    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch AMLA news and publications."""
        logger.info("Fetching AMLA news...")

        try:
            feed = feedparser.parse(self.RSS_URL)
            entries = []

            for entry in feed.entries:
                # Extract CELEX if mentioned in content
                celex = self._extract_celex(entry)

                entries.append(
                    {
                        "title": entry.get("title", "AMLA Update"),
                        "link": entry.get("link", ""),
                        "description": entry.get("summary", ""),
                        "published": entry.get("published"),
                        "celex": celex,
                        "source_system": "amla",
                        "jurisdiction": "EU",
                        "source_reference": entry.get("link"),
                        "language": "en",
                        "authority_type": "aml_supervisor",
                        "raw_entry": entry,
                    }
                )

            logger.info(f"AMLA: Found {len(entries)} entries")
            return entries

        except Exception as e:
            logger.error(f"AMLA fetch error: {e}")
            return []

    def _extract_celex(self, entry: Any) -> Optional[str]:
        """Try to extract CELEX from entry content."""
        text = str(entry)
        import re

        matches = re.findall(r"3\d{4}[RLDC]\d{4}", text)
        return matches[0] if matches else None


class ESMAFetcher:
    """Fetcher for ESMA Digital Finance & MiCA updates."""

    BASE_URL = "https://www.esma.europa.eu"
    RSS_URL = "https://www.esma.europa.eu/rss.xml"

    # Specific MiCA pages to monitor
    MICA_URLS = [
        "https://www.esma.europa.eu/esmas-activities/digital-finance-and-innovation/markets-crypto-assets-regulation-mica",
    ]

    def fetch(self) -> List[Dict[str, Any]]:
        """Fetch ESMA updates, focusing on crypto/MiCA."""
        logger.info("Fetching ESMA updates...")

        entries = []

        # Fetch RSS
        try:
            feed = feedparser.parse(self.RSS_URL)

            for entry in feed.entries:
                title = entry.get("title", "")
                summary = entry.get("summary", "")

                # Filter for crypto/MiCA/AML relevant content
                if self._is_relevant(title, summary):
                    entries.append(
                        {
                            "title": f"[ESMA] {title}",
                            "link": entry.get("link", ""),
                            "description": summary,
                            "published": entry.get("published"),
                            "celex": self._extract_celex(entry),
                            "source_system": "esma",
                            "jurisdiction": "EU",
                            "source_reference": entry.get("link"),
                            "language": "en",
                            "authority_type": "securities_supervisor",
                            "topics": self._extract_topics(title, summary),
                            "raw_entry": entry,
                        }
                    )

        except Exception as e:
            logger.error(f"ESMA RSS fetch error: {e}")

        logger.info(f"ESMA: Found {len(entries)} relevant entries")
        return entries

    def _is_relevant(self, title: str, summary: str) -> bool:
        """Check if entry is relevant to crypto/AML."""
        keywords = [
            "crypto",
            "mica",
            "aml",
            "cft",
            "terrorist financing",
            "digital finance",
            "blockchain",
            "token",
            "asset-referenced",
            "casp",
            "crypto-asset",
            "stablecoin",
            "e-money token",
        ]
        text = f"{title} {summary}".lower()
        return any(kw in text for kw in keywords)

    def _extract_topics(self, title: str, summary: str) -> List[str]:
        """Extract topics from content."""
        topics = []
        text = f"{title} {summary}".lower()

        topic_map = {
            "mica": "MiCA",
            "crypto": "Crypto-Assets",
            "aml": "AML",
            "cft": "CFT",
            "stablecoin": "Stablecoins",
            "token": "Tokens",
            "authorization": "Authorization",
            "technical standard": "Technical Standards",
        }

        for keyword, topic in topic_map.items():
            if keyword in text:
                topics.append(topic)

        return topics

    def _extract_celex(self, entry: Any) -> Optional[str]:
        """Extract CELEX from entry."""
        text = str(entry)
        import re

        matches = re.findall(r"3\d{4}[RLD]\d{4}", text)
        return matches[0] if matches else None


class NationalFIUFetcher:
    """Fetcher for national Financial Intelligence Units."""

    SOURCES = {
        "tracfin": {
            "name": "TRACFIN France",
            "url": "https://www.economie.gouv.fr/tracfin/rss",
            "jurisdiction": "FR",
            "language": "fr",
        },
    }

    def fetch(self, source_key: str = "tracfin") -> List[Dict[str, Any]]:
        """Fetch FIU updates."""
        if source_key not in self.SOURCES:
            logger.warning(f"Unknown FIU source: {source_key}")
            return []

        config = self.SOURCES[source_key]
        logger.info(f"Fetching {config['name']}...")

        try:
            feed = feedparser.parse(config["url"])
            entries = []

            for entry in feed.entries:
                entries.append(
                    {
                        "title": entry.get("title", f"{config['name']} Update"),
                        "link": entry.get("link", ""),
                        "description": entry.get("summary", ""),
                        "published": entry.get("published"),
                        "celex": None,  # FIUs rarely reference CELEX directly
                        "source_system": source_key,
                        "jurisdiction": config["jurisdiction"],
                        "source_reference": entry.get("link"),
                        "language": config["language"],
                        "authority_type": "fiu",
                        "raw_entry": entry,
                    }
                )

            logger.info(f"{config['name']}: Found {len(entries)} entries")
            return entries

        except Exception as e:
            logger.error(f"{config['name']} fetch error: {e}")
            return []


class SupervisoryAggregator:
    """Aggregates updates from all supervisory authorities."""

    def __init__(self):
        self.amla = AMLAFetcher()
        self.esma = ESMAFetcher()
        self.fiu = NationalFIUFetcher()

    def fetch_all(self) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch from all supervisory sources."""
        return {
            "amla": self.amla.fetch(),
            "esma": self.esma.fetch(),
            "tracfin": self.fiu.fetch("tracfin"),
        }

    def fetch_by_jurisdiction(self, jurisdiction: str) -> List[Dict[str, Any]]:
        """Fetch sources for specific jurisdiction."""
        all_entries = []

        mapping = {
            "EU": ["amla", "esma"],
            "FR": ["tracfin"],
        }

        for source in mapping.get(jurisdiction, []):
            if source == "amla":
                all_entries.extend(self.amla.fetch())
            elif source == "esma":
                all_entries.extend(self.esma.fetch())
            elif source == "tracfin":
                all_entries.extend(self.fiu.fetch("tracfin"))

        return all_entries
