import feedparser
import logging
import re
from typing import List, Dict, Any
from src.config import settings

logger = logging.getLogger(__name__)

class RSSFetcher:
    # Official Journal feeds (generic placeholders, often use search RSS)
    # For MVP we can use the direct feed URLs if they are stable
    OJ_L_FEED = "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=L&lang=en"
    OJ_C_FEED = "https://eur-lex.europa.eu/RSS/feed.html?type=OJ&oj=C&lang=en"
    
    def fetch_feed(self, url: str) -> List[Dict[str, Any]]:
        """
        Fetch and parse a single RSS feed.
        Returns a list of dictionaries with normalized keys.
        """
        logger.info(f"Fetching RSS feed: {url}")
        try:
            feed = feedparser.parse(url, agent=settings.RSS_USER_AGENT)
            if feed.bozo:
                logger.warning(f"Feed parse warning for {url}: {feed.bozo_exception}")
            
            entries = []
            for entry in feed.entries:
                entries.append(self._normalize_entry(entry))
            return entries
        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
            return []

    def get_latest_oj_entries(self) -> List[Dict[str, Any]]:
        """
        Get combined entries from OJ L and C series feeds.
        """
        entries = []
        entries.extend(self.fetch_feed(self.OJ_L_FEED))
        entries.extend(self.fetch_feed(self.OJ_C_FEED))
        return entries
        
    def _normalize_entry(self, entry: Any) -> Dict[str, Any]:
        """
        Extract relevant fields and attempt to find identifiers.
        """
        link = getattr(entry, "link", "")
        title = getattr(entry, "title", "No Title")
        description = getattr(entry, "description", "")
        published = getattr(entry, "published", None)
        
        # extraction logic
        celex = self._extract_celex(link) or self._extract_celex(description)
        
        return {
            "title": title,
            "link": link,
            "description": description,
            "published": published,
            "celex": celex,
            "raw_entry": entry
        }
    
    def _extract_celex(self, text: str) -> str:
        """
        Attempt to extract CELEX number from URL or text.
        Common pattern: CELEX:32023R1234
        Or in URL: ...uri=CELEX:32023R1234...
        """
        if not text:
            return None
            
        # Regex for CELEX (simplified) => 3 + year + document type + number
        # e.g., 32023R0901, 32023L0123
        # Strict pattern: [0-9][0-9]{4}[A-Z][0-9]{3,4}
        # But often found as parameter: CELEX:([A-Z0-9]+)
        match = re.search(r"CELEX[:=]([0-9A-Z]+)", text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None
