# Add at the top of rag_service.py temporarily
import logging

logger = logging.getLogger(__name__)


# In __init__:
def __init__(self, db=None):
    from src.config import settings

    try:
        from anthropic import AsyncAnthropic
    except ImportError:
        AsyncAnthropic = None  # type: ignore

    api_key = settings.ANTHROPIC_API_KEY
    logger.info(f"ANTHROPIC_API_KEY from settings: {api_key[:20]}..." if api_key else "NOT SET")
    self.client = AsyncAnthropic(api_key=api_key) if api_key and AsyncAnthropic else None
    logger.info(f"Client created: {self.client is not None}")
    self.db = db
