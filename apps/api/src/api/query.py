"""
Natural Language Query API Endpoints

Provides a ChatGPT-style interface for asking questions about EU regulations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from src.database import get_db
from src.ai.rag_service import RAGService, ConversationManager
from src.auth.dependencies import CurrentUser, get_current_user_optional
from src.tenancy.context import get_current_tenant
import os

router = APIRouter(prefix="/query", tags=["Natural Language Query"])


def _request_user_id(request: Request) -> Optional[str]:
    request_user = getattr(request.state, "user", None)
    return getattr(request_user, "user_id", None)


# Request/Response Models
class QueryRequest(BaseModel):
    """Natural language query request."""

    query: str = Field(..., description="User's question in natural language")
    compliance_domain: Optional[str] = Field(
        None, description="Filter by compliance domain (aml, kyc, sanctions, etc.)"
    )
    risk_level: Optional[str] = Field(
        None, description="Filter by risk level (critical, high, medium, low)"
    )
    max_documents: Optional[int] = Field(
        5, description="Maximum documents to retrieve (1-10)", ge=1, le=10
    )


class SourceDocument(BaseModel):
    """Source document reference."""

    celex: str
    title: str
    relevance_score: float
    publication_date: Optional[str] = None
    compliance_domain: Optional[str] = None
    risk_level: Optional[str] = None
    article_ref: Optional[str] = None
    section_title: Optional[str] = None
    chunk_id: Optional[str] = None
    snippet: Optional[str] = None


class QueryResponse(BaseModel):
    """Natural language query response."""

    query: str
    answer: str
    confidence: str  # high, medium, low
    sources: List[SourceDocument]
    document_count: int
    model: Optional[str] = None
    followup_questions: Optional[List[str]] = None


class ConversationRequest(BaseModel):
    """Multi-turn conversation request."""

    query: str
    conversation_id: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None


# In-memory conversation storage (in production, use Redis or database)
conversations: Dict[str, ConversationManager] = {}


@router.post("/ask", response_model=QueryResponse)
async def ask_question(
    request: QueryRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Ask a natural language question about EU regulations.

    **Examples:**
    - "What are the new KYC requirements for crypto exchanges?"
    - "Show me all AML regulations affecting transaction monitoring"
    - "What changed in sanctions screening in 2025?"
    - "What are the implementation deadlines for the latest AML directives?"

    The system uses RAG (Retrieval Augmented Generation) to:
    1. Find relevant documents using semantic search
    2. Generate a comprehensive answer using AI
    3. Provide source citations

    **Returns:**
    - AI-generated answer
    - Source documents with CELEX numbers
    - Confidence level
    - Suggested follow-up questions
    """
    rag_service = RAGService()
    tenant_id = get_current_tenant()

    filters = {}
    if request.compliance_domain:
        filters["compliance_domain"] = request.compliance_domain
    if request.risk_level:
        filters["risk_level"] = request.risk_level

    try:
        result = await rag_service.answer_query(
            query=request.query,
            db=db,
            max_documents=request.max_documents,
            filters=filters,
            tenant_id=tenant_id,
            user_id=(current_user.user_id if current_user else _request_user_id(http_request)),
        )

        # Add follow-up suggestions
        result["followup_questions"] = rag_service.suggest_followup_questions(
            query=request.query, answer=result["answer"], documents=result.get("sources", [])
        )

        return QueryResponse(query=request.query, **result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query processing failed: {str(e)}")


@router.post("/conversation", response_model=QueryResponse)
async def conversation_turn(
    request: ConversationRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: Optional[CurrentUser] = Depends(get_current_user_optional),
):
    """
    Multi-turn conversation with context retention.

    Maintains conversation history to provide context-aware answers.
    Use the same conversation_id to continue a conversation.

    **Example:**
    ```
    POST /query/conversation
    {
        "query": "What are the AML requirements?",
        "conversation_id": "abc123"
    }

    # Follow-up question with same ID
    POST /query/conversation
    {
        "query": "What about crypto exchanges specifically?",
        "conversation_id": "abc123"  # Same ID for context
    }
    ```
    """
    import uuid

    # Get or create conversation
    conv_id = request.conversation_id or str(uuid.uuid4())

    if conv_id not in conversations:
        conversations[conv_id] = ConversationManager()

    conv_manager = conversations[conv_id]
    tenant_id = get_current_tenant()

    try:
        result = await conv_manager.ask(
            query=request.query,
            filters=request.filters,
            tenant_id=tenant_id,
            user_id=(current_user.user_id if current_user else _request_user_id(http_request)),
        )

        return QueryResponse(query=request.query, **result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Conversation processing failed: {str(e)}")


@router.delete("/conversation/{conversation_id}")
def clear_conversation(conversation_id: str):
    """
    Clear conversation history.

    Use this to start a fresh conversation or free up memory.
    """
    if conversation_id in conversations:
        conversations[conversation_id].clear_history()
        del conversations[conversation_id]
        return {"message": "Conversation cleared", "conversation_id": conversation_id}
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.get("/suggestions")
def get_query_suggestions(
    domain: Optional[str] = Query(None, description="Compliance domain filter"),
    db: Session = Depends(get_db),
):
    """
    Get suggested questions users can ask.

    Provides example queries to help users get started.
    """
    suggestions = {
        "general": [
            "What are the latest AML regulations?",
            "Show me high-risk compliance requirements",
            "What regulations affect transaction monitoring?",
            "What are the upcoming implementation deadlines?",
        ],
        "aml": [
            "What are the new AML requirements for banks?",
            "What changed in the 6th AML Directive?",
            "What are the AML reporting requirements?",
            "What are the penalties for AML non-compliance?",
        ],
        "kyc": [
            "What are the KYC requirements for high-risk customers?",
            "What are the enhanced due diligence requirements?",
            "What are the KYC requirements for crypto exchanges?",
            "What customer identification documents are required?",
        ],
        "sanctions": [
            "What are the latest EU sanctions?",
            "What are the sanctions screening requirements?",
            "How often must sanctions lists be updated?",
            "What are the penalties for sanctions violations?",
        ],
        "reporting": [
            "What are the SAR reporting requirements?",
            "What are the CTR thresholds?",
            "What are the regulatory reporting deadlines?",
            "What information must be included in SARs?",
        ],
    }

    if domain and domain in suggestions:
        return {"domain": domain, "suggestions": suggestions[domain]}
    else:
        return {"domain": "all", "suggestions": suggestions}


@router.get("/health")
def query_health_check():
    """
    Health check for query service.

    Returns status of RAG service and AI availability.
    """
    rag_service = RAGService()

    return {
        "status": "ok",
        "ai_available": rag_service.client is not None,
        "active_conversations": len(conversations),
    }
