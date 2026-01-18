"""
Script to index all legal documents from database into OpenSearch.
"""
from src.database import SessionLocal
from src.models.models import LegalDocument
from src.search import get_opensearch_client, init_indices

db = SessionLocal()
client = get_opensearch_client()

# Ensure index exists
try:
    init_indices()
    print("✅ OpenSearch index initialized")
except Exception as e:
    print(f"Index already exists or error: {e}")

# Fetch all documents from database
documents = db.query(LegalDocument).all()
print(f"\nFound {len(documents)} documents in database")

# Index each document
indexed_count = 0
for doc in documents:
    try:
        doc_body = {
            "celex": doc.celex,
            "title": doc.title,
            "type": doc.type or "Unknown",
            "status": doc.status,
            "publication_date": doc.publication_date.isoformat() if doc.publication_date else None,
            "content": doc.title,  # Using title as content for now
        }
        
        # Index document (using celex as ID for idempotency)
        client.index(
            index="legal_documents",
            id=doc.celex,
            body=doc_body,
            refresh=True  # Make immediately searchable
        )
        indexed_count += 1
        print(f"Indexed: {doc.celex} - {doc.title[:60]}...")
        
    except Exception as e:
        print(f"Error indexing {doc.celex}: {e}")

print(f"\n✅ Successfully indexed {indexed_count}/{len(documents)} documents")

# Verify by searching
print("\n--- Testing Search ---")
try:
    response = client.search(
        index="legal_documents",
        body={"query": {"match_all": {}}, "size": 3}
    )
    print(f"Total documents in OpenSearch: {response['hits']['total']['value']}")
    print("\nSample documents:")
    for hit in response['hits']['hits']:
        print(f"  - {hit['_source']['celex']}: {hit['_source']['title'][:60]}...")
except Exception as e:
    print(f"Search test failed: {e}")

db.close()
