# Yufeed System Architecture - EU Legal Data Flow

## Overview

This document explains how Yufeed gathers EU legal information from CELEX/EUR-Lex and Légifrance, processes it through a RAG system, extracts obligations, and manages the compliance workflow.

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           DATA INGESTION PIPELINE                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────┐    ┌──────────────┐                                           │
│  │ EUR-Lex RSS  │    │ Légifrance   │                                           │
│  │ (CELEX docs) │    │ RSS (JORF)   │                                           │
│  └──────┬───────┘    └──────┬───────┘                                           │
│         │                   │                                                   │
│         └─────────┬─────────┘                                                   │
│                   ▼                                                             │
│  ┌─────────────────────────────────┐                                            │
│  │   IngestionManager              │  ← Weekly/daily ingestion orchestrator    │
│  │   (ingestion/manager.py)        │                                            │
│  └──────────────┬──────────────────┘                                            │
│                 │                                                               │
│                 ▼                                                               │
│  ┌─────────────────────────────────┐                                            │
│  │   IngestionProcessor            │  ← Processes each document entry          │
│  │   (ingestion/processor.py)      │                                            │
│  └──────────────┬──────────────────┘                                            │
│                 │                                                               │
└─────────────────┼───────────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      DOCUMENT PROCESSING & STORAGE                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │  CellarClient   │  │ ContentExtractor│  │    AI Analyzer  │                 │
│  │  (SPARQL/       │  │ (HTML/PDF text) │  │  (Claude/OpenAI)│                 │
│  │   Metadata)     │  │                 │  │                 │                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                          │
│           └────────────────────┴────────────────────┘                          │
│                              │                                                 │
│                              ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │              LegalDocument (PostgreSQL)                      │              │
│  │  - celex, title, type (regulation/directive/decision)       │              │
│  │  - full_text, article_breakdown                             │              │
│  │  - obligations_json (AI-extracted)                          │              │
│  │  - compliance_domain, risk_level, ai_summary                │              │
│  │  - scope_tags, subject_tags                                 │              │
│  └──────────────────────────┬──────────────────────────────────┘              │
│                             │                                                  │
└─────────────────────────────┼──────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RAG INDEXING PIPELINE                                    │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐                 │
│  │   RAGChunker    │  │  Embedding      │  │  OpenSearch     │                 │
│  │ (chunk_document)│  │  (vectorize)    │  │  (vector DB)    │                 │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘                 │
│           │                    │                    │                          │
│           └────────────────────┴────────────────────┘                          │
│                              │                                                 │
│                              ▼                                                 │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │              LegalChunk (PostgreSQL)                         │              │
│  │  - chunk_id, doc_id, celex                                   │              │
│  │  - chunk_text, token_count                                   │              │
│  │  - article_ref, section_title                                │              │
│  └─────────────────────────────────────────────────────────────┘              │
│                                                                                  │
│  RAG Query Flow:                                                                 │
│  User Query → Search OpenSearch → Retrieve Chunks → Claude → Answer             │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                      OBLIGATION & POLICY WORKFLOW                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │  1. AI Analysis creates obligations_json in LegalDocument   │              │
│  │     (ai/analyzer.py → extract_obligations)                  │              │
│  └──────────────────────────┬──────────────────────────────────┘              │
│                             │                                                  │
│                             ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │  2. seed_obligations_for_doc() creates RegulatoryObligation │              │
│  │     (services/obligation_service.py)                        │              │
│  │     - Status: "draft"                                       │              │
│  │     - obligation_id: "OBL-XXXXXXXXXX"                       │              │
│  └──────────────────────────┬──────────────────────────────────┘              │
│                             │                                                  │
│                             ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │  3. Review Workflow (API: /api/obligations/{id})            │              │
│  │     draft → in_review → approved/rejected                   │              │
│  └──────────────────────────┬──────────────────────────────────┘              │
│                             │                                                  │
│                             ▼ (on approval)                                    │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │  4. Auto-link to PolicyDocument                             │              │
│  │     - Match obligation text to PolicyTemplate               │              │
│  │     - Create InternalRule in PolicySection                  │              │
│  │     - linked_policy_id set                                  │              │
│  └──────────────────────────┬──────────────────────────────────┘              │
│                             │                                                  │
│                             ▼                                                  │
│  ┌─────────────────────────────────────────────────────────────┐              │
│  │  5. Policy Library (services/policy_library.py)             │              │
│  │     - Master policies from templates                        │              │
│  │     - Obligation sections                                   │              │
│  └─────────────────────────────────────────────────────────────┘              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Key Components Explained

### 1. Ingestion Layer

