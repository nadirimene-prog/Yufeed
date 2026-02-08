"""
Content Backfill Service.

Backfills content for documents that were ingested with metadata only.
This happens when:
- Documents came from search results (metadata_only flag)
- Content extraction failed during initial ingestion
- Documents need content refresh
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from src.models import LegalDocument, LegalDocumentText
from src.ingestion.content_extractor import ContentExtractor
from src.ingestion.title import derive_title_from_text, is_placeholder_title
from src.search import index_document
from src.ai.analyzer import analyze_document
from src.ai.cost_tracker import log_usage_from_analysis
from src.ai.rag_indexer import RAGIndexer
from src.services.obligation_service import seed_obligations_for_doc
from src.compliance.scope import infer_scope_tags
from src.config import settings
from src.utils.time import utc_now

logger = logging.getLogger(__name__)


class ContentBackfillService:
    """
    Service to backfill content for metadata-only documents.

    Finds documents without full_text or with stale content and
    attempts to extract fresh content from EUR-Lex.
    """

    def __init__(self, db: Session):
        self.db = db
        self.extractor = ContentExtractor()
        self.rag_indexer = RAGIndexer(db) if settings.RAG_INDEX_ENABLED else None

    def find_candidates(
        self,
        limit: int = 50,
        language: Optional[str] = None,
        source_system: str = "eur-lex",
    ) -> list:
        """
        Find documents that need content backfill.

        Prioritizes:
        1. Documents with no full_text at all
        2. Documents from specified source system
        3. Documents in preferred language

        Args:
            limit: Maximum number of candidates to return
            language: Preferred language (optional)
            source_system: Source system to filter by

        Returns:
            List of LegalDocument instances
        """
        query = self.db.query(LegalDocument).filter(
            LegalDocument.source_system == source_system,
            or_(
                LegalDocument.full_text.is_(None),
                LegalDocument.full_text == "",
            ),
        )

        if language:
            # Prefer documents in the specified language
            query = query.order_by((LegalDocument.primary_language == language).desc())

        # Prefer newest publications, then newest IDs as a fallback
        order_fields = [
            LegalDocument.publication_date.desc(),
            LegalDocument.id.desc(),
        ]
        query = query.order_by(*order_fields)

        return query.limit(limit).all()

    def backfill_document(
        self,
        doc: LegalDocument,
        language: Optional[str] = None,
        analyze: bool = True,
    ) -> bool:
        """
        Backfill content for a single document.

        Args:
            doc: Document to backfill
            language: Language to extract (defaults to doc.primary_language)
            analyze: Whether to run AI analysis after extraction

        Returns:
            True if content was successfully extracted
        """
        celex = doc.celex
        lang = language or doc.primary_language or "en"

        logger.info(f"Backfilling content for {celex} ({lang})")

        try:
            content_result = self.extractor.extract_content(celex, language=lang)

            if not content_result or not content_result.get("full_text"):
                logger.warning(f"No content extracted for {celex}")
                return False

            # Update main document
            if lang == (doc.primary_language or "en"):
                doc.full_text = content_result["full_text"]
                doc.article_breakdown = {"articles": content_result.get("article_breakdown", [])}
                doc.content_extraction_method = content_result.get("extraction_method")
                doc.content_extracted_at = utc_now()
                doc.word_count = content_result.get("word_count")
                if is_placeholder_title(doc.title):
                    detected = derive_title_from_text(doc.full_text)
                    if detected and not is_placeholder_title(detected):
                        doc.title = detected

            # Create/update language-specific text record
            existing_text = (
                self.db.query(LegalDocumentText)
                .filter(
                    LegalDocumentText.doc_id == doc.id,
                    LegalDocumentText.language == lang,
                )
                .first()
            )

            if existing_text:
                existing_text.full_text = content_result["full_text"]
                existing_text.article_breakdown = {
                    "articles": content_result.get("article_breakdown", [])
                }
                existing_text.content_extraction_method = content_result.get("extraction_method")
                existing_text.content_extracted_at = utc_now()
                existing_text.word_count = content_result.get("word_count")
            else:
                doc_text = LegalDocumentText(
                    doc_id=doc.id,
                    language=lang,
                    full_text=content_result["full_text"],
                    article_breakdown={"articles": content_result.get("article_breakdown", [])},
                    content_extraction_method=content_result.get("extraction_method"),
                    content_extracted_at=utc_now(),
                    word_count=content_result.get("word_count"),
                )
                self.db.add(doc_text)

            self.db.commit()
            logger.info(f"Content backfilled for {celex}: {doc.word_count} words")

            # Index in OpenSearch
            try:
                index_document(doc)
                if self.rag_indexer:
                    self.rag_indexer.index_document(doc)
            except Exception as idx_err:
                logger.warning(f"Failed to index {celex} in OpenSearch: {idx_err}")

            # Run AI analysis if requested
            if analyze:
                try:
                    self._analyze_document(doc)
                except Exception as ai_err:
                    logger.warning(f"AI analysis failed for {celex}: {ai_err}")

            return True

        except Exception as e:
            logger.error(f"Content extraction failed for {celex}: {e}")
            return False

    def _analyze_document(self, doc: LegalDocument):
        """Run AI analysis on a document."""
        article_breakdown = None
        if isinstance(doc.article_breakdown, dict):
            article_breakdown = doc.article_breakdown.get("articles")
        elif isinstance(doc.article_breakdown, list):
            article_breakdown = doc.article_breakdown
        has_full_text = bool(doc.full_text and str(doc.full_text).strip())
        has_articles = bool(article_breakdown)
        if not has_full_text and not has_articles:
            logger.info(f"Skipping AI analysis for {doc.celex}: no content available")
            return

        analysis_results = analyze_document(
            {
                "celex": doc.celex,
                "title": doc.title,
                "publication_date": doc.publication_date,
                "full_text": doc.full_text,
                "article_breakdown": article_breakdown,
            }
        )

        log_usage_from_analysis(self.db, analysis_results, document_id=doc.id)

        doc.compliance_domain = analysis_results.get("compliance_domain")
        doc.risk_level = analysis_results.get("risk_level")
        if not doc.type and analysis_results.get("document_type"):
            doc.type = analysis_results.get("document_type")
        doc.obligations_json = analysis_results.get("obligations_json")
        doc.implementation_deadline = analysis_results.get("implementation_deadline")
        doc.ai_summary = analysis_results.get("ai_summary")
        doc.analyzed_at = analysis_results.get("analyzed_at")
        subject_tags = analysis_results.get("subject_tags")
        if subject_tags:
            doc.subject_tags = subject_tags

        scope_tags = infer_scope_tags(
            doc.title,
            doc.full_text,
            doc.ai_summary,
            doc.obligations_json,
        )
        if scope_tags:
            doc.scope_tags = scope_tags

        self.db.commit()

        # Seed obligations
        seed_obligations_for_doc(self.db, doc, allow_existing=True)

    def backfill_batch(
        self,
        limit: int = 50,
        language: Optional[str] = None,
        analyze: bool = True,
    ) -> dict:
        """
        Backfill content for a batch of documents.

        Args:
            limit: Maximum documents to process
            language: Preferred language
            analyze: Whether to run AI analysis

        Returns:
            Dictionary with stats: processed, filled, errors
        """
        candidates = self.find_candidates(limit=limit, language=language)

        logger.info(f"Found {len(candidates)} documents needing content backfill")

        processed = 0
        filled = 0
        errors = 0

        for doc in candidates:
            processed += 1
            try:
                success = self.backfill_document(doc, language=language, analyze=analyze)
                if success:
                    filled += 1
            except Exception as e:
                logger.error(f"Backfill failed for {doc.celex}: {e}")
                errors += 1

        return {
            "processed": processed,
            "filled": filled,
            "errors": errors,
        }

    def get_backfill_stats(self) -> dict:
        """
        Get statistics about documents needing backfill.
        """
        from sqlalchemy import func

        total = self.db.query(func.count(LegalDocument.id)).scalar()

        needs_content = (
            self.db.query(func.count(LegalDocument.id))
            .filter(
                or_(
                    LegalDocument.full_text.is_(None),
                    LegalDocument.full_text == "",
                )
            )
            .scalar()
        )

        needs_analysis = (
            self.db.query(func.count(LegalDocument.id))
            .filter(
                LegalDocument.full_text.isnot(None),
                LegalDocument.analyzed_at.is_(None),
            )
            .scalar()
        )

        return {
            "total_documents": total,
            "needs_content": needs_content,
            "needs_analysis": needs_analysis,
            "fully_processed": total - needs_content - needs_analysis,
        }
