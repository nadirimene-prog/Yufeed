import logging
import datetime
from sqlalchemy.orm import Session
from typing import Optional

import traceback
from src.utils.time import utc_now
from src.models import (
    LegalDocument,
    LegalVersion,
    LegalDocumentText,
    VersionKind,
    OfficialJournalAct,
    LegalRelation,
)
from src.models.compliance_workflow import FailedIngestionItem
from src.ingestion.cellar import CellarClient
from src.ingestion.content_extractor import ContentExtractor
from src.services.confidence_scorer import ConfidenceScorer
from src.ingestion.oj_mapping import extract_oj_act_identifier
from src.search import index_document
from src.ai.analyzer import analyze_document
from src.ai.cost_tracker import log_usage_from_analysis
from src.ai.rag_indexer import RAGIndexer
from src.services.obligation_service import (
    seed_obligations_for_doc,
    mark_related_obligations_for_review,
)
from src.compliance.scope import infer_scope_tags, normalize_scopes, scope_keywords
from src.config import settings
from src.ingestion.title import derive_title_from_text, is_placeholder_title

logger = logging.getLogger(__name__)


class IngestionProcessor:
    def __init__(self, db: Session):
        self.db = db
        self.cellar = CellarClient()
        self.content_extractor = ContentExtractor()
        self.confidence_scorer = ConfidenceScorer()
        self._rag_indexer: Optional[RAGIndexer] = None

    def _get_rag_indexer(self) -> Optional[RAGIndexer]:
        if not settings.RAG_INDEX_ENABLED:
            return None
        if self._rag_indexer is None:
            self._rag_indexer = RAGIndexer(self.db)
        return self._rag_indexer

    def process_entry(self, entry: dict):
        """
        Process a single normalized RSS entry.
        """
        celex = entry.get("celex")
        if not celex:
            logger.warning(f"Skipping entry without CELEX: {entry.get('link')}")
            return
        metadata_only = bool(entry.get("metadata_only"))

        # Check if exists
        existing_doc = self.db.query(LegalDocument).filter(LegalDocument.celex == celex).first()

        if existing_doc:
            return self._handle_existing_doc(existing_doc, entry, metadata_only=metadata_only)
        return self._handle_new_doc(celex, entry, metadata_only=metadata_only)

    def _handle_new_doc(self, celex: str, entry: dict, metadata_only: bool = False):
        logger.info(f"New document detected: {celex}")

        # Try to enrich with CELLAR metadata
        cellar_metadata = None
        if entry.get("source_system") == "eur-lex":
            try:
                cellar_metadata = self.cellar.query_by_celex(celex)
            except Exception as e:
                logger.warning(f"Failed to fetch CELLAR metadata for {celex}: {e}")

        # Instantiate doc with RSS data + CELLAR enrichment
        title = entry.get("title")
        pub_date = self._parse_date(entry.get("published"))
        entry_into_force = None
        eli = entry.get("eli")
        cellar_id = None
        doc_type = None
        language = (entry.get("language") or "en").lower()
        source_system = entry.get("source_system")
        source_reference = entry.get("source_reference") or entry.get("link")
        jurisdiction = entry.get("jurisdiction")

        if cellar_metadata:
            # Prefer CELLAR data when available
            if cellar_metadata.get("title"):
                title = cellar_metadata["title"]
            if cellar_metadata.get("date_document"):
                pub_date = cellar_metadata["date_document"]
            entry_into_force = cellar_metadata.get("date_entry_into_force")
            eli = cellar_metadata.get("eli") or eli
            cellar_id = cellar_metadata.get("cellar_id")

            # Extract document type from work_type URI
            work_type = cellar_metadata.get("work_type", "")
            if "regulation" in work_type.lower():
                doc_type = "regulation"
            elif "directive" in work_type.lower():
                doc_type = "directive"
            elif "decision" in work_type.lower():
                doc_type = "decision"

        if not self._matches_scope(title or "", entry):
            logger.info(f"Skipping {celex} due to scope filter: {settings.REGULATORY_SCOPE_FILTER}")
            return "skipped"

        publication_day = pub_date.date() if isinstance(pub_date, datetime.datetime) else None
        oj_act_identifier, oj_signature_identifier = self._resolve_oj_identifiers(
            entry, publication_day
        )

        new_doc = LegalDocument(
            celex=celex,
            source_system=source_system,
            source_reference=source_reference,
            jurisdiction=jurisdiction,
            primary_language=language,
            eli=eli,
            cellar_id=cellar_id,
            title=title,
            type=doc_type,
            status="active",
            publication_date=pub_date,
            entry_into_force_date=entry_into_force,
            last_modified=utc_now(),
            jurisdictional_scope=jurisdiction or None,
            oj_act_identifier=oj_act_identifier,
            oj_signature_identifier=oj_signature_identifier,
        )

        self.db.add(new_doc)
        self.db.commit()
        self.db.refresh(new_doc)

        # Extract document content
        if not metadata_only:
            try:
                content_result = None
                if entry.get("source_system") == "eur-lex":
                    logger.info(f"Extracting content for {celex}")
                    content_result = self.content_extractor.extract_content(
                        celex, language=language
                    )

                if content_result and content_result.get("full_text"):
                    if language == (new_doc.primary_language or "en"):
                        new_doc.full_text = content_result["full_text"]
                        new_doc.article_breakdown = {
                            "articles": content_result.get("article_breakdown", [])
                        }
                        new_doc.content_extraction_method = content_result.get("extraction_method")
                        new_doc.content_extracted_at = utc_now()
                        new_doc.word_count = content_result.get("word_count")
                        if is_placeholder_title(new_doc.title):
                            detected = derive_title_from_text(new_doc.full_text)
                            if detected and not is_placeholder_title(detected):
                                new_doc.title = detected

                    doc_text = LegalDocumentText(
                        doc_id=new_doc.id,
                        language=language,
                        full_text=content_result.get("full_text"),
                        article_breakdown={"articles": content_result.get("article_breakdown", [])},
                        content_extraction_method=content_result.get("extraction_method"),
                        content_extracted_at=utc_now(),
                        word_count=content_result.get("word_count"),
                        source_url=entry.get("link"),
                    )
                    self.db.add(doc_text)

                    logger.info(
                        f"Content extracted for {celex}: {new_doc.word_count} words via {new_doc.content_extraction_method}"
                    )
                    self.db.commit()

                    # Index document in OpenSearch
                    try:
                        index_document(new_doc)
                        logger.info(f"Document {celex} indexed in OpenSearch")
                        rag_indexer = self._get_rag_indexer()
                        if rag_indexer:
                            rag_indexer.index_document(new_doc)
                            logger.info(f"RAG chunks indexed for {celex}")
                    except Exception as idx_err:
                        logger.warning(f"Failed to index {celex} in OpenSearch: {idx_err}")

            except Exception as e:
                logger.warning(f"Content extraction failed for {celex}: {e}")

        # Store related documents if found via CELLAR
        if cellar_id:
            try:
                relations = self.cellar.get_related_documents(cellar_id)
                for relation in relations:
                    related_celex = relation.get("related_celex")
                    relation_type = relation.get("relation_type")
                    if not related_celex or not relation_type:
                        continue
                    related_doc = (
                        self.db.query(LegalDocument)
                        .filter(LegalDocument.celex == related_celex)
                        .first()
                    )
                    if not related_doc:
                        logger.debug(
                            "Skipping relation for %s (%s -> %s): related document not in database",
                            celex,
                            relation_type,
                            related_celex,
                        )
                        continue
                    # Check if relation already exists (idempotency)
                    existing_relation = (
                        self.db.query(LegalRelation)
                        .filter(
                            LegalRelation.from_doc_id == new_doc.id,
                            LegalRelation.relation_type == relation_type,
                            LegalRelation.to_doc_id == related_doc.id,
                        )
                        .first()
                    )
                    if not existing_relation:
                        legal_relation = LegalRelation(
                            from_doc_id=new_doc.id,
                            relation_type=relation_type,
                            to_doc_id=related_doc.id,
                        )
                        self.db.add(legal_relation)
                        logger.info(f"Stored relation: {celex} {relation_type} {related_celex}")
                if relations:
                    self.db.commit()
                    # Mark related obligations for review if this doc amends/repeals others
                    try:
                        marked = mark_related_obligations_for_review(self.db, new_doc)
                        if marked:
                            logger.info(
                                f"Marked {marked} related obligations for review due to {celex}"
                            )
                    except Exception as cascade_err:
                        logger.warning(
                            f"Failed to cascade obligation review for {celex}: {cascade_err}"
                        )
            except Exception as e:
                logger.warning(f"Failed to fetch/store relations for {celex}: {e}")

        # Create Alert - REMOVED (Legacy AlertEvent model missing)
        # alert = AlertEvent(
        #     doc_id=new_doc.id,
        #     event_type=AlertEventType.NEW_DOC,
        #     detected_at=datetime.datetime.utcnow()
        # )
        # self.db.add(alert)

        # Create Initial Version (with idempotency check)
        source_url = entry.get("link")
        existing_version = (
            self.db.query(LegalVersion)
            .filter(
                LegalVersion.doc_id == new_doc.id,
                LegalVersion.language == language,
                LegalVersion.source_url == source_url,
            )
            .first()
        )
        if not existing_version:
            version = LegalVersion(
                doc_id=new_doc.id,
                kind=VersionKind.INITIAL,
                language=language,
                source_url=source_url,
            )
            self.db.add(version)
            self.db.commit()

        if metadata_only:
            logger.info(f"Metadata-only ingestion for {celex}; skipping content analysis.")
            return "new"

        # Analyze and seed obligations
        try:
            analyzed = self._maybe_analyze_doc(new_doc, force=True)
            if analyzed:
                seed_obligations_for_doc(self.db, new_doc)
        except Exception as exc:
            logger.warning(f"Failed to analyze or seed obligations for {celex}: {exc}")
            # Save to DLQ for later retry
            self._save_analysis_failure_to_dlq(new_doc, exc, entry)

        logger.info(f"Created new document {celex} with ID {new_doc.id}")
        return "new"

    def _handle_existing_doc(self, doc: LegalDocument, entry: dict, metadata_only: bool = False):
        # Check for changes
        # Simple Logic: If the RSS entry suggests a modification or if we want to periodically update.
        # For now, we will log that we saw it.
        # If we had a hash of the content, we would compare it here.

        # Check if title changed (simple heuristic)
        if not self._matches_scope(doc.title or "", entry):
            return "skipped"

        updated = False
        doc_changed = False
        incoming_title = entry.get("title")
        if (
            incoming_title
            and not is_placeholder_title(incoming_title)
            and doc.title != incoming_title
        ):
            logger.info(f"Document {doc.celex} title updated.")
            doc.title = incoming_title
            doc.last_modified = utc_now()

            # alert = AlertEvent(
            #    doc_id=doc.id,
            #    event_type=AlertEventType.UPDATED_DOC,
            #    detected_at=datetime.datetime.utcnow()
            # )
            # self.db.add(alert)
            self.db.commit()
            updated = True
            doc_changed = True

        language = (entry.get("language") or doc.primary_language or "en").lower()
        if not doc.primary_language:
            doc.primary_language = language
            doc_changed = True
        if not doc.source_system and entry.get("source_system"):
            doc.source_system = entry.get("source_system")
            doc_changed = True
        if not doc.source_reference and entry.get("source_reference"):
            doc.source_reference = entry.get("source_reference")
            doc_changed = True
        if not doc.jurisdiction and entry.get("jurisdiction"):
            doc.jurisdiction = entry.get("jurisdiction")
            doc_changed = True
        if not doc.eli and entry.get("eli"):
            doc.eli = entry.get("eli")
            doc_changed = True
        publication_day = doc.publication_date.date() if doc.publication_date else None
        if not doc.oj_act_identifier or not doc.oj_signature_identifier:
            oj_act_identifier, oj_signature_identifier = self._resolve_oj_identifiers(
                entry, publication_day
            )
            if oj_act_identifier and doc.oj_act_identifier != oj_act_identifier:
                doc.oj_act_identifier = oj_act_identifier
                doc_changed = True
            if oj_signature_identifier and doc.oj_signature_identifier != oj_signature_identifier:
                doc.oj_signature_identifier = oj_signature_identifier
                doc_changed = True
        source_url = entry.get("link")
        existing_version = (
            self.db.query(LegalVersion)
            .filter(
                LegalVersion.doc_id == doc.id,
                LegalVersion.language == language,
                LegalVersion.source_url == source_url,
            )
            .first()
        )
        if not existing_version:
            version = LegalVersion(
                doc_id=doc.id,
                kind=VersionKind.CONSOLIDATED,
                language=language,
                source_url=source_url,
            )
            self.db.add(version)
            doc.last_modified = utc_now()
            self.db.commit()
            updated = True
        elif doc_changed:
            doc.last_modified = utc_now()
            self.db.commit()
            updated = True

        existing_text = (
            self.db.query(LegalDocumentText)
            .filter(
                LegalDocumentText.doc_id == doc.id,
                LegalDocumentText.language == language,
            )
            .first()
        )
        should_refresh_content = (
            not metadata_only
            and doc.source_system == "eur-lex"
            and (updated or doc_changed or not existing_text)
        )
        if should_refresh_content:
            try:
                content_result = self.content_extractor.extract_content(
                    doc.celex, language=language
                )
                if content_result and content_result.get("full_text"):
                    if language == (doc.primary_language or "en"):
                        doc.full_text = content_result.get("full_text")
                        doc.article_breakdown = {
                            "articles": content_result.get("article_breakdown", [])
                        }
                        doc.content_extraction_method = content_result.get("extraction_method")
                        doc.content_extracted_at = utc_now()
                        doc.word_count = content_result.get("word_count")
                        if is_placeholder_title(doc.title):
                            detected = derive_title_from_text(doc.full_text)
                            if detected and not is_placeholder_title(detected):
                                doc.title = detected

                    if existing_text:
                        existing_text.full_text = content_result.get("full_text")
                        existing_text.article_breakdown = {
                            "articles": content_result.get("article_breakdown", [])
                        }
                        existing_text.content_extraction_method = content_result.get(
                            "extraction_method"
                        )
                        existing_text.content_extracted_at = utc_now()
                        existing_text.word_count = content_result.get("word_count")
                        existing_text.source_url = source_url
                    else:
                        doc_text = LegalDocumentText(
                            doc_id=doc.id,
                            language=language,
                            full_text=content_result.get("full_text"),
                            article_breakdown={
                                "articles": content_result.get("article_breakdown", [])
                            },
                            content_extraction_method=content_result.get("extraction_method"),
                            content_extracted_at=utc_now(),
                            word_count=content_result.get("word_count"),
                            source_url=source_url,
                        )
                        self.db.add(doc_text)
                    self.db.commit()
                    updated = True
            except Exception as exc:
                logger.warning(f"Content extraction failed for {doc.celex} ({language}): {exc}")

        analysis_needed = not metadata_only and (doc.analyzed_at is None or doc_changed or updated)
        if analysis_needed:
            try:
                analyzed = self._maybe_analyze_doc(doc, force=True)
                if analyzed:
                    seed_obligations_for_doc(self.db, doc, allow_existing=True)
            except Exception as exc:
                logger.warning(f"Failed to analyze or seed obligations for {doc.celex}: {exc}")
                # Save to DLQ for later retry
                self._save_analysis_failure_to_dlq(doc, exc, entry)

        if updated:
            try:
                index_document(doc)
                logger.info(f"Document {doc.celex} re-indexed in OpenSearch")
            except Exception as idx_err:
                logger.warning(f"Failed to re-index {doc.celex} in OpenSearch: {idx_err}")

            # Queue RAG re-indexing if content was refreshed
            if should_refresh_content and doc.full_text:
                try:
                    from src.worker import index_document_rag

                    index_document_rag.delay(doc.id)
                    logger.info(f"Queued RAG re-indexing for document {doc.celex}")
                except Exception as rag_err:
                    logger.warning(f"Failed to queue RAG re-indexing for {doc.celex}: {rag_err}")

        return "updated" if updated else "unchanged"

    def _resolve_oj_identifiers(self, entry: dict, publication_day: datetime.date | None):
        oj_ref = entry.get("oj_ref") or entry.get("source_reference")
        act_identifier = extract_oj_act_identifier(oj_ref)
        if act_identifier:
            record = (
                self.db.query(OfficialJournalAct)
                .filter(OfficialJournalAct.act_identifier == act_identifier)
                .first()
            )
            if record:
                return record.act_identifier, record.signature_identifier
            return act_identifier, None

        series = entry.get("oj_series")
        if publication_day and series:
            matches = (
                self.db.query(OfficialJournalAct)
                .filter(
                    OfficialJournalAct.publication_date == publication_day,
                    OfficialJournalAct.series == series,
                )
                .all()
            )
            if len(matches) == 1:
                return matches[0].act_identifier, matches[0].signature_identifier

        return None, None

    def _matches_scope(self, title: str, entry: dict) -> bool:
        scope_filter = (settings.REGULATORY_SCOPE_FILTER or "").strip()
        scopes = normalize_scopes(scope_filter)
        if not scope_filter or not scopes:
            return True
        keywords = scope_keywords(scopes)
        if not keywords:
            return True
        haystack = " ".join(
            [
                title or "",
                entry.get("summary") or "",
                entry.get("description") or "",
            ]
        ).lower()
        if not haystack.strip():
            return True
        return any(keyword in haystack for keyword in keywords)

    def _maybe_analyze_doc(self, doc: LegalDocument, force: bool = False) -> bool:
        if doc.analyzed_at and not force:
            return False

        article_breakdown = None
        if isinstance(doc.article_breakdown, dict):
            article_breakdown = doc.article_breakdown.get("articles")
        elif isinstance(doc.article_breakdown, list):
            article_breakdown = doc.article_breakdown

        has_full_text = bool(doc.full_text and str(doc.full_text).strip())
        has_articles = bool(article_breakdown)
        if not has_full_text and not has_articles:
            logger.info(f"Skipping AI analysis for {doc.celex}: no content available")
            return False

        # Calculate confidence score before analysis
        confidence = self.confidence_scorer.calculate_confidence(
            full_text=doc.full_text, articles=article_breakdown, analysis_method="llm"
        )

        logger.info(
            f"AI analysis confidence for {doc.celex}: {confidence.score:.3f} ({confidence.quality_tier})"
        )

        analysis_results = analyze_document(
            {
                "celex": doc.celex,
                "title": doc.title,
                "publication_date": doc.publication_date,
                "full_text": doc.full_text,
                "article_breakdown": article_breakdown,
            }
        )

        doc.compliance_domain = analysis_results.get("compliance_domain")
        doc.risk_level = analysis_results.get("risk_level")
        doc.obligations_json = analysis_results.get("obligations_json")
        doc.implementation_deadline = analysis_results.get("implementation_deadline")
        doc.ai_summary = analysis_results.get("ai_summary")
        doc.analyzed_at = analysis_results.get("analyzed_at")

        # Store confidence metadata (if the column exists)
        try:
            doc.ai_confidence = confidence.score
            doc.analysis_quality = confidence.quality_tier
        except AttributeError:
            # Column doesn't exist yet, will be added in migration
            pass
        scope_tags = infer_scope_tags(
            doc.title,
            doc.full_text,
            doc.ai_summary,
            doc.obligations_json,
        )
        if scope_tags:
            doc.scope_tags = scope_tags
        self.db.commit()
        self.db.refresh(doc)
        return True

    def _save_analysis_failure_to_dlq(self, doc: LegalDocument, exc: Exception, entry: dict):
        """
        Save AI analysis failure to Dead Letter Queue for later retry.

        Args:
            doc: The document that failed analysis
            exc: The exception that occurred
            entry: Original entry dict for retry
        """
        import json as json_module

        try:
            # Check if already in DLQ
            existing = (
                self.db.query(FailedIngestionItem)
                .filter(
                    FailedIngestionItem.celex == doc.celex,
                    FailedIngestionItem.source_key == "ai_analysis",
                    FailedIngestionItem.status.in_(["pending", "retrying"]),
                )
                .first()
            )

            if existing:
                # Update existing entry
                existing.retry_count += 1
                existing.error_message = str(exc)
                existing.error_traceback = traceback.format_exc()
                existing.last_retry_at = utc_now()
            else:
                # Create new DLQ entry
                failed_item = FailedIngestionItem(
                    celex=doc.celex,
                    source_key="ai_analysis",
                    error_message=str(exc),
                    error_traceback=traceback.format_exc(),
                    entry_json=json_module.dumps(
                        {
                            "doc_id": doc.id,
                            "celex": doc.celex,
                            "action": "analyze",
                            "original_entry": entry,
                        }
                    ),
                    status="pending",
                    max_retries=3,
                )
                self.db.add(failed_item)

            self.db.commit()
            logger.info(f"Saved AI analysis failure to DLQ for {doc.celex}")
        except Exception as dlq_err:
            logger.error(f"Failed to save to DLQ for {doc.celex}: {dlq_err}")

    def _parse_date(self, date_obj):
        # date_obj from feedparser is struct_time usually, or None
        if not date_obj:
            return None
        if isinstance(date_obj, str):
            # Try parsing isoformat
            try:
                return datetime.datetime.fromisoformat(date_obj)
            except (ValueError, TypeError):
                return None
        # feedparser struct_time
        try:
            return datetime.datetime(*date_obj[:6])
        except (ValueError, TypeError, IndexError):
            return None
