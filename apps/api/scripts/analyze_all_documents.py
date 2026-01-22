"""
Script to analyze all existing documents with AI.
Run this to populate compliance fields for existing documents.
"""
from src.database import SessionLocal
from src.models.models import LegalDocument
from src.ai.analyzer import analyze_document

db = SessionLocal()

# Get all documents that haven't been analyzed
documents = db.query(LegalDocument).filter(LegalDocument.analyzed_at == None).all()

print(f"Found {len(documents)} documents to analyze\n")

analyzed_count = 0
for doc in documents:
    try:
        print(f"Analyzing: {doc.celex} - {doc.title[:60]}...")
        
        analysis_results = analyze_document({
            "celex": doc.celex,
            "title": doc.title,
            "publication_date": doc.publication_date
        })
        
        # Update document
        doc.compliance_domain = analysis_results.get("compliance_domain")
        doc.risk_level = analysis_results.get("risk_level")
        doc.obligations_json = analysis_results.get("obligations_json")
        doc.implementation_deadline = analysis_results.get("implementation_deadline")
        doc.ai_summary = analysis_results.get("ai_summary")
        doc.analyzed_at = analysis_results.get("analyzed_at")
        
        db.commit()
        analyzed_count += 1
        
        print(f"  ✓ Domain: {doc.compliance_domain}, Risk: {doc.risk_level}")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        db.rollback()

print(f"\n✅ Successfully analyzed {analyzed_count}/{len(documents)} documents")
db.close()
