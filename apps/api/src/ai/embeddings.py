"""
Embedding provider for RAG indexing and retrieval.
"""
from typing import List, Optional
import logging
import os

from src.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """Thin wrapper around sentence-transformers embeddings."""

    def __init__(self):
        self.provider = os.getenv("RAG_EMBEDDING_PROVIDER", settings.RAG_EMBEDDING_PROVIDER)
        self.model_name = os.getenv("RAG_EMBEDDING_MODEL", settings.RAG_EMBEDDING_MODEL)
        allow_download = os.getenv("RAG_ALLOW_EMBEDDING_DOWNLOAD", "").strip().lower() in {
            "1",
            "true",
            "yes",
            "y",
        }
        self._model = None
        self._dim: Optional[int] = None
        self._available = False

        if self.provider == "disabled":
            logger.info("RAG embeddings disabled via RAG_EMBEDDING_PROVIDER=disabled")
            return

        if self.provider != "sentence_transformers":
            logger.warning(
                "Unknown RAG_EMBEDDING_PROVIDER=%s. Falling back to disabled.",
                self.provider,
            )
            return

        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            # Default to local-only to avoid blocking ingestion/backfill on a large HF download.
            # Set RAG_ALLOW_EMBEDDING_DOWNLOAD=true to opt into downloading the model in the container.
            try:
                self._model = SentenceTransformer(
                    self.model_name,
                    local_files_only=not allow_download,
                )
            except TypeError:
                # Older sentence-transformers may not support local_files_only; keep it non-blocking by default.
                if not allow_download:
                    raise
                self._model = SentenceTransformer(self.model_name)
            self._dim = self._model.get_sentence_embedding_dimension()
            self._available = True
            logger.info("Loaded embedding model %s (dim=%s)", self.model_name, self._dim)
        except Exception as exc:
            logger.warning("Embedding model unavailable: %s", exc)
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    @property
    def dimension(self) -> Optional[int]:
        return self._dim

    def embed_texts(self, texts: List[str]) -> Optional[List[List[float]]]:
        if not self._available or not self._model:
            return None
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> Optional[List[float]]:
        embeddings = self.embed_texts([text])
        if not embeddings:
            return None
        return embeddings[0]
