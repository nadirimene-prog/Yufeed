"""
RAG indexing pipeline for legal document chunks.
"""
from typing import Dict, List, Optional
import logging

from sqlalchemy.orm import Session

from src.ai.embeddings import EmbeddingProvider
from src.ai.rag_chunker import chunk_document
from src.config import settings
from src.models.models import LegalDocument
from src.models.rag_models import LegalChunk
from src.search import get_opensearch_client, init_rag_index

logger = logging.getLogger(__name__)


class RAGIndexer:
    def __init__(self, db: Session, embedding_provider: Optional[EmbeddingProvider] = None):
        self.db = db
        self.embedding_provider = embedding_provider or EmbeddingProvider()
        self.client = get_opensearch_client()

        dim = self.embedding_provider.dimension or settings.RAG_EMBEDDING_DIM
        init_rag_index(embedding_dim=dim)

    def index_document(self, document: LegalDocument) -> int:
        """Chunk and index a single document. Returns chunk count."""
        if not settings.RAG_INDEX_ENABLED:
            logger.info("RAG indexing disabled; skipping %s", document.celex)
            return 0

        # Remove existing chunks for this document
        self.db.query(LegalChunk).filter(LegalChunk.doc_id == document.id).delete()
        self.db.commit()

        chunk_rows: List[LegalChunk] = []
        chunk_payloads: List[Dict[str, object]] = []

        chunks = list(chunk_document(document))
        if not chunks:
            return 0

        texts = [c["text"] for c in chunks]
        embeddings = self.embedding_provider.embed_texts(texts) if self.embedding_provider.available else None

        for idx, chunk in enumerate(chunks):
            chunk_id = f"{document.celex}_{chunk['chunk_index']}"
            text = chunk["text"]
            chunk_rows.append(
                LegalChunk(
                    chunk_id=chunk_id,
                    doc_id=document.id,
                    celex=document.celex,
                    source_system=document.source_system,
                    jurisdiction=document.jurisdiction,
                    language=document.primary_language,
                    section_title=chunk.get("section_title"),
                    article_ref=chunk.get("article_ref"),
                    chunk_index=int(chunk["chunk_index"]),
                    chunk_text=text,
                    token_count=len(text.split()),
                    char_count=len(text),
                )
            )

            payload = {
                "chunk_id": chunk_id,
                "doc_id": document.id,
                "celex": document.celex,
                "title": document.title,
                "chunk_text": text,
                "section_title": chunk.get("section_title"),
                "article_ref": chunk.get("article_ref"),
                "source_system": document.source_system,
                "jurisdiction": document.jurisdiction,
                "language": document.primary_language,
                "publication_date": document.publication_date.isoformat() if document.publication_date else None,
                "implementation_deadline": document.implementation_deadline.isoformat() if document.implementation_deadline else None,
                "compliance_domain": document.compliance_domain,
                "risk_level": document.risk_level,
                "scope_tags": getattr(document, "scope_tags", None),
                "subject_tags": getattr(document, "subject_tags", None),
                "chunk_index": int(chunk["chunk_index"]),
                "char_count": len(text),
                "token_count": len(text.split()),
            }
            if embeddings:
                payload["embedding"] = embeddings[idx]
            chunk_payloads.append(payload)

        # Persist chunk rows
        self.db.bulk_save_objects(chunk_rows)
        self.db.commit()

        # Index in OpenSearch
        index_name = settings.RAG_INDEX_NAME
        for payload in chunk_payloads:
            try:
                self.client.index(index=index_name, id=payload["chunk_id"], body=payload)
            except Exception as exc:
                logger.warning("Failed to index chunk %s: %s", payload["chunk_id"], exc)

        return len(chunk_payloads)

    def index_all_documents(self, limit: Optional[int] = None) -> int:
        """Index all legal documents. Returns total chunk count."""
        query = self.db.query(LegalDocument).order_by(LegalDocument.id.asc())
        if limit:
            query = query.limit(limit)

        total_chunks = 0
        for doc in query.all():
            try:
                total_chunks += self.index_document(doc)
            except Exception as exc:
                logger.warning("Failed to index %s: %s", doc.celex, exc)

        return total_chunks
