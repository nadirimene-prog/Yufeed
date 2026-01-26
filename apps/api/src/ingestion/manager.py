import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from .rss import RSSFetcher
from .processor import IngestionProcessor
from .legifrance import LegifranceFetcher
from src.config import settings
from src.models import RegulatorySource, IngestionRun

logger = logging.getLogger(__name__)

class IngestionManager:
    def __init__(self, db: Session):
        self.db = db
        self.rss = RSSFetcher()
        self.legifrance = LegifranceFetcher()
        self.processor = IngestionProcessor(db)

    def run_weekly_ingestion(self):
        logger.info("Starting weekly ingestion...")
        end_date = datetime.utcnow().date()
        start_date = (datetime.utcnow() - timedelta(days=7)).date()

        languages = [
            lang.strip().lower()
            for lang in (settings.EURLEX_LANGUAGES or "en,fr").split(",")
            if lang.strip()
        ]
        if not languages:
            languages = ["en"]

        sources = []
        for lang in languages:
            sources.append(
                {
                    "source_key": f"eur-lex-oj-{lang}",
                    "name": f"EUR-Lex Official Journal ({lang.upper()})",
                    "jurisdiction": "EU",
                    "language": lang,
                    "source_type": "rss",
                    "schedule": "weekly",
                    "base_url": "https://eur-lex.europa.eu/RSS/feed.html",
                    "fetch": lambda l=lang, s=start_date, e=end_date: self.rss.get_latest_oj_entries(
                        language=l,
                        start_date=s,
                        end_date=e,
                    ),
                }
            )

        sources.append(
            {
                "source_key": "legifrance-jorf-fr",
                "name": "Légifrance JORF (FR)",
                "jurisdiction": "FR",
                "language": "fr",
                "source_type": "rss",
                "schedule": "weekly",
                "base_url": settings.LEGIFRANCE_JORF_RSS_URL or "",
                "fetch": self.legifrance.fetch_latest,
            }
        )

        for source_config in sources:
            source = self._get_or_create_source(source_config)
            if not source.is_active:
                continue

            run = IngestionRun(
                source_id=source.id,
                status="running",
                started_at=datetime.utcnow(),
            )
            self.db.add(run)
            self.db.commit()

            seen = 0
            created = 0
            updated = 0
            errors = []

            try:
                entries = source_config["fetch"]()
                logger.info(
                    f"{source.source_key}: Found {len(entries)} entries."
                )
                for entry in entries:
                    seen += 1
                    try:
                        result = self.processor.process_entry(entry)
                        if result == "new":
                            created += 1
                        elif result == "updated":
                            updated += 1
                    except Exception as exc:
                        logger.error(
                            f"Error processing entry {entry.get('link')}: {exc}"
                        )
                        errors.append({"error": str(exc), "entry": entry.get("link")})
            except Exception as exc:
                logger.error(f"Ingestion failed for {source.source_key}: {exc}")
                errors.append({"error": str(exc)})

            run.items_seen = seen
            run.items_new = created
            run.items_updated = updated
            run.errors_json = errors or None
            run.completed_at = datetime.utcnow()
            run.status = "failed" if errors else "completed"
            self.db.commit()

            source.last_ingested_at = run.completed_at
            self.db.commit()

        logger.info("Weekly ingestion complete.")

    def run_daily_ingestion(self):
        """
        Backward-compatible alias for older callers.
        """
        logger.warning("run_daily_ingestion is deprecated; use run_weekly_ingestion.")
        self.run_weekly_ingestion()

    def _get_or_create_source(self, config: dict) -> RegulatorySource:
        source = self.db.query(RegulatorySource).filter(
            RegulatorySource.source_key == config["source_key"]
        ).first()
        if source:
            source.name = config["name"]
            source.jurisdiction = config["jurisdiction"]
            source.language = config["language"]
            source.source_type = config["source_type"]
            source.base_url = config["base_url"]
            source.schedule = config.get("schedule", source.schedule)
            source.updated_at = datetime.utcnow()
            self.db.commit()
            return source

        source = RegulatorySource(
            source_key=config["source_key"],
            name=config["name"],
            jurisdiction=config["jurisdiction"],
            language=config["language"],
            source_type=config["source_type"],
            base_url=config["base_url"],
            schedule=config.get("schedule", "weekly"),
            is_active=True,
        )
        self.db.add(source)
        self.db.commit()
        return source
