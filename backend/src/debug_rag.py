import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ai.orchestrator import AMLOfficer
from src.database import SessionLocal

async def test_ask():
    db = SessionLocal()
    try:
        officer = AMLOfficer(db)
        question = "What are the CDD requirements for high-risk customers under AMLD 5?"
        print(f"Asking question: {question}")
        
        response = await officer.ask(question=question)
        
        print("\nResponse:")
        import json
        print(f"Response:\n{json.dumps(response, indent=2, default=str)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(test_ask())
