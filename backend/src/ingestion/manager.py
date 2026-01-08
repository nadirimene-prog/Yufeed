import logging
from sqlalchemy.orm import Session
from src.models import Watchlist
from .rss import RSSFetcher
from .processor import IngestionProcessor

logger = logging.getLogger(__name__)

class IngestionManager:
    def __init__(self, db: Session):
        self.db = db
        self.rss = RSSFetcher()
        self.processor = IngestionProcessor(db)

    def run_daily_ingestion(self):
        logger.info("Starting daily ingestion...")
        
        # 1. Official Journal Feeds (L and C)
        entries = self.rss.get_latest_oj_entries()
        logger.info(f"Found {len(entries)} entries in OJ feeds.")
        
        for entry in entries:
            try:
                self.processor.process_entry(entry)
            except Exception as e:
                logger.error(f"Error processing entry {entry.get('link')}: {e}")
                
        # 2. Watchlist Feeds
        # Iterate over user watchlists that have an RSS URL
        watchlists = self.db.query(Watchlist).filter(Watchlist.rss_url != None).all()
        for watchlist in watchlists:
            logger.info(f"Processing watchlist {watchlist.name} feed: {watchlist.rss_url}")
            try:
                wl_entries = self.rss.fetch_feed(watchlist.rss_url)
                for entry in wl_entries:
                    # TODO: Link alert to watchlist explicitly if needed, currently generic alert
                    # For now just modify processor to handle this context if we want to tag the alert with watchlist_id
                    # We will pass a simple 'source' context if we expand process_entry signature
                    self.processor.process_entry(entry)
            except Exception as e:
                logger.error(f"Error processing watchlist {watchlist.id}: {e}")

        logger.info("Daily ingestion complete.")
