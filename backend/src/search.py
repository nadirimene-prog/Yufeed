from opensearchpy import OpenSearch
from src.config import settings
from typing import List, Optional, Dict, Any
from datetime import datetime
import os

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
