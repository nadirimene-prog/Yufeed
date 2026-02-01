"""
RAG (Retrieval Augmented Generation) Service for Natural Language Queries

This service enables users to ask questions about EU regulations in natural language
and get AI-powered answers based on the document corpus.
"""

from typing import List, Dict, Any, Optional
import asyncio
import re
from anthropic import AsyncAnthropic
from sqlalchemy.orm import Session
from src.models.models import LegalDocument
from src.search import search_documents as opensearch_documents, search_rag_chunks
import os
import logging

logger = logging.getLogger(__name__)
MAX_QUERY_LENGTH = 2000
CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class RAGService:
    """
    Retrieval Augmented Generation service for answering questions about legal documents.

    Uses a two-stage approach:
    1. Retrieval: Find relevant documents using OpenSearch
    2. Generation: Use Claude to synthesize an answer from retrieved documents
    """

    def __init__(self, db: Optional[Session] = None):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = AsyncAnthropic(api_key=api_key) if api_key else None
        self.db = db

    async def answer_query(
        self,
        query: str,
        db: Optional[Session] = None,
        max_documents: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Answer a natural language query using RAG.

        Args:
            query: User's question in natural language
            db: Database session
            max_documents: Maximum number of documents to retrieve
            filters: Optional filters (compliance_domain, risk_level, etc.)

        Returns:
            Dict containing answer, sources, and metadata
        """
        db = db or self.db
        if not db:
            raise ValueError("Database session is required for RAGService")

        query = self._sanitize_query(query)

        # Step 1: Retrieve relevant chunks (RAG)
        retrieved_chunks = await self._retrieve_chunks(
            query=query,
            db=db,
            max_documents=max_documents,
            filters=filters
        )

        if not retrieved_chunks:
            return {
                "answer": "I couldn't find any relevant documents to answer your question. Please try rephrasing or use different search terms.",
                "sources": [],
                "confidence": "low",
                "document_count": 0
            }

        # Step 2: Generate answer using Claude
        if self.client:
            answer_data = await self._generate_answer(query, retrieved_chunks)
        else:
            answer_data = self._fallback_answer(query, retrieved_chunks)

        # Add source chunks
        answer_data["sources"] = [
            {
                "celex": chunk.get("celex"),
                "title": chunk.get("title"),
                "relevance_score": chunk.get("score", 0),
                "publication_date": chunk.get("publication_date"),
                "compliance_domain": chunk.get("compliance_domain"),
                "risk_level": chunk.get("risk_level"),
                "implementation_deadline": chunk.get("implementation_deadline"),
                "article_ref": chunk.get("article_ref"),
                "section_title": chunk.get("section_title"),
                "chunk_id": chunk.get("chunk_id"),
                "snippet": (chunk.get("chunk_text") or "")[:300],
            }
            for chunk in retrieved_chunks
        ]
        answer_data["document_count"] = len({c.get("celex") for c in retrieved_chunks if c.get("celex")})

        return answer_data

    async def _retrieve_chunks(
        self,
        query: str,
        db: Session,
        max_documents: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks using OpenSearch hybrid search.
        """
        filters = filters or {}

        # Hybrid chunk search (BM25 + vector when available)
        try:
            search_results = await asyncio.to_thread(
                search_rag_chunks,
                q=query,
                size=max(max_documents * 3, 5),
                filters=filters,
            )
            chunks = search_results.get("results", [])
        except Exception as exc:
            logger.warning("RAG chunk search failed: %s", exc)
            chunks = []

        if chunks:
            return chunks

        # Fallback: document-level search when no chunks are indexed yet
        search_results = await asyncio.to_thread(
            opensearch_documents,
            q=query,
            size=max_documents,
            compliance_domain=filters.get("compliance_domain"),
            risk_level=filters.get("risk_level"),
        )

        enriched_docs: List[Dict[str, Any]] = []
        for source in search_results.get("results", []):
            doc = db.query(LegalDocument).filter(
                LegalDocument.celex == source.get("celex")
            ).first()
            if doc:
                source["ai_summary"] = doc.ai_summary
                source["obligations_json"] = doc.obligations_json
                source["implementation_deadline"] = doc.implementation_deadline
                source["compliance_domain"] = doc.compliance_domain
                source["risk_level"] = doc.risk_level
                source["publication_date"] = doc.publication_date
                source["title"] = doc.title

            chunk_text = (
                source.get("ai_summary")
                or source.get("full_text")
                or source.get("title")
                or ""
            )
            enriched_docs.append(
                {
                    "chunk_id": f"{source.get('celex')}_summary",
                    "celex": source.get("celex"),
                    "title": source.get("title"),
                    "chunk_text": chunk_text,
                    "section_title": None,
                    "article_ref": None,
                    "score": source.get("score", 0),
                    "publication_date": source.get("publication_date"),
                    "compliance_domain": source.get("compliance_domain"),
                    "risk_level": source.get("risk_level"),
                }
            )

        return enriched_docs

    async def _generate_answer(self, query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an answer using Claude with retrieved chunks as context.
        """
        if not self.client:
            logger.info("RAGService operating in Demo Mode (no API key)")
            return {
                "answer": (
                    "I am currently operating in **Demo Mode** because no `ANTHROPIC_API_KEY` was found. "
                    "In a live environment, I would analyze the retrieved legal documents to provide a precise answer. "
                    "\n\n**Retrieved Documents:**\n" + 
                    "\n".join([f"- {d.get('title')} ({d.get('celex')})" for d in chunks[:3]])
                ),
                "confidence": "low",
                "model": "demo-fallback"
            }

        prompt = self._build_rag_prompt(query, chunks)

        try:
            message = await self.client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=2000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            answer_text = message.content[0].text

            # Determine confidence based on relevance
            avg_score = sum(d.get("score", 0) for d in chunks) / len(chunks)
            confidence = "high" if avg_score > 5.0 else "medium" if avg_score > 2.0 else "low"

            return {
                "answer": answer_text,
                "confidence": confidence,
                "model": "claude-3-5-sonnet"
            }

        except Exception as e:
            logger.error(f"RAG generation error: {e}")
            return self._fallback_answer(query, chunks)

    def _fallback_answer(self, query: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback answer when AI is unavailable.
        Returns a summary of retrieved documents.
        """
        doc_count = len({c.get("celex") for c in chunks if c.get("celex")})
        answer_parts = [
            "⚠️ **Demo Mode**: No `ANTHROPIC_API_KEY` configured. Showing retrieved documents without AI analysis.\n",
            f"Found {doc_count} relevant document(s) across {len(chunks)} passages:\n"
        ]

        for i, chunk in enumerate(chunks[:3], 1):
            answer_parts.append(f"\n{i}. {chunk.get('title')} ({chunk.get('celex')})")
            text = (chunk.get("chunk_text") or "")[:200]
            if text:
                answer_parts.append(f"   Excerpt: {text}...")
            if chunk.get("compliance_domain"):
                answer_parts.append(f"   Domain: {chunk.get('compliance_domain')}")

        if len(chunks) > 3:
            answer_parts.append(f"\n... and {len(chunks) - 3} more passages")

        return {
            "answer": "\n".join(answer_parts),
            "confidence": "low",
            "model": "fallback"
        }

    def _build_rag_prompt(self, query: str, chunks: List[Dict[str, Any]]) -> str:
        """
        Build a RAG prompt for Claude with retrieved chunks.
        """
        context_parts = []

        max_chunks = min(len(chunks), 8)
        for i, chunk in enumerate(chunks[:max_chunks], 1):
            excerpt = chunk.get("chunk_text") or ""
            if len(excerpt) > 1200:
                excerpt = f"{excerpt[:1200]}..."

            article_ref = chunk.get("article_ref") or "N/A"
            section_title = chunk.get("section_title") or ""
            header = f"[{i}] {chunk.get('title')} ({chunk.get('celex')})"
            if section_title:
                header += f" | {section_title}"
            header += f" | Article: {article_ref}"

            context_parts.append(f"{header}\n{excerpt}\n")

        prompt = f"""You are an expert AML/CFT compliance analyst helping banking compliance officers understand EU regulations.

User Question: {query}

Based on the following EU legal documents, provide a comprehensive, accurate answer:

{'=' * 80}
{chr(10).join(context_parts)}
{'=' * 80}

Instructions:
1. Answer the question directly and concisely
2. Cite sources using the bracket IDs like [1], [2] that correspond to the excerpts
3. Reference specific CELEX numbers when making claims
4. Highlight key obligations and deadlines
5. If the excerpts don't fully answer the question, acknowledge limitations
6. Use clear, professional language suitable for compliance officers
7. Structure your answer with bullet points or sections if appropriate

Answer:"""

        return prompt

    async def ask(
        self,
        question: str,
        max_documents: int = 5,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Public API for asking a question.
        Matches the orchestrator's expectations.
        """
        response = await self.answer_query(
            query=question,
            max_documents=max_documents,
            filters=filters
        )

        # Add follow-up questions
        response["followup_questions"] = self.suggest_followup_questions(
            query=question,
            answer=response["answer"],
            documents=response.get("sources", [])
        )

        return response

    def suggest_followup_questions(
        self,
        query: str,
        answer: str,
        documents: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Suggest relevant follow-up questions based on the query and answer.
        """
        suggestions = []

        # Extract unique compliance domains and business areas
        domains = set(d.get("compliance_domain") for d in documents if d.get("compliance_domain"))

        # Generic follow-ups based on domain
        if "aml" in domains:
            suggestions.append("What are the recent changes in AML requirements?")
            suggestions.append("What are the implementation deadlines for AML regulations?")

        if "kyc" in domains:
            suggestions.append("What are the enhanced KYC requirements for high-risk customers?")

        if "sanctions" in domains:
            suggestions.append("What are the latest sanctions screening requirements?")

        # Query-specific follow-ups
        if "deadline" not in query.lower() and any(d.get("implementation_deadline") for d in documents):
            suggestions.append("What are the implementation deadlines for these regulations?")

        if "impact" not in query.lower():
            suggestions.append("What is the operational impact of these regulations?")

        return suggestions[:3]  # Return top 3 suggestions

    def _sanitize_query(self, query: str) -> str:
        if not isinstance(query, str):
            raise ValueError("Query must be a string")
        cleaned = CONTROL_CHAR_RE.sub("", query).strip()
        if not cleaned:
            raise ValueError("Query cannot be empty")
        if len(cleaned) > MAX_QUERY_LENGTH:
            raise ValueError("Query too long")
        return cleaned


class ConversationManager:
    """
    Manages multi-turn conversations with context retention.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rag_service = RAGService(db)
        self.conversation_history: List[Dict[str, str]] = []

    async def ask(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a query in the context of the conversation.
        """
        # TODO: In production, enhance query with conversation context
        response = await self.rag_service.ask(
            question=query,
            filters=filters
        )

        # Store in conversation history
        self.conversation_history.append({
            "role": "user",
            "content": query
        })
        self.conversation_history.append({
            "role": "assistant",
            "content": response["answer"]
        })

        # Add follow-up suggestions
        response["followup_questions"] = self.rag_service.suggest_followup_questions(
            query=query,
            answer=response["answer"],
            documents=response.get("sources", [])
        )

        return response

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
