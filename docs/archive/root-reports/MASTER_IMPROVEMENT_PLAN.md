# Yufeed Master Improvement Plan
## Comprehensive End-to-End Pipeline Optimization

**Created:** 2026-02-17  
**Status:** Ready for Execution  
**Priority:** Critical (Content extraction failing 93%)

---

## EXECUTIVE SUMMARY

### Current State Problems
| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Content extraction success | 6.5% (17/261) | 70%+ | Critical |
| CELEX accuracy | ~80% | 98%+ | High |
| Obligation quality | Low (title-only) | High (full-text) | High |
| RAG granularity | Document-level | Article-level | Medium |
| Manual review required | 100% | 30% | High |

### Root Causes Identified
1. EUR-Lex RSS feeds broken (404) - using CELLAR now
2. CELEX numbers wrong format (e.g., 32015D2366 instead of 32015L2366)
3. No retry logic for content extraction
4. Single-chunk RAG indexing
5. No confidence threshold for AI analysis
6. No deduplication of obligations

---

## PHASE 1: CRITICAL FIXES (Execute First)

### 1.1 Content Extraction Overhaul
**Priority:** CRITICAL  
**Impact:** 10x improvement in document coverage

**Current Problem:**
- Only 17/261 documents have full_text
- CELLAR XHTML fails silently
- EUR-Lex HTML fallback often 404s
- No PDF/OCR fallback

**Solution:**
```python
# New extraction strategy with multiple fallbacks
EXTRACTION_STRATEGIES = [
    ("cellar_xhtml", priority=1),
    ("eurlex_html", priority=2),
    ("pdf_text_extraction", priority=3),  # NEW
    ("ocr_fallback", priority=4),          # NEW
]

# CELEX variant attempts
CELEX_VARIANTS = [
    "{original}",
    "{fix_document_type}",  # D→L, R→D, etc.
    "{without_sector}",     # Remove leading digit
]
```

**Implementation:**
- [ ] Create `content_extractor_v2.py` with retry logic
- [ ] Add CELEX normalization function
- [ ] Implement PDF text extraction
- [ ] Add progress tracking for batch processing

### 1.2 CELEX Normalization Engine
**Priority:** CRITICAL  
**Impact:** Fix 20% of documents with wrong CELEX

**Known Patterns to Fix:**
```python
CELEX_FIXES = {
    # Document type corrections based on title keywords
    "PSD2": {"wrong": "D2366", "correct": "L2366"},  # Directive not Decision
    "GDPR": {"wrong": "D", "correct": "R"},          # Regulation not Directive
    "AML5": {"wrong": "L", "correct": "D"},          # Directive not Law
    "MiCA": {"wrong": "L", "correct": "R"},          # Regulation
    # Add more as discovered
}
```

**Implementation:**
- [ ] Create `celex_utils.py` with validation/normalization
- [ ] Add regex patterns for common formats
- [ ] Create database migration to fix existing documents
- [ ] Add validation to ingestion pipeline

### 1.3 AI Analysis Confidence Threshold
**Priority:** HIGH  
**Impact:** Reduce low-quality obligations by 50%

**Current:** Creates obligations even from titles only
**Target:** Only auto-create if confidence > 0.7

**Confidence Factors:**
- Has full_text: +0.3
- Has article_breakdown: +0.2
- LLM was used (not heuristic): +0.3
- Content word count > 1000: +0.2

**Implementation:**
- [ ] Modify `analyze_document()` to return confidence
- [ ] Update `seed_obligations_for_doc()` with threshold
- [ ] Create review queue for low-confidence items
- [ ] Add UI indicator for confidence level

---

## PHASE 2: QUALITY IMPROVEMENTS

### 2.1 Article-Level RAG Chunking
**Priority:** HIGH  
**Impact:** 3x better search precision

**Current:** Single chunk per document
**Target:** Chunk by articles with metadata

```python
class ArticleChunk:
    chunk_id: str  # {celex}_art_{number}
    celex: str
    article_number: str
    article_title: str
    content: str
    embedding: List[float]
    obligations_in_article: List[str]
```

**Implementation:**
- [ ] Modify `rag_chunker.py` for article-level splitting
- [ ] Update `rag_indexer.py` to store article metadata
- [ ] Enhance `rag_service.py` for article-aware retrieval
- [ ] Re-index all documents with new strategy

### 2.2 Obligation Deduplication
**Priority:** MEDIUM  
**Impact:** Reduce duplicate work by 30%

