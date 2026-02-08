"""
Script to add sample EU legal documents to the database for testing.
"""

from src.database import SessionLocal
from src.models.models import LegalDocument
from datetime import datetime

db = SessionLocal()

# Sample documents covering AML, MiCA, GDPR, Payments
sample_docs = [
    {
        "celex": "32024R1624",
        "title": "Regulation (EU) 2024/1624 on the prevention of the use of the financial system for the purposes of money laundering or terrorist financing (AML Regulation)",
        "type": "Regulation",
        "publication_date": datetime(2024, 5, 31),
        "entry_into_force_date": datetime(2024, 7, 1),
        "status": "active",
        "eli": "http://data.europa.eu/eli/reg/2024/1624/oj",
    },
    {
        "celex": "32023R1114",
        "title": "Regulation (EU) 2023/1114 on markets in crypto-assets (MiCA)",
        "type": "Regulation",
        "publication_date": datetime(2023, 6, 9),
        "entry_into_force_date": datetime(2023, 6, 29),
        "status": "active",
        "eli": "http://data.europa.eu/eli/reg/2023/1114/oj",
    },
    {
        "celex": "32015D2366",
        "title": "Directive (EU) 2015/2366 on payment services in the internal market (PSD2)",
        "type": "Directive",
        "publication_date": datetime(2015, 12, 23),
        "entry_into_force_date": datetime(2016, 1, 12),
        "status": "active",
        "eli": "http://data.europa.eu/eli/dir/2015/2366/oj",
    },
    {
        "celex": "32023L2226",
        "title": "Council Directive (EU) 2023/2226 amending Directive 2011/16/EU on administrative cooperation in the field of taxation (DAC8 - Crypto Assets Reporting)",
        "type": "Directive",
        "publication_date": datetime(2023, 10, 17),
        "entry_into_force_date": datetime(2023, 11, 6),
        "status": "active",
        "eli": "http://data.europa.eu/eli/dir/2023/2226/oj",
    },
    {
        "celex": "32024R0901",
        "title": "Regulation (EU) 2024/901 on the establishment of a European Digital Identity Framework (eIDAS 2.0)",
        "type": "Regulation",
        "publication_date": datetime(2024, 3, 13),
        "entry_into_force_date": datetime(2024, 4, 2),
        "status": "active",
        "eli": "http://data.europa.eu/eli/reg/2024/901/oj",
    },
    {
        "celex": "32022R2554",
        "title": "Regulation (EU) 2022/2554 on digital operational resilience for the financial sector (DORA)",
        "type": "Regulation",
        "publication_date": datetime(2022, 12, 14),
        "entry_into_force_date": datetime(2023, 1, 16),
        "status": "active",
        "eli": "http://data.europa.eu/eli/reg/2022/2554/oj",
    },
    {
        "celex": "52023PC0567",
        "title": "Proposal for a Regulation on the prevention of money laundering and terrorist financing (AMLR Proposal)",
        "type": "Regulation",
        "publication_date": datetime(2023, 7, 5),
        "status": "proposal",
        "eli": "http://data.europa.eu/eli/reg_pr/2023/567",
    },
]

try:
    # Check if documents already exist
    existing_celexes = {doc.celex for doc in db.query(LegalDocument.celex).all()}

    added_count = 0
    for doc_data in sample_docs:
        if doc_data["celex"] not in existing_celexes:
            doc = LegalDocument(**doc_data)
            db.add(doc)
            added_count += 1
            print(f"Added: {doc_data['celex']} - {doc_data['title'][:60]}...")
        else:
            print(f"Skipped (exists): {doc_data['celex']}")

    db.commit()
    print(f"\n✅ Successfully added {added_count} new documents to the database")
    print(f"Total documents in database: {db.query(LegalDocument).count()}")

except Exception as e:
    db.rollback()
    print(f"❌ Error: {e}")
finally:
    db.close()
