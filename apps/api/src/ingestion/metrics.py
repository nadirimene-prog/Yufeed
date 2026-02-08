"""
Prometheus Metrics for Ingestion Pipeline

Provides observability into the document ingestion process.
"""

from prometheus_client import Counter, Histogram, Gauge

# Document Processing Metrics
DOCS_PROCESSED = Counter(
    "ingestion_documents_processed_total",
    "Total number of documents processed",
    ["source", "status"],  # status: new, updated, skipped, error
)

DOCS_INGESTION_DURATION = Histogram(
    "ingestion_document_duration_seconds",
    "Time spent processing a single document",
    ["source"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

# Content Extraction Metrics
CONTENT_EXTRACTION_TOTAL = Counter(
    "ingestion_content_extraction_total",
    "Total content extraction attempts",
    ["method", "status"],  # method: cellar_xhtml, html, pdf_available; status: success, failure
)

CONTENT_EXTRACTION_DURATION = Histogram(
    "ingestion_content_extraction_seconds",
    "Time spent extracting document content",
    ["method"],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

# CELLAR/SPARQL Metrics
CELLAR_QUERIES_TOTAL = Counter(
    "ingestion_cellar_queries_total",
    "Total CELLAR SPARQL queries",
    ["query_type", "status"],  # query_type: single, bulk; status: success, failure, cache_hit
)

CELLAR_QUERY_DURATION = Histogram(
    "ingestion_cellar_query_seconds",
    "CELLAR SPARQL query duration",
    ["query_type"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0],
)

CELLAR_CACHE_HITS = Counter("ingestion_cellar_cache_hits_total", "CELLAR cache hit count")

CELLAR_CACHE_MISSES = Counter("ingestion_cellar_cache_misses_total", "CELLAR cache miss count")

# AI Analysis Metrics
AI_ANALYSIS_TOTAL = Counter(
    "ingestion_ai_analysis_total",
    "Total AI analysis operations",
    ["status"],  # success, failure, skipped
)

AI_ANALYSIS_DURATION = Histogram(
    "ingestion_ai_analysis_seconds",
    "AI document analysis duration",
    buckets=[1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
)

AI_ANALYSIS_COST = Counter(
    "ingestion_ai_analysis_cost_dollars", "Cumulative AI analysis cost in dollars"
)

AI_ANALYSIS_TOKENS = Counter(
    "ingestion_ai_analysis_tokens_total",
    "Total tokens used in AI analysis",
    ["direction"],  # input, output
)

# RAG Indexing Metrics
RAG_INDEXING_TOTAL = Counter(
    "ingestion_rag_indexing_total",
    "Total RAG indexing operations",
    ["status"],  # success, failure, skipped
)

RAG_INDEXING_DURATION = Histogram(
    "ingestion_rag_indexing_seconds",
    "RAG indexing duration",
    buckets=[1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
)

RAG_CHUNKS_CREATED = Counter("ingestion_rag_chunks_created_total", "Total RAG chunks created")

# Search Indexing Metrics
SEARCH_INDEXING_TOTAL = Counter(
    "ingestion_search_indexing_total",
    "Total search indexing operations",
    ["status"],  # success, failure
)

SEARCH_INDEXING_DURATION = Histogram(
    "ingestion_search_indexing_seconds",
    "Search indexing duration",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0],
)

# Ingestion Run Metrics
INGESTION_RUNS_TOTAL = Counter(
    "ingestion_runs_total",
    "Total ingestion runs",
    ["source", "status"],  # status: completed, failed, partial
)

INGESTION_RUN_DURATION = Histogram(
    "ingestion_run_duration_seconds",
    "Total duration of ingestion runs",
    ["source"],
    buckets=[60, 300, 600, 1200, 1800, 3600, 7200],
)

# Dead Letter Queue Metrics
DLQ_ITEMS_TOTAL = Gauge(
    "ingestion_dlq_items_total",
    "Current number of items in dead letter queue",
    ["status"],  # pending, retrying, exhausted
)

DLQ_RETRIES_TOTAL = Counter(
    "ingestion_dlq_retries_total", "Total DLQ retry attempts", ["status"]  # success, failure
)

# Document Relations Metrics
RELATIONS_STORED = Counter(
    "ingestion_relations_stored_total", "Total document relations stored", ["relation_type"]
)


def record_document_processed(source: str, status: str):
    """Record a document processing event."""
    DOCS_PROCESSED.labels(source=source, status=status).inc()


def record_content_extraction(method: str, status: str, duration: float = None):
    """Record a content extraction event."""
    CONTENT_EXTRACTION_TOTAL.labels(method=method, status=status).inc()
    if duration is not None:
        CONTENT_EXTRACTION_DURATION.labels(method=method).observe(duration)


def record_cellar_query(
    query_type: str, status: str, duration: float = None, cache_hit: bool = False
):
    """Record a CELLAR query event."""
    CELLAR_QUERIES_TOTAL.labels(query_type=query_type, status=status).inc()
    if duration is not None:
        CELLAR_QUERY_DURATION.labels(query_type=query_type).observe(duration)
    if cache_hit:
        CELLAR_CACHE_HITS.inc()
    else:
        CELLAR_CACHE_MISSES.inc()


def record_ai_analysis(
    status: str,
    duration: float = None,
    cost: float = None,
    input_tokens: int = None,
    output_tokens: int = None,
):
    """Record an AI analysis event."""
    AI_ANALYSIS_TOTAL.labels(status=status).inc()
    if duration is not None:
        AI_ANALYSIS_DURATION.observe(duration)
    if cost is not None:
        AI_ANALYSIS_COST.inc(cost)
    if input_tokens is not None:
        AI_ANALYSIS_TOKENS.labels(direction="input").inc(input_tokens)
    if output_tokens is not None:
        AI_ANALYSIS_TOKENS.labels(direction="output").inc(output_tokens)


def record_rag_indexing(status: str, duration: float = None, chunks_created: int = None):
    """Record a RAG indexing event."""
    RAG_INDEXING_TOTAL.labels(status=status).inc()
    if duration is not None:
        RAG_INDEXING_DURATION.observe(duration)
    if chunks_created is not None:
        RAG_CHUNKS_CREATED.inc(chunks_created)


def record_search_indexing(status: str, duration: float = None):
    """Record a search indexing event."""
    SEARCH_INDEXING_TOTAL.labels(status=status).inc()
    if duration is not None:
        SEARCH_INDEXING_DURATION.observe(duration)


def record_ingestion_run(source: str, status: str, duration: float = None):
    """Record an ingestion run completion."""
    INGESTION_RUNS_TOTAL.labels(source=source, status=status).inc()
    if duration is not None:
        INGESTION_RUN_DURATION.labels(source=source).observe(duration)


def update_dlq_gauge(pending: int, retrying: int, exhausted: int):
    """Update DLQ item counts."""
    DLQ_ITEMS_TOTAL.labels(status="pending").set(pending)
    DLQ_ITEMS_TOTAL.labels(status="retrying").set(retrying)
    DLQ_ITEMS_TOTAL.labels(status="exhausted").set(exhausted)


def record_dlq_retry(status: str):
    """Record a DLQ retry attempt."""
    DLQ_RETRIES_TOTAL.labels(status=status).inc()


def record_relation_stored(relation_type: str):
    """Record a document relation storage event."""
    RELATIONS_STORED.labels(relation_type=relation_type).inc()