**Current:** No deduplication
**Target:** Semantic similarity detection

```python
def find_duplicate_obligations(new_obligation, threshold=0.85):
    new_embedding = embed(new_obligation.text)

    for existing in all_obligations:
        similarity = cosine_similarity(new_embedding, existing.embedding)
        if similarity > threshold:
            return existing, similarity
    return None, 0
```

**Implementation:**
- [ ] Add embedding field to obligations
- [ ] Create deduplication service
- [ ] Run on existing 57 obligations
- [ ] Add to creation pipeline

### 2.3 Document Version Control
**Priority:** MEDIUM  
**Impact:** Track amendments automatically

**Current:** Updates overwrite previous
**Target:** Version history with change detection

```python
class DocumentVersion:
    doc_id: int
    version: int
    content_hash: str
    extracted_at: datetime
    change_summary: str  # AI-generated
    obligations_changed: List[int]
```

**Implementation:**
- [ ] Create `document_versions` table
- [ ] Add content hash calculation
- [ ] Implement change detection
- [ ] Auto-flag obligations for review on changes

---

## PHASE 3: AUTOMATION & INTELLIGENCE

### 3.1 Automatic Relationship Detection
**Priority:** MEDIUM  
**Impact:** Auto-link related documents

**Current:** Manual linking only
**Target:** Detect amends/repeals/supersedes

**Detection Methods:**
1. Title analysis ("amending Regulation...")
2. CELLAR relation queries
3. Content diff analysis

**Implementation:**
- [ ] Create relationship detection service
- [ ] Parse amendment language in titles
- [ ] Query CELLAR for relations
- [ ] Auto-flag obligations for review

### 3.2 Parallel Processing with Celery
**Priority:** LOW  
**Impact:** 5x faster batch processing

**Current:** Sequential processing
**Target:** Distributed task queue

**Implementation:**
- [ ] Set up Celery with Redis
- [ ] Create async tasks for:
  - Document ingestion
  - Content extraction
  - AI analysis
  - RAG indexing
- [ ] Add progress tracking UI

### 3.3 Multi-Language Content Extraction
**Priority:** LOW  
**Impact:** Full EU language coverage

**Current:** Primary language only
**Target:** All 24 EU languages

**Implementation:**
- [ ] Loop through available languages
- [ ] Store translations in DB
- [ ] Enable cross-language RAG
- [ ] Add language preference UI

---

## DATABASE SCHEMA CHANGES

### New Tables

```sql
-- Document versions for tracking changes
CREATE TABLE document_versions (
    id INTEGER PRIMARY KEY,
    doc_id INTEGER REFERENCES legal_documents(id),
    version INTEGER NOT NULL,
    content_hash VARCHAR(64),
    full_text TEXT,
    word_count INTEGER,
    extracted_at TIMESTAMP,
    change_summary TEXT,
    obligations_changed JSON
);

-- Obligation embeddings for deduplication
CREATE TABLE obligation_embeddings (
    obligation_id INTEGER PRIMARY KEY REFERENCES regulatory_obligations(id),
    embedding VECTOR(384),  -- Using pgvector
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Processing queue for async tasks
CREATE TABLE processing_queue (
    id INTEGER PRIMARY KEY,
    task_type VARCHAR(50),
    celex VARCHAR(64),
    status VARCHAR(20),  -- pending, processing, completed, failed
    priority INTEGER DEFAULT 5,
    created_at TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);

-- Content extraction attempts tracking
CREATE TABLE extraction_attempts (
    id INTEGER PRIMARY KEY,
    celex VARCHAR(64),
    strategy VARCHAR(50),
    success BOOLEAN,
    word_count INTEGER,
    error_message TEXT,
    attempted_at TIMESTAMP
);
```

### Modified Tables

```sql
-- Add confidence score to documents
ALTER TABLE legal_documents ADD COLUMN ai_confidence FLOAT;
ALTER TABLE legal_documents ADD COLUMN analysis_quality VARCHAR(20);

-- Add embedding to obligations
ALTER TABLE regulatory_obligations ADD COLUMN embedding_vector VECTOR(384);
```

---

## FILE STRUCTURE CHANGES

### New Files to Create

