"""
Ingestion Manager - Orchestrates the regulatory document ingestion pipeline.

Features:
- Multi-source ingestion (EUR-Lex, Légifrance)
- Incremental tracking (only processes new documents)
- Error alerting via email
- Retry logic for transient failures
- Parallel processing for improved throughput
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Tuple
from sqlalchemy.orm import Session

from .rss import RSSFetcher
from .processor import IngestionProcessor
from .legifrance import LegifranceFetcher
from .alerts import send_ingestion_report, send_ingestion_failure_alert, IngestionReport
from src.config import settings
from src.ingestion.config import IngestionConfig
from src.models import RegulatorySource, IngestionRun
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


def _parse_start_date(value: Optional[str]) -> Optional[datetime.date]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """
    Execute a function with exponential backoff retry.

    Args:
        func: Function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries (seconds)
        max_delay: Maximum delay between retries (seconds)
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Result of the function

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return func()
        except exceptions as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"All {max_retries + 1} attempts failed: {e}")
                raise

            delay = min(base_delay * (2**attempt), max_delay)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay:.1f}s...")
            time.sleep(delay)

    raise last_exception


class IngestionManager:
    """
    Manages the ingestion of regulatory documents from multiple sources.

    Improvements over basic implementation:
    - Incremental ingestion using last_ingested_at tracking
    - Email alerts on success/failure with detailed reports
    - Retry logic for transient network failures
    - Better error isolation (one source failure doesn't stop others)
    """

    def __init__(self, db: Session):
        self.db = db
        self.rss = RSSFetcher()
        self.legifrance = LegifranceFetcher()
        self.processor = IngestionProcessor(db)

    def run_weekly_ingestion(self, send_alerts: bool = True) -> List[IngestionReport]:
        """
        Run the weekly ingestion process for all configured sources.

        Args:
            send_alerts: Whether to send email alerts on completion

        Returns:
            List of IngestionReport for each source processed
        """
        logger.info("Starting weekly ingestion...")

        # Get configured languages
        languages = self._get_languages()

        # Build source configurations
        sources = self._build_source_configs(languages)

        # Process each source
        reports: List[IngestionReport] = []

        for source_config in sources:
            try:
                report = self._process_source(source_config)
                reports.append(report)
            except Exception as exc:
                logger.error(f"Critical failure for source {source_config['source_key']}: {exc}")
                # Send immediate alert for critical failures
                if send_alerts:
                    send_ingestion_failure_alert(
                        source_name=source_config["name"],
                        error_message=str(exc),
                    )
                # Create failed report
                reports.append(
                    IngestionReport(
                        source_name=source_config["name"],
                        status="failed",
                        started_at=utc_now(),
                        completed_at=utc_now(),
                        items_seen=0,
                        items_new=0,
                        items_updated=0,
                        items_skipped=0,
                        errors=[{"error": str(exc), "entry": "N/A"}],
                    )
                )

        # Send consolidated report
        if send_alerts and reports:
            send_ingestion_report(reports)

        logger.info("Weekly ingestion complete.")
        return reports

    def run_daily_ingestion(self):
        """Backward-compatible alias for older callers."""
        logger.warning("run_daily_ingestion is deprecated; use run_weekly_ingestion.")
        return self.run_weekly_ingestion()

    def _get_languages(self) -> List[str]:
        """Get configured languages for ingestion."""
        languages = [
            lang.strip().lower()
            for lang in (settings.EURLEX_LANGUAGES or "en,fr").split(",")
            if lang.strip()
        ]
        return languages if languages else ["en"]

    def _build_source_configs(self, languages: List[str]) -> List[Dict[str, Any]]:
        """Build configuration for all ingestion sources."""
        sources = []

        # EUR-Lex sources (one per language)
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
                    "fetch": lambda s, e, l=lang: self.rss.get_latest_oj_entries(
                        language=l,
                        start_date=s,
                        end_date=e,
                    ),
                }
            )

        # Légifrance source (French legal gazette)
        if settings.LEGIFRANCE_JORF_RSS_URL:
            sources.append(
                {
                    "source_key": "legifrance-jorf-fr",
                    "name": "Légifrance JORF (FR)",
                    "jurisdiction": "FR",
                    "language": "fr",
                    "source_type": "rss",
                    "schedule": "weekly",
                    "base_url": settings.LEGIFRANCE_JORF_RSS_URL,
                    "fetch": lambda s, e: self.legifrance.fetch_latest(),
                }
            )

        return sources

    def _process_source(
        self,
        source_config: Dict[str, Any],
        start_date: Optional[datetime.date] = None,
        end_date: Optional[datetime.date] = None,
    ) -> IngestionReport:
        """
        Process a single ingestion source.

        Args:
            source_config: Configuration dict for the source

        Returns:
            IngestionReport with results
        """
        source_key = source_config["source_key"]
        logger.info(f"Processing source: {source_key}")

        # Get or create source record
        source = self._get_or_create_source(source_config)

        # Resolve incremental date range
        resolved_end = end_date or utc_now().date()
        if start_date:
            resolved_start = start_date
        elif source.last_ingested_at:
            resolved_start = source.last_ingested_at.date()
        else:
            resolved_start = _parse_start_date(settings.EURLEX_OJ_START_DATE)
            if not resolved_start:
                resolved_start = (utc_now() - timedelta(days=30)).date()

        if not source.is_active:
            logger.info(f"Source {source_key} is inactive, skipping.")
            return IngestionReport(
                source_name=source_config["name"],
                status="skipped",
                started_at=utc_now(),
                completed_at=utc_now(),
                items_seen=0,
                items_new=0,
                items_updated=0,
                items_skipped=0,
                errors=[],
            )

        # Create ingestion run record
        run = IngestionRun(
            source_id=source.id,
            status="running",
            started_at=utc_now(),
        )
        self.db.add(run)
        self.db.commit()

        # Track metrics
        seen = 0
        created = 0
        updated = 0
        skipped = 0
        errors = []

        try:
            # Fetch entries with retry logic
            entries = retry_with_backoff(
                func=lambda: source_config["fetch"](resolved_start, resolved_end),
                max_retries=3,
                base_delay=2.0,
                exceptions=(Exception,),
            )

            logger.info(
                f"{source_key}: Found {len(entries)} entries "
                f"from {resolved_start} to {resolved_end}."
            )

            # Process entries (parallel or sequential based on config)
            parallel_workers = IngestionConfig.PARALLEL_WORKERS
            use_parallel = parallel_workers > 1 and len(entries) > 1

            if use_parallel:
                logger.info(f"Processing {len(entries)} entries with {parallel_workers} workers")
                results = self._process_entries_parallel(entries, parallel_workers)
            else:
                logger.info(f"Processing {len(entries)} entries sequentially")
                results = self._process_entries_sequential(entries)

            # Aggregate results
            for result in results:
                seen += 1
                if result["status"] == "new":
                    created += 1
                elif result["status"] == "updated":
                    updated += 1
                elif result["status"] in ("skipped", "unchanged"):
                    skipped += 1
                elif result["status"] == "error":
                    errors.append({"error": result["error"], "entry": result["entry"]})

        except Exception as exc:
            logger.error(f"Fetch failed for {source_key}: {exc}")
            errors.append({"error": f"Fetch failed: {exc}", "entry": "N/A"})

        # Update run record
        run.items_seen = seen
        run.items_new = created
        run.items_updated = updated
        run.errors_json = errors or None
        run.completed_at = utc_now()
        run.status = "failed" if (errors and seen == 0) else "partial" if errors else "completed"
        self.db.commit()

        # Update source last ingested timestamp
        source.last_ingested_at = run.completed_at
        self.db.commit()

        return IngestionReport(
            source_name=source_config["name"],
            status=run.status,
            started_at=run.started_at,
            completed_at=run.completed_at,
            items_seen=seen,
            items_new=created,
            items_updated=updated,
            items_skipped=skipped,
            errors=errors,
        )

    def _process_entries_sequential(self, entries: List[dict]) -> List[dict]:
        """Process entries one by one (original behavior)."""
        results = []
        for entry in entries:
            result = self._process_single_entry(entry)
            results.append(result)
        return results

    def _process_entries_parallel(self, entries: List[dict], max_workers: int) -> List[dict]:
        """
        Process entries in parallel using ThreadPoolExecutor.

        Note: Each thread creates its own IngestionProcessor with a fresh DB session
        to avoid SQLAlchemy session threading issues.
        """
        from src.database import SessionLocal

        results = []

        def process_with_new_session(entry: dict) -> dict:
            """Process a single entry with its own database session."""
            db = SessionLocal()
            try:
                processor = IngestionProcessor(db)
                try:
                    result = processor.process_entry(entry)
                    return {
                        "status": result,
                        "entry": entry.get("link", entry.get("celex", "unknown")),
                        "error": None,
                    }
                except Exception as exc:
                    entry_link = entry.get("link", entry.get("celex", "unknown"))
                    logger.error(f"Error processing entry {entry_link}: {exc}")
                    return {
                        "status": "error",
                        "entry": entry_link,
                        "error": str(exc),
                    }
            finally:
                db.close()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_entry = {
                executor.submit(process_with_new_session, entry): entry for entry in entries
            }

            # Collect results as they complete
            for future in as_completed(future_to_entry):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    entry = future_to_entry[future]
                    entry_link = entry.get("link", entry.get("celex", "unknown"))
                    logger.error(f"Parallel processing failed for {entry_link}: {exc}")
                    results.append(
                        {
                            "status": "error",
                            "entry": entry_link,
                            "error": str(exc),
                        }
                    )

        return results

    def _process_single_entry(self, entry: dict) -> dict:
        """Process a single entry and return result dict."""
        try:
            result = self.processor.process_entry(entry)
            return {
                "status": result,
                "entry": entry.get("link", entry.get("celex", "unknown")),
                "error": None,
            }
        except Exception as exc:
            entry_link = entry.get("link", entry.get("celex", "unknown"))
            logger.error(f"Error processing entry {entry_link}: {exc}")
            return {
                "status": "error",
                "entry": entry_link,
                "error": str(exc),
            }

    def _get_or_create_source(self, config: Dict[str, Any]) -> RegulatorySource:
        """Get existing source or create new one."""
        source = (
            self.db.query(RegulatorySource)
            .filter(RegulatorySource.source_key == config["source_key"])
            .first()
        )

        if source:
            # Update existing source
            source.name = config["name"]
            source.jurisdiction = config["jurisdiction"]
            source.language = config["language"]
            source.source_type = config["source_type"]
            source.base_url = config["base_url"]
            source.schedule = config.get("schedule", source.schedule)
            source.updated_at = utc_now()
            self.db.commit()
            return source

        # Create new source
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

    def run_manual_ingestion(
        self,
        source_keys: Optional[List[str]] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        send_alerts: bool = False,
    ) -> List[IngestionReport]:
        """
        Run manual ingestion for specific sources or date range.

        Args:
            source_keys: List of source keys to process (None = all)
            start_date: Override start date
            end_date: Override end date
            send_alerts: Whether to send email alerts

        Returns:
            List of IngestionReport
        """
        logger.info(
            f"Starting manual ingestion: sources={source_keys}, dates={start_date}-{end_date}"
        )

        end_dt = end_date or utc_now()
        start_dt = start_date or (end_dt - timedelta(days=30))

        languages = self._get_languages()
        all_sources = self._build_source_configs(languages)

        # Filter to requested sources
        if source_keys:
            sources = [s for s in all_sources if s["source_key"] in source_keys]
        else:
            sources = all_sources

        reports = []
        for source_config in sources:
            try:
                report = self._process_source(
                    source_config,
                    start_date=start_dt.date() if hasattr(start_dt, "date") else start_dt,
                    end_date=end_dt.date() if hasattr(end_dt, "date") else end_dt,
                )
                reports.append(report)
            except Exception as exc:
                logger.error(f"Failed to process {source_config['source_key']}: {exc}")
                reports.append(
                    IngestionReport(
                        source_name=source_config["name"],
                        status="failed",
                        started_at=utc_now(),
                        completed_at=utc_now(),
                        items_seen=0,
                        items_new=0,
                        items_updated=0,
                        items_skipped=0,
                        errors=[{"error": str(exc)}],
                    )
                )

        if send_alerts and reports:
            send_ingestion_report(reports)

        return reports