**Files:**
- `ingestion/manager.py` - Orchestrates ingestion from multiple sources
- `ingestion/processor.py` - Processes individual documents
- `ingestion/rss.py` - Fetches EUR-Lex RSS feeds
- `ingestion/legifrance.py` - Fetches French JORF
- `ingestion/cellar.py` - SPARQL client for EU metadata
- `ingestion/content_extractor.py` - Extracts full text from HTML

**Flow:**
1. `IngestionManager.run_weekly_ingestion()` triggers the pipeline
2. Fetches RSS feeds from EUR-Lex (by language) and Légifrance
3. Each entry is normalized with CELEX, title, publication date
4. `IngestionProcessor.process_entry()` handles each document

**Key Issue Areas:**
- EUR-Lex RSS only returns recent documents (Official Journal)
- Content extraction can fail if EUR-Lex HTML structure changes
- SPARQL endpoint can be slow/unavailable

### 2. AI Analysis Layer

**Files:**
- `ai/analyzer.py` - Main analysis orchestrator
- Uses Claude (Anthropic) or OpenAI GPT-4

**Functions:**
- `classify_document()` → compliance_domain (aml, crypto, payments, etc.)
- `assess_risk_level()` → risk_level (high, medium, low)
- `extract_obligations()` → obligations_json array
- `extract_deadline()` → implementation_deadline
- `generate_summary()` → ai_summary

**Obligation JSON Format:**
```json
[
  {
    "obligation": "Banks must verify customer identity...",
    "article": "Article 5",
    "deadline": "2026-01-01",
    "applicability": "banks, PSPs",
    "source_excerpt": "..."
  }
]
```

**Key Issue Areas:**
- Requires ANTHROPIC_API_KEY or OPENAI_API_KEY
- Falls back to heuristics if AI unavailable (less accurate)
- Obligations may be incomplete if document text is missing

### 3. RAG System

**Files:**
- `ai/rag_indexer.py` - Indexes documents into chunks
- `ai/rag_chunker.py` - Splits documents into chunks
- `ai/rag_service.py` - Query/retrieval service
- `ai/embeddings.py` - Vector embedding generation
- `search.py` - OpenSearch integration

**Indexing Flow:**
1. Document chunked by articles/sections (`chunk_document()`)
2. Each chunk embedded using sentence-transformers
3. Stored in PostgreSQL (`LegalChunk` model)
4. Indexed in OpenSearch for hybrid search (BM25 + vectors)

**Query Flow:**
1. User query → `RAGService.answer_query()`
2. Retrieve relevant chunks from OpenSearch
3. Send to Claude with context
4. Return synthesized answer with sources

**Key Issue Areas:**
- Requires OpenSearch running
- Embeddings require GPU/memory for sentence-transformers
- RAG_INDEX_ENABLED must be true in settings

### 4. Obligation Workflow

**Files:**
- `services/obligation_service.py` - Creates obligations from AI analysis
- `api/obligations.py` - REST API for obligation management

**Status Flow:**
```
draft → in_review → approved → (linked to policy)
   ↓       ↓           ↓
        rejected ←────┘
```

**On Approval:**
1. Auto-matches to PolicyTemplate by text similarity
2. Creates/updates PolicyDocument (master policy)
3. Creates PolicySection "OBL - Mapped obligations"
4. Creates InternalRule linked to obligation
5. Sets `linked_policy_id` on obligation

**Key Issue Areas:**
- Requires PolicyTemplates to exist in database
- Text matching may fail to find appropriate policy
- No policy templates = approval fails with 409 error

## Configuration Requirements

### Environment Variables

```bash
# AI Providers (need at least one)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# Databases
DATABASE_URL=postgresql://user:pass@localhost/yufeed
REDIS_URL=redis://localhost:6379/0
OPENSEARCH_URL=https://localhost:9200

# Ingestion
EURLEX_LANGUAGES=en,fr
LEGIFRANCE_JORF_RSS_URL=https://www.legifrance.gouv.fr/...
RSS_USER_AGENT=Yufeed/1.0

# RAG
RAG_INDEX_ENABLED=true
RAG_EMBEDDING_DIM=384
RAG_INDEX_NAME=legal_chunks

# Feature Flags
REGULATORY_SCOPE_FILTER=  # Filter by keywords (optional)
```

## Common Issues & Solutions

### Issue 1: No documents being ingested

**Symptoms:** Empty database, no obligations created

**Check:**
```bash
# 1. Check if RSS fetcher is working
python -c "from src.ingestion.rss import RSSFetcher; r = RSSFetcher(); print(r.get_latest_oj_entries('en'))"

# 2. Check ingestion run status
psql -c "SELECT * FROM ingestion_runs ORDER BY started_at DESC LIMIT 5;"

# 3. Check for failed items
psql -c "SELECT * FROM failed_ingestion_items WHERE status != 'resolved';"
```

