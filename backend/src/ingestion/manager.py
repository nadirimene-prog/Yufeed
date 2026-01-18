import logging
from sqlalchemy.orm import Session
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
                
        # 2. Watchlist Feeds - REMOVED (Legacy)
        # Transferred to Transaction Monitoring System

        logger.info("Daily ingestion complete.")
