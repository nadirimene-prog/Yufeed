import logging
import datetime
from sqlalchemy.orm import Session
from src.models import LegalDocument, LegalVersion, AlertEventType, VersionKind
from src.ingestion.cellar import CellarClient
from src.ingestion.rss import RSSFetcher
from src.ingestion.content_extractor import ContentExtractor
from src.search import index_document

logger = logging.getLogger(__name__)

class IngestionProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.cellar = CellarClient()
        self.content_extractor = ContentExtractor()

    def process_entry(self, entry: dict):
        """
        Process a single normalized RSS entry.
        """
        celex = entry.get("celex")
        if not celex:
            logger.warning(f"Skipping entry without CELEX: {entry.get('link')}")
            return

        # Check if exists
        existing_doc = self.db.query(LegalDocument).filter(LegalDocument.celex == celex).first()
        
        if existing_doc:
            self._handle_existing_doc(existing_doc, entry)
        else:
            self._handle_new_doc(celex, entry)

    def _handle_new_doc(self, celex: str, entry: dict):
        logger.info(f"New document detected: {celex}")

        # Try to enrich with CELLAR metadata
        cellar_metadata = None
        try:
            cellar_metadata = self.cellar.query_by_celex(celex)
        except Exception as e:
            logger.warning(f"Failed to fetch CELLAR metadata for {celex}: {e}")

        # Instantiate doc with RSS data + CELLAR enrichment
        title = entry.get("title")
        pub_date = self._parse_date(entry.get("published"))
        entry_into_force = None
        eli = None
        cellar_id = None
        doc_type = None

        if cellar_metadata:
            # Prefer CELLAR data when available
            if cellar_metadata.get("title"):
                title = cellar_metadata["title"]
            if cellar_metadata.get("date_document"):
                pub_date = cellar_metadata["date_document"]
            entry_into_force = cellar_metadata.get("date_entry_into_force")
            eli = cellar_metadata.get("eli")
            cellar_id = cellar_metadata.get("cellar_id")

            # Extract document type from work_type URI
            work_type = cellar_metadata.get("work_type", "")
            if "regulation" in work_type.lower():
                doc_type = "regulation"
            elif "directive" in work_type.lower():
                doc_type = "directive"
            elif "decision" in work_type.lower():
                doc_type = "decision"

        new_doc = LegalDocument(
            celex=celex,
            eli=eli,
            cellar_id=cellar_id,
            title=title,
            type=doc_type,
            status="active",
            publication_date=pub_date,
            entry_into_force_date=entry_into_force,
            last_modified=datetime.datetime.utcnow()
        )

        self.db.add(new_doc)
        self.db.commit()
        self.db.refresh(new_doc)

        # Extract document content
        try:
            logger.info(f"Extracting content for {celex}")
            content_result = self.content_extractor.extract_content(celex)

            if content_result and content_result.get("full_text"):
                new_doc.full_text = content_result["full_text"]
                new_doc.article_breakdown = {"articles": content_result.get("article_breakdown", [])}
                new_doc.content_extraction_method = content_result.get("extraction_method")
                new_doc.content_extracted_at = datetime.datetime.utcnow()
                new_doc.word_count = content_result.get("word_count")

                logger.info(f"Content extracted for {celex}: {new_doc.word_count} words via {new_doc.content_extraction_method}")
                self.db.commit()

                # Index document in OpenSearch
                try:
                    index_document(new_doc)
                    logger.info(f"Document {celex} indexed in OpenSearch")
                except Exception as idx_err:
                    logger.warning(f"Failed to index {celex} in OpenSearch: {idx_err}")

        except Exception as e:
            logger.warning(f"Content extraction failed for {celex}: {e}")

        # Store related documents if found via CELLAR
        if cellar_id:
            try:
                relations = self.cellar.get_related_documents(cellar_id)
                for relation in relations:
                    # Store in database (requires LegalRelation handling)
                    # For now just log
                    logger.info(f"Found relation: {celex} {relation['relation_type']} {relation['related_celex']}")
            except Exception as e:
                logger.warning(f"Failed to fetch relations for {celex}: {e}")

        # Create Alert - REMOVED (Legacy AlertEvent model missing)
        # alert = AlertEvent(
        #     doc_id=new_doc.id,
        #     event_type=AlertEventType.NEW_DOC,
        #     detected_at=datetime.datetime.utcnow()
        # )
        # self.db.add(alert)

        # Create Initial Version
        version = LegalVersion(
            doc_id=new_doc.id,
            kind=VersionKind.INITIAL,
            language="en",
            source_url=entry.get("link")
        )
        self.db.add(version)
        self.db.commit()
        logger.info(f"Created new document {celex} with ID {new_doc.id}")

    def _handle_existing_doc(self, doc: LegalDocument, entry: dict):
        # Check for changes
        # Simple Logic: If the RSS entry suggests a modification or if we want to periodically update.
        # For now, we will log that we saw it.
        # If we had a hash of the content, we would compare it here.
        
        # Check if title changed (simple heuristic)
        if doc.title != entry.get("title") and entry.get("title"):
             logger.info(f"Document {doc.celex} title updated.")
             doc.title = entry.get("title")
             doc.last_modified = datetime.datetime.utcnow()
             
             # alert = AlertEvent(
             #    doc_id=doc.id,
             #    event_type=AlertEventType.UPDATED_DOC,
             #    detected_at=datetime.datetime.utcnow()
             # )
             # self.db.add(alert)
             self.db.commit()

    def _parse_date(self, date_obj):
        # date_obj from feedparser is struct_time usually, or None
        if not date_obj:
            return None
        if isinstance(date_obj, str):
            # Try parsing isoformat
            try:
                return datetime.datetime.fromisoformat(date_obj)
            except:
                return None
        # feedparser struct_time
        try:
             return datetime.datetime(*date_obj[:6])
        except:
            return None
