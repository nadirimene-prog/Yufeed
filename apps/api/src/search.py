from opensearchpy import OpenSearch
from src.config import settings
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)
_embedding_provider = None

def get_opensearch_client():
    """
    Create OpenSearch client with proper security configuration.

    For production:
    - Set OPENSEARCH_SECURITY_ENABLED=true
    - Set OPENSEARCH_USER and OPENSEARCH_PASSWORD
    - Enable SSL/TLS with proper certificates
    """
    # Parse URL
    hosts = [settings.OPENSEARCH_URL]
    if "http" not in settings.OPENSEARCH_URL:
         hosts = [{"host": settings.OPENSEARCH_URL, "port": 9200}]

    # Check if security is enabled (for production)
    security_enabled = os.getenv("OPENSEARCH_SECURITY_ENABLED", "false").lower() == "true"

    if security_enabled:
        # Production configuration with security
        opensearch_user = os.getenv("OPENSEARCH_USER", "admin")
        opensearch_password = os.getenv("OPENSEARCH_PASSWORD")

        if not opensearch_password:
            raise ValueError("OPENSEARCH_PASSWORD must be set when security is enabled")

        client = OpenSearch(
            hosts=hosts,
            http_auth=(opensearch_user, opensearch_password),
            http_compress=True,
            use_ssl=True,
            verify_certs=True,
            ssl_show_warn=True,
            ca_certs=os.getenv("OPENSEARCH_CA_CERT_PATH", "/etc/ssl/certs/ca-certificates.crt")
        )
    else:
        # Development configuration (insecure - for local testing only)
        client = OpenSearch(
            hosts=hosts,
            http_compress=True,
            use_ssl=False,
            verify_certs=False,
            ssl_assert_hostname=False,
            ssl_show_warn=False
        )

    return client

def init_indices():
    client = get_opensearch_client()
    index_name = "legal_documents"
    index_body = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            }
        },
        "mappings": {
            "properties": {
                "celex": {"type": "keyword"},
                "eli": {"type": "keyword"},
                "cellar_id": {"type": "keyword"},
                "title": {"type": "text"},
                "content": {"type": "text"},
                "publication_date": {"type": "date"},
                "entry_into_force_date": {"type": "date"},
                "keywords": {"type": "keyword"},
                "status": {"type": "keyword"},
                "type": {"type": "keyword"},
                # Compliance fields for fast filtering
                "compliance_domain": {"type": "keyword"},
                "risk_level": {"type": "keyword"},
                "implementation_deadline": {"type": "date"},
                "jurisdictional_scope": {"type": "keyword"},
                "ai_summary": {"type": "text"},
                # Full-text content fields
                "full_text": {"type": "text"},
                "word_count": {"type": "integer"}
            }
        }
    }

    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=index_body)


def init_rag_index(embedding_dim: int) -> None:
    client = get_opensearch_client()
    index_name = settings.RAG_INDEX_NAME
    index_body = {
        "settings": {
            "index": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "knn": True,
            }
        },
        "mappings": {
            "properties": {
                "chunk_id": {"type": "keyword"},
                "doc_id": {"type": "integer"},
                "celex": {"type": "keyword"},
                "title": {"type": "text"},
                "chunk_text": {"type": "text"},
                "section_title": {"type": "text"},
                "article_ref": {"type": "keyword"},
                "source_system": {"type": "keyword"},
                "jurisdiction": {"type": "keyword"},
                "language": {"type": "keyword"},
                "publication_date": {"type": "date"},
                "implementation_deadline": {"type": "date"},
                "compliance_domain": {"type": "keyword"},
                "risk_level": {"type": "keyword"},
                "scope_tags": {"type": "keyword"},
                "subject_tags": {"type": "keyword"},
                "chunk_index": {"type": "integer"},
                "char_count": {"type": "integer"},
                "token_count": {"type": "integer"},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": embedding_dim,
                    "method": {
                        "engine": "nmslib",
                        "space_type": "cosinesimil",
                        "name": "hnsw",
                        "parameters": {"ef_construction": 256, "m": 16},
                    },
                },
            }
        },
    }

    if not client.indices.exists(index=index_name):
        client.indices.create(index=index_name, body=index_body)
        return

    try:
        existing = client.indices.get_mapping(index=index_name)
        properties = existing.get(index_name, {}).get("mappings", {}).get("properties", {})
        embedding = properties.get("embedding") if isinstance(properties, dict) else None
        existing_dim = embedding.get("dimension") if isinstance(embedding, dict) else None
        if existing_dim and existing_dim != embedding_dim:
            logger.warning(
                "RAG index %s exists with embedding_dim=%s (expected %s)",
                index_name,
                existing_dim,
                embedding_dim,
            )
    except Exception as exc:
        logger.warning("Failed to inspect RAG index mapping: %s", exc)

