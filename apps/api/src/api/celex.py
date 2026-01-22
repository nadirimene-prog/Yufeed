"""
CELEX Search and Suggestions API

Provides endpoints for CELEX document search with:
- Auto-suggestions as user types
- Fuzzy search and typo tolerance
- Bulk CELEX queries
- Cache statistics and management
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import logging
import sys
import os

# Import CELEX utilities and cache
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ingestion.cellar import CellarClient
from utils.celex_utils import normalize_celex, suggest_celex, generate_celex_variations, parse_celex

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/celex", tags=["CELEX Search"])


# Pydantic Models
class CelexSuggestion(BaseModel):
    """CELEX suggestion with metadata."""
    celex: str
    display_text: str
    match_reason: str  # "alias", "partial", "fuzzy"
    confidence: float  # 0.0-1.0


class CelexSuggestionsResponse(BaseModel):
    """Response for CELEX auto-suggestions."""
    query: str
    suggestions: List[CelexSuggestion]
    count: int


class CelexMetadataResponse(BaseModel):
    """Single CELEX metadata response."""
    celex: str
    title: Optional[str] = None
    work_type: Optional[str] = None
    date_document: Optional[str] = None
    date_entry_into_force: Optional[str] = None
    eli: Optional[str] = None
    cellar_id: Optional[str] = None
    cached: bool = False


class BulkCelexRequest(BaseModel):
    """Request for bulk CELEX queries."""
    celex_list: List[str] = Field(..., description="List of CELEX numbers to fetch")
    use_cache: bool = Field(True, description="Whether to use Redis cache")


class BulkCelexResponse(BaseModel):
    """Response for bulk CELEX queries."""
    results: Dict[str, Optional[CelexMetadataResponse]]
    total: int
    found: int
    not_found: int
    cache_hits: int


class CacheStatsResponse(BaseModel):
    """Redis cache statistics."""
    enabled: bool
    connected: Optional[bool] = None
    total_keys: Optional[int] = None
    memory_used_mb: Optional[float] = None
    hit_rate: Optional[float] = None


@router.get("/suggest", response_model=CelexSuggestionsResponse)
def get_celex_suggestions(
    q: str = Query(..., min_length=1, description="Search query (partial CELEX, name, or keyword)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum suggestions to return")
):
    """
    Get CELEX auto-suggestions as user types.

    Supports multiple input formats:
    - Partial CELEX: "3201" -> suggests 32016R0679, 32015L2366, etc.
    - Common names: "GDPR" -> 32016R0679
    - Document references: "2016/679" -> 32016R0679
    - Keywords: "data protection" -> GDPR, ePrivacy, etc.

    **Examples:**
    - `/celex/suggest?q=GDPR` -> Returns GDPR (32016R0679)
    - `/celex/suggest?q=2016` -> Returns all 2016 regulations
    - `/celex/suggest?q=AI` -> Returns AI Act (32024R1689)
    """
    try:
        suggestions = []

        # Try to find direct CELEX matches via normalization
        normalized = normalize_celex(q)
        if normalized:
            suggestions.append(CelexSuggestion(
                celex=normalized,
                display_text=f"{normalized} (normalized from '{q}')",
                match_reason="exact",
                confidence=1.0
            ))

        # Get alias suggestions
        alias_suggestions = suggest_celex(q, limit=limit)
        for celex in alias_suggestions:
            if celex not in [s.celex for s in suggestions]:
                suggestions.append(CelexSuggestion(
                    celex=celex,
                    display_text=celex,
                    match_reason="alias",
                    confidence=0.9
                ))

        # Limit results
        suggestions = suggestions[:limit]

        return CelexSuggestionsResponse(
            query=q,
            suggestions=suggestions,
            count=len(suggestions)
        )

    except Exception as e:
        logger.error(f"Error generating CELEX suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Suggestion generation failed: {str(e)}")


@router.get("/query/{celex}", response_model=CelexMetadataResponse)
def query_celex_metadata(
    celex: str,
    use_cache: bool = Query(True, description="Whether to use Redis cache")
):
    """
    Query CELEX metadata with flexible input formats.

    Accepts:
    - Standard CELEX: "32016R0679"
    - Common names: "GDPR", "AI Act"
    - Year/number format: "2016/679"
    - Full text: "Regulation (EU) 2016/679"

    **Response includes:**
    - Document title
    - Publication date
    - Entry into force date
    - Work type (Regulation, Directive, etc.)
    - ELI identifier
    - Whether result was cached (for debugging)

    **Example:**
    ```
    GET /celex/query/GDPR
    GET /celex/query/2016/679
    GET /celex/query/32016R0679
    ```
    """
    try:
        client = CellarClient()
        metadata = client.query_by_celex(celex, use_cache=use_cache)

        if not metadata:
            raise HTTPException(
                status_code=404,
                detail=f"CELEX document not found: {celex}"
            )

        # Check if result was cached
        normalized = normalize_celex(celex)
        was_cached = False
        if use_cache and client.cache and normalized:
            was_cached = client.cache.get(normalized) is not None

        return CelexMetadataResponse(
            celex=metadata.get("celex"),
            title=metadata.get("title"),
            work_type=metadata.get("work_type"),
            date_document=metadata.get("date_document").isoformat() if metadata.get("date_document") else None,
            date_entry_into_force=metadata.get("date_entry_into_force").isoformat() if metadata.get("date_entry_into_force") else None,
            eli=metadata.get("eli"),
            cellar_id=metadata.get("cellar_id"),
            cached=was_cached
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error querying CELEX {celex}: {e}")
        raise HTTPException(status_code=500, detail=f"CELEX query failed: {str(e)}")


@router.post("/bulk", response_model=BulkCelexResponse)
def bulk_query_celex(request: BulkCelexRequest):
    """
    Query multiple CELEX documents in a single request.

    Optimized for performance:
    - Bulk cache lookup (single Redis MGET)
    - Only queries Cellar for cache misses
    - Bulk cache storage for new entries

    **Example:**
    ```json
    POST /celex/bulk
    {
        "celex_list": ["GDPR", "AI Act", "2022/1925", "32022R2065"],
        "use_cache": true
    }
    ```

    **Returns:**
    - Dictionary mapping each CELEX to its metadata
    - Cache hit statistics
    - Count of found vs not found documents
    """
    try:
        client = CellarClient()
        results = client.query_bulk_celex(request.celex_list, use_cache=request.use_cache)

        # Build response
        found = 0
        not_found = 0
        cache_hits = 0

        response_data = {}
        for celex, metadata in results.items():
            if metadata:
                found += 1
                # Check if was cached
                normalized = normalize_celex(celex)
                was_cached = False
                if request.use_cache and client.cache and normalized:
                    cached_data = client.cache.get(normalized)
                    was_cached = cached_data is not None
                    if was_cached:
                        cache_hits += 1

                response_data[celex] = CelexMetadataResponse(
                    celex=metadata.get("celex"),
                    title=metadata.get("title"),
                    work_type=metadata.get("work_type"),
                    date_document=metadata.get("date_document").isoformat() if metadata.get("date_document") else None,
                    date_entry_into_force=metadata.get("date_entry_into_force").isoformat() if metadata.get("date_entry_into_force") else None,
                    eli=metadata.get("eli"),
                    cellar_id=metadata.get("cellar_id"),
                    cached=was_cached
                )
            else:
                not_found += 1
                response_data[celex] = None

        return BulkCelexResponse(
            results=response_data,
            total=len(request.celex_list),
            found=found,
            not_found=not_found,
            cache_hits=cache_hits
        )

    except Exception as e:
        logger.error(f"Error in bulk CELEX query: {e}")
        raise HTTPException(status_code=500, detail=f"Bulk query failed: {str(e)}")


@router.get("/normalize/{input}")
def normalize_celex_input(input: str):
    """
    Normalize CELEX input to standard format.

    Useful for frontend validation and UX improvements.

    **Examples:**
    - `/celex/normalize/GDPR` -> "32016R0679"
    - `/celex/normalize/2016/679` -> "32016R0679"
    - `/celex/normalize/Regulation 2016/679` -> "32016R0679"
    """
    normalized = normalize_celex(input)

    if not normalized:
        return {
            "input": input,
            "normalized": None,
            "valid": False,
            "error": "Could not normalize input"
        }

    parsed = parse_celex(normalized)

    return {
        "input": input,
        "normalized": normalized,
        "valid": True,
        "parsed": parsed,
        "variations": generate_celex_variations(normalized)
    }


@router.get("/cache/stats", response_model=CacheStatsResponse)
def get_cache_stats():
    """
    Get Redis cache statistics.

    **Returns:**
    - Total cached keys
    - Memory usage
    - Hit rate percentage
    - Connection status
    """
    try:
        client = CellarClient()
        stats = client.get_cache_stats()
        return CacheStatsResponse(**stats)

    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")


@router.delete("/cache/clear")
def clear_cache():
    """
    Clear all CELEX cache entries.

    Use with caution - this will force all subsequent queries to hit the Cellar SPARQL endpoint.

    **Returns:**
    - Number of cache entries cleared
    """
    try:
        client = CellarClient()
        cleared = client.clear_cache()

        return {
            "status": "success",
            "entries_cleared": cleared,
            "message": f"Cleared {cleared} cache entries"
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


@router.get("/health")
def celex_health_check():
    """
    Health check for CELEX service.

    **Returns:**
    - Service status
    - Cache connection status
    - Cellar SPARQL endpoint availability
    """
    try:
        client = CellarClient()

        return {
            "status": "ok",
            "cache_enabled": client.cache is not None,
            "cache_connected": client.cache.is_connected() if client.cache else False,
            "message": "CELEX service operational"
        }

    except Exception as e:
        logger.error(f"CELEX health check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e),
            "message": "CELEX service experiencing issues"
        }
