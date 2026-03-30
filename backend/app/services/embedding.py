import logging
import os
import threading

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Loads SentenceTransformer on first use when eager=False (for low-RAM hosts like Render free)."""

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        eager: bool = True,
    ):
        self.model_name = model_name
        self._model: SentenceTransformer | None = None
        self._dim: int | None = None
        self._lock = threading.Lock()
        if eager:
            self._ensure_model()

    def _ensure_model(self) -> SentenceTransformer:
        with self._lock:
            if self._model is None:
                os.environ.setdefault("OMP_NUM_THREADS", "1")
                os.environ.setdefault("MKL_NUM_THREADS", "1")
                os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
                try:
                    import torch

                    torch.set_num_threads(int(os.getenv("TORCH_NUM_THREADS", "1")))
                except Exception:
                    pass
                logger.info("Loading embedding model: %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
                self._dim = self._model.get_sentence_embedding_dimension()
                logger.info("Model loaded — embedding dimension: %d", self._dim)
            return self._model

    @property
    def model(self) -> SentenceTransformer:
        return self._ensure_model()

    @property
    def dim(self) -> int:
        self._ensure_model()
        assert self._dim is not None
        return self._dim

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        m = self._ensure_model()
        embeddings = m.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        return self.encode([query])[0]