def search_documents(
    q: Optional[str] = None,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    compliance_domain: Optional[str] = None,
    risk_level: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    from_: int = 0,
    size: int = 10
) -> Dict[str, Any]:
    client = get_opensearch_client()
    index_name = "legal_documents"

    must_clauses = []
    filter_clauses = []

    # Full-text search
    if q:
        must_clauses.append({
            "multi_match": {
                "query": q,
                "fields": ["title^3", "full_text^2", "ai_summary^1.5", "celex", "content"]
            }
        })
    else:
        must_clauses.append({"match_all": {}})

    # Filters
    if doc_type:
        filter_clauses.append({"term": {"type": doc_type}})

    if status:
        filter_clauses.append({"term": {"status": status}})

    if compliance_domain:
        filter_clauses.append({"term": {"compliance_domain": compliance_domain}})

    if risk_level:
        filter_clauses.append({"term": {"risk_level": risk_level}})

    if date_from or date_to:
        range_query = {}
        if date_from:
            range_query["gte"] = date_from.isoformat()
        if date_to:
            range_query["lte"] = date_to.isoformat()
        filter_clauses.append({"range": {"publication_date": range_query}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "filter": filter_clauses
            }
        },
        "from": from_,
        "size": size,
        "track_total_hits": True,
        "sort": [
            {"_score": {"order": "desc"}},
            {"publication_date": {"order": "desc"}}
        ]
    }

    response = client.search(index=index_name, body=body)

    hits = response["hits"]["hits"]
    total = response["hits"]["total"]["value"]

    results = []
    for hit in hits:
        source = hit["_source"]
        source["score"] = hit["_score"]
        results.append(source)

    return {
        "total": total,
        "results": results
    }


def _rrf_scores(hits: List[Dict[str, Any]], k: int = 60) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    for rank, hit in enumerate(hits, start=1):
        doc_id = hit.get("_id")
        if not doc_id:
            continue
        scores[doc_id] = 1.0 / (k + rank)
    return scores


def _merge_hybrid_results(
    bm25_hits: List[Dict[str, Any]],
    vector_hits: List[Dict[str, Any]],
    alpha: float,
    size: int,
) -> List[Dict[str, Any]]:
    bm25_scores = _rrf_scores(bm25_hits)
    vector_scores = _rrf_scores(vector_hits)

    merged: Dict[str, Dict[str, Any]] = {}
    for hit in bm25_hits + vector_hits:
        doc_id = hit.get("_id")
        if not doc_id:
            continue
        if doc_id not in merged:
            merged[doc_id] = hit

    scored: List[Tuple[float, Dict[str, Any]]] = []
    for doc_id, hit in merged.items():
        bm25 = bm25_scores.get(doc_id, 0.0)
        vector = vector_scores.get(doc_id, 0.0)
        score = (alpha * bm25) + ((1.0 - alpha) * vector)
        hit["_hybrid_score"] = score
        hit["_bm25_score"] = bm25
        hit["_vector_score"] = vector
        scored.append((score, hit))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [hit for _, hit in scored[:size]]


