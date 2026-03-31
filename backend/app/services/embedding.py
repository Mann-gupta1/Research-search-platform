import logging
import os
import threading
import time
from typing import Any, Optional

import numpy as np
import requests

logger = logging.getLogger(__name__)

# HF Inference via Router (api-inference.huggingface.co returns 410 Gone — deprecated)
_DEFAULT_HF_INFERENCE_URL = (
    "https://router.huggingface.co/hf-inference/models/"
    "sentence-transformers/all-MiniLM-L6-v2"
)


def _l2_normalize(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-12:
        return v.astype(np.float32)
    return (v / n).astype(np.float32)


def _raw_to_vector(raw: Any) -> np.ndarray:
    """HF feature-extraction: [seq, dim] token embeddings or [dim] vector."""
    arr = np.asarray(raw, dtype=np.float32)
    if arr.ndim == 3:
        if arr.shape[0] == 1:
            arr = arr[0]
        else:
            arr = arr.mean(axis=0)
    if arr.ndim == 2:
        return arr.mean(axis=0).astype(np.float32)
    if arr.ndim == 1:
        return arr.astype(np.float32)
    raise ValueError(f"Unexpected embedding array shape: {arr.shape}")


def _validate_hf_response(data: Any) -> None:
    """HF sometimes returns {'error': '...'} instead of a vector."""
    if isinstance(data, dict):
        err = data.get("error") or data.get("message") or data
        raise RuntimeError(f"Hugging Face API error object: {err}")
    if data is None:
        raise ValueError("Empty response from Hugging Face API")


def _peel_nested_list_wrapper(data: Any) -> Any:
    """
    HF sometimes returns [[v1,...,v384]] instead of [v1,...,v384].
    Peel only when: one outer element, inner is a flat numeric vector (not token rows).
    Token matrices: [[row],[row],...] — inner[0] is a list of floats (one token) but
    len(data[0])>1 rows → do not peel here; _raw_to_vector mean-pools.
    """
    if not isinstance(data, list) or len(data) != 1:
        return data
    inner = data[0]
    if not isinstance(inner, list) or len(inner) == 0:
        return data
    if not isinstance(inner[0], (int, float)):
        return data
    arr = np.asarray(inner, dtype=np.float32)
    if arr.ndim == 1:
        return inner
    return data


def _parse_hf_json(data: Any) -> np.ndarray:
    """
    Normalize HF Inference responses (feature-extraction / models API).
    Handles error JSON, nested lists, token matrices [seq, dim], and plain [dim].
    """
    _validate_hf_response(data)
    cur = _peel_nested_list_wrapper(data)
    try:
        return _raw_to_vector(cur)
    except Exception as e:
        preview = repr(data)[:400] if not isinstance(data, dict) else str(data)[:400]
        raise ValueError(f"Could not parse HF embedding: {e}; preview={preview}") from e


class EmbeddingService:
    """
    If HUGGINGFACEHUB_API_TOKEN is set (and EMBEDDING_BACKEND allows it), uses
    Hugging Face Inference API — no local PyTorch (good for Render free tier).

    Otherwise uses SentenceTransformer locally (same model name, same 384-dim vectors).
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        eager: bool = True,
        hf_token: Optional[str] = None,
        embedding_backend: str = "auto",
        hf_inference_url: Optional[str] = None,
        expected_dim: int = 384,
    ):
        self.model_name = model_name
        self._expected_dim = expected_dim
        self._hf_inference_url = hf_inference_url or os.getenv(
            "HF_INFERENCE_URL", _DEFAULT_HF_INFERENCE_URL
        )

        self._use_hf = False
        if embedding_backend == "hf":
            if not hf_token:
                raise ValueError("EMBEDDING_BACKEND=hf requires HUGGINGFACEHUB_API_TOKEN")
            self._use_hf = True
        elif embedding_backend == "local":
            self._use_hf = False
        else:
            self._use_hf = bool(hf_token)

        self._hf_token = hf_token
        self._model = None
        self._dim: Optional[int] = expected_dim if self._use_hf else None
        self._lock = threading.Lock()

        if self._use_hf:
            logger.info(
                "EmbeddingService: Hugging Face Inference API (%s)",
                self._hf_inference_url,
            )
            if eager:
                try:
                    self._hf_embed_single("warmup")
                except Exception as e:
                    logger.warning("HF warm-up failed (retry on first query): %s", e)
        elif eager:
            self._ensure_model()

    def _hf_request(self, inputs: str | list[str]) -> Any:
        headers = {
            "Authorization": f"Bearer {self._hf_token}",
            "Content-Type": "application/json",
        }
        last_txt = ""
        for attempt in range(4):
            r = requests.post(
                self._hf_inference_url,
                headers=headers,
                json={"inputs": inputs},
                timeout=120,
            )
            last_txt = r.text
            if r.status_code == 503:
                time.sleep(10 * (attempt + 1))
                logger.warning("HF API 503 — model loading, retry %s", attempt + 1)
                continue
            if r.status_code == 410:
                raise RuntimeError(
                    "HF API 410: api-inference.huggingface.co is deprecated. "
                    "Set HF_INFERENCE_URL to https://router.huggingface.co/hf-inference/models/"
                    "<your-model> (see embedding.py default). "
                    + r.text[:400]
                )
            if r.status_code >= 400:
                raise RuntimeError(f"HF API {r.status_code}: {r.text[:800]}")
            try:
                data = r.json()
            except ValueError as e:
                raise RuntimeError(f"HF API non-JSON body: {last_txt[:500]}") from e
            _validate_hf_response(data)
            return data
        raise RuntimeError(f"HF API failed after retries: {last_txt[:500]}")

    def _hf_embed_single(self, text: str) -> np.ndarray:
        data = self._hf_request(text)
        vec = _parse_hf_json(data)
        out = _l2_normalize(vec)
        if out.shape[0] != self._expected_dim:
            raise ValueError(
                f"Embedding length {out.shape[0]} != expected {self._expected_dim} "
                "(Milvus collection dim); check HF model / HF_INFERENCE_URL"
            )
        if os.getenv("HF_EMBED_DEBUG", "").lower() in ("1", "true", "yes"):
            logger.info("HF embedding OK: len=%s", int(out.shape[0]))
        return out

    def _hf_embed_chunk(self, texts: list[str]) -> np.ndarray:
        """Batch request when possible; same 384-d L2-normalized vectors as local model."""
        if len(texts) == 1:
            return self._hf_embed_single(texts[0])[np.newaxis, :]

        data = self._hf_request(texts)
        # Batch: list of per-sequence outputs
        if isinstance(data, list) and len(data) == len(texts):
            rows = [_l2_normalize(_parse_hf_json(item)) for item in data]
            return np.stack(rows, axis=0)

        # Fallback: one call per text (handles odd response shapes)
        rows = [self._hf_embed_single(t) for t in texts]
        return np.stack(rows, axis=0)

    def _ensure_model(self):
        if self._use_hf:
            return None
        from sentence_transformers import SentenceTransformer

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
    def model(self):
        if self._use_hf:
            raise RuntimeError("Local model disabled when using HF Inference API")
        return self._ensure_model()

    @property
    def dim(self) -> int:
        if self._use_hf:
            return self._expected_dim
        self._ensure_model()
        assert self._dim is not None
        return self._dim

    @property
    def is_ready(self) -> bool:
        if self._use_hf:
            return True
        return self._model is not None

    def encode(self, texts: list[str], batch_size: int = 64) -> np.ndarray:
        if not texts:
            return np.array([], dtype=np.float32).reshape(0, self._expected_dim)
        if self._use_hf:
            # Chunk to respect HF payload / rate limits
            chunk_size = int(os.getenv("HF_EMBED_CHUNK_SIZE", "16"))
            parts: list[np.ndarray] = []
            for start in range(0, len(texts), chunk_size):
                chunk = texts[start : start + chunk_size]
                parts.append(self._hf_embed_chunk(chunk))
                if start + chunk_size < len(texts):
                    time.sleep(float(os.getenv("HF_EMBED_DELAY_SEC", "0.1")))
            return np.vstack(parts)
        m = self._ensure_model()
        embeddings = m.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,
        )
        return np.array(embeddings, dtype=np.float32)

    def encode_query(self, query: str) -> np.ndarray:
        if self._use_hf:
            return self._hf_embed_single(query)
        v = self.encode([query])[0]
        if v.shape[0] != self._expected_dim:
            raise ValueError(
                f"Query embedding length {v.shape[0]} != expected {self._expected_dim}"
            )
        return v

    def warm(self) -> None:
        if self._use_hf:
            try:
                self._hf_embed_single("warmup")
            except Exception as e:
                logger.warning("HF warm: %s", e)
        else:
            self._ensure_model()