```
apps/api/src/
├── extraction/
│   ├── __init__.py
│   ├── content_extractor_v2.py      # NEW: Multi-strategy extractor
│   ├── celex_utils.py               # NEW: Validation/normalization
│   ├── pdf_extractor.py             # NEW: PDF text extraction
│   └── retry_handler.py             # NEW: Exponential backoff
│
├── analysis/
│   ├── __init__.py
│   ├── confidence_scorer.py         # NEW: Quality scoring
│   ├── deduplication_service.py     # NEW: Semantic dedup
│   └── relationship_detector.py     # NEW: Auto-relations
│
├── processing/
│   ├── __init__.py
│   ├── celery_app.py                # NEW: Celery setup
│   └── tasks.py                     # NEW: Async tasks
│
└── utils/
    └── content_hash.py              # NEW: Hash calculation

apps/api/scripts/
├── fix_existing_documents.py        # Fix current 261 docs
├── reindex_rag_articles.py          # Re-chunk by articles
├── deduplicate_obligations.py       # Clean up 57 obligations
└── setup_celery.py                  # Initialize task queue
```

### Files to Modify

1. `ingestion/processor.py` - Use new extractor, add confidence check
2. `ingestion/manager.py` - Add batch processing, progress tracking
3. `ai/analyzer.py` - Return confidence scores
4. `ai/rag_chunker.py` - Article-level chunking
5. `ai/rag_indexer.py` - Store article metadata
6. `services/obligation_service.py` - Add deduplication
7. `models/models.py` - Add new fields

---

## EXECUTION CHECKLIST

### Pre-Execution
- [ ] Backup database
- [ ] Verify API is running
- [ ] Check disk space for embeddings
- [ ] Ensure Redis available for Celery

### Phase 1 Execution
- [ ] 1.1 Create content_extractor_v2.py
- [ ] 1.2 Create celex_utils.py
- [ ] 1.3 Run CELEX fix on existing documents
- [ ] 1.4 Re-extract content for all documents
- [ ] 1.5 Add confidence threshold to analyzer
- [ ] 1.6 Test end-to-end flow

### Phase 2 Execution
- [ ] 2.1 Create article-level chunker
- [ ] 2.2 Re-index all documents
- [ ] 2.3 Create deduplication service
- [ ] 2.4 Run on existing obligations
- [ ] 2.5 Create version control tables
- [ ] 2.6 Implement change detection

### Phase 3 Execution
- [ ] 3.1 Set up Celery
- [ ] 3.2 Create async tasks
- [ ] 3.3 Implement relationship detection
- [ ] 3.4 Add multi-language support

### Post-Execution
- [ ] Run full test suite
- [ ] Verify all sources working
- [ ] Check API performance
- [ ] Update documentation
- [ ] Train team on new features

---

## SUCCESS METRICS

| Metric | Before | After Phase 1 | After Phase 2 | After Phase 3 |
|--------|--------|---------------|---------------|---------------|
| Docs with content | 6.5% | 70% | 75% | 80% |
| CELEX accuracy | 80% | 98% | 98% | 98% |
| Obligation quality | Low | Medium | High | High |
| RAG precision | Low | Medium | High | High |
| Manual review % | 100% | 50% | 30% | 20% |
| Processing time | 10min/doc | 5min/doc | 2min/doc | 30sec/doc |

---

## RISK MITIGATION

| Risk | Mitigation |
|------|------------|
| Break existing ingestion | Keep old code path, add feature flag |
| Database migration fails | Backup first, test on copy |
| AI costs spike | Add cost tracking, daily limits |
| Performance degradation | Add caching, async processing |
| Data loss | Full backup, incremental checkpoints |

---

## DOCUMENTATION UPDATES NEEDED

1. Update `SYSTEM_ARCHITECTURE.md` with new components
2. Create `EXTRACTION_STRATEGIES.md` for troubleshooting
3. Update API documentation with confidence scores
4. Create `MIGRATION_GUIDE.md` for team
5. Update `README.md` with new capabilities

---

## NEXT STEPS

**Ready to execute Phase 1?**

Execute this command to start:
```bash
cd /Users/imenenadir/Documents/Yufeed/apps/api && \
python3 execute_master_plan.py --phase 1 --backup
```

Or execute individual components:
```bash
# Component 1.1: Content extraction overhaul
python3 scripts/implement_content_extractor_v2.py

# Component 1.2: CELEX normalization
python3 scripts/implement_celex_utils.py

# Component 1.3: Fix existing documents
python3 scripts/fix_existing_documents.py
```

---

**END OF MASTER PLAN**