def search_rag_chunks(
    q: str,
    size: int = 8,
    filters: Optional[Dict[str, Any]] = None,
    alpha: Optional[float] = None,
) -> Dict[str, Any]:
    client = get_opensearch_client()
    index_name = settings.RAG_INDEX_NAME
    filters = filters or {}
    alpha = settings.RAG_HYBRID_ALPHA if alpha is None else alpha

    filter_clauses = []
    for field in [
        "compliance_domain",
        "risk_level",
        "jurisdiction",
        "language",
        "source_system",
    ]:
        if filters.get(field):
            filter_clauses.append({"term": {field: filters[field]}})

    if filters.get("publication_date"):
        filter_clauses.append({"range": {"publication_date": filters["publication_date"]}})

    bm25_body = {
        "query": {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": [
                                "chunk_text^2",
                                "title^1.5",
                                "section_title",
                                "article_ref",
                                "celex",
                            ],
                        }
                    }
                ],
                "filter": filter_clauses,
            }
        },
        "size": max(size * 3, 10),
        "track_total_hits": True,
    }

    bm25_response = client.search(index=index_name, body=bm25_body)
    bm25_hits = bm25_response.get("hits", {}).get("hits", [])

    vector_hits: List[Dict[str, Any]] = []
    if alpha < 1.0:
        try:
            from src.ai.embeddings import EmbeddingProvider

            global _embedding_provider
            if _embedding_provider is None:
                _embedding_provider = EmbeddingProvider()
            provider = _embedding_provider
            if provider.available:
                vector = provider.embed_query(q)
            else:
                vector = None
        except Exception as exc:
            logger.warning("Embedding provider unavailable: %s", exc)
            vector = None

        if vector:
            vector_query = {
                "bool": {
                    "filter": filter_clauses,
                    "must": [
                        {
                            "knn": {
                                "embedding": {
                                    "vector": vector,
                                    "k": max(size * 5, 20),
                                }
                            }
                        }
                    ],
                }
            }
            vector_body = {
                "query": vector_query,
                "size": max(size * 3, 10),
                "track_total_hits": True,
            }
            try:
                vector_response = client.search(index=index_name, body=vector_body)
                vector_hits = vector_response.get("hits", {}).get("hits", [])
            except Exception as exc:
                logger.warning("Vector search failed, falling back to BM25 only: %s", exc)
                vector_hits = []

    if not vector_hits or alpha >= 1.0:
        hits = bm25_hits[:size]
    else:
        hits = _merge_hybrid_results(bm25_hits, vector_hits, alpha=alpha, size=size)

    results = []
    for hit in hits:
        source = hit.get("_source", {})
        source["score"] = hit.get("_hybrid_score", hit.get("_score", 0.0))
        source["bm25_score"] = hit.get("_bm25_score")
        source["vector_score"] = hit.get("_vector_score")
        results.append(source)

    return {
        "total": len(results),
        "results": results,
    }


def index_document(document):
    """
    Index a single document in OpenSearch.

    Args:
        document: LegalDocument model instance
    """
    client = get_opensearch_client()
    index_name = "legal_documents"

    body = {
        "celex": document.celex,
        "eli": document.eli,
        "cellar_id": document.cellar_id,
        "title": document.title,
        "content": "",  # Legacy field
        "publication_date": document.publication_date.isoformat() if document.publication_date else None,
        "entry_into_force_date": document.entry_into_force_date.isoformat() if document.entry_into_force_date else None,
        "status": document.status,
        "type": document.type,
        "compliance_domain": document.compliance_domain,
        "risk_level": document.risk_level,
        "implementation_deadline": document.implementation_deadline.isoformat() if document.implementation_deadline else None,
        "jurisdictional_scope": document.jurisdictional_scope,
        "ai_summary": document.ai_summary,
        "full_text": document.full_text,
        "word_count": document.word_count
    }

    try:
        client.index(index=index_name, id=document.celex, body=body)
        return True
    except Exception as e:
        print(f"Failed to index document {document.celex}: {e}")
        return False
