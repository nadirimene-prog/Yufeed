import sys
import os
import requests
import json
from datetime import datetime
from src.database import SessionLocal
from src.models import models
from src.search import get_opensearch_client, init_indices

# Ensure we can import src
sys.path.append(os.getcwd())

API_URL = "http://localhost:8000"

def test_api_flow():
    print("WARNING: Ideally run this with backend running: `uvicorn src.main:app --host 0.0.0.0 --port 8000`")
    
    # 1. Setup DB Data
    db = SessionLocal()
    # clean up
    db.query(models.AlertEvent).delete()
    db.query(models.LegalVersion).delete()
    db.query(models.LegalRelation).delete()
    db.query(models.LegalDocument).delete()
    db.query(models.Watchlist).delete()
    db.commit()

    print(" Creating dummy document...")
    doc = models.LegalDocument(
        celex="32016R0679",
        title="Regulation (EU) 2016/679 (GDPR)",
        type="regulation",
        publication_date=datetime(2016, 5, 4),
        status="active"
    )
    db.add(doc)
    db.commit()
    print(f" Document created: {doc.celex}")

    # 2. Setup OpenSearch Index
    print(" Indexing document in OpenSearch...")
    init_indices()
    client = get_opensearch_client()
    client.index(
        index="legal_documents",
        body={
            "celex": doc.celex,
            "title": doc.title,
            "content": "Full text of General Data Protection Regulation...",
            "publication_date": "2016-05-04",
            "type": "regulation",
            "status": "active"
        },
        refresh=True
    )
    print(" Document indexed")

    # 3. Test Search API
    print(" Testing /search endpoint...")
    try:
        r = requests.get(f"{API_URL}/search", params={"q": "General Data Protection", "type": "regulation"})
        if r.status_code == 200:
            data = r.json()
            print(f" Search results: {data['total']} hits")
            assert data['total'] > 0
            print(" Search test PASSED")
        else:
            print(f" Search test FAILED: {r.status_code} - {r.text}")
    except Exception as e:
         print(f" Search test FAILED (connection error? is backend running?): {e}")

    # 4. Test Watchlists
    print(" Testing POST /watchlists...")
    try:
        payload = {
            "name": "GDPR Watch",
            "mode": "email",
            "query_json": {"q": "GDPR"},
            "schedule": "daily"
        }
        r = requests.post(f"{API_URL}/watchlists", json=payload)
        if r.status_code == 200:
            wl = r.json()
            print(f" Watchlist created: {wl['id']}")
            
            # Test GET /watchlists
            r2 = requests.get(f"{API_URL}/watchlists")
            print(f" Watchlists count: {len(r2.json())}")
            print(" Watchlist test PASSED")
        else:
            print(f" Watchlist test FAILED: {r.status_code} - {r.text}")

    except Exception as e:
         print(f" Watchlist test FAILED: {e}")

    db.close()

if __name__ == "__main__":
    test_api_flow()
