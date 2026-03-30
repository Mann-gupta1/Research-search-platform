#!/usr/bin/env python3
"""
Insert ~50 synthetic patent/paper records into Milvus + metadata DB for UI demos.

Uses the same env as the backend: MILVUS_URI/MILVUS_TOKEN or MILVUS_HOST/PORT,
DATABASE_URL or SQLITE_DB_PATH, EMBEDDING_MODEL.

Usage (from repo root):
  cd backend
  set PYTHONPATH=.
  python ../scripts/seed_demo_50.py

Or with env file / exports for Render + Zilliz + Postgres.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

_BACKEND_ROOT = os.path.join(os.path.dirname(__file__), "..", "backend")
sys.path.insert(0, _BACKEND_ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(_BACKEND_ROOT, ".env"))
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Varied technical snippets so semantic search returns sensible clusters
_DEMOS: list[dict] = [
    {
        "title": "Thermal management system for lithium-ion battery packs",
        "abstract": "A battery pack assembly with phase change materials and liquid cooling channels to limit cell temperature during fast charging cycles.",
        "doc_type": "patent",
        "tags": ["batteries", "thermal", "EV"],
    },
    {
        "title": "Solid-state electrolyte interface for sodium-ion cells",
        "abstract": "Composite polymer electrolyte with improved ionic conductivity and dendrite suppression for next-generation sodium batteries.",
        "doc_type": "paper",
        "tags": ["batteries", "materials"],
    },
    {
        "title": "Transformer architectures for protein structure prediction",
        "abstract": "We present a deep learning model using attention mechanisms to predict 3D coordinates from amino acid sequences with improved accuracy.",
        "doc_type": "paper",
        "tags": ["ML", "biology"],
    },
    {
        "title": "Federated learning for hospital-grade ECG classification",
        "abstract": "Privacy-preserving federated training across institutions without centralizing raw patient electrocardiogram data.",
        "doc_type": "paper",
        "tags": ["ML", "healthcare", "privacy"],
    },
    {
        "title": "Method for defect detection on semiconductor wafers using CNNs",
        "abstract": "Convolutional neural network pipeline for inline wafer inspection with sub-micron defect localization.",
        "doc_type": "patent",
        "tags": ["ML", "manufacturing"],
    },
    {
        "title": "Graph neural networks for molecular property estimation",
        "abstract": "Message-passing networks on molecular graphs to predict solubility and toxicity with limited labeled data.",
        "doc_type": "paper",
        "tags": ["ML", "chemistry"],
    },
    {
        "title": "High-entropy alloy coatings for turbine blades",
        "abstract": "Multicomponent alloy design improving creep resistance and oxidation behavior in gas turbine hot sections.",
        "doc_type": "patent",
        "tags": ["materials", "aerospace"],
    },
    {
        "title": "Perovskite tandem solar cells with textured interconnect",
        "abstract": "Two-terminal tandem stack achieving higher efficiency through optimized bandgap grading and light trapping.",
        "doc_type": "paper",
        "tags": ["solar", "materials"],
    },
    {
        "title": "Reinforcement learning for adaptive traffic signal control",
        "abstract": "Multi-agent RL coordinating intersections to reduce congestion using simulated urban mobility datasets.",
        "doc_type": "paper",
        "tags": ["ML", "transport"],
    },
    {
        "title": "Quantum error mitigation via zero-noise extrapolation",
        "abstract": "Techniques to estimate noiseless expectation values on NISQ hardware using scaled noise circuits.",
        "doc_type": "paper",
        "tags": ["quantum", "physics"],
    },
]


def _expand_to_n(seed_rows: list[dict], n: int) -> list[dict]:
    """Cycle and vary titles so we have exactly n unique docs."""
    out: list[dict] = []
    years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
    for i in range(n):
        base = seed_rows[i % len(seed_rows)].copy()
        base["title"] = f"{base['title']} (variant {i+1})"
        base["abstract"] = (
            base["abstract"]
            + f" Additional context block {i+1} discusses scalability and experimental validation."
        )
        y = years[i % len(years)]
        m = (i % 12) + 1
        d = (i % 28) + 1
        base["publication_date"] = f"{y}-{m:02d}-{d:02d}"
        base["citation_count"] = (i * 7 + 3) % 200
        out.append(base)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed ~50 demo documents")
    parser.add_argument(
        "--count",
        type=int,
        default=50,
        help="Number of documents (default 50)",
    )
    args = parser.parse_args()

    from app.config import settings
    from app.db.metadata_store import MetadataStore
    from app.db.milvus_client import MilvusClient
    from app.services.embedding import EmbeddingService

    n = max(1, min(args.count, 500))
    rows = _expand_to_n(_DEMOS, n)

    docs: list[dict] = []
    for i, r in enumerate(rows):
        doc_id = f"demo_seed_{i+1:03d}"
        dt = r["doc_type"]
        docs.append(
            {
                "doc_id": doc_id,
                "title": r["title"],
                "abstract": r["abstract"],
                "doc_type": dt,
                "publication_date": r["publication_date"],
                "citation_count": r["citation_count"],
                "tags": json.dumps(r["tags"]),
                "source_url": f"https://example.com/doc/{doc_id}",
            }
        )

    logger.info("Embedding %d abstracts with %s ...", n, settings.embedding_model)
    emb = EmbeddingService(settings.embedding_model, eager=True)
    abstracts = [d["abstract"] for d in docs]
    vectors = emb.encode(abstracts)

    logger.info("Connecting to Milvus and metadata store ...")
    milvus = MilvusClient()
    store = MetadataStore(
        settings.sqlite_db_path,
        database_url=settings.database_url,
    )

    try:
        milvus.insert(
            [d["doc_id"] for d in docs],
            [d["doc_type"] for d in docs],
            vectors.tolist(),
        )
        store.insert_batch(docs)
        logger.info("Inserted %d vectors into Milvus and %d rows into metadata DB.", n, n)
    finally:
        milvus.close()
        store.close()


if __name__ == "__main__":
    main()
