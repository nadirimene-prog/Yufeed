"""
RAG (Retrieval Augmented Generation) Service for Natural Language Queries

This service enables users to ask questions about EU regulations in natural language
and get AI-powered answers based on the document corpus.
"""

from typing import List, Dict, Any, Optional
from anthropic import Anthropic
from sqlalchemy.orm import Session
from src.models.models import LegalDocument
from src.search import search_documents as opensearch_documents
import os


class RAGService:
    """
    Retrieval Augmented Generation service for answering questions about legal documents.

    Uses a two-stage approach:
    1. Retrieval: Find relevant documents using OpenSearch
    2. Generation: Use Claude to synthesize an answer from retrieved documents
    """

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=api_key) if api_key else None

    def answer_query(
        self,
        query: str,
        db: Session,
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
        # Step 1: Retrieve relevant documents
        retrieved_docs = self._retrieve_documents(
            query=query,
            db=db,
            max_documents=max_documents,
            filters=filters
        )

        if not retrieved_docs:
            return {
                "answer": "I couldn't find any relevant documents to answer your question. Please try rephrasing or use different search terms.",
                "sources": [],
                "confidence": "low",
                "document_count": 0
            }

        # Step 2: Generate answer using Claude
        if self.client:
            answer_data = self._generate_answer(query, retrieved_docs)
        else:
            answer_data = self._fallback_answer(query, retrieved_docs)

        # Add source documents
        answer_data["sources"] = [
            {
                "celex": doc["celex"],
                "title": doc["title"],
                "relevance_score": doc.get("_score", 0),
                "publication_date": doc.get("publication_date"),
                "compliance_domain": doc.get("compliance_domain"),
                "risk_level": doc.get("risk_level")
            }
            for doc in retrieved_docs
        ]
        answer_data["document_count"] = len(retrieved_docs)

        return answer_data

    def _retrieve_documents(
        self,
        query: str,
        db: Session,
        max_documents: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant documents using OpenSearch.

        Uses hybrid search combining:
        - Full-text search on title, summary, obligations
        - Filters for compliance domain, risk level, etc.
        """
        filters = filters or {}

        # Search OpenSearch
        search_results = opensearch_documents(
            query=query,
            limit=max_documents,
            compliance_domain=filters.get("compliance_domain"),
            risk_level=filters.get("risk_level")
        )

        # Enrich with database data
        enriched_docs = []
        for hit in search_results.get("hits", {}).get("hits", []):
            source = hit["_source"]
            source["_score"] = hit["_score"]

            # Get full document from database for additional context
            doc = db.query(LegalDocument).filter(
                LegalDocument.celex == source["celex"]
            ).first()

            if doc:
                source["ai_summary"] = doc.ai_summary
                source["obligations_json"] = doc.obligations_json
                source["implementation_deadline"] = doc.implementation_deadline
                source["compliance_domain"] = doc.compliance_domain
                source["risk_level"] = doc.risk_level

                enriched_docs.append(source)

        return enriched_docs

    def _generate_answer(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate an answer using Claude with retrieved documents as context.
        """
        prompt = self._build_rag_prompt(query, documents)

        try:
            message = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }]
            )

            answer_text = message.content[0].text

            # Determine confidence based on document relevance
            avg_score = sum(d.get("_score", 0) for d in documents) / len(documents)
            confidence = "high" if avg_score > 5.0 else "medium" if avg_score > 2.0 else "low"

            return {
                "answer": answer_text,
                "confidence": confidence,
                "model": "claude-sonnet-4"
            }

        except Exception as e:
            print(f"RAG generation error: {e}")
            return self._fallback_answer(query, documents)

    def _fallback_answer(self, query: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback answer when AI is unavailable.
        Returns a summary of retrieved documents.
        """
        answer_parts = [f"Found {len(documents)} relevant document(s):\n"]

        for i, doc in enumerate(documents[:3], 1):
            answer_parts.append(f"\n{i}. {doc['title']} ({doc['celex']})")
            if doc.get("ai_summary"):
                answer_parts.append(f"   Summary: {doc['ai_summary'][:200]}...")
            if doc.get("compliance_domain"):
                answer_parts.append(f"   Domain: {doc['compliance_domain']}")

        if len(documents) > 3:
            answer_parts.append(f"\n... and {len(documents) - 3} more documents")

        return {
            "answer": "\n".join(answer_parts),
            "confidence": "low",
            "model": "fallback"
        }

    def _build_rag_prompt(self, query: str, documents: List[Dict[str, Any]]) -> str:
        """
        Build a RAG prompt for Claude with retrieved documents.
        """
        context_parts = []

        for i, doc in enumerate(documents, 1):
            context = f"Document {i}: {doc['title']} ({doc['celex']})\n"

            if doc.get("ai_summary"):
                context += f"Summary: {doc['ai_summary']}\n"

            if doc.get("obligations_json"):
                obligations = doc["obligations_json"]
                if isinstance(obligations, dict):
                    context += "Key Obligations:\n"
                    for key, value in list(obligations.items())[:5]:
                        context += f"  - {value}\n"

            if doc.get("compliance_domain"):
                context += f"Compliance Domain: {doc['compliance_domain']}\n"

            if doc.get("risk_level"):
                context += f"Risk Level: {doc['risk_level']}\n"

            if doc.get("implementation_deadline"):
                context += f"Deadline: {doc['implementation_deadline']}\n"

            context_parts.append(context)

        prompt = f"""You are an expert AML/CFT compliance analyst helping banking compliance officers understand EU regulations.

User Question: {query}

Based on the following EU legal documents, provide a comprehensive, accurate answer:

{'=' * 80}
{chr(10).join(context_parts)}
{'=' * 80}

Instructions:
1. Answer the question directly and concisely
2. Reference specific documents by CELEX number when making claims
3. Highlight key obligations and deadlines
4. If the question asks about implementation, provide actionable guidance
5. If the documents don't fully answer the question, acknowledge limitations
6. Use clear, professional language suitable for compliance officers
7. Structure your answer with bullet points or sections if appropriate

Answer:"""

        return prompt

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


class ConversationManager:
    """
    Manages multi-turn conversations with context retention.
    """

    def __init__(self, db: Session):
        self.db = db
        self.rag_service = RAGService()
        self.conversation_history: List[Dict[str, str]] = []

    def ask(self, query: str, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a query in the context of the conversation.
        """
        # TODO: In production, enhance query with conversation context
        response = self.rag_service.answer_query(
            query=query,
            db=self.db,
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
