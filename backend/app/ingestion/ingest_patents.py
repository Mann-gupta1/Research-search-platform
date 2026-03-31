"""
Ingest patent abstracts from PatentsView bulk data (TSV format).

Download from: https://patentsview.org/download/data-download-tables
File: g_patent_abstract.tsv
"""

import csv
import json
import logging
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import settings
from app.db.metadata_store import MetadataStore
from app.db.milvus_client import MilvusClient
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

PATENTS_TSV_URL = "https://s3.amazonaws.com/data.patentsview.org/download/g_patent_abstract.tsv.zip"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
MAX_ROWS = 50000
BATCH_SIZE = 500


def download_patents_data(data_dir: str) -> str:
    os.makedirs(data_dir, exist_ok=True)
    zip_path = os.path.join(data_dir, "g_patent_abstract.tsv.zip")
    tsv_path = os.path.join(data_dir, "g_patent_abstract.tsv")

    if os.path.exists(tsv_path):
        logger.info("TSV file already exists at %s", tsv_path)
        return tsv_path

    logger.info("Downloading patent abstracts from %s", PATENTS_TSV_URL)
    response = requests.get(PATENTS_TSV_URL, stream=True, timeout=300)
    response.raise_for_status()

    with open(zip_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    import zipfile
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(data_dir)

    logger.info("Downloaded and extracted to %s", tsv_path)
    return tsv_path


def parse_patents(tsv_path: str, max_rows: int = MAX_ROWS) -> list[dict]:
    logger.info("Parsing patents from %s (max %d rows)", tsv_path, max_rows)
    patents = []

    with open(tsv_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for i, row in enumerate(reader):
            if i >= max_rows:
                break
            patent_id = row.get("patent_id", "").strip()
            abstract = row.get("patent_abstract", "").strip()
            if not patent_id or not abstract or len(abstract) < 50:
                continue

            patents.append({
                "doc_id": f"patent_{patent_id}",
                "title": f"Patent {patent_id}",
                "abstract": abstract[:2000],
                "doc_type": "patent",
                "publication_date": row.get("patent_date", ""),
                "citation_count": 0,
                "tags": json.dumps([]),
                "source_url": f"https://patents.google.com/patent/US{patent_id}",
            })

    logger.info("Parsed %d patents", len(patents))
    return patents


def ingest_patents():
    tsv_path = download_patents_data(DATA_DIR)
    patents = parse_patents(tsv_path)

    if not patents:
        logger.warning("No patents to ingest")
        return

    embedding_service = EmbeddingService(
        settings.embedding_model,
        eager=True,
        hf_token=settings.huggingfacehub_api_token,
        embedding_backend=settings.embedding_backend,
        hf_inference_url=settings.hf_inference_url,
    )
    milvus_client = MilvusClient()
    metadata_store = MetadataStore(
        settings.sqlite_db_path,
        database_url=settings.database_url,
    )

    try:
        for start in range(0, len(patents), BATCH_SIZE):
            batch = patents[start : start + BATCH_SIZE]
            abstracts = [p["abstract"] for p in batch]
            embeddings = embedding_service.encode(abstracts)

            doc_ids = [p["doc_id"] for p in batch]
            doc_types = [p["doc_type"] for p in batch]
            emb_list = embeddings.tolist()

            milvus_client.insert(doc_ids, doc_types, emb_list)
            metadata_store.insert_batch(batch)
            logger.info(
                "Ingested patent batch %d-%d / %d",
                start,
                start + len(batch),
                len(patents),
            )

        logger.info("Patent ingestion complete: %d documents", len(patents))
    finally:
        milvus_client.close()
        metadata_store.close()


if __name__ == "__main__":
    ingest_patents()