**Solutions:**
- EUR-Lex RSS only has recent OJ entries - may need manual backfill
- Check `REGULATORY_SCOPE_FILTER` isn't filtering everything
- Verify RSS_USER_AGENT is set

### Issue 2: Documents ingested but no obligations

**Symptoms:** LegalDocument records exist, obligations_json is NULL

**Check:**
```bash
# Check documents without analysis
psql -c "SELECT celex, title, analyzed_at, obligations_json IS NULL as missing_obligations FROM legal_documents WHERE analyzed_at IS NULL LIMIT 10;"

# Check if AI key is configured
python -c "from src.config import settings; print('Anthropic:', bool(settings.ANTHROPIC_API_KEY))"
```

**Solutions:**
- Set ANTHROPIC_API_KEY or OPENAI_API_KEY
- Run manual analysis: `python scripts/reanalyze_documents.py`
- Check failed_ingestion_items for AI analysis failures

### Issue 3: RAG queries return no results

**Symptoms:** "I couldn't find any relevant documents"

**Check:**
```bash
# Check if chunks exist
psql -c "SELECT COUNT(*) FROM legal_chunks;"

# Check OpenSearch index
curl -s $OPENSEARCH_URL/legal_chunks/_count

# Check if RAG is enabled
python -c "from src.config import settings; print('RAG enabled:', settings.RAG_INDEX_ENABLED)"
```

**Solutions:**
- Re-index documents: `python -c "from src.ai.rag_indexer import RAGIndexer; ..."`
- Verify OpenSearch connection
- Check RAG_INDEX_ENABLED=true

### Issue 4: Obligations can't be approved

**Symptoms:** 409 error on approval, "No policy templates available"

**Check:**
```bash
# Check if templates exist
psql -c "SELECT template_id, name, category FROM policy_templates WHERE is_active = true;"

# Check obligations without policies
psql -c "SELECT obligation_id, status FROM regulatory_obligations WHERE linked_policy_id IS NULL;"
```

**Solutions:**
- Create PolicyTemplate records
- Run `ensure_master_policies()` to create master policies
- Manually link obligations to policies

### Issue 5: Content extraction fails

**Symptoms:** full_text is NULL, word_count is NULL

**Check:**
```bash
# Check extraction methods
psql -c "SELECT content_extraction_method, COUNT(*) FROM legal_documents GROUP BY content_extraction_method;"
```

**Solutions:**
- EUR-Lex HTML structure may have changed
- Try Cellar XHTML endpoint (more reliable)
- Check network connectivity to publications.europa.eu

## Database Schema (Simplified)

```
┌─────────────────────┐
│  regulatory_sources │ ← EUR-Lex, Légifrance config
├─────────────────────┤
│  ingestion_runs     │ ← Track ingestion batches
├─────────────────────┤
│  legal_documents    │ ← Main document storage
│  - celex (PK)       │
│  - full_text        │
│  - obligations_json │
│  - analyzed_at      │
├─────────────────────┤
│  legal_chunks       │ ← RAG chunks
│  - embedding        │
├─────────────────────┤
│  regulatory_obligations │ ← Extracted obligations
│  - status (draft/approved)│
│  - linked_policy_id │
├─────────────────────┤
│  policy_templates   │ ← Policy templates
├─────────────────────┤
│  policy_documents   │ ← Master policies
│  - policy_id        │
│  - status           │
├─────────────────────┤
│  internal_rules     │ ← Rules mapped to obligations
└─────────────────────┘
```

## Next Steps for Debugging

1. **Verify ingestion is working:**
   ```bash
   cd apps/api && python -c "
   from src.database import SessionLocal
   from src.ingestion.manager import IngestionManager
   db = SessionLocal()
   mgr = IngestionManager(db)
   reports = mgr.run_manual_ingestion(send_alerts=False)
   for r in reports:
       print(f'{r.source_name}: {r.status} - {r.items_new} new, {r.items_updated} updated')
   "
   ```

2. **Check document analysis status:**
   ```bash
   psql -c "
   SELECT
       COUNT(*) as total_docs,
       COUNT(analyzed_at) as analyzed,
       COUNT(CASE WHEN obligations_json IS NOT NULL THEN 1 END) as has_obligations
   FROM legal_documents;
   "
   ```

3. **Verify RAG indexing:**
   ```bash
   psql -c "SELECT COUNT(DISTINCT doc_id) as docs_with_chunks, COUNT(*) as total_chunks FROM legal_chunks;"
   ```

4. **Check obligation workflow:**
   ```bash
   psql -c "
   SELECT
       status,
       COUNT(*) as count,
       COUNT(linked_policy_id) as linked_to_policy
   FROM regulatory_obligations
   GROUP BY status;
   "
   ```
