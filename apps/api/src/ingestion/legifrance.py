import feedparser
import hashlib
import logging
from typing import List, Dict, Any

from src.config import settings

logger = logging.getLogger(__name__)


class LegifranceFetcher:
    """
    Basic RSS ingestion for Légifrance.

    Uses a configurable RSS URL. If LEGIFRANCE_JORF_RSS_URL is empty,
    this source is skipped.
    """

    def __init__(self):
        self.rss_url = settings.LEGIFRANCE_JORF_RSS_URL

    def fetch_latest(self) -> List[Dict[str, Any]]:
        if not self.rss_url:
            logger.info("LEGIFRANCE_JORF_RSS_URL not configured; skipping.")
            return []

        logger.info(f"Fetching Légifrance RSS feed: {self.rss_url}")
        try:
            feed = feedparser.parse(self.rss_url, agent=settings.RSS_USER_AGENT)
            if feed.bozo:
                logger.warning(f"Légifrance RSS parse warning: {feed.bozo_exception}")

            entries = []
            for entry in feed.entries:
                entries.append(self._normalize_entry(entry))
            return entries
        except Exception as exc:
            logger.error(f"Failed to fetch Légifrance RSS: {exc}")
            return []

    def _normalize_entry(self, entry: Any) -> Dict[str, Any]:
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", "Sans titre")
        description = getattr(entry, "description", "")
        published = getattr(entry, "published", None)
        guid = getattr(entry, "id", None) or getattr(entry, "guid", None)

        source_reference = guid or link or title
        digest = hashlib.sha1(source_reference.encode("utf-8")).hexdigest()[:12].upper()
        legal_id = f"FR-{digest}"

        return {
            "title": title,
            "link": link,
            "description": description,
            "published": published,
            "celex": legal_id,
            "language": "fr",
            "source_system": "legifrance",
            "jurisdiction": "FR",
            "source_reference": source_reference,
            "raw_entry": entry,
        }
