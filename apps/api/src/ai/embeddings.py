"""
Embedding provider for RAG indexing and retrieval.
"""

from typing import Any, Dict, List, Optional, Tuple
import logging
import os
import threading

from src.config import settings

logger = logging.getLogger(__name__)


_MODEL_CACHE_LOCK = threading.Lock()
_MODEL_CACHE: Dict[Tuple[str, str], Dict[str, Any]] = {}
_WARMUP_LOCK = threading.Lock()
_WARMUP_STARTED = False


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
        self._encode_lock: Optional[threading.Lock] = None

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

            cache_key = (self.provider, self.model_name)
            cached = _MODEL_CACHE.get(cache_key)
            if cached:
                self._model = cached["model"]
                self._dim = cached["dim"]
                self._encode_lock = cached["encode_lock"]
                self._available = True
                return

            with _MODEL_CACHE_LOCK:
                cached = _MODEL_CACHE.get(cache_key)
                if cached:
                    self._model = cached["model"]
                    self._dim = cached["dim"]
                    self._encode_lock = cached["encode_lock"]
                    self._available = True
                    return

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
                self._encode_lock = threading.Lock()
                _MODEL_CACHE[cache_key] = {
                    "model": self._model,
                    "dim": self._dim,
                    "encode_lock": self._encode_lock,
                }
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
        encode_lock = self._encode_lock
        if encode_lock is None:
            return None
        with encode_lock:
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


def warm_embeddings_async() -> None:
    """Best-effort background warmup to reduce first-request latency."""
    global _WARMUP_STARTED
    with _WARMUP_LOCK:
        if _WARMUP_STARTED:
            return
        _WARMUP_STARTED = True

    def _run() -> None:
        global _WARMUP_STARTED
        try:
            provider = EmbeddingProvider()
            logger.info(
                "Embedding warmup completed (available=%s, model=%s)",
                provider.available,
                provider.model_name,
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning("Embedding warmup failed: %s", exc)
            with _WARMUP_LOCK:
                _WARMUP_STARTED = False

    thread = threading.Thread(target=_run, name="embedding-warmup", daemon=True)
    thread.start()
