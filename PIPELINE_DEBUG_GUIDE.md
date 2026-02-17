# Pipeline Debug Guide - Quick Actions

## Understanding the Data Flow

The system has 4 main stages:

1. **INGEST** → Fetch documents from EUR-Lex/Légifrance
2. **ANALYZE** → AI extracts obligations from documents
3. **INDEX** → Documents chunked and indexed for RAG
4. **WORKFLOW** → Obligations reviewed and linked to policies

## Quick Diagnosis Commands

Run these from `/Users/imenenadir/Documents/Yufeed/apps/api`:

### 1. Check Database State

```bash
# Using SQLite (default for local dev)
sqlite3 compliance.db "
SELECT
    (SELECT COUNT(*) FROM legal_documents) as total_docs,
    (SELECT COUNT(*) FROM legal_documents WHERE analyzed_at IS NOT NULL) as analyzed,
    (SELECT COUNT(*) FROM regulatory_obligations) as total_obligations,
    (SELECT COUNT(*) FROM regulatory_obligations WHERE status='approved') as approved_obligations,
    (SELECT COUNT(*) FROM legal_chunks) as rag_chunks,
    (SELECT COUNT(*) FROM policy_templates WHERE is_active=1) as policy_templates;
"
```

### 2. Check Environment Variables

```bash
# Check if AI keys are set
echo "Anthropic: $ANTHROPIC_API_KEY"
echo "OpenAI: $OPENAI_API_KEY"

# Check config
cat .env | grep -E "(ANTHROPIC|OPENAI|RAG|DATABASE)"
```

### 3. Check Recent Ingestion

```bash
sqlite3 compliance.db "
SELECT source_key, last_ingested_at, is_active
FROM regulatory_sources;
"
```

## Common Problems & Solutions

### Problem 1: No Documents

**Symptom:** `total_docs = 0`

**Cause:** Ingestion hasn't run

**Fix:**
```bash
cd apps/api/src

# Run ingestion manually
python3 -c "
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from ingestion.manager import IngestionManager

db = SessionLocal()
mgr = IngestionManager(db)
reports = mgr.run_manual_ingestion(send_alerts=False)
for r in reports:
    print(f'{r.source_name}: {r.status} - {r.items_new} new, {r.items_updated} updated')
db.close()
"
```

### Problem 2: Documents But No Obligations

**Symptom:** `total_docs > 0` but `total_obligations = 0`

**Cause 1:** Documents not analyzed (no AI key)

**Fix:**
```bash
# Check if AI is configured
export ANTHROPIC_API_KEY=your-key-here

# Re-analyze documents
cd apps/api/src
python3 -c "
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from models import LegalDocument
from ai.analyzer import analyze_document
from services.obligation_service import seed_obligations_for_doc

db = SessionLocal()
docs = db.query(LegalDocument).filter(LegalDocument.analyzed_at.is_(None)).all()
print(f'Found {len(docs)} documents to analyze')

for doc in docs[:5]:  # Analyze first 5
    print(f'Analyzing {doc.celex}...')
    try:
        result = analyze_document({
            'celex': doc.celex,
            'title': doc.title,
            'publication_date': doc.publication_date,
            'full_text': doc.full_text,
            'article_breakdown': doc.article_breakdown.get('articles') if isinstance(doc.article_breakdown, dict) else None,
        })
        doc.compliance_domain = result.get('compliance_domain')
        doc.risk_level = result.get('risk_level')
        doc.obligations_json = result.get('obligations_json')
        doc.ai_summary = result.get('ai_summary')
        doc.analyzed_at = result.get('analyzed_at')
        db.commit()

        count = seed_obligations_for_doc(db, doc)
        print(f'  Created {count} obligations')
    except Exception as e:
        print(f'  Error: {e}')
db.close()
"
```

**Cause 2:** Documents have no full_text (content extraction failed)

**Fix:**
```bash
# Check extraction status
sqlite3 compliance.db "
SELECT content_extraction_method, COUNT(*)
FROM legal_documents
GROUP BY content_extraction_method;
"

# If most are NULL, content extraction is failing
# This happens when EUR-Lex blocks requests or changes HTML structure
```

### Problem 3: No RAG Chunks

**Symptom:** `rag_chunks = 0`

**Fix:**
```bash
cd apps/api/src
python3 -c "
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from ai.rag_indexer import RAGIndexer

db = SessionLocal()
indexer = RAGIndexer(db)
count = indexer.index_all_documents()
print(f'Indexed {count} chunks')
db.close()
"
```

### Problem 4: Can't Approve Obligations

**Symptom:** HTTP 409 "No policy templates available"

**Fix:**
```bash
# Check templates
sqlite3 compliance.db "SELECT template_id, name, is_active FROM policy_templates;"

# If empty, create defaults
cd apps/api/src
python3 -c "
import sys
sys.path.insert(0, '.')
from database import SessionLocal
from models.compliance_workflow import PolicyTemplate

db = SessionLocal()

templates = [
    {'template_id': 'aml-cft-policy', 'name': 'AML/CFT Policy', 'category': 'aml/cft', 'version': '1.0', 'is_active': True},
    {'template_id': 'kyc-policy', 'name': 'KYC Policy', 'category': 'kyc', 'version': '1.0', 'is_active': True},
    {'template_id': 'sanctions-policy', 'name': 'Sanctions Policy', 'category': 'sanctions', 'version': '1.0', 'is_active': True},
]

for t in templates:
    if not db.query(PolicyTemplate).filter_by(template_id=t['template_id']).first():
        db.add(PolicyTemplate(**t))
        print(f'Created {t[\"template_id\"]}')

db.commit()
db.close()
"
```

## The Complete Flow Test

Test each stage:

```bash
# Stage 1: Ingest a specific document
curl -X POST http://localhost:8000/api/ingestion/manual \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"celex": "32016R0679", "source_system": "eur-lex"}'

# Stage 2: Check document was created
sqlite3 compliance.db "SELECT celex, title, analyzed_at FROM legal_documents WHERE celex='32016R0679';"

# Stage 3: Check obligations created
sqlite3 compliance.db "SELECT obligation_id, status FROM regulatory_obligations WHERE celex='32016R0679';"

# Stage 4: Check RAG chunks
sqlite3 compliance.db "SELECT COUNT(*) FROM legal_chunks WHERE celex='32016R0679';"

# Stage 5: Test RAG query
curl "http://localhost:8000/api/query/rag?q=What+are+the+AML+requirements"

# Stage 6: Approve obligation (after creating policy templates)
curl -X PATCH http://localhost:8000/api/obligations/1/approve \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"status": "approved"}'
```

## File Locations

Key files you might need to debug:

| Component | File |
|-----------|------|
| Ingestion | `apps/api/src/ingestion/manager.py` |
| Document Processor | `apps/api/src/ingestion/processor.py` |
| AI Analysis | `apps/api/src/ai/analyzer.py` |
| RAG Indexer | `apps/api/src/ai/rag_indexer.py` |
| Obligations | `apps/api/src/services/obligation_service.py` |
| Policies | `apps/api/src/services/policy_library.py` |
| API Routes | `apps/api/src/api/obligations.py` |

## Need More Help?

1. Check the full architecture doc: `SYSTEM_ARCHITECTURE.md`
2. Run the full diagnostic (requires proper Python path setup)
3. Check logs: `apps/api/logs/` or console output
4. Review the data models: `apps/api/src/models/`
